"""
依赖注入容器模块

实现IoC容器，管理服务的生命周期和依赖关系。

设计模式:
- 依赖注入 (Dependency Injection)
- 服务定位器 (Service Locator)
- 单例模式 (Singleton)

使用示例:
    from app.core.container import Container, inject
    
    container = Container()
    container.register_singleton('db', DatabaseManager)
    
    @inject
    def my_function(db: DatabaseManager):
        pass
"""

from typing import Dict, Type, Any, Optional, Callable, TypeVar, Generic, List
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import inspect
import uuid
from loguru import logger

try:
    from starlette.requests import Request
except ImportError:
    Request = Any  # type: ignore


class Lifetime(Enum):
    """服务生命周期"""
    SINGLETON = "singleton"  # 单例（全局共享）
    TRANSIENT = "transient"  # 瞬态（每次创建新实例）
    SCOPED = "scoped"        # 作用域（在同一作用域内共享，如 per-request）


@dataclass
class ServiceDescriptor:
    """
    服务描述符
    
    Attributes:
        service_type: 服务类型
        implementation: 实现类或工厂函数
        lifetime: 生命周期
        instance: 单例实例（如果适用）
        dispose: 资源释放方法名或可调用对象
    """
    service_type: Type
    implementation: Any
    lifetime: Lifetime
    instance: Optional[Any] = None
    dispose: Optional[Callable[[Any], None]] = None


T = TypeVar('T')


class ScopeContext:
    """作用域上下文，用于管理 per-request 等作用域内的实例"""
    
    def __init__(self, scope_id: str):
        self.scope_id = scope_id
        self._instances: Dict[str, Any] = {}
    
    def get(self, name: str) -> Optional[Any]:
        return self._instances.get(name)
    
    def set(self, name: str, instance: Any) -> None:
        self._instances[name] = instance
    
    def has(self, name: str) -> bool:
        return name in self._instances
    
    def dispose(self, container: 'Container') -> None:
        """释放作用域内的所有实例"""
        for name, instance in self._instances.items():
            try:
                descriptor = container._services.get(name)
                if descriptor and descriptor.dispose:
                    if callable(descriptor.dispose):
                        descriptor.dispose(instance)
                    elif isinstance(descriptor.dispose, str):
                        dispose_method = getattr(instance, descriptor.dispose, None)
                        if callable(dispose_method):
                            dispose_method()
            except Exception as e:
                logger.warning(f"释放作用域实例失败 {name}: {e}")
        self._instances.clear()
        logger.debug(f"作用域 {self.scope_id} 已释放")


