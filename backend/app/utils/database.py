"""
数据库连接模块

负责管理MySQL数据库连接，使用SQLAlchemy作为ORM框架。

主要功能:
1. 数据库连接池管理
2. 会话管理
3. 数据表模型定义
4. 常用查询方法

使用示例:
    from app.utils.database import get_db, BoltData
    
    with get_db() as db:
        data = db.query(BoltData).limit(100).all()
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional, List

from sqlalchemy import create_engine, Column, BigInteger, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from app.utils.config import config

# 创建基类
Base = declarative_base()


class BoltData(Base):
    """
    螺栓预紧力数据表模型
    
    对应数据库表: sc_bolt_data
    存储采集的螺栓预紧力原始数据
    
    Attributes:
        id: 主键，自增长
        sensor_id: 通道ID/螺栓ID
        collector_id: 采集器ID
        splitter_num: 分线器ID
        position: 安装位置
        ptf: 预紧力值
        create_time: 创建时间
    """
    __tablename__ = 'sc_bolt_data'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id = Column(BigInteger, nullable=False, comment='通道ID/螺栓ID')
    collector_id = Column(BigInteger, comment='采集器ID')
    splitter_num = Column(BigInteger, comment='分线器ID')
    position = Column(String(200), comment='安装位置')
    ptf = Column(Float, comment='预紧力')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    
    # 索引
    __table_args__ = (
        Index('idx_sensor_time', 'sensor_id', 'create_time'),
    )
    
    @property
    def flange_id(self) -> str:
        """
        获取法兰面ID
        
        法兰面ID由采集器ID、分线器ID和安装位置拼接而成
        
        Returns:
            str: 法兰面ID
        """
        return f"{self.collector_id}-{self.splitter_num}-{self.position}"


class AbnormalPrediction(Base):
    """
    异常预测结果表模型
    
    对应数据库表: sci_abnormal_prediction
    存储模型预测的异常结果
    
    Attributes:
        id: 主键，自增长
        bolt_id: 螺栓编码
        flm_id: 法兰面组编码
        node_type: 节点类型（螺栓/法兰面）
        year_month: 年月
        pw_type: 预警预测类型
        begin_time: 预计发生起始时间
        end_time: 预计发生结束时间
        confidence: 预测置信度
        rec_measures: 推荐措施
        recent_time: 状态时间
        create_time: 创建时间
    """
    __tablename__ = 'sci_abnormal_prediction'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bolt_id = Column(BigInteger, comment='螺栓编码')
    flm_id = Column(String(100), comment='法兰面组编码')
    node_type = Column(String(6), comment='节点类型')
    year_month = Column(String(6), comment='年月')
    pw_type = Column(String(10), comment='预警预测类型')
    begin_time = Column(DateTime, comment='预计发生起始时间')
    end_time = Column(DateTime, comment='预计发生结束时间')
    confidence = Column(Float, comment='预测置信度')
    rec_measures = Column(String(1000), comment='推荐措施')
    recent_time = Column(DateTime, comment='状态时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    
    # 索引
    __table_args__ = (
        Index('idx_node_type', 'node_type'),
        Index('idx_bolt_id', 'bolt_id'),
        Index('idx_flm_id', 'flm_id'),
    )


class MonthPrediction(Base):
    """
    月度预测结果表模型
    
    对应数据库表: ci_month_prediction_details
    存储未来30天的预测结果
    
    Attributes:
        与AbnormalPrediction相同
    """
    __tablename__ = 'ci_month_prediction_details'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bolt_id = Column(BigInteger, comment='螺栓编码')
    flm_id = Column(String(100), comment='法兰面组编码')
    node_type = Column(String(6), comment='节点类型')
    year_month = Column(String(6), comment='年月')
    pw_type = Column(String(10), comment='预警预测类型')
    begin_time = Column(DateTime, comment='预计发生起始时间')
    end_time = Column(DateTime, comment='预计发生结束时间')
    confidence = Column(Float, comment='预测置信度')
    rec_measures = Column(String(1000), comment='推荐措施')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')


class DatabaseManager:
    """
    数据库管理器类
    
    单例模式实现，管理数据库连接池和会话。
    支持延迟初始化，数据库不可用时不会阻止应用启动。
    
    Attributes:
        _instance: 单例实例
        _engine: SQLAlchemy引擎
        _session_factory: 会话工厂
        _is_connected: 数据库是否已连接
    """
    
    _instance: Optional['DatabaseManager'] = None
    
    def __new__(cls) -> 'DatabaseManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._is_connected = False
            cls._instance._engine = None
            cls._instance._session_factory = None
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        # 延迟初始化，不在导入时连接数据库
        
    def _init_engine(self) -> bool:
        """
        初始化数据库引擎
        
        Returns:
            bool: 是否连接成功
        """
        if self._is_connected:
            return True
            
        try:
            db_config = config.get('database', {})
            
            # 构建连接URL，添加超时设置
            url = (
                f"mysql+pymysql://{db_config.get('user', 'root')}:"
                f"{db_config.get('password', '')}@"
                f"{db_config.get('host', '127.0.0.1')}:"
                f"{db_config.get('port', 3306)}/"
                f"{db_config.get('database', 'bolt_preload')}?"
                f"charset={db_config.get('charset', 'utf8mb4')}"
            )
            
            self._engine = create_engine(
                url,
                pool_size=db_config.get('pool_size', 5),
                max_overflow=db_config.get('max_overflow', 10),
                pool_recycle=3600,
                pool_pre_ping=True,
                pool_timeout=5,  # 5秒超时
                connect_args={'connect_timeout': 5},
                echo=False
            )
            
            # 测试连接
            with self._engine.connect() as conn:
                conn.execute("SELECT 1")
            
            self._session_factory = sessionmaker(bind=self._engine)
            self._is_connected = True
            logger.info("数据库连接初始化成功")
            return True
            
        except Exception as e:
            logger.warning(f"数据库连接失败（服务将继续运行）: {e}")
            self._is_connected = False
            return False
        
    def get_session(self) -> Optional[Session]:
        """
        获取数据库会话
        
        Returns:
            Session: SQLAlchemy会话对象，如果数据库不可用返回None
        """
        if not self._is_connected:
            self._init_engine()
        
        if self._session_factory is None:
            return None
        return self._session_factory()
    
    def is_connected(self) -> bool:
        """检查数据库是否已连接"""
        return self._is_connected
    
    def create_tables(self) -> None:
        """
        创建所有数据表
        """
        if not self._is_connected:
            self._init_engine()
        
        if self._engine is not None:
            Base.metadata.create_all(self._engine)
            logger.info("数据表创建成功")
        else:
            logger.warning("数据库未连接，跳过表创建")
        
    def close(self) -> None:
        """
        关闭数据库连接
        """
        if self._engine is not None:
            self._engine.dispose()
            self._is_connected = False
            logger.info("数据库连接已关闭")


# 全局数据库管理器（延迟初始化）
db_manager = DatabaseManager()


@contextmanager
def get_db() -> Generator[Optional[Session], None, None]:
    """
    获取数据库会话的上下文管理器
    
    自动处理会话的提交和回滚。
    如果数据库不可用，yield None。
    
    Yields:
        Session: 数据库会话，如果不可用则为None
        
    Example:
        with get_db() as db:
            if db is not None:
                data = db.query(BoltData).all()
    """
    session = db_manager.get_session()
    if session is None:
        yield None
        return
        
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库操作错误: {e}")
        raise
    finally:
        session.close()


def get_bolt_recent_data(sensor_id: int, limit: int = 100) -> List[BoltData]:
    """
    获取螺栓最近的预紧力数据
    
    Args:
        sensor_id: 螺栓/传感器ID
        limit: 获取记录数量，默认100
        
    Returns:
        List[BoltData]: 预紧力数据列表
    """
    with get_db() as db:
        return db.query(BoltData).filter(
            BoltData.sensor_id == sensor_id
        ).order_by(
            BoltData.create_time.desc()
        ).limit(limit).all()


def get_flange_recent_data(flange_id: str, limit_per_bolt: int = 200) -> List[BoltData]:
    """
    获取法兰面所有螺栓最近的预紧力数据
    
    Args:
        flange_id: 法兰面ID (格式: collector_id-splitter_num-position)
        limit_per_bolt: 每个螺栓获取的记录数量，默认200
        
    Returns:
        List[BoltData]: 预紧力数据列表
    """
    parts = flange_id.split('-')
    if len(parts) < 3:
        raise ValueError(f"无效的法兰面ID格式: {flange_id}")
    
    collector_id = int(parts[0])
    splitter_num = int(parts[1])
    position = '-'.join(parts[2:])
    
    with get_db() as db:
        # 使用子查询获取每个螺栓的最近数据
        from sqlalchemy import text
        
        query = text("""
            SELECT id, sensor_id, collector_id, splitter_num, position, ptf, create_time
            FROM (
                SELECT *,
                    @rn := IF(@sensor_id = sensor_id, @rn + 1, 1) as rn,
                    @sensor_id := sensor_id
                FROM (
                    SELECT id, sensor_id, collector_id, splitter_num, position, ptf, create_time
                    FROM sc_bolt_data
                    WHERE collector_id = :collector_id 
                        AND splitter_num = :splitter_num 
                        AND position = :position
                    ORDER BY sensor_id, create_time DESC
                ) sorted,
                (SELECT @rn := 0, @sensor_id := NULL) vars
            ) ranked
            WHERE rn <= :limit_per_bolt
            ORDER BY sensor_id, create_time DESC
        """)
        
        result = db.execute(query, {
            'collector_id': collector_id,
            'splitter_num': splitter_num,
            'position': position,
            'limit_per_bolt': limit_per_bolt
        })
        
        return result.fetchall()
