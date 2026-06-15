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
    fault_type = Column(String(10), comment='故障类型：loosening/overload/fracture/fatigue/corrosion')
    fault_confidence = Column(Float, comment='故障分类置信度')
    fault_evidence = Column(Text, comment='故障证据JSON')
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
    fault_type = Column(String(10), comment='故障类型：loosening/overload/fracture/fatigue/corrosion')
    fault_confidence = Column(Float, comment='故障分类置信度')
    fault_evidence = Column(Text, comment='故障证据JSON')
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
        Index('idx_node', 'node_type', 'node_id'),
        Index('idx_due_time', 'due_time'),
    )


class WorkOrderDisposalRecord(Base):
    """
    工单处置记录表模型

    对应数据库表: sc_work_order_disposals
    存储现场人员上传的处置记录。

    Attributes:
        id: 主键
        work_order_id: 关联工单ID
        disposal_type: 处置类型 (torque_adjustment/replacement/inspection/other)
        disposal_content: 处置内容描述
        disposal_time: 处置时间
        operator_id: 操作人ID
        operator_name: 操作人姓名
        before_value: 处置前值（如预紧力）
        after_value: 处置后值
        materials_used: 使用材料 JSON
        photos: 现场照片URL列表 JSON
        notes: 备注
        extra_info: 扩展信息 JSON
        create_time: 创建时间
    """
    __tablename__ = 'sc_work_order_disposals'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id = Column(BigInteger, nullable=False, comment='关联工单ID')
    disposal_type = Column(String(50), comment='处置类型')
    disposal_content = Column(Text, comment='处置内容描述')
    disposal_time = Column(DateTime, comment='处置时间')
    operator_id = Column(String(50), comment='操作人ID')
    operator_name = Column(String(100), comment='操作人姓名')
    before_value = Column(Float, comment='处置前值')
    after_value = Column(Float, comment='处置后值')
    materials_used = Column(Text, comment='使用材料 JSON')
    photos = Column(Text, comment='现场照片 URL 列表 JSON')
    notes = Column(Text, comment='备注')
    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_disposal_wo', 'work_order_id'),
        Index('idx_disposal_time', 'disposal_time'),
        Index('idx_disposal_operator', 'operator_id'),
    )


class WorkOrderRetestRecord(Base):
    """
    工单复测数据表模型

    对应数据库表: sc_work_order_retests
    存储复测数据及复测结果。

    Attributes:
        id: 主键
        work_order_id: 关联工单ID
        retest_time: 复测时间
        retester_id: 复测人ID
        retester_name: 复测人姓名
        retest_result: 复测结果 (pass/fail/pending)
        measured_value: 复测测量值（如预紧力）
        data_points: 复测数据点 JSON (时序数据)
        before_risk_score: 复测前风险评分
        after_risk_score: 复测后风险评分
        status_after_retest: 复测后状态 (normal/warning/critical)
        confidence: 复测置信度
        retest_notes: 复测备注
        photos: 复测照片 URL 列表 JSON
        extra_info: 扩展信息 JSON
        create_time: 创建时间
    """
    __tablename__ = 'sc_work_order_retests'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id = Column(BigInteger, nullable=False, comment='关联工单ID')
    retest_time = Column(DateTime, comment='复测时间')
    retester_id = Column(String(50), comment='复测人ID')
    retester_name = Column(String(100), comment='复测人姓名')
    retest_result = Column(String(20), comment='复测结果 pass/fail/pending')
    measured_value = Column(Float, comment='复测测量值')
    data_points = Column(Text, comment='复测数据点 JSON')
    before_risk_score = Column(Float, comment='复测前风险评分')
    after_risk_score = Column(Float, comment='复测后风险评分')
    status_after_retest = Column(String(20), comment='复测后状态')
    confidence = Column(Float, comment='复测置信度')
    retest_notes = Column(Text, comment='复测备注')
    photos = Column(Text, comment='复测照片 URL 列表 JSON')
    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_retest_wo', 'work_order_id'),
        Index('idx_retest_time', 'retest_time'),
        Index('idx_retest_result', 'retest_result'),
    )


class WorkOrderPredictionCompare(Base):
    """
    工单复测前后预测对比表模型

    对应数据库表: sc_work_order_pred_compares
    存储复测后重新预测的结果，并与原预测对比。

    Attributes:
        id: 主键
        work_order_id: 关联工单ID
        retest_id: 关联复测记录ID
        original_prediction_id: 原始预测记录ID
        retest_prediction_id: 复测后预测记录ID
        original_status: 原始状态
        retest_status: 复测后状态
        original_risk_score: 原始风险评分
        retest_risk_score: 复测后风险评分
        original_confidence: 原始置信度
        retest_confidence: 复测后置信度
        risk_change: 风险变化 (improved/stable/worsened)
        risk_delta: 风险评分变化值
        status_match: 状态是否一致
        is_false_positive: 是否为误报（原预警正常/改进后正常）
        is_recurring: 是否为重复故障
        comparison_detail: 对比详情 JSON
        create_time: 创建时间
    """
    __tablename__ = 'sc_work_order_pred_compares'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id = Column(BigInteger, nullable=False, comment='关联工单ID')
    retest_id = Column(BigInteger, comment='关联复测记录ID')
    original_prediction_id = Column(BigInteger, comment='原始预测记录ID')
    retest_prediction_id = Column(BigInteger, comment='复测后预测记录ID')
    original_status = Column(String(20), comment='原始状态')
    retest_status = Column(String(20), comment='复测后状态')
    original_risk_score = Column(Float, comment='原始风险评分')
    retest_risk_score = Column(Float, comment='复测后风险评分')
    original_confidence = Column(Float, comment='原始置信度')
    retest_confidence = Column(Float, comment='复测后置信度')
    risk_change = Column(String(20), comment='风险变化 improved/stable/worsened')
    risk_delta = Column(Float, comment='风险评分变化值')
    status_match = Column(Boolean, comment='状态是否一致')
    is_false_positive = Column(Boolean, default=False, comment='是否误报')
    is_recurring = Column(Boolean, default=False, comment='是否重复故障')
    comparison_detail = Column(Text, comment='对比详情 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_compare_wo', 'work_order_id'),
        Index('idx_compare_retest', 'retest_id'),
        Index('idx_compare_false_positive', 'is_false_positive'),
        Index('idx_compare_recurring', 'is_recurring'),
        Index('idx_compare_time', 'create_time'),
    )


