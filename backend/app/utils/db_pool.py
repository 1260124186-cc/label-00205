"""
数据库连接池管理模块

提供高性能的数据库连接池管理功能。

功能:
1. 连接池管理
2. 自动重试机制
3. 连接健康检查
4. 连接泄漏检测

使用示例:
    from app.utils.db_pool import DatabasePool
    
    pool = DatabasePool()
    with pool.get_connection() as conn:
        result = conn.execute(query)
"""

import time
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from loguru import logger

from app.utils.config import config


@dataclass
class ConnectionStats:
    """
    连接统计信息
    
    Attributes:
        total_connections: 总连接数
        active_connections: 活动连接数
        idle_connections: 空闲连接数
        overflow_connections: 溢出连接数
        checkout_count: 获取次数
        checkin_count: 归还次数
        invalidated_count: 失效连接数
    """
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    overflow_connections: int = 0
    checkout_count: int = 0
    checkin_count: int = 0
    invalidated_count: int = 0


class RetryPolicy:
    """
    重试策略
    
    Attributes:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数退避基数
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, attempt: int) -> float:
        """
        获取重试延迟
        
        Args:
            attempt: 当前尝试次数（从0开始）
            
        Returns:
            float: 延迟秒数
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """
        判断是否应该重试
        
        Args:
            attempt: 当前尝试次数
            error: 发生的错误
            
        Returns:
            bool: 是否重试
        """
        if attempt >= self.max_retries:
            return False
        
        # 只对连接错误重试
        if isinstance(error, OperationalError):
            return True
        
        return False


class DatabasePool:
    """
    数据库连接池
    
    基于SQLAlchemy的连接池管理器。
    
    Attributes:
        engine: SQLAlchemy引擎
        session_factory: Session工厂
        stats: 连接统计
    """
    
    _instance: Optional['DatabasePool'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'DatabasePool':
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化连接池"""
        if getattr(self, '_initialized', False):
            return
        
        db_config = config.get('database', {})
        
        # 构建连接URL
        self.db_url = self._build_url(db_config)
        
        # 连接池配置
        pool_config = {
            'pool_size': db_config.get('pool_size', 10),
            'max_overflow': db_config.get('max_overflow', 20),
            'pool_timeout': db_config.get('pool_timeout', 30),
            'pool_recycle': db_config.get('pool_recycle', 1800),
            'pool_pre_ping': True,  # 检查连接是否有效
        }
        
        # 重试策略
        self.retry_policy = RetryPolicy(
            max_retries=db_config.get('max_retries', 3),
            base_delay=0.5
        )
        
        # 创建引擎
        self.engine = None
        self.session_factory = None
        self.stats = ConnectionStats()
        
        self._pool_config = pool_config
        self._initialized = True
        self._healthy = False
        
        logger.info(f"数据库连接池配置完成: pool_size={pool_config['pool_size']}")
    
    def _build_url(self, db_config: Dict) -> str:
        """构建数据库连接URL"""
        host = db_config.get('host', '127.0.0.1')
        port = db_config.get('port', 3306)
        user = db_config.get('user', 'root')
        password = db_config.get('password', '')
        database = db_config.get('database', 'bolt_preload')
        charset = db_config.get('charset', 'utf8mb4')
        
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"
    
    def _init_engine(self) -> bool:
        """初始化引擎"""
        try:
            self.engine = create_engine(
                self.db_url,
                poolclass=QueuePool,
                **self._pool_config
            )
            
            # 注册事件监听
            self._register_events()
            
            # Session工厂
            self.session_factory = sessionmaker(bind=self.engine)
            
            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._healthy = True
            logger.info("数据库连接池初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            self._healthy = False
            return False
    
    def _register_events(self) -> None:
        """注册连接池事件"""
        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            self.stats.checkout_count += 1
            self.stats.active_connections += 1
        
        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            self.stats.checkin_count += 1
            self.stats.active_connections -= 1
        
        @event.listens_for(self.engine, "invalidate")
        def on_invalidate(dbapi_conn, connection_record, exception):
            self.stats.invalidated_count += 1
            logger.warning(f"连接失效: {exception}")
    
    @contextmanager
    def get_connection(self) -> Generator[Session, None, None]:
        """
        获取数据库连接（带重试）
        
        Yields:
            Session: 数据库会话
        """
        # 延迟初始化
        if self.engine is None:
            if not self._init_engine():
                yield None
                return
        
        session = None
        last_error = None
        
        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                session = self.session_factory()
                yield session
                session.commit()
                return
                
            except OperationalError as e:
                last_error = e
                if session:
                    session.rollback()
                
                if self.retry_policy.should_retry(attempt, e):
                    delay = self.retry_policy.get_delay(attempt)
                    logger.warning(f"数据库操作失败，{delay:.1f}秒后重试 ({attempt + 1}/{self.retry_policy.max_retries})")
                    time.sleep(delay)
                else:
                    break
                    
            except Exception as e:
                last_error = e
                if session:
                    session.rollback()
                break
                
            finally:
                if session:
                    session.close()
        
        logger.error(f"数据库操作最终失败: {last_error}")
        yield None
    
    @contextmanager
    def get_session(self) -> Generator[Optional[Session], None, None]:
        """获取Session的别名方法"""
        with self.get_connection() as session:
            yield session
    
    def execute_with_retry(
        self,
        query: str,
        params: Optional[Dict] = None
    ) -> Optional[Any]:
        """
        执行SQL（带重试）
        
        Args:
            query: SQL语句
            params: 参数
            
        Returns:
            查询结果
        """
        with self.get_connection() as session:
            if session is None:
                return None
            
            try:
                result = session.execute(text(query), params or {})
                return result
            except Exception as e:
                logger.error(f"SQL执行失败: {e}")
                return None
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态
        """
        result = {
            'healthy': False,
            'latency_ms': None,
            'pool_stats': None,
            'error': None
        }
        
        if self.engine is None:
            if not self._init_engine():
                result['error'] = "无法初始化连接池"
                return result
        
        try:
            start = time.time()
            
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            latency = (time.time() - start) * 1000
            
            result['healthy'] = True
            result['latency_ms'] = round(latency, 2)
            result['pool_stats'] = {
                'pool_size': self.engine.pool.size(),
                'checked_in': self.engine.pool.checkedin(),
                'checked_out': self.engine.pool.checkedout(),
                'overflow': self.engine.pool.overflow(),
                'invalidated': self.stats.invalidated_count
            }
            
        except Exception as e:
            result['error'] = str(e)
            self._healthy = False
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        if self.engine is None:
            return {'status': 'not_initialized'}
        
        return {
            'pool_size': self.engine.pool.size(),
            'active': self.engine.pool.checkedout(),
            'idle': self.engine.pool.checkedin(),
            'overflow': self.engine.pool.overflow(),
            'checkout_count': self.stats.checkout_count,
            'checkin_count': self.stats.checkin_count,
            'invalidated': self.stats.invalidated_count
        }
    
    def close(self) -> None:
        """关闭连接池"""
        if self.engine:
            self.engine.dispose()
            logger.info("数据库连接池已关闭")


# 全局连接池实例
db_pool = DatabasePool()