class Container:
    """
    依赖注入容器
    
    管理服务注册和解析。支持三种生命周期：
    - SINGLETON: 全局单例，容器内共享
    - TRANSIENT: 每次解析都创建新实例
    - SCOPED: 在同一作用域内共享（如 HTTP 请求）
    
    Attributes:
        _services: 服务描述符字典
        _scopes: 作用域上下文字典 {scope_id: ScopeContext}
        _current_scope_id: 当前作用域ID（用于协程/线程环境）
    """
    
    _instance: Optional['Container'] = None
    
    def __new__(cls) -> 'Container':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        
        self._services: Dict[str, ServiceDescriptor] = {}
        self._scopes: Dict[str, ScopeContext] = {}
        self._initialized = True
        
        logger.debug("依赖注入容器初始化完成")
    
    def register(
        self,
        name: str,
        implementation: Any,
        lifetime: Lifetime = Lifetime.SINGLETON,
        dispose: Optional[Callable[[Any], None]] = None,
    ) -> 'Container':
        """
        注册服务
        
        Args:
            name: 服务名称
            implementation: 实现类或工厂函数
            lifetime: 生命周期
            dispose: 资源释放方法（函数或方法名字符串）
            
        Returns:
            self (支持链式调用)
        """
        service_type = implementation if isinstance(implementation, type) else type(implementation)
        
        self._services[name] = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=lifetime,
            instance=None,
            dispose=dispose,
        )
        
        logger.debug(f"注册服务: {name} -> {service_type.__name__} ({lifetime.value})")
        
        return self
    
    def register_singleton(
        self,
        name: str,
        implementation: Any,
        dispose: Optional[Callable[[Any], None]] = None,
    ) -> 'Container':
        """注册单例服务"""
        return self.register(name, implementation, Lifetime.SINGLETON, dispose)
    
    def register_transient(
        self,
        name: str,
        implementation: Any,
        dispose: Optional[Callable[[Any], None]] = None,
    ) -> 'Container':
        """注册瞬态服务"""
        return self.register(name, implementation, Lifetime.TRANSIENT, dispose)
    
    def register_scoped(
        self,
        name: str,
        implementation: Any,
        dispose: Optional[Callable[[Any], None]] = None,
    ) -> 'Container':
        """注册作用域服务"""
        return self.register(name, implementation, Lifetime.SCOPED, dispose)
    
    def register_instance(self, name: str, instance: Any) -> 'Container':
        """
        注册已创建的实例
        
        Args:
            name: 服务名称
            instance: 服务实例
            
        Returns:
            self
        """
        self._services[name] = ServiceDescriptor(
            service_type=type(instance),
            implementation=type(instance),
            lifetime=Lifetime.SINGLETON,
            instance=instance,
        )
        
        return self
    
    def resolve(self, name: str, scope_id: Optional[str] = None) -> Any:
        """
        解析服务
        
        Args:
            name: 服务名称
            scope_id: 作用域ID（用于 SCOPED 生命周期的服务）
            
        Returns:
            服务实例
            
        Raises:
            KeyError: 服务未注册
        """
        if name not in self._services:
            raise KeyError(f"服务未注册: {name}")
        
        descriptor = self._services[name]
        
        # 单例 - 返回已有实例或创建新实例
        if descriptor.lifetime == Lifetime.SINGLETON:
            if descriptor.instance is None:
                descriptor.instance = self._create_instance(descriptor, scope_id)
            return descriptor.instance
        
        # 瞬态 - 每次创建新实例
        elif descriptor.lifetime == Lifetime.TRANSIENT:
            return self._create_instance(descriptor, scope_id)
        
        # 作用域 - 在同一作用域内共享
        elif descriptor.lifetime == Lifetime.SCOPED:
            if scope_id is None:
                raise ValueError(f"服务 {name} 是作用域服务，必须提供 scope_id")
            
            scope = self._scopes.get(scope_id)
            if scope is None:
                raise ValueError(f"作用域不存在: {scope_id}")
            
            if not scope.has(name):
                scope.set(name, self._create_instance(descriptor, scope_id))
            return scope.get(name)
        
        return self._create_instance(descriptor, scope_id)
    
    def _create_instance(self, descriptor: ServiceDescriptor, scope_id: Optional[str] = None) -> Any:
        """
        创建服务实例
        
        自动解析构造函数依赖。
        """
        impl = descriptor.implementation
        
        # 如果是类，尝试自动注入依赖
        if isinstance(impl, type):
            sig = inspect.signature(impl.__init__)
            params = sig.parameters
            
            kwargs = {}
            for param_name, param in params.items():
                if param_name == 'self':
                    continue
                
                if param_name in self._services:
                    kwargs[param_name] = self.resolve(param_name, scope_id)
            
            return impl(**kwargs)
        
        # 如果是可调用对象（工厂函数）
        elif callable(impl):
            return impl()
        
        # 直接返回
        return impl
    
    def get(self, name: str, default: Any = None, scope_id: Optional[str] = None) -> Any:
        """
        安全获取服务
        
        Args:
            name: 服务名称
            default: 默认值
            scope_id: 作用域ID
            
        Returns:
            服务实例或默认值
        """
        try:
            return self.resolve(name, scope_id)
        except KeyError:
            return default
    
    def has(self, name: str) -> bool:
        """检查服务是否已注册"""
        return name in self._services
    
    # ========== 作用域管理 ==========
    
    def create_scope(self) -> str:
        """
        创建新作用域
        
        Returns:
            作用域ID
        """
        scope_id = str(uuid.uuid4())
        self._scopes[scope_id] = ScopeContext(scope_id)
        logger.debug(f"创建作用域: {scope_id}")
        return scope_id
    
    def dispose_scope(self, scope_id: str) -> None:
        """
        释放作用域
        
        Args:
            scope_id: 作用域ID
        """
        scope = self._scopes.pop(scope_id, None)
        if scope:
            scope.dispose(self)
    
    @contextmanager
    def scope(self):
        """
        作用域上下文管理器
        
        Usage:
            with container.scope() as scope_id:
                service = container.resolve('my_service', scope_id)
        """
        scope_id = self.create_scope()
        try:
            yield scope_id
        finally:
            self.dispose_scope(scope_id)
    
    # ========== 生命周期管理 ==========
    
    def shutdown(self) -> None:
        """
        关闭容器，释放所有资源
        
        按注册的逆序释放所有单例服务和作用域服务。
        """
        logger.info("容器开始关闭，释放资源...")
        
        # 释放所有作用域
        for scope_id in list(self._scopes.keys()):
            try:
                self.dispose_scope(scope_id)
            except Exception as e:
                logger.warning(f"释放作用域失败 {scope_id}: {e}")
        
        # 释放所有单例
        for name in reversed(list(self._services.keys())):
            descriptor = self._services[name]
            if descriptor.lifetime == Lifetime.SINGLETON and descriptor.instance is not None:
                try:
                    if descriptor.dispose:
                        if callable(descriptor.dispose):
                            descriptor.dispose(descriptor.instance)
                        elif isinstance(descriptor.dispose, str):
                            dispose_method = getattr(descriptor.instance, descriptor.dispose, None)
                            if callable(dispose_method):
                                dispose_method()
                    logger.debug(f"已释放单例服务: {name}")
                except Exception as e:
                    logger.warning(f"释放单例服务失败 {name}: {e}")
        
        logger.info("容器关闭完成")
    
    def reset(self) -> None:
        """重置容器（清空所有服务和作用域）"""
        self._services.clear()
        self._scopes.clear()
    
    # ========== FastAPI Depends 支持 ==========
    
    def provider(self, name: str) -> Callable[..., Any]:
        """
        创建 FastAPI Depends 兼容的依赖提供者
        
        Usage:
            # 在路由中
            from app.core.container import container
            from fastapi import Depends
            
            @app.get("/predict")
            def predict(service: PredictionService = Depends(container.provider("prediction_service"))):
                pass
        
        Args:
            name: 服务名称
            
        Returns:
            可用于 FastAPI Depends 的依赖提供者函数
        """
        def _provider(request: Optional[Request] = None) -> Any:
            """
            依赖提供者
            
            尝试从请求作用域获取服务，如果没有请求作用域则使用单例模式解析。
            
            作用域获取优先级:
            1. 从 request.state.scope_id 获取（HTTP 请求上下文）
            2. 从 contextvar 获取（异步任务等上下文）
            3. 使用全局单例
            """
            scope_id = None
            
            if request is not None:
                try:
                    scope_id = getattr(request.state, 'scope_id', None)
                except Exception:
                    pass
            
            if scope_id is None:
                try:
                    from app.middleware import get_current_scope_id
                    scope_id = get_current_scope_id()
                except Exception:
                    pass
            
            return self.resolve(name, scope_id)
        
        return _provider


