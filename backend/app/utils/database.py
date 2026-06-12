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

from sqlalchemy import create_engine, Column, BigInteger, String, Float, DateTime, Index, Text, Boolean, Integer
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


# ============================================================
# 告警与通知模块数据表模型
# ============================================================

class AlertRule(Base):
    """
    告警规则表模型
    
    对应数据库表: sc_alert_rules
    定义告警触发条件：等级、节点、静默期、升级策略
    
    Attributes:
        id: 主键
        rule_name: 规则名称
        alert_level: 告警级别 (1=关注, 2=检查, 3=紧急, 4=故障)
        node_type: 节点类型 (bolt/flange/all)
        node_ids: 节点ID列表 (JSON, 空表示全部)
        min_confidence: 最低置信度阈值
        silence_period: 静默期（分钟），同节点同级别在此期间不重复告警
        enable_upgrade: 是否启用自动升级
        upgrade_minutes: 未处理自动升级时间（分钟）
        upgrade_to_level: 升级到的级别
        enabled: 是否启用
        description: 规则描述
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_alert_rules'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_name = Column(String(200), nullable=False, comment='规则名称')
    alert_level = Column(Integer, nullable=False, comment='告警级别 1-4')
    node_type = Column(String(20), default='all', comment='节点类型 bolt/flange/all')
    node_ids = Column(Text, comment='节点ID列表 JSON')
    min_confidence = Column(Float, default=0.0, comment='最低置信度')
    silence_period = Column(Integer, default=30, comment='静默期（分钟）')
    enable_upgrade = Column(Boolean, default=True, comment='是否启用自动升级')
    upgrade_minutes = Column(Integer, default=30, comment='未处理升级时间（分钟）')
    upgrade_to_level = Column(Integer, comment='升级到的级别')
    enabled = Column(Boolean, default=True, comment='是否启用')
    description = Column(String(500), comment='规则描述')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    __table_args__ = (
        Index('idx_alert_level', 'alert_level'),
        Index('idx_enabled', 'enabled'),
    )


class AlertEvent(Base):
    """
    告警事件表模型
    
    对应数据库表: sc_alert_events
    存储实际产生的告警事件
    
    Attributes:
        id: 主键
        alert_no: 告警编号
        rule_id: 关联规则ID
        alert_level: 当前告警级别
        original_level: 原始告警级别
        node_type: 节点类型
        node_id: 节点ID
        title: 告警标题
        content: 告警内容
        confidence: 置信度
        risk_score: 风险评分
        recommendations: 推荐措施 JSON
        status: 状态 (pending=待处理, processing=处理中, resolved=已解决, ignored=已忽略)
        handler_id: 处理人ID
        handler_name: 处理人姓名
        handle_time: 处理时间
        handle_note: 处理备注
        is_upgraded: 是否已升级
        upgrade_count: 升级次数
        last_upgrade_time: 最后升级时间
        work_order_id: 关联工单ID
        source_prediction_id: 来源预测记录ID
        silence_until: 静默截止时间
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_alert_events'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    alert_no = Column(String(50), unique=True, comment='告警编号')
    rule_id = Column(BigInteger, comment='关联规则ID')
    alert_level = Column(Integer, nullable=False, comment='当前告警级别')
    original_level = Column(Integer, comment='原始告警级别')
    node_type = Column(String(20), comment='节点类型')
    node_id = Column(String(100), comment='节点ID')
    title = Column(String(200), comment='告警标题')
    content = Column(Text, comment='告警内容')
    confidence = Column(Float, comment='置信度')
    risk_score = Column(Float, comment='风险评分')
    recommendations = Column(Text, comment='推荐措施 JSON')
    status = Column(String(20), default='pending', comment='状态 pending/processing/resolved/ignored')
    handler_id = Column(String(50), comment='处理人ID')
    handler_name = Column(String(100), comment='处理人姓名')
    handle_time = Column(DateTime, comment='处理时间')
    handle_note = Column(Text, comment='处理备注')
    is_upgraded = Column(Boolean, default=False, comment='是否已升级')
    upgrade_count = Column(Integer, default=0, comment='升级次数')
    last_upgrade_time = Column(DateTime, comment='最后升级时间')
    work_order_id = Column(BigInteger, comment='关联工单ID')
    source_prediction_id = Column(BigInteger, comment='来源预测记录ID')
    silence_until = Column(DateTime, comment='静默截止时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_level', 'alert_level'),
        Index('idx_node', 'node_type', 'node_id'),
        Index('idx_create_time', 'create_time'),
    )


