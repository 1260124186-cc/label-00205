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

from typing import Dict, Type, Any, Optional, Callable, TypeVar, Generic
from functools import wraps
from dataclasses import dataclass
from enum import Enum
import inspect
from loguru import logger


class Lifetime(Enum):
    """服务生命周期"""
    SINGLETON = "singleton"  # 单例
    TRANSIENT = "transient"  # 瞬态（每次创建新实例）
    SCOPED = "scoped"        # 作用域（在同一作用域内共享）


@dataclass
class ServiceDescriptor:
    """
    服务描述符
    
    Attributes:
        service_type: 服务类型
        implementation: 实现类或工厂函数
        lifetime: 生命周期
        instance: 单例实例（如果适用）
    """
    service_type: Type
    implementation: Any
    lifetime: Lifetime
    instance: Optional[Any] = None


T = TypeVar('T')


class Container:
    """
    依赖注入容器
    
    管理服务注册和解析。
    
    Attributes:
        _services: 服务描述符字典
        _scoped_instances: 作用域实例字典
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
        self._scoped_instances: Dict[str, Any] = {}
        self._initialized = True
        
        logger.debug("依赖注入容器初始化完成")
    
    def register(
        self,
        name: str,
        implementation: Any,
        lifetime: Lifetime = Lifetime.SINGLETON
    ) -> 'Container':
        """
        注册服务
        
        Args:
            name: 服务名称
            implementation: 实现类或工厂函数
            lifetime: 生命周期
            
        Returns:
            self (支持链式调用)
        """
        service_type = implementation if isinstance(implementation, type) else type(implementation)
        
        self._services[name] = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=lifetime,
            instance=None
        )
        
        logger.debug(f"注册服务: {name} -> {service_type.__name__} ({lifetime.value})")
        
        return self
    
    def register_singleton(self, name: str, implementation: Any) -> 'Container':
        """注册单例服务"""
        return self.register(name, implementation, Lifetime.SINGLETON)
    
    def register_transient(self, name: str, implementation: Any) -> 'Container':
        """注册瞬态服务"""
        return self.register(name, implementation, Lifetime.TRANSIENT)
    
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
            instance=instance
        )
        
        return self
    
    def resolve(self, name: str) -> Any:
        """
        解析服务
        
        Args:
            name: 服务名称
            
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
                descriptor.instance = self._create_instance(descriptor)
            return descriptor.instance
        
        # 瞬态 - 每次创建新实例
        elif descriptor.lifetime == Lifetime.TRANSIENT:
            return self._create_instance(descriptor)
        
        # 作用域 - 在同一作用域内共享
        elif descriptor.lifetime == Lifetime.SCOPED:
            if name not in self._scoped_instances:
                self._scoped_instances[name] = self._create_instance(descriptor)
            return self._scoped_instances[name]
        
        return self._create_instance(descriptor)
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """
        创建服务实例
        
        自动解析构造函数依赖。
        """
        impl = descriptor.implementation
        
        # 如果是类，尝试自动注入依赖
        if isinstance(impl, type):
            # 获取构造函数签名
            sig = inspect.signature(impl.__init__)
            params = sig.parameters
            
            kwargs = {}
            for param_name, param in params.items():
                if param_name == 'self':
                    continue
                
                # 尝试解析依赖
                if param_name in self._services:
                    kwargs[param_name] = self.resolve(param_name)
            
            return impl(**kwargs)
        
        # 如果是可调用对象（工厂函数）
        elif callable(impl):
            return impl()
        
        # 直接返回
        return impl
    
    def get(self, name: str, default: Any = None) -> Any:
        """
        安全获取服务
        
        Args:
            name: 服务名称
            default: 默认值
            
        Returns:
            服务实例或默认值
        """
        try:
            return self.resolve(name)
        except KeyError:
            return default
    
    def has(self, name: str) -> bool:
        """检查服务是否已注册"""
        return name in self._services
    
    def clear_scoped(self) -> None:
        """清除作用域实例"""
        self._scoped_instances.clear()
    
    def reset(self) -> None:
        """重置容器"""
        self._services.clear()
        self._scoped_instances.clear()


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
                # 尝试从容器解析
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
        注册所有服务
        
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
        
        logger.info("服务注册完成")


# 全局容器实例
container = Container()