class CmmsIntegrationConfig(Base):
    """
    CMMS/EAM 集成配置表模型

    对应数据库表: sc_cmms_configs
    存储第三方 CMMS/EAM 系统的集成配置。

    Attributes:
        id: 主键
        system_name: 系统名称
        system_type: 系统类型 (maximo/sap_eam/infor/eam/other)
        base_url: 系统基础URL
        auth_type: 认证类型 (basic/api_key/oauth2/token)
        auth_config: 认证配置 JSON
        work_order_sync: 是否同步工单
        work_order_webhook_url: 工单Webhook URL
        work_order_push_url: 工单推送URL
        status_mapping: 状态映射 JSON
        priority_mapping: 优先级映射 JSON
        field_mapping: 字段映射 JSON
        enabled: 是否启用
        sync_direction: 同步方向 (push/pull/bidirectional)
        last_sync_time: 最后同步时间
        sync_interval: 同步间隔（分钟）
        tenant_id: 租户ID
        extra_info: 扩展信息 JSON
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_cmms_configs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    system_name = Column(String(200), nullable=False, comment='系统名称')
    system_type = Column(String(50), comment='系统类型')
    base_url = Column(String(500), comment='系统基础URL')
    auth_type = Column(String(30), comment='认证类型')
    auth_config = Column(Text, comment='认证配置 JSON')
    work_order_sync = Column(Boolean, default=False, comment='是否同步工单')
    work_order_webhook_url = Column(String(500), comment='工单Webhook URL')
    work_order_push_url = Column(String(500), comment='工单推送URL')
    status_mapping = Column(Text, comment='状态映射 JSON')
    priority_mapping = Column(Text, comment='优先级映射 JSON')
    field_mapping = Column(Text, comment='字段映射 JSON')
    enabled = Column(Boolean, default=True, comment='是否启用')
    sync_direction = Column(String(20), default='push', comment='同步方向')
    last_sync_time = Column(DateTime, comment='最后同步时间')
    sync_interval = Column(Integer, default=60, comment='同步间隔分钟')
    tenant_id = Column(BigInteger, comment='租户ID')
    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_cmms_enabled', 'enabled'),
        Index('idx_cmms_tenant', 'tenant_id'),
        Index('idx_cmms_type', 'system_type'),
    )


class CmmsSyncLog(Base):
    """
    CMMS/EAM 同步日志表模型

    对应数据库表: sc_cmms_sync_logs
    存储与 CMMS 系统同步的日志记录。

    Attributes:
        id: 主键
        config_id: 关联配置ID
        sync_type: 同步类型 (work_order_create/work_order_update/status_update/pull)
        sync_direction: 同步方向 (push/pull)
        work_order_id: 关联工单ID
        external_id: 外部系统ID
        status: 同步状态 (success/failed/pending)
        request_data: 请求数据 JSON
        response_data: 响应数据 JSON
        error_message: 错误信息
        retry_count: 重试次数
        sync_time: 同步时间
        create_time: 创建时间
    """
    __tablename__ = 'sc_cmms_sync_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_id = Column(BigInteger, comment='关联配置ID')
    sync_type = Column(String(50), comment='同步类型')
    sync_direction = Column(String(20), comment='同步方向 push/pull')
    work_order_id = Column(BigInteger, comment='关联工单ID')
    external_id = Column(String(100), comment='外部系统ID')
    status = Column(String(20), default='pending', comment='同步状态')
    request_data = Column(Text, comment='请求数据 JSON')
    response_data = Column(Text, comment='响应数据 JSON')
    error_message = Column(Text, comment='错误信息')
    retry_count = Column(Integer, default=0, comment='重试次数')
    sync_time = Column(DateTime, comment='同步时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_cmms_log_config', 'config_id'),
        Index('idx_cmms_log_wo', 'work_order_id'),
        Index('idx_cmms_log_status', 'status'),
        Index('idx_cmms_log_time', 'sync_time'),
        Index('idx_cmms_log_external', 'external_id'),
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


class DataQualityCheck(Base):
    """
    数据质量检查表模型

    对应数据库表: sc_data_quality_checks
    存储每次数据质量检查的结果。
    """
    __tablename__ = 'sc_data_quality_checks'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id = Column(String(50), nullable=False, comment='传感器/螺栓ID')
    total_points = Column(Integer, comment='总数据点数')
    valid_points = Column(Integer, comment='有效数据点数')
    overall_score = Column(Float, comment='综合质量评分')
    completeness_score = Column(Float, comment='完整性评分')
    consistency_score = Column(Float, comment='一致性评分')
    validity_score = Column(Float, comment='有效性评分')
    stability_score = Column(Float, comment='稳定性评分')
    rule_scores = Column(Text, comment='各规则评分 JSON')
    violations = Column(Text, comment='规则违反记录 JSON')
    quality_level = Column(String(20), comment='质量等级 excellent/good/fair/poor/critical')
    valid_for_training = Column(Boolean, default=True, comment='是否适合训练')
    confidence_adjustment = Column(Float, default=1.0, comment='置信度调整系数')
    check_time = Column(DateTime, default=datetime.now, comment='检查时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_dqc_sensor', 'sensor_id'),
        Index('idx_dqc_time', 'check_time'),
        Index('idx_dqc_score', 'overall_score'),
        Index('idx_dqc_level', 'quality_level'),
    )


class QualityReport(Base):
    """
    质量报告表模型

    对应数据库表: sc_quality_reports
    存储每日数据质量报告。
    """
    __tablename__ = 'sc_quality_reports'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    report_date = Column(DateTime, nullable=False, comment='报告日期')
    total_sensors = Column(Integer, comment='总传感器数')
    average_score = Column(Float, comment='平均质量评分')
    quality_distribution = Column(Text, comment='质量分布 JSON')
    problem_sensors = Column(Text, comment='问题传感器排行 JSON')
    recommendations = Column(Text, comment='修复建议 JSON')
    anomaly_statistics = Column(Text, comment='异常统计 JSON')
    quality_trend = Column(Text, comment='质量趋势 JSON')
    summary = Column(Text, comment='报告摘要')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_qr_date', 'report_date', unique=True),
        Index('idx_qr_create', 'create_time'),
    )


class Tenant(Base):
    __tablename__ = 'sc_tenants'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_code = Column(String(64), unique=True, nullable=False, comment='租户编码')
    tenant_name = Column(String(200), nullable=False, comment='租户名称')
    contact_email = Column(String(200), comment='联系邮箱')
    contact_phone = Column(String(50), comment='联系电话')
    status = Column(String(20), default='active', comment='状态 active/suspended/deleted')
    settings = Column(Text, comment='租户配置 JSON')
    expire_time = Column(DateTime, comment='到期时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_tenant_code', 'tenant_code'),
        Index('idx_tenant_status', 'status'),
    )


class OrganizationNode(Base):
    __tablename__ = 'sc_org_nodes'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, comment='所属租户ID')
    parent_id = Column(BigInteger, comment='父节点ID')
    node_code = Column(String(100), comment='节点编码')
    node_name = Column(String(200), nullable=False, comment='节点名称')
    node_type = Column(String(20), nullable=False, comment='节点类型 group/factory/unit/flange/bolt')
    path = Column(String(500), comment='层级路径 /id/id/... 用于快速查询祖先')
    level = Column(Integer, default=0, comment='层级深度 0=集团 1=工厂 2=装置 3=法兰面 4=螺栓')
    sort_order = Column(Integer, default=0, comment='排序序号')
    extra_info = Column(Text, comment='扩展信息 JSON')
    status = Column(String(20), default='active', comment='状态 active/inactive')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_org_tenant', 'tenant_id'),
        Index('idx_org_parent', 'parent_id'),
        Index('idx_org_type', 'tenant_id', 'node_type'),
        Index('idx_org_path', 'path'),
    )


class TenantQuota(Base):
    __tablename__ = 'sc_tenant_quotas'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, unique=True, nullable=False, comment='租户ID')
    max_models = Column(Integer, default=10, comment='最大模型数')
    max_api_calls_per_day = Column(Integer, default=10000, comment='每日最大API调用次数')
    max_storage_mb = Column(Integer, default=5120, comment='存储上限 MB')
    max_users = Column(Integer, default=50, comment='最大用户数')
    max_org_nodes = Column(Integer, default=500, comment='最大组织节点数')
    current_model_count = Column(Integer, default=0, comment='当前模型数')
    current_api_calls_today = Column(Integer, default=0, comment='今日API调用次数')
    current_storage_mb = Column(Float, default=0.0, comment='当前存储用量 MB')
    current_user_count = Column(Integer, default=0, comment='当前用户数')
    current_org_node_count = Column(Integer, default=0, comment='当前组织节点数')
    api_call_reset_date = Column(String(10), comment='API调用计数重置日期 YYYY-MM-DD')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_quota_tenant', 'tenant_id'),
    )


class TenantUser(Base):
    __tablename__ = 'sc_tenant_users'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, comment='所属租户ID')
    username = Column(String(100), nullable=False, comment='用户名')
    password_hash = Column(String(128), comment='密码哈希')
    display_name = Column(String(200), comment='显示名称')
    email = Column(String(200), comment='邮箱')
    phone = Column(String(50), comment='手机号')
    role = Column(String(30), default='viewer', comment='角色 tenant_admin/admin/operator/viewer')
    org_node_id = Column(BigInteger, comment='关联组织节点ID')
    status = Column(String(20), default='active', comment='状态 active/disabled')
    last_login_time = Column(DateTime, comment='最后登录时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_user_tenant', 'tenant_id'),
        Index('idx_user_tenant_username', 'tenant_id', 'username', unique=True),
        Index('idx_user_role', 'role'),
    )


class TenantAPIKey(Base):
    __tablename__ = 'sc_tenant_api_keys'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, comment='所属租户ID')
    api_key = Column(String(64), unique=True, nullable=False, comment='API密钥')
    key_name = Column(String(200), comment='密钥名称')
    permissions = Column(Text, comment='权限列表 JSON ["read","write","admin"]')
    rate_limit = Column(Integer, default=1000, comment='速率限制 每分钟')
    user_id = Column(BigInteger, comment='关联用户ID')
    expires_at = Column(DateTime, comment='过期时间')
    last_used_at = Column(DateTime, comment='最后使用时间')
    status = Column(String(20), default='active', comment='状态 active/revoked')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_apikey_tenant', 'tenant_id'),
        Index('idx_apikey_key', 'api_key'),
        Index('idx_apikey_status', 'status'),
    )


class KnowledgeCase(Base):
    """
    知识库案例表模型（CBR - 基于案例的推理）

    对应数据库表: sc_knowledge_cases
    结构化存储历史故障案例：工况、传感器特征、诊断结论、处置方案、效果评估。

    Attributes:
        id: 主键
        case_no: 案例编号
        case_title: 案例标题
        node_type: 节点类型 bolt/flange
        node_id: 节点ID
        fault_type: 故障类型
        fault_level: 故障级别 1-4
        working_condition: 工况描述 JSON
        sensor_features: 传感器特征向量 JSON (58维特征)
        feature_vector: 归一化特征向量 (用于相似度计算，存储为逗号分隔字符串)
        diagnosis: 诊断结论
        root_cause: 根本原因分析
        treatment_plan: 处置方案 JSON
        effect_evaluation: 效果评估 JSON
        effectiveness_score: 效果评分 0-100
        status: 状态 draft/pending_review/approved/rejected
        version: 当前版本号
        tenant_id: 所属租户ID
        creator_id: 创建人ID
        creator_name: 创建人姓名
        reviewer_id: 审核人ID
        reviewer_name: 审核人姓名
        review_time: 审核时间
        review_comment: 审核意见
        source_alert_id: 来源告警ID
        source_prediction_id: 来源预测记录ID
        tags: 标签 JSON
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_knowledge_cases'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_no = Column(String(50), unique=True, nullable=False, comment='案例编号')
    case_title = Column(String(500), nullable=False, comment='案例标题')
    node_type = Column(String(20), comment='节点类型 bolt/flange')
    node_id = Column(String(100), comment='节点ID')
    fault_type = Column(String(100), comment='故障类型')
    fault_level = Column(Integer, comment='故障级别 1-4')
    working_condition = Column(Text, comment='工况描述 JSON')
    sensor_features = Column(Text, comment='传感器特征 JSON (58维特征名+值)')
    feature_vector = Column(Text, comment='归一化特征向量 (逗号分隔字符串)')
    diagnosis = Column(Text, comment='诊断结论')
    root_cause = Column(Text, comment='根本原因分析')
    treatment_plan = Column(Text, comment='处置方案 JSON')
    effect_evaluation = Column(Text, comment='效果评估 JSON')
    effectiveness_score = Column(Float, comment='效果评分 0-100')
    status = Column(String(20), default='draft', comment='状态 draft/pending_review/approved/rejected')
    version = Column(Integer, default=1, comment='当前版本号')
    tenant_id = Column(BigInteger, comment='所属租户ID')
    creator_id = Column(String(50), comment='创建人ID')
    creator_name = Column(String(100), comment='创建人姓名')
    reviewer_id = Column(String(50), comment='审核人ID')
    reviewer_name = Column(String(100), comment='审核人姓名')
    review_time = Column(DateTime, comment='审核时间')
    review_comment = Column(Text, comment='审核意见')
    source_alert_id = Column(BigInteger, comment='来源告警ID')
    source_prediction_id = Column(BigInteger, comment='来源预测记录ID')
    tags = Column(Text, comment='标签 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_case_status', 'status'),
        Index('idx_case_node', 'node_type', 'node_id'),
        Index('idx_case_fault', 'fault_type', 'fault_level'),
        Index('idx_case_tenant', 'tenant_id'),
        Index('idx_case_time', 'create_time'),
        Index('idx_case_effectiveness', 'effectiveness_score'),
    )