class AlertSubscription(Base):
    """
    告警订阅管理表模型
    
    对应数据库表: sc_alert_subscriptions
    按角色/装置订阅不同级别的告警
    
    Attributes:
        id: 主键
        subscriber_type: 订阅者类型 (role/user/device)
        subscriber_id: 订阅者ID (角色ID/用户ID/装置ID)
        subscriber_name: 订阅者名称
        min_alert_level: 最低订阅级别 (1-4)
        alert_levels: 订阅的告警级别列表 JSON (如 [3,4] 表示只订阅紧急和故障)
        node_type: 节点类型过滤 (bolt/flange/all)
        node_ids: 节点ID列表 JSON (空表示全部)
        notify_channels: 通知渠道 JSON (如 ["email", "sms", "webhook"])
        notify_targets: 通知目标 JSON (如 {"email": ["a@b.com"], "sms": ["138xxxx"]})
        enabled: 是否启用
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_alert_subscriptions'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subscriber_type = Column(String(20), nullable=False, comment='订阅者类型 role/user/device')
    subscriber_id = Column(String(100), nullable=False, comment='订阅者ID')
    subscriber_name = Column(String(200), comment='订阅者名称')
    min_alert_level = Column(Integer, default=1, comment='最低订阅级别')
    alert_levels = Column(Text, comment='订阅的告警级别列表 JSON')
    node_type = Column(String(20), default='all', comment='节点类型过滤')
    node_ids = Column(Text, comment='节点ID列表 JSON')
    notify_channels = Column(Text, comment='通知渠道 JSON')
    notify_targets = Column(Text, comment='通知目标 JSON')
    enabled = Column(Boolean, default=True, comment='是否启用')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    __table_args__ = (
        Index('idx_subscriber', 'subscriber_type', 'subscriber_id'),
        Index('idx_enabled', 'enabled'),
    )


class NotificationChannel(Base):
    """
    通知渠道配置表模型
    
    对应数据库表: sc_notification_channels
    配置各类通知渠道的参数
    
    Attributes:
        id: 主键
        channel_type: 渠道类型 (email/sms/webhook/dingtalk/wechat)
        channel_name: 渠道名称
        config: 渠道配置 JSON
        enabled: 是否启用
        is_default: 是否为默认渠道
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_notification_channels'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    channel_type = Column(String(50), nullable=False, comment='渠道类型')
    channel_name = Column(String(200), comment='渠道名称')
    config = Column(Text, comment='渠道配置 JSON')
    enabled = Column(Boolean, default=True, comment='是否启用')
    is_default = Column(Boolean, default=False, comment='是否默认渠道')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    __table_args__ = (
        Index('idx_channel_type', 'channel_type'),
    )


class NotificationLog(Base):
    """
    通知发送日志表模型
    
    对应数据库表: sc_notification_logs
    记录每次通知发送结果
    
    Attributes:
        id: 主键
        alert_id: 关联告警ID
        channel_type: 通知渠道
        subscriber_id: 接收者ID
        subscriber_name: 接收者名称
        target: 发送目标 (邮箱/手机号/URL)
        title: 通知标题
        content: 通知内容
        status: 发送状态 (success/failed/pending)
        error_message: 错误信息
        retry_count: 重试次数
        send_time: 发送时间
    """
    __tablename__ = 'sc_notification_logs'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    alert_id = Column(BigInteger, comment='关联告警ID')
    channel_type = Column(String(50), comment='通知渠道')
    subscriber_id = Column(String(100), comment='接收者ID')
    subscriber_name = Column(String(200), comment='接收者名称')
    target = Column(String(500), comment='发送目标')
    title = Column(String(200), comment='通知标题')
    content = Column(Text, comment='通知内容')
    status = Column(String(20), default='pending', comment='发送状态')
    error_message = Column(Text, comment='错误信息')
    retry_count = Column(Integer, default=0, comment='重试次数')
    send_time = Column(DateTime, default=datetime.now, comment='发送时间')
    
    __table_args__ = (
        Index('idx_alert_id', 'alert_id'),
        Index('idx_status', 'status'),
    )