def inject(func: Callable) -> Callable:
    """
    依赖注入装饰器
    
    自动从容器解析函数参数。
    
    Usage:
        @inject
        def my_function(db: DatabaseManager, config: Config):
            pass
    """
    sig = inspect.signature(func)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        container = Container()
        
        # 获取未提供的参数
        bound = sig.bind_partial(*args, **kwargs)
        
        for param_name, param in sig.parameters.items():
            if param_name not in bound.arguments:
                if container.has(param_name):
                    kwargs[param_name] = container.resolve(param_name)
        
        return func(*args, **kwargs)
    
    return wrapper


class ServiceProvider:
    """
    服务提供者
    
    用于初始化和注册所有服务。
    """
    
    @staticmethod
    def register_services(container: Container) -> None:
        """
        注册所有核心服务
        
        Args:
            container: 容器实例
        """
        from app.utils.config import Config
        from app.services.anomaly_detection import AnomalyDetector
        from app.services.kalman_filter import KalmanFilterService
        from app.services.preprocessing import DataPreprocessor
        from app.services.feature_engineering import FeatureEngineer
        from app.models.risk_model import BayesianRiskModel
        
        # 注册核心服务
        container.register_singleton('config', Config)
        container.register_singleton('anomaly_detector', AnomalyDetector)
        container.register_singleton('kalman_filter', KalmanFilterService)
        container.register_singleton('preprocessor', DataPreprocessor)
        container.register_singleton('feature_engineer', FeatureEngineer)
        container.register_singleton('risk_model', BayesianRiskModel)
        
        logger.info("核心服务注册完成")
    
    @staticmethod
    def register_prediction_services(container: Container) -> None:
        """
        注册预测相关服务
        
        Args:
            container: 容器实例
        """
        from app.services.prediction.orchestrator import PredictionOrchestrator
        from app.services.prediction.repository import PredictionRepository
        from app.services.prediction.rule_classifier import RuleBasedClassifier
        from app.services.prediction.warning_strategy import WarningStrategyPolicy
        from app.services.prediction.strategy_config_service import StrategyConfigService
        from app.services.training_service import TrainingService
        from app.services.prediction_service import PredictionService
        
        # 注册 Repository（作用域，每个请求一个数据库会话）
        container.register_scoped('prediction_repository', PredictionRepository)
        
        # 注册策略服务（单例）
        container.register_singleton('rule_classifier', RuleBasedClassifier)
        container.register_singleton('warning_strategy', WarningStrategyPolicy)
        container.register_singleton('strategy_config_service', StrategyConfigService)
        
        # 注册编排器和服务（单例，内部管理模型缓存）
        container.register_singleton(
            'prediction_orchestrator',
            PredictionOrchestrator,
            dispose='clear_model_cache',
        )
        
        # 注册兼容层 PredictionService
        container.register_singleton(
            'prediction_service',
            PredictionService,
            dispose='clear_model_cache',
        )
        
        # 注册训练服务（单例）
        container.register_singleton('training_service', TrainingService)
        
        logger.info("预测服务注册完成")
    
    @staticmethod
    def register_database_services(container: Container) -> None:
        """
        注册数据库相关服务
        
        Args:
            container: 容器实例
        """
        from app.utils.database import DatabaseManager
        from app.utils.db_pool import DatabasePool
        
        # 注册数据库管理器（单例，关闭时释放连接）
        container.register_singleton(
            'db_manager',
            DatabaseManager,
            dispose='close',
        )
        
        # 注册数据库连接池（单例）
        container.register_singleton(
            'db_pool',
            DatabasePool,
            dispose='close',
        )
        
        logger.info("数据库服务注册完成")
    
    @staticmethod
    def register_all(container: Container) -> None:
        """
        注册所有服务
        
        Args:
            container: 容器实例
        """
        ServiceProvider.register_services(container)
        ServiceProvider.register_database_services(container)
        ServiceProvider.register_prediction_services(container)
        logger.info("所有服务注册完成")


# 全局容器实例
container = Container()