class KnowledgeCaseVersion(Base):
    """
    知识库案例版本历史表

    对应数据库表: sc_knowledge_case_versions
    记录案例的每个版本，支持版本回溯和对比。

    Attributes:
        id: 主键
        case_id: 关联案例ID
        version: 版本号
        case_title: 案例标题（该版本）
        diagnosis: 诊断结论（该版本）
        treatment_plan: 处置方案（该版本）
        effect_evaluation: 效果评估（该版本）
        effectiveness_score: 效果评分（该版本）
        feature_vector: 特征向量（该版本）
        change_summary: 变更说明
        operator_id: 操作人ID
        operator_name: 操作人姓名
        create_time: 创建时间
    """
    __tablename__ = 'sc_knowledge_case_versions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, nullable=False, comment='关联案例ID')
    version = Column(Integer, nullable=False, comment='版本号')
    case_title = Column(String(500), comment='案例标题')
    diagnosis = Column(Text, comment='诊断结论')
    root_cause = Column(Text, comment='根本原因分析')
    treatment_plan = Column(Text, comment='处置方案 JSON')
    effect_evaluation = Column(Text, comment='效果评估 JSON')
    effectiveness_score = Column(Float, comment='效果评分')
    feature_vector = Column(Text, comment='特征向量')
    change_summary = Column(String(500), comment='变更说明')
    operator_id = Column(String(50), comment='操作人ID')
    operator_name = Column(String(100), comment='操作人姓名')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_version_case', 'case_id', 'version'),
        Index('idx_version_time', 'create_time'),
    )