class WorkOrder(Base):
    """
    工单表模型
    
    对应数据库表: sc_work_orders
    与告警联动，紧急预警自动建单
    
    Attributes:
        id: 主键
        order_no: 工单编号
        alert_id: 关联告警ID
        title: 工单标题
        description: 工单描述
        priority: 优先级 (low/medium/high/urgent)
        status: 状态 (open/assigned/in_progress/resolved/closed)
        node_type: 节点类型
        node_id: 节点ID
        alert_level: 告警级别
        risk_score: 风险评分
        assignee_id: 指派处理人ID
        assignee_name: 指派处理人姓名
        creator_id: 创建人ID
        creator_name: 创建人姓名
        due_time: 截止时间
        resolve_time: 解决时间
        resolve_note: 解决备注
        recommendations: 推荐措施 JSON
        extra_info: 扩展信息 JSON
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_work_orders'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True, comment='工单编号')
    alert_id = Column(BigInteger, comment='关联告警ID')
    title = Column(String(200), nullable=False, comment='工单标题')
    description = Column(Text, comment='工单描述')
    priority = Column(String(20), default='medium', comment='优先级')
    status = Column(String(20), default='open', comment='状态')
    node_type = Column(String(20), comment='节点类型')
    node_id = Column(String(100), comment='节点ID')
    alert_level = Column(Integer, comment='告警级别')
    risk_score = Column(Float, comment='风险评分')
    assignee_id = Column(String(50), comment='处理人ID')
    assignee_name = Column(String(100), comment='处理人姓名')
    creator_id = Column(String(50), comment='创建人ID')
    creator_name = Column(String(100), comment='创建人姓名')
    due_time = Column(DateTime, comment='截止时间')
    resolve_time = Column(DateTime, comment='解决时间')
    resolve_note = Column(Text, comment='解决备注')
    recommendations = Column(Text, comment='推荐措施 JSON')
    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_priority', 'priority'),
        Index('idx_alert_id', 'alert_id'),
        Index('idx_assignee', 'assignee_id'),
        Index('idx_create_time', 'create_time'),
    )


class PredictionAudit(Base):
    """
    预测审计快照表模型

    对应数据库表: sc_prediction_audit
    每次预测完整快照：输入哈希、模型版本、特征摘要、中间结果、最终决策、策略版本。
    保留 N 年可配置。
    """
    __tablename__ = 'sc_prediction_audit'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    prediction_id = Column(String(64), nullable=False, comment='预测唯一ID (UUID)')
    node_type = Column(String(20), nullable=False, comment='节点类型 bolt/flange')
    node_id = Column(String(100), nullable=False, comment='节点ID')
    input_hash = Column(String(64), comment='输入数据SHA256哈希')
    model_version = Column(String(50), comment='模型版本号')
    model_type = Column(String(20), comment='模型类型 lstm/rule/attention')
    feature_summary = Column(Text, comment='特征摘要 JSON: mean/std/min/max/count')
    intermediate_results = Column(Text, comment='中间结果 JSON: 预处理/模型原始输出/风险评估')
    final_decision = Column(Text, comment='最终决策 JSON: status_code/status/confidence/risk_score')
    strategy_version = Column(String(50), comment='预警策略版本')
    strategy_type = Column(Integer, comment='策略类型 1=应报尽报 2=精准报警')
    explainability = Column(Text, comment='可解释性报告 JSON: attention/key_timesteps/factors/rules')
    retention_years = Column(Integer, default=3, comment='保留年限')
    expire_time = Column(DateTime, comment='过期时间 (create_time + retention_years)')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_audit_node', 'node_type', 'node_id'),
        Index('idx_audit_time', 'create_time'),
        Index('idx_audit_expire', 'expire_time'),
        Index('idx_audit_model_version', 'model_version'),
    )


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