class KnowledgeCaseReview(Base):
    """
    知识库案例审核记录表

    对应数据库表: sc_knowledge_case_reviews
    记录案例的审核流程，支持多级审核。

    Attributes:
        id: 主键
        case_id: 关联案例ID
        version: 对应版本号
        review_level: 审核级别 1-3
        reviewer_id: 审核人ID
        reviewer_name: 审核人姓名
        review_result: 审核结果 approved/rejected/revision_required
        review_comment: 审核意见
        create_time: 审核时间
    """
    __tablename__ = 'sc_knowledge_case_reviews'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, nullable=False, comment='关联案例ID')
    version = Column(Integer, comment='对应版本号')
    review_level = Column(Integer, default=1, comment='审核级别 1-3')
    reviewer_id = Column(String(50), comment='审核人ID')
    reviewer_name = Column(String(100), comment='审核人姓名')
    review_result = Column(String(30), comment='审核结果 approved/rejected/revision_required')
    review_comment = Column(Text, comment='审核意见')
    create_time = Column(DateTime, default=datetime.now, comment='审核时间')

    __table_args__ = (
        Index('idx_review_case', 'case_id'),
        Index('idx_review_result', 'review_result'),
        Index('idx_review_time', 'create_time'),
    )


class APIAuditLog(Base):
    __tablename__ = 'sc_api_audit_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    key_id = Column(String(50), comment='API密钥ID')
    key_name = Column(String(200), comment='密钥名称')
    method = Column(String(10), comment='HTTP方法 GET/POST/PUT/DELETE')
    path = Column(String(500), comment='请求路径')
    status_code = Column(Integer, comment='响应状态码')
    client_ip = Column(String(50), comment='客户端IP')
    request_id = Column(String(64), comment='请求ID')
    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_api_audit_key', 'key_id'),
        Index('idx_api_audit_path', 'path'),
        Index('idx_api_audit_status', 'status_code'),
        Index('idx_api_audit_time', 'create_time'),
        Index('idx_api_audit_method', 'method'),
    )


# ============================================================
# 数字孪生与健康度评分模块 ORM 模型
# ============================================================

class BoltHealthHistory(Base):
    """
    螺栓健康度历史表模型

    对应数据库表: sc_bolt_health_history
    存储螺栓每次计算的健康度指数历史记录。

    Attributes:
        id: 主键
        bolt_id: 螺栓ID
        flange_id: 法兰面ID
        hi_score: 综合健康度指数 0-100
        hi_level: 健康等级 excellent/good/fair/poor/critical
        preload_stability_score: 预紧力稳定性得分
        alert_frequency_score: 预警频率得分
        fault_history_score: 故障历史得分
        environmental_stress_score: 环境应力得分
        service_age_score: 使用年限得分
        factors_detail: 各因子得分详情 JSON
        trend: 健康趋势 improving/stable/declining
        trend_rate: 趋势变化率
        current_preload: 当前预紧力
        nominal_preload: 额定预紧力
        preload_deviation: 预紧力偏差率
        last_maintenance_date: 上次维护日期
        working_condition: 工况信息 JSON
        data_source: 数据来源 automatic/manual
        tenant_id: 租户ID
        create_time: 创建时间
    """
    __tablename__ = 'sc_bolt_health_history'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bolt_id = Column(String(50), nullable=False, comment='螺栓ID')
    flange_id = Column(String(100), comment='法兰面ID')
    hi_score = Column(Float, nullable=False, comment='综合健康度指数 0-100')
    hi_level = Column(String(20), nullable=False, comment='健康等级')
    preload_stability_score = Column(Float, comment='预紧力稳定性得分')
    alert_frequency_score = Column(Float, comment='预警频率得分')
    fault_history_score = Column(Float, comment='故障历史得分')
    environmental_stress_score = Column(Float, comment='环境应力得分')
    service_age_score = Column(Float, comment='使用年限得分')
    factors_detail = Column(Text, comment='各因子得分详情 JSON')
    trend = Column(String(20), comment='健康趋势')
    trend_rate = Column(Float, comment='趋势变化率')
    current_preload = Column(Float, comment='当前预紧力')
    nominal_preload = Column(Float, comment='额定预紧力')
    preload_deviation = Column(Float, comment='预紧力偏差率')
    last_maintenance_date = Column(DateTime, comment='上次维护日期')
    working_condition = Column(Text, comment='工况信息 JSON')
    data_source = Column(String(50), default='automatic', comment='数据来源')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_bolt_health_bolt', 'bolt_id'),
        Index('idx_bolt_health_flange', 'flange_id'),
        Index('idx_bolt_health_time', 'create_time'),
        Index('idx_bolt_health_score', 'hi_score'),
        Index('idx_bolt_health_level', 'hi_level'),
    )


class FlangeHealthHistory(Base):
    """
    法兰面健康度历史表模型

    对应数据库表: sc_flange_health_history
    存储法兰面每次计算的健康度指数历史记录。
    """
    __tablename__ = 'sc_flange_health_history'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    flange_id = Column(String(100), nullable=False, comment='法兰面ID')
    hi_score = Column(Float, nullable=False, comment='综合健康度指数 0-100')
    hi_level = Column(String(20), nullable=False, comment='健康等级')
    worst_bolt_hi = Column(Float, comment='最差螺栓健康度')
    worst_bolt_id = Column(String(50), comment='最差螺栓ID')
    average_bolt_hi = Column(Float, comment='平均螺栓健康度')
    median_bolt_hi = Column(Float, comment='螺栓健康度中位数')
    degradation_rate = Column(Float, comment='劣化速率（HI/天）')
    bolt_count = Column(Integer, comment='螺栓总数')
    healthy_bolt_count = Column(Integer, comment='健康螺栓数(HI>=70)')
    warning_bolt_count = Column(Integer, comment='预警螺栓数(50<=HI<70)')
    critical_bolt_count = Column(Integer, comment='危险螺栓数(HI<50)')
    bolts_summary = Column(Text, comment='螺栓健康度摘要 JSON')
    trend = Column(String(20), comment='健康趋势')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_flange_health_flange', 'flange_id'),
        Index('idx_flange_health_time', 'create_time'),
        Index('idx_flange_health_score', 'hi_score'),
    )


class RULPrediction(Base):
    """
    RUL预测结果表模型

    对应数据库表: sc_rul_predictions
    存储剩余使用寿命预测结果。
    """
    __tablename__ = 'sc_rul_predictions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    node_id = Column(String(100), nullable=False, comment='节点ID')
    node_type = Column(String(20), nullable=False, comment='节点类型 bolt/flange')
    current_hi = Column(Float, comment='当前健康度')
    rul_days = Column(Float, comment='预测剩余使用寿命（天）')
    rul_lower_bound = Column(Float, comment='RUL下限（天）')
    rul_upper_bound = Column(Float, comment='RUL上限（天）')
    rul_confidence = Column(Float, comment='RUL预测置信度')
    failure_threshold = Column(Float, default=30, comment='故障阈值 HI')
    warning_threshold = Column(Float, default=50, comment='预警阈值 HI')
    days_to_warning = Column(Float, comment='距离预警的天数')
    historical_hi = Column(Text, comment='历史HI序列 JSON')
    forecast_series = Column(Text, comment='预测序列 JSON')
    degradation_model = Column(String(50), comment='劣化模型类型')
    model_params = Column(Text, comment='模型参数 JSON')
    model_r_squared = Column(Float, comment='模型拟合优度 R²')
    tenant_id = Column(BigInteger, comment='租户ID')
    prediction_date = Column(DateTime, default=datetime.now, comment='预测日期')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_rul_node', 'node_type', 'node_id'),
        Index('idx_rul_time', 'prediction_date'),
        Index('idx_rul_rul', 'rul_days'),
    )


class HealthRollupReport(Base):
    """
    产线/装置健康度汇总报表表模型

    对应数据库表: sc_health_rollup_reports
    存储产线/装置级的健康度汇总报表。
    """
    __tablename__ = 'sc_health_rollup_reports'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    report_no = Column(String(50), unique=True, comment='报表编号')
    line_id = Column(String(100), nullable=False, comment='产线/装置ID')
    line_name = Column(String(200), comment='产线/装置名称')
    line_type = Column(String(50), comment='产线类型')
    overall_hi = Column(Float, nullable=False, comment='整体健康度')
    overall_level = Column(String(20), nullable=False, comment='整体健康等级')
    total_flange_count = Column(Integer, comment='法兰面总数')
    total_bolt_count = Column(Integer, comment='螺栓总数')
    healthy_flange_count = Column(Integer, comment='健康法兰面数')
    warning_flange_count = Column(Integer, comment='预警法兰面数')
    critical_flange_count = Column(Integer, comment='危险法兰面数')
    healthy_bolt_count = Column(Integer, comment='健康螺栓数')
    warning_bolt_count = Column(Integer, comment='预警螺栓数')
    critical_bolt_count = Column(Integer, comment='危险螺栓数')
    worst_flange_hi = Column(Float, comment='最差法兰面健康度')
    worst_flange_id = Column(String(100), comment='最差法兰面ID')
    average_degradation_rate = Column(Float, comment='平均劣化速率')
    flanges_summary = Column(Text, comment='法兰面健康度摘要 JSON')
    risk_summary = Column(Text, comment='风险汇总 JSON')
    maintenance_priorities = Column(Text, comment='维护优先级排序 JSON')
    report_date = Column(DateTime, comment='报告日期')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_rollup_line', 'line_id'),
        Index('idx_rollup_date', 'report_date'),
        Index('idx_rollup_time', 'create_time'),
        Index('idx_rollup_line_date', 'line_id', 'report_date', unique=True),
    )


class DegradationCurve(Base):
    """
    劣化曲线数据表模型

    对应数据库表: sc_degradation_curves
    存储劣化曲线拟合数据。
    """
    __tablename__ = 'sc_degradation_curves'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    node_id = Column(String(100), nullable=False, comment='节点ID')
    node_type = Column(String(20), nullable=False, comment='节点类型 bolt/flange')
    curve_data = Column(Text, comment='曲线数据点 JSON')
    degradation_rate = Column(Float, comment='劣化速率')
    acceleration_rate = Column(Float, comment='劣化加速度')
    model_type = Column(String(50), comment='拟合模型类型')
    model_params = Column(Text, comment='模型参数 JSON')
    r_squared = Column(Float, comment='拟合优度 R²')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_degradation_node', 'node_type', 'node_id'),
        Index('idx_degradation_time', 'create_time'),
    )


class HealthConfig(Base):
    """
    健康度配置表模型

    对应数据库表: sc_health_config
    存储健康度计算的配置参数，如权重、阈值等。
    """
    __tablename__ = 'sc_health_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, unique=True, comment='配置键')
    config_value = Column(Text, comment='配置值 JSON')
    config_type = Column(String(50), comment='配置类型')
    description = Column(String(500), comment='配置描述')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_health_config_key', 'config_key'),
    )


class JobExecutionLog(Base):
    """
    任务执行日志表模型

    对应数据库表: sc_job_execution_log
    记录每次任务执行的起止时间、处理节点数、成功/失败数、错误摘要。
    """
    __tablename__ = 'sc_job_execution_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_name = Column(String(100), nullable=False, comment='任务名称')
    job_type = Column(String(50), nullable=False, comment='任务类型')
    trigger_type = Column(String(20), default='scheduled', comment='触发类型: scheduled/manual')
    status = Column(String(20), default='running', comment='状态: running/completed/failed/skipped')
    start_time = Column(DateTime, nullable=False, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    duration_seconds = Column(Integer, comment='执行时长（秒）')
    total_nodes = Column(Integer, default=0, comment='处理节点总数')
    success_count = Column(Integer, default=0, comment='成功处理节点数')
    failed_count = Column(Integer, default=0, comment='失败节点数')
    skipped_count = Column(Integer, default=0, comment='跳过节点数')
    shard_index = Column(Integer, comment='分片索引')
    shard_total = Column(Integer, comment='总分片数')
    bolt_id_min = Column(String(100), comment='处理的最小bolt_id')
    bolt_id_max = Column(String(100), comment='处理的最大bolt_id')
    error_summary = Column(Text, comment='错误摘要 JSON')
    error_details = Column(Text, comment='详细错误信息 JSON')
    instance_id = Column(String(100), comment='执行实例ID')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_job_name', 'job_name'),
        Index('idx_job_type', 'job_type'),
        Index('idx_status', 'status'),
        Index('idx_start_time', 'start_time'),
        Index('idx_instance', 'instance_id'),
        Index('idx_tenant', 'tenant_id'),
    )


class SchedulerLeader(Base):
    """
    调度器Leader选举表模型

    对应数据库表: sc_scheduler_leader
    用于大集群场景下的单实例Leader选举，避免重复预测。
    使用基于租约的乐观锁机制。
    """
    __tablename__ = 'sc_scheduler_leader'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    leader_key = Column(String(100), nullable=False, unique=True, comment='Leader锁键')
    leader_id = Column(String(100), nullable=False, comment='当前Leader实例ID')
    lease_expire_time = Column(DateTime, nullable=False, comment='租约过期时间')
    last_heartbeat = Column(DateTime, default=datetime.now, comment='最后心跳时间')
    version = Column(BigInteger, default=0, comment='版本号（乐观锁）')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_leader_key', 'leader_key'),
        Index('idx_lease_expire', 'lease_expire_time'),
    )


class TrainingLog(Base):
    """
    训练日志表模型

    对应数据库表: sc_training_logs
    存储训练任务的完整日志：状态机、指标、配置等。
    """
    __tablename__ = 'sc_training_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, comment='训练会话ID')
    model_id = Column(String(100), comment='模型标识（bolt_id或flange_id）')
    model_type = Column(String(20), comment='模型类型 bolt/flange')
    status = Column(String(20), default='pending', comment='状态 pending/running/completed/failed')
    start_time = Column(DateTime, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    total_epochs = Column(Integer, comment='总epoch数')
    current_epoch = Column(Integer, default=0, comment='当前epoch')
    best_val_acc = Column(Float, comment='最佳验证准确率')
    best_val_loss = Column(Float, comment='最佳验证损失')
    best_epoch = Column(Integer, comment='最佳epoch')
    final_train_acc = Column(Float, comment='最终训练准确率')
    final_train_loss = Column(Float, comment='最终训练损失')
    final_val_acc = Column(Float, comment='最终验证准确率')
    final_val_loss = Column(Float, comment='最终验证损失')
    precision = Column(Float, comment='精确率')
    recall = Column(Float, comment='召回率')
    f1_score = Column(Float, comment='F1分数')
    confusion_matrix = Column(Text, comment='混淆矩阵 JSON')
    class_distribution = Column(Text, comment='类别分布 JSON')
    samples_count = Column(Integer, comment='训练样本数')
    val_samples_count = Column(Integer, comment='验证样本数')
    config = Column(Text, comment='训练配置 JSON')
    metrics_history = Column(Text, comment='逐epoch指标历史 JSON')
    error_message = Column(Text, comment='错误信息')
    error_stack = Column(Text, comment='错误栈追踪')
    data_source = Column(String(50), comment='数据来源 csv/db/manual')
    is_incremental = Column(Boolean, default=False, comment='是否增量训练')
    base_model_version = Column(String(50), comment='基础模型版本号（增量训练用）')
    freeze_layers = Column(Text, comment='冻结的层名称列表 JSON')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_session_id', 'session_id', unique=True),
        Index('idx_model', 'model_type', 'model_id'),
        Index('idx_status', 'status'),
        Index('idx_start_time', 'start_time'),
        Index('idx_tenant', 'tenant_id'),
    )


class ModelVersionORM(Base):
    """
    模型版本表模型

    对应数据库表: sc_model_versions
    存储模型版本信息和评估指标。
    """
    __tablename__ = 'sc_model_versions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_id = Column(String(100), nullable=False, comment='模型标识')
    model_type = Column(String(20), nullable=False, comment='模型类型 bolt/flange')
    version = Column(String(20), nullable=False, comment='版本号 vX.Y.Z')
    file_path = Column(String(500), comment='模型文件路径')
    file_hash = Column(String(64), comment='文件MD5哈希')
    file_size_bytes = Column(BigInteger, comment='文件大小（字节）')
    metrics = Column(Text, comment='训练和验证指标 JSON')
    config = Column(Text, comment='训练配置 JSON')
    is_active = Column(Boolean, default=False, comment='是否为当前活动版本')
    description = Column(String(500), comment='版本描述')
    training_session_id = Column(String(100), comment='关联的训练会话ID')
    parent_version = Column(String(20), comment='父版本号（增量训练用）')
    training_samples = Column(Integer, comment='训练样本数')
    validation_samples = Column(Integer, comment='验证样本数')
    training_duration_seconds = Column(Float, comment='训练时长（秒）')
    architecture_summary = Column(Text, comment='模型架构摘要 JSON')
    freeze_layers = Column(Text, comment='冻结层列表 JSON（增量训练）')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_model_version', 'model_id', 'version', unique=True),
        Index('idx_model_type', 'model_type'),
        Index('idx_active', 'is_active'),
        Index('idx_create_time', 'create_time'),
        Index('idx_tenant', 'tenant_id'),
    )


class AnomalyData(Base):
    """
    异常数据表模型

    对应数据库表: sc_anomaly_data
    存储预处理阶段检出的异常数据，含异常类型、评分、详情等。
    支持异常确认/误报标注，用于模型再训练。
    """
    __tablename__ = 'sc_anomaly_data'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id = Column(String(50), comment='传感器/螺栓ID')
    anomaly_value = Column(Float, comment='异常值')
    anomaly_type = Column(String(50), comment='异常类型: isolation_forest, zscore, iqr, sudden_change, out_of_range')
    anomaly_score = Column(Float, comment='异常评分')
    original_time = Column(DateTime, comment='原始数据时间')
    details = Column(Text, comment='详细信息JSON')
    classification = Column(String(20), comment='异常分类: true_anomaly/collection_anomaly/uncertain/mixed')
    classification_confidence = Column(Float, comment='分类置信度')
    collection_subtype = Column(String(20), comment='采集异常子类型')
    true_anomaly_subtype = Column(String(20), comment='真异常子类型')
    classification_evidence = Column(Text, comment='分类证据JSON')
    is_confirmed = Column(Boolean, default=False, comment='是否已确认')
    is_false_positive = Column(Boolean, default=False, comment='是否为误报')
    confirmed_by = Column(String(50), comment='确认人ID')
    confirmed_time = Column(DateTime, comment='确认时间')
    confirm_note = Column(Text, comment='确认备注')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_anomaly_sensor', 'sensor_id'),
        Index('idx_anomaly_type', 'anomaly_type'),
        Index('idx_anomaly_time', 'original_time'),
        Index('idx_anomaly_classification', 'classification'),
        Index('idx_anomaly_confirmed', 'is_confirmed'),
        Index('idx_anomaly_false_positive', 'is_false_positive'),
        Index('idx_anomaly_create_time', 'create_time'),
    )


class StrategyConfig(Base):
    __tablename__ = 'sc_strategy_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scope = Column(String(20), nullable=False, default='global', comment='作用域 global/bolt/flange/production_line')
    node_type = Column(String(20), comment='节点类型 bolt/flange/production_line，global时为NULL')
    node_id = Column(String(100), comment='节点ID，global时为NULL')
    strategy_type = Column(Integer, nullable=False, default=1, comment='策略类型 1=应报尽报 2=精准报警')
    confidence_threshold = Column(Float, nullable=False, default=0.7, comment='置信度阈值 0-1')
    false_positive_threshold = Column(Float, comment='误报容忍度 0-1')
    false_negative_threshold = Column(Float, comment='漏报容忍度 0-1')
    version = Column(Integer, nullable=False, default=1, comment='版本号，每次更新自增')
    is_active = Column(Boolean, default=True, comment='是否为当前生效版本')
    description = Column(String(500), comment='变更说明')
    operator_id = Column(String(50), comment='操作人ID')
    operator_name = Column(String(100), comment='操作人姓名')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_strategy_scope', 'scope', 'node_type', 'node_id'),
        Index('idx_strategy_active', 'is_active'),
        Index('idx_strategy_version', 'scope', 'node_type', 'node_id', 'version'),
        Index('idx_strategy_tenant', 'tenant_id'),
    )


class StrategyAuditLog(Base):
    __tablename__ = 'sc_strategy_audit_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_id = Column(BigInteger, nullable=False, comment='关联策略配置ID')
    scope = Column(String(20), nullable=False, comment='作用域 global/bolt/flange/production_line')
    node_type = Column(String(20), comment='节点类型')
    node_id = Column(String(100), comment='节点ID')
    action = Column(String(30), nullable=False, comment='操作类型 create/update/rollback')
    old_value = Column(Text, comment='变更前值 JSON')
    new_value = Column(Text, comment='变更后值 JSON')
    version_before = Column(Integer, comment='变更前版本号')
    version_after = Column(Integer, comment='变更后版本号')
    change_summary = Column(String(500), comment='变更摘要')
    operator_id = Column(String(50), comment='操作人ID')
    operator_name = Column(String(100), comment='操作人姓名')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_audit_config', 'config_id'),
        Index('idx_audit_scope', 'scope', 'node_type', 'node_id'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_time', 'create_time'),
        Index('idx_audit_operator', 'operator_id'),
    )


class ManualLabelData(Base):
    """
    人工标注数据表模型

    对应数据库表: sc_manual_label_data
    存储人工导入的标注数据，用于覆盖自动生成的规则标签。
    """
    __tablename__ = 'sc_manual_label_data'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    node_id = Column(String(100), nullable=False, comment='节点ID（bolt_id或flange_id）')
    node_type = Column(String(20), nullable=False, comment='节点类型 bolt/flange')
    data_hash = Column(String(64), comment='数据内容哈希（用于去重）')
    label = Column(Integer, nullable=False, comment='人工标注标签 0-4')
    label_source = Column(String(50), comment='标签来源 csv/db/manual_import')
    label_confidence = Column(Float, default=1.0, comment='标注置信度 0-1')
    data_points = Column(Text, comment='对应的数据点/时序数据 JSON')
    data_timestamp = Column(DateTime, comment='数据时间戳')
    label_time = Column(DateTime, default=datetime.now, comment='标注时间')
    labeler_id = Column(String(50), comment='标注人ID')
    labeler_name = Column(String(100), comment='标注人姓名')
    review_status = Column(String(20), default='pending', comment='审核状态 pending/approved/rejected')
    reviewer_id = Column(String(50), comment='审核人ID')
    review_time = Column(DateTime, comment='审核时间')
    notes = Column(Text, comment='备注')
    extra_info = Column(Text, comment='扩展信息 JSON')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_node_label', 'node_type', 'node_id'),
        Index('idx_label_source', 'label_source'),
        Index('idx_review_status', 'review_status'),
        Index('idx_data_hash', 'data_hash'),
        Index('idx_label_time', 'label_time'),
        Index('idx_tenant', 'tenant_id'),
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
