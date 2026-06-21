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
from typing import Generator, Optional, List, Dict

import numpy as np

from sqlalchemy import create_engine, Column, BigInteger, String, Float, DateTime, Index, Text, Boolean, Integer, BINARY, Date
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
    存储采集的螺栓预紧力原始数据（含多变量辅传感器扩展字段）

    Attributes:
        id: 主键，自增长
        sensor_id: 通道ID/螺栓ID
        collector_id: 采集器ID
        splitter_num: 分线器ID
        position: 安装位置
        ptf: 预紧力值
        temperature: 环境温度 (°C)
        humidity: 环境湿度 (%)
        vibration: 振动加速度 (g)
        torque: 拧紧扭矩 (N·m)
        pressure: 介质压力 (MPa)
        data_quality: 数据质量 full/partial/degraded
        missing_channels: 缺失通道列表 JSON
        create_time: 创建时间
    """
    __tablename__ = 'sc_bolt_data'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
    sensor_id = Column(BigInteger, nullable=False, comment='通道ID/螺栓ID')
    collector_id = Column(BigInteger, comment='采集器ID')
    splitter_num = Column(BigInteger, comment='分线器ID')
    position = Column(String(200), comment='安装位置')
    ptf = Column(Float, comment='预紧力')
    temperature = Column(Float, comment='环境温度 (°C)')
    humidity = Column(Float, comment='环境湿度 (%)')
    vibration = Column(Float, comment='振动加速度 (g)')
    torque = Column(Float, comment='拧紧扭矩 (N·m)')
    pressure = Column(Float, comment='介质压力 (MPa)')
    data_quality = Column(String(20), default='full', comment='数据质量: full=完整, partial=部分缺失, degraded=降级单变量')
    missing_channels = Column(Text, comment='缺失通道列表 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    # 索引
    __table_args__ = (
        Index('idx_tenant_sensor_time', 'tenant_id', 'sensor_id', 'create_time'),
        Index('idx_sensor_time', 'sensor_id', 'create_time'),
        Index('idx_data_quality', 'data_quality'),
        Index('idx_tenant', 'tenant_id'),
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

    def to_multivariate_dict(self) -> Dict[str, Optional[float]]:
        """
        转换为多变量数据字典

        Returns:
            Dict: 包含各通道值的字典
        """
        return {
            'preload': self.ptf,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'vibration': self.vibration,
            'torque': self.torque,
            'pressure': self.pressure,
        }

    def get_available_channels(self) -> List[str]:
        """
        获取可用通道列表

        Returns:
            List[str]: 有有效值的通道名称列表
        """
        channels = []
        channel_map = {
            'preload': self.ptf,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'vibration': self.vibration,
            'torque': self.torque,
            'pressure': self.pressure,
        }
        for name, value in channel_map.items():
            if value is not None and not (isinstance(value, float) and np.isnan(value)):
                channels.append(name)
        return channels


class AbnormalPrediction(Base):
    """
    异常预测结果表模型

    对应数据库表: sci_abnormal_prediction
    存储模型预测的异常结果

    Attributes:
        id: 主键，自增长
        tenant_id: 租户ID
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
    threshold_version = Column(String(50), comment='生效阈值版本号')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    # 索引
    __table_args__ = (
        Index('idx_tenant_node_type', 'tenant_id', 'node_type'),
        Index('idx_tenant_bolt_id', 'tenant_id', 'bolt_id'),
        Index('idx_tenant_flm_id', 'tenant_id', 'flm_id'),
        Index('idx_node_type', 'node_type'),
        Index('idx_bolt_id', 'bolt_id'),
        Index('idx_flm_id', 'flm_id'),
        Index('idx_tenant', 'tenant_id'),
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
    threshold_version = Column(String(50), comment='生效阈值版本号')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_tenant_bolt', 'tenant_id', 'bolt_id'),
        Index('idx_tenant_flm', 'tenant_id', 'flm_id'),
        Index('idx_tenant', 'tenant_id'),
    )


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
        tenant_id: 租户ID
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_level', 'tenant_id', 'alert_level'),
        Index('idx_tenant_enabled', 'tenant_id', 'enabled'),
        Index('idx_alert_level', 'alert_level'),
        Index('idx_enabled', 'enabled'),
        Index('idx_tenant', 'tenant_id'),
    )


class AlertEvent(Base):
    """
    告警事件表模型

    对应数据库表: sc_alert_events
    存储实际产生的告警事件

    Attributes:
        id: 主键
        tenant_id: 租户ID
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_status', 'tenant_id', 'status'),
        Index('idx_tenant_level', 'tenant_id', 'alert_level'),
        Index('idx_tenant_node', 'tenant_id', 'node_type', 'node_id'),
        Index('idx_status', 'status'),
        Index('idx_level', 'alert_level'),
        Index('idx_node', 'node_type', 'node_id'),
        Index('idx_create_time', 'create_time'),
        Index('idx_tenant', 'tenant_id'),
    )


class MaintenanceWindow(Base):
    """
    维护窗口表模型

    对应数据库表: sc_maintenance_windows
    存储计划检修和临时作业的维护窗口，窗口内告警按策略静默。

    Attributes:
        id: 主键
        window_no: 窗口编号
        window_name: 窗口名称
        node_scope: 作用范围 device/flange/bolt (装置/法兰/螺栓)
        node_type: 节点类型 bolt/flange
        node_ids: 节点ID列表 JSON，空表示该 scope 下全部
        device_id: 装置ID (当 node_scope=device 时使用)
        start_time: 开始时间
        end_time: 结束时间
        actual_end_time: 实际结束时间（提前结束时设置）
        window_type: 窗口类型 planned=计划检修 / temporary=临时作业
        suppress_level: 静默级别 all=全部静默 / non_emergency=仅静默非紧急
        status: 状态 pending/active/ended/cancelled
        reason: 维护原因/说明
        operator_id: 操作人ID
        operator_name: 操作人姓名
        suppressed_count: 被静默的告警数量
        extra_info: 扩展信息 JSON
        tenant_id: 租户ID
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_maintenance_windows'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    window_no = Column(String(50), unique=True, comment='窗口编号')
    window_name = Column(String(200), nullable=False, comment='窗口名称')
    node_scope = Column(String(20), nullable=False, comment='作用范围 device/flange/bolt')
    node_type = Column(String(20), comment='节点类型 bolt/flange')
    node_ids = Column(Text, comment='节点ID列表 JSON')
    device_id = Column(String(100), comment='装置ID')
    start_time = Column(DateTime, nullable=False, comment='开始时间')
    end_time = Column(DateTime, nullable=False, comment='结束时间')
    actual_end_time = Column(DateTime, comment='实际结束时间')
    window_type = Column(String(20), nullable=False, default='planned', comment='窗口类型 planned/temporary')
    suppress_level = Column(String(20), nullable=False, default='all', comment='静默级别 all/non_emergency')
    status = Column(String(20), nullable=False, default='pending', comment='状态 pending/active/ended/cancelled')
    reason = Column(String(500), comment='维护原因/说明')
    operator_id = Column(String(50), comment='操作人ID')
    operator_name = Column(String(100), comment='操作人姓名')
    suppressed_count = Column(Integer, default=0, comment='被静默的告警数量')
    extra_info = Column(Text, comment='扩展信息 JSON')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_mw_status', 'status'),
        Index('idx_mw_scope', 'node_scope'),
        Index('idx_mw_type', 'window_type'),
        Index('idx_mw_time_range', 'start_time', 'end_time'),
        Index('idx_mw_device', 'device_id'),
        Index('idx_mw_tenant_status', 'tenant_id', 'status'),
        Index('idx_mw_tenant_time', 'tenant_id', 'start_time', 'end_time'),
        Index('idx_tenant', 'tenant_id'),
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_subscriber', 'tenant_id', 'subscriber_type', 'subscriber_id'),
        Index('idx_tenant_enabled', 'tenant_id', 'enabled'),
        Index('idx_subscriber', 'subscriber_type', 'subscriber_id'),
        Index('idx_enabled', 'enabled'),
        Index('idx_tenant', 'tenant_id'),
    )


class NotificationChannel(Base):
    """
    通知渠道配置表模型

    对应数据库表: sc_notification_channels
    配置各类通知渠道的参数

    Attributes:
        id: 主键
        tenant_id: 租户ID
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
    tenant_id = Column(BigInteger, comment='租户ID')
    channel_type = Column(String(50), nullable=False, comment='渠道类型')
    channel_name = Column(String(200), comment='渠道名称')
    config = Column(Text, comment='渠道配置 JSON')
    enabled = Column(Boolean, default=True, comment='是否启用')
    is_default = Column(Boolean, default=False, comment='是否默认渠道')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_tenant_channel_type', 'tenant_id', 'channel_type'),
        Index('idx_tenant_default', 'tenant_id', 'is_default'),
        Index('idx_channel_type', 'channel_type'),
        Index('idx_tenant', 'tenant_id'),
    )


class NotificationLog(Base):
    """
    通知发送日志表模型

    对应数据库表: sc_notification_logs
    记录每次通知发送结果

    Attributes:
        id: 主键
        tenant_id: 租户ID
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_alert', 'tenant_id', 'alert_id'),
        Index('idx_tenant_status', 'tenant_id', 'status'),
        Index('idx_alert_id', 'alert_id'),
        Index('idx_status', 'status'),
        Index('idx_tenant', 'tenant_id'),
    )


class WorkOrder(Base):
    """
    工单表模型

    对应数据库表: sc_work_orders
    与告警联动，紧急预警自动建单

    Attributes:
        id: 主键
        tenant_id: 租户ID
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_status', 'tenant_id', 'status'),
        Index('idx_tenant_priority', 'tenant_id', 'priority'),
        Index('idx_tenant_alert', 'tenant_id', 'alert_id'),
        Index('idx_tenant_assignee', 'tenant_id', 'assignee_id'),
        Index('idx_tenant_node', 'tenant_id', 'node_type', 'node_id'),
        Index('idx_status', 'status'),
        Index('idx_priority', 'priority'),
        Index('idx_alert_id', 'alert_id'),
        Index('idx_assignee', 'assignee_id'),
        Index('idx_create_time', 'create_time'),
        Index('idx_node', 'node_type', 'node_id'),
        Index('idx_due_time', 'due_time'),
        Index('idx_tenant', 'tenant_id'),
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_wo', 'tenant_id', 'work_order_id'),
        Index('idx_tenant_time', 'tenant_id', 'disposal_time'),
        Index('idx_disposal_wo', 'work_order_id'),
        Index('idx_disposal_time', 'disposal_time'),
        Index('idx_disposal_operator', 'operator_id'),
        Index('idx_tenant', 'tenant_id'),
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_wo', 'tenant_id', 'work_order_id'),
        Index('idx_tenant_time', 'tenant_id', 'retest_time'),
        Index('idx_retest_wo', 'work_order_id'),
        Index('idx_retest_time', 'retest_time'),
        Index('idx_retest_result', 'retest_result'),
        Index('idx_tenant', 'tenant_id'),
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_wo', 'tenant_id', 'work_order_id'),
        Index('idx_tenant_retest', 'tenant_id', 'retest_id'),
        Index('idx_compare_wo', 'work_order_id'),
        Index('idx_compare_retest', 'retest_id'),
        Index('idx_compare_false_positive', 'is_false_positive'),
        Index('idx_compare_recurring', 'is_recurring'),
        Index('idx_compare_time', 'create_time'),
        Index('idx_tenant', 'tenant_id'),
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
        Index('idx_tenant', 'tenant_id'),
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_config', 'tenant_id', 'config_id'),
        Index('idx_tenant_status', 'tenant_id', 'status'),
        Index('idx_tenant_time', 'tenant_id', 'sync_time'),
        Index('idx_cmms_log_config', 'config_id'),
        Index('idx_cmms_log_wo', 'work_order_id'),
        Index('idx_cmms_log_status', 'status'),
        Index('idx_cmms_log_time', 'sync_time'),
        Index('idx_cmms_log_external', 'external_id'),
        Index('idx_tenant', 'tenant_id'),
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
    uncertainty_metrics = Column(Text, comment='不确定性度量 JSON: status_prob_mean/status_prob_std/epistemic_uncertainty/confidence_interval')
    retention_years = Column(Integer, default=3, comment='保留年限')
    expire_time = Column(DateTime, comment='过期时间 (create_time + retention_years)')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_tenant_node', 'tenant_id', 'node_type', 'node_id'),
        Index('idx_tenant_time', 'tenant_id', 'create_time'),
        Index('idx_audit_node', 'node_type', 'node_id'),
        Index('idx_audit_time', 'create_time'),
        Index('idx_audit_expire', 'expire_time'),
        Index('idx_audit_model_version', 'model_version'),
        Index('idx_tenant', 'tenant_id'),
    )


class DataQualityCheck(Base):
    """
    数据质量检查表模型

    对应数据库表: sc_data_quality_checks
    存储每次数据质量检查的结果。
    """
    __tablename__ = 'sc_data_quality_checks'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_sensor', 'tenant_id', 'sensor_id'),
        Index('idx_tenant_time', 'tenant_id', 'check_time'),
        Index('idx_dqc_sensor', 'sensor_id'),
        Index('idx_dqc_time', 'check_time'),
        Index('idx_dqc_score', 'overall_score'),
        Index('idx_dqc_level', 'quality_level'),
        Index('idx_tenant', 'tenant_id'),
    )


class QualityReport(Base):
    """
    质量报告表模型

    对应数据库表: sc_quality_reports
    存储每日数据质量报告。
    """
    __tablename__ = 'sc_quality_reports'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_date', 'tenant_id', 'report_date', unique=True),
        Index('idx_qr_date', 'report_date', unique=True),
        Index('idx_qr_create', 'create_time'),
        Index('idx_tenant', 'tenant_id'),
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
    max_training_concurrency = Column(Integer, default=2, comment='最大训练并发数')
    current_model_count = Column(Integer, default=0, comment='当前模型数')
    current_api_calls_today = Column(Integer, default=0, comment='今日API调用次数')
    current_storage_mb = Column(Float, default=0.0, comment='当前存储用量 MB')
    current_user_count = Column(Integer, default=0, comment='当前用户数')
    current_org_node_count = Column(Integer, default=0, comment='当前组织节点数')
    current_training_concurrency = Column(Integer, default=0, comment='当前训练并发数')
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
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_case_version', 'tenant_id', 'case_id', 'version'),
        Index('idx_version_case', 'case_id', 'version'),
        Index('idx_version_time', 'create_time'),
        Index('idx_tenant', 'tenant_id'),
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
    tenant_id = Column(BigInteger, comment='租户ID')
    case_id = Column(BigInteger, nullable=False, comment='关联案例ID')
    version = Column(Integer, comment='对应版本号')
    review_level = Column(Integer, default=1, comment='审核级别 1-3')
    reviewer_id = Column(String(50), comment='审核人ID')
    reviewer_name = Column(String(100), comment='审核人姓名')
    review_result = Column(String(30), comment='审核结果 approved/rejected/revision_required')
    review_comment = Column(Text, comment='审核意见')
    create_time = Column(DateTime, default=datetime.now, comment='审核时间')

    __table_args__ = (
        Index('idx_tenant_case', 'tenant_id', 'case_id'),
        Index('idx_review_case', 'case_id'),
        Index('idx_review_result', 'review_result'),
        Index('idx_review_time', 'create_time'),
        Index('idx_tenant', 'tenant_id'),
    )


class APIAuditLog(Base):
    __tablename__ = 'sc_api_audit_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
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
        Index('idx_tenant_key', 'tenant_id', 'key_id'),
        Index('idx_tenant_path', 'tenant_id', 'path'),
        Index('idx_tenant_time', 'tenant_id', 'create_time'),
        Index('idx_api_audit_key', 'key_id'),
        Index('idx_api_audit_path', 'path'),
        Index('idx_api_audit_status', 'status_code'),
        Index('idx_api_audit_time', 'create_time'),
        Index('idx_api_audit_method', 'method'),
        Index('idx_tenant', 'tenant_id'),
    )


class WorkingConditionAudit(Base):
    """
    工况变更审计表模型

    对应数据库表: sc_working_condition_audit
    记录每次工况识别结果和工况变更事件，用于审计和追溯。
    """
    __tablename__ = 'sc_working_condition_audit'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, nullable=False, comment='事件ID (UUID)')
    node_type = Column(String(20), nullable=False, comment='节点类型 bolt/flange')
    node_id = Column(String(100), nullable=False, comment='节点ID')
    from_condition = Column(String(50), comment='原工况')
    from_condition_label = Column(String(100), comment='原工况名称')
    from_confidence = Column(Float, comment='原工况置信度')
    to_condition = Column(String(50), comment='新工况')
    to_condition_label = Column(String(100), comment='新工况名称')
    to_confidence = Column(Float, comment='新工况置信度')
    is_transition = Column(Boolean, default=False, comment='是否为过渡态')
    trigger_data_points = Column(Integer, comment='触发数据点数')
    feature_evidence = Column(Text, comment='特征证据 JSON')
    condition_probabilities = Column(Text, comment='各工况概率分布 JSON')
    baseline_info = Column(Text, comment='基线信息 JSON')
    anomaly_summary = Column(Text, comment='异常检测摘要 JSON')
    retention_days = Column(Integer, default=365, comment='保留天数')
    expire_time = Column(DateTime, comment='过期时间')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_wc_audit_node', 'node_type', 'node_id'),
        Index('idx_wc_audit_time', 'create_time'),
        Index('idx_wc_audit_expire', 'expire_time'),
        Index('idx_wc_audit_condition', 'from_condition', 'to_condition'),
        Index('idx_wc_audit_event_id', 'event_id'),
        Index('idx_tenant', 'tenant_id'),
    )


class WorkingConditionBaseline(Base):
    """
    工况基线配置表模型

    对应数据库表: sc_working_condition_baselines
    存储各工况的基线参数和阈值配置。
    """
    __tablename__ = 'sc_working_condition_baselines'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    node_type = Column(String(20), nullable=False, comment='节点类型 bolt/flange')
    node_id = Column(String(100), nullable=False, comment='节点ID')
    condition = Column(String(50), nullable=False, comment='工况类型')
    condition_label = Column(String(100), comment='工况名称')
    mean_value = Column(Float, comment='基线均值')
    std_value = Column(Float, comment='基线标准差')
    upper_bound = Column(Float, comment='异常上界')
    lower_bound = Column(Float, comment='异常下界')
    warning_upper = Column(Float, comment='预警上界')
    warning_lower = Column(Float, comment='预警下界')
    trend_slope = Column(Float, comment='趋势斜率')
    trend_intercept = Column(Float, comment='趋势截距')
    sample_count = Column(Integer, comment='样本数量')
    threshold_config = Column(Text, comment='阈值配置 JSON')
    is_active = Column(Boolean, default=True, comment='是否生效')
    version = Column(Integer, default=1, comment='版本号')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_wc_baseline_node', 'node_type', 'node_id'),
        Index('idx_wc_baseline_condition', 'condition'),
        Index('idx_wc_baseline_active', 'is_active'),
        Index('idx_tenant', 'tenant_id'),
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
        Index('idx_tenant', 'tenant_id'),
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
        Index('idx_tenant', 'tenant_id'),
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
        Index('idx_tenant', 'tenant_id'),
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
        Index('idx_tenant', 'tenant_id'),
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
        Index('idx_tenant', 'tenant_id'),
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
        Index('idx_tenant', 'tenant_id'),
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
        Index('idx_tenant', 'tenant_id'),
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
        Index('idx_tenant', 'tenant_id'),
    )


# ============================================================
# SSO / 企业身份认证模块 ORM 模型
# ============================================================

class SSOProvider(Base):
    """
    SSO 身份提供者配置表模型

    对应数据库表: sc_sso_providers
    存储 OIDC 和 SAML 身份提供者的配置信息。
    """
    __tablename__ = 'sc_sso_providers'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, comment='租户ID，0表示平台级')
    provider_name = Column(String(200), nullable=False, comment='提供者名称，如 Azure AD、Okta')
    provider_type = Column(String(20), nullable=False, comment='协议类型 oidc/saml')
    status = Column(String(20), default='inactive', comment='状态 active/inactive')
    is_default = Column(Boolean, default=False, comment='是否为默认提供者')
    sort_order = Column(Integer, default=0, comment='排序序号')

    # OIDC 配置
    issuer_url = Column(String(500), comment='OIDC Issuer URL')
    client_id = Column(String(200), comment='OIDC Client ID')
    client_secret = Column(String(500), comment='OIDC Client Secret（加密存储）')
    authorization_endpoint = Column(String(500), comment='授权端点 URL')
    token_endpoint = Column(String(500), comment='令牌端点 URL')
    userinfo_endpoint = Column(String(500), comment='用户信息端点 URL')
    jwks_uri = Column(String(500), comment='JWKS 公钥 URL')
    scopes = Column(Text, comment='请求的 scope 列表 JSON')

    # SAML 配置
    saml_entity_id = Column(String(500), comment='SAML Entity ID')
    saml_sso_url = Column(String(500), comment='SAML SSO URL')
    saml_slo_url = Column(String(500), comment='SAML SLO URL')
    saml_idp_cert = Column(Text, comment='SAML IdP 证书')
    saml_name_id_format = Column(String(200), comment='SAML NameID 格式')

    # 用户属性映射
    attribute_mapping = Column(Text, comment='IdP 属性到本地用户字段的映射 JSON')
    # 角色映射规则
    role_mapping = Column(Text, comment='IdP groups/roles 到本地角色的映射 JSON')

    # JIT 配置
    jit_enabled = Column(Boolean, default=True, comment='是否启用 JIT 自动建号')
    jit_default_role = Column(String(30), default='viewer', comment='JIT 默认角色')
    jit_auto_activate = Column(Boolean, default=True, comment='JIT 创建用户是否自动激活')

    # 会话配置
    session_max_age = Column(Integer, default=86400, comment='会话最大时长（秒）')
    session_idle_timeout = Column(Integer, default=3600, comment='会话空闲超时（秒）')

    # 扩展配置
    extra_config = Column(Text, comment='扩展配置 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_sso_tenant', 'tenant_id'),
        Index('idx_sso_type', 'provider_type'),
        Index('idx_sso_status', 'status'),
        Index('idx_sso_default', 'tenant_id', 'is_default'),
    )


class UserSession(Base):
    """
    用户会话表模型

    对应数据库表: sc_user_sessions
    存储用户登录会话信息，支持强制登出。
    """
    __tablename__ = 'sc_user_sessions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, comment='会话ID（JWT jti）')
    tenant_id = Column(BigInteger, nullable=False, comment='租户ID')
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    username = Column(String(100), comment='用户名')
    display_name = Column(String(200), comment='显示名称')

    auth_method = Column(String(30), comment='认证方式 password/oidc/saml/api_key')
    sso_provider_id = Column(BigInteger, comment='SSO 提供者ID')
    idp_session_id = Column(String(200), comment='IdP 会话ID（用于 SLO）')

    ip_address = Column(String(50), comment='客户端IP')
    user_agent = Column(String(500), comment='用户代理')
    device_info = Column(Text, comment='设备信息 JSON')

    login_time = Column(DateTime, default=datetime.now, comment='登录时间')
    last_activity_time = Column(DateTime, default=datetime.now, comment='最后活动时间')
    expires_at = Column(DateTime, comment='过期时间')

    status = Column(String(20), default='active', comment='状态 active/revoked/expired/logged_out')
    revoke_reason = Column(String(200), comment='撤销原因')
    revoke_time = Column(DateTime, comment='撤销时间')
    revoked_by = Column(String(100), comment='撤销人')

    refresh_token_hash = Column(String(128), comment='刷新令牌哈希')
    refresh_expires_at = Column(DateTime, comment='刷新令牌过期时间')

    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_session_tenant', 'tenant_id'),
        Index('idx_session_user', 'user_id'),
        Index('idx_session_status', 'status'),
        Index('idx_session_expires', 'expires_at'),
        Index('idx_session_login_time', 'login_time'),
        Index('idx_session_sso_provider', 'sso_provider_id'),
    )


class ServiceAccount(Base):
    """
    服务账号表模型

    对应数据库表: sc_service_accounts
    独立于普通用户的服务账号管理，用于 API 集成和自动化任务。
    """
    __tablename__ = 'sc_service_accounts'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, comment='租户ID')
    account_name = Column(String(100), nullable=False, comment='账号名称')
    display_name = Column(String(200), comment='显示名称')
    description = Column(String(500), comment='描述')

    status = Column(String(20), default='active', comment='状态 active/disabled')
    role = Column(String(30), default='viewer', comment='角色 tenant_admin/admin/operator/viewer')

    # API Key 信息（可以有多个密钥轮换）
    current_api_key_id = Column(BigInteger, comment='当前生效的 API Key ID')

    # 使用限制
    rate_limit = Column(Integer, default=1000, comment='速率限制（每分钟）')
    allowed_ips = Column(Text, comment='允许的IP白名单 JSON，空表示不限制')
    allowed_scopes = Column(Text, comment='允许的 scope 列表 JSON')

    # 有效期
    expires_at = Column(DateTime, comment='过期时间，NULL表示永久')
    last_used_at = Column(DateTime, comment='最后使用时间')
    last_used_ip = Column(String(50), comment='最后使用IP')

    # 负责人
    owner_id = Column(BigInteger, comment='负责人用户ID')
    owner_name = Column(String(200), comment='负责人姓名')
    owner_email = Column(String(200), comment='负责人邮箱')

    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_svc_account_tenant', 'tenant_id'),
        Index('idx_svc_account_name', 'tenant_id', 'account_name', unique=True),
        Index('idx_svc_account_status', 'status'),
        Index('idx_svc_account_role', 'role'),
    )


class ServiceAccountKey(Base):
    """
    服务账号 API Key 表模型

    对应数据库表: sc_service_account_keys
    存储服务账号的 API 密钥，支持密钥轮换。
    """
    __tablename__ = 'sc_service_account_keys'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    service_account_id = Column(BigInteger, nullable=False, comment='服务账号ID')
    tenant_id = Column(BigInteger, nullable=False, comment='租户ID')

    key_name = Column(String(200), comment='密钥名称')
    key_prefix = Column(String(20), comment='密钥前缀（用于识别）')
    key_hash = Column(String(128), nullable=False, comment='密钥哈希（SHA256）')

    status = Column(String(20), default='active', comment='状态 active/expiring/revoked')
    expires_at = Column(DateTime, comment='过期时间')
    last_used_at = Column(DateTime, comment='最后使用时间')
    last_used_ip = Column(String(50), comment='最后使用IP')

    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_svc_key_account', 'service_account_id'),
        Index('idx_svc_key_tenant', 'tenant_id'),
        Index('idx_svc_key_hash', 'key_hash', unique=True),
        Index('idx_svc_key_status', 'status'),
        Index('idx_svc_key_expires', 'expires_at'),
    )


class JWTKeyStore(Base):
    """
    JWT 签名密钥存储表模型

    对应数据库表: sc_jwt_keys
    存储 JWT 签名密钥，支持密钥轮换。
    """
    __tablename__ = 'sc_jwt_keys'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    kid = Column(String(64), unique=True, nullable=False, comment='密钥ID')
    algorithm = Column(String(20), default='RS256', comment='签名算法 RS256/HS256/ES256')
    key_type = Column(String(20), default='asymmetric', comment='密钥类型 symmetric/asymmetric')

    private_key = Column(Text, comment='私钥（PEM格式，加密存储）')
    public_key = Column(Text, comment='公钥（PEM格式）')
    secret_key = Column(String(200), comment='对称密钥（加密存储）')

    status = Column(String(20), default='active', comment='状态 active/rotating/expired')
    is_current = Column(Boolean, default=False, comment='是否为当前签名密钥')

    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    activated_at = Column(DateTime, comment='激活时间')
    expires_at = Column(DateTime, comment='过期时间')
    rotated_at = Column(DateTime, comment='轮换时间')

    __table_args__ = (
        Index('idx_jwt_kid', 'kid'),
        Index('idx_jwt_status', 'status'),
        Index('idx_jwt_current', 'is_current'),
        Index('idx_jwt_expires', 'expires_at'),
    )


class UserSSOLink(Base):
    """
    用户 SSO 身份关联表模型

    对应数据库表: sc_user_sso_links
    存储本地用户与 IdP 身份的关联关系。
    """
    __tablename__ = 'sc_user_sso_links'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, comment='租户ID')
    user_id = Column(BigInteger, nullable=False, comment='本地用户ID')
    sso_provider_id = Column(BigInteger, nullable=False, comment='SSO 提供者ID')

    idp_user_id = Column(String(200), nullable=False, comment='IdP 用户唯一标识（sub/NameID）')
    idp_username = Column(String(200), comment='IdP 用户名')
    idp_email = Column(String(200), comment='IdP 邮箱')

    linked_at = Column(DateTime, default=datetime.now, comment='关联时间')
    last_login_at = Column(DateTime, comment='最后登录时间')
    login_count = Column(Integer, default=0, comment='登录次数')

    idp_groups = Column(Text, comment='IdP 用户组列表 JSON')
    idp_attributes = Column(Text, comment='IdP 用户属性 JSON')

    is_primary = Column(Boolean, default=False, comment='是否为主要登录方式')
    status = Column(String(20), default='active', comment='状态 active/disconnected')

    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_sso_link_user', 'user_id'),
        Index('idx_sso_link_tenant', 'tenant_id'),
        Index('idx_sso_link_provider', 'sso_provider_id'),
        Index('idx_sso_link_idp_user', 'sso_provider_id', 'idp_user_id', unique=True),
        Index('idx_sso_link_status', 'status'),
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


class MultivariateBoltData(Base):
    """
    螺栓多变量传感器时序数据表模型

    对应数据库表: sc_bolt_multivariate_data
    独立存储高精度多通道传感器采集数据，支持预紧力、温度、振动、扭矩等多通道。
    """
    __tablename__ = 'sc_bolt_multivariate_data'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
    sensor_id = Column(BigInteger, nullable=False, comment='通道ID/螺栓ID')
    collector_id = Column(BigInteger, comment='采集器ID')
    splitter_num = Column(BigInteger, comment='分线器ID')
    position = Column(String(200), comment='安装位置')
    timestamp = Column(DateTime, nullable=False, comment='采集时间戳')
    preload = Column(Float, comment='预紧力 (kN)')
    temperature = Column(Float, comment='环境温度 (°C)')
    humidity = Column(Float, comment='环境湿度 (%)')
    vibration_x = Column(Float, comment='X轴振动加速度 (g)')
    vibration_y = Column(Float, comment='Y轴振动加速度 (g)')
    vibration_z = Column(Float, comment='Z轴振动加速度 (g)')
    torque = Column(Float, comment='拧紧扭矩 (N·m)')
    pressure = Column(Float, comment='介质压力 (MPa)')
    axial_force = Column(Float, comment='轴向力 (kN)')
    strain = Column(Float, comment='应变 (με)')
    rpm = Column(Float, comment='转速 (RPM)')
    extra_channels = Column(Text, comment='扩展通道数据 JSON')
    data_quality = Column(String(20), default='full', comment='数据质量: full/partial/degraded')
    missing_channels = Column(Text, comment='缺失通道列表 JSON')
    interpolation_flags = Column(Text, comment='插值标记 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_tenant_sensor_time_multi', 'tenant_id', 'sensor_id', 'timestamp'),
        Index('idx_sensor_time_multi', 'sensor_id', 'timestamp'),
        Index('idx_collector_multi', 'collector_id', 'splitter_num', 'position'),
        Index('idx_quality_multi', 'data_quality'),
        Index('idx_create_time_multi', 'create_time'),
        Index('idx_tenant_multi', 'tenant_id'),
    )

    def to_channel_array(self, channel_list: List[str]) -> np.ndarray:
        """
        按指定通道列表抽取数据为数组

        Args:
            channel_list: 通道名称列表，如 ["preload", "temperature"]

        Returns:
            np.ndarray: 1D 数组，长度等于 len(channel_list)，缺失通道用 np.nan 填充
        """
        values = []
        for ch in channel_list:
            val = getattr(self, ch, None)
            values.append(np.nan if val is None else float(val))
        return np.array(values, dtype=np.float32)

    def get_available_channels(self) -> List[str]:
        """
        获取可用（非空）通道列表
        """
        channels = ['preload', 'temperature', 'humidity', 'vibration_x', 'vibration_y',
                    'vibration_z', 'torque', 'pressure', 'axial_force', 'strain', 'rpm']
        available = []
        for ch in channels:
            val = getattr(self, ch, None)
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                available.append(ch)
        return available


class MultivariateTrainingConfig(Base):
    """
    多变量训练数据集配置表模型

    对应数据库表: sc_multivariate_training_config
    存储各模型的多变量训练配置，包括输入通道、序列长度、插值方式等。
    """
    __tablename__ = 'sc_multivariate_training_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
    model_id = Column(String(100), nullable=False, comment='模型标识（bolt_id 或 flange_id）')
    model_type = Column(String(20), nullable=False, comment='模型类型: bolt/flange')
    input_channels = Column(Text, nullable=False, comment='输入通道配置 JSON')
    target_channel = Column(String(50), default='preload', comment='预测目标通道')
    sequence_length = Column(Integer, default=100, comment='输入序列长度')
    interpolation_method = Column(String(20), default='linear', comment='插值方法: linear/spline/time_aware')
    allow_degraded_training = Column(Boolean, default=True, comment='是否允许降级训练')
    min_complete_ratio = Column(Float, default=0.5, comment='最低完整数据比例')
    data_normalization = Column(String(20), default='channel_wise', comment='归一化方式')
    extra_params = Column(Text, comment='扩展参数 JSON')
    is_active = Column(Boolean, default=True, comment='是否为活动配置')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_tenant_model_config', 'tenant_id', 'model_id', 'model_type', 'is_active', unique=True),
        Index('idx_model_config', 'model_id', 'model_type', 'is_active', unique=True),
        Index('idx_model_type', 'model_type'),
        Index('idx_tenant_config', 'tenant_id'),
    )

    @property
    def input_channels_list(self) -> List[str]:
        """将 input_channels JSON 解析为列表"""
        import json
        try:
            return json.loads(self.input_channels)
        except (json.JSONDecodeError, TypeError):
            return ['preload']


# ============================================================
# 备件库存与 RUL 联动模块 ORM 模型
# ============================================================

class BoltSkuMapping(Base):
    """
    螺栓型号与备件SKU映射表模型

    对应数据库表: sc_bolt_sku_mapping
    存储螺栓型号规格与备件SKU的对应关系。
    """
    __tablename__ = 'sc_bolt_sku_mapping'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bolt_model = Column(String(100), nullable=False, comment='螺栓型号')
    bolt_spec = Column(String(200), comment='螺栓规格描述')
    material = Column(String(100), comment='材质')
    standard = Column(String(100), comment='标准（如GB/T、DIN）')
    diameter = Column(Float, comment='公称直径(mm)')
    length = Column(Float, comment='公称长度(mm)')
    grade = Column(String(50), comment='性能等级')
    sku_code = Column(String(100), unique=True, nullable=False, comment='备件SKU编码')
    sku_name = Column(String(200), nullable=False, comment='备件名称')
    unit = Column(String(20), default='个', comment='计量单位')
    unit_price = Column(Float, comment='单价')
    supplier = Column(String(200), comment='供应商')
    manufacturer = Column(String(200), comment='生产厂家')
    lead_time_days = Column(Integer, default=7, comment='采购周期(天)')
    min_order_qty = Column(Integer, default=1, comment='最小订货量')
    is_active = Column(Boolean, default=True, comment='是否启用')
    description = Column(String(500), comment='备注说明')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_bolt_model', 'bolt_model'),
        Index('idx_sku_code', 'sku_code'),
        Index('idx_sku_active', 'is_active'),
        Index('idx_sku_tenant', 'tenant_id'),
    )


class SparePartInventory(Base):
    """
    备件库存表模型

    对应数据库表: sc_spare_part_inventory
    存储备件的当前库存信息。
    """
    __tablename__ = 'sc_spare_part_inventory'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sku_code = Column(String(100), nullable=False, comment='备件SKU编码')
    warehouse_code = Column(String(50), default='main', comment='仓库编码')
    warehouse_name = Column(String(100), default='主仓库', comment='仓库名称')
    location = Column(String(100), comment='库位')
    quantity_on_hand = Column(Integer, default=0, comment='现有库存数量')
    quantity_reserved = Column(Integer, default=0, comment='已预留数量')
    quantity_available = Column(Integer, default=0, comment='可用库存数量')
    quantity_on_order = Column(Integer, default=0, comment='在途数量')
    reorder_point = Column(Integer, default=10, comment='再订货点')
    safety_stock = Column(Integer, default=5, comment='安全库存量')
    min_stock = Column(Integer, default=0, comment='最低库存量')
    max_stock = Column(Integer, comment='最高库存量')
    avg_consumption_rate = Column(Float, comment='平均消耗速率(个/天)')
    last_receipt_date = Column(DateTime, comment='最近入库日期')
    last_issue_date = Column(DateTime, comment='最近出库日期')
    batch_no = Column(String(100), comment='批次号')
    expiry_date = Column(DateTime, comment='有效期')
    quality_status = Column(String(20), default='qualified', comment='质量状态 qualified/inspecting/rejected')
    unit_price = Column(Float, comment='库存单价')
    total_value = Column(Float, comment='库存总值')
    abc_category = Column(String(1), comment='ABC分类 A/B/C')
    turnover_rate = Column(Float, comment='库存周转率')
    extra_info = Column(Text, comment='扩展信息 JSON')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_inv_sku', 'sku_code'),
        Index('idx_inv_warehouse', 'warehouse_code'),
        Index('idx_inv_available', 'quantity_available'),
        Index('idx_inv_abc', 'abc_category'),
        Index('idx_inv_tenant', 'tenant_id'),
        Index('idx_inv_sku_warehouse', 'sku_code', 'warehouse_code', unique=True),
    )


class SparePartDemand(Base):
    """
    备件需求建议表模型

    对应数据库表: sc_spare_part_demands
    存储基于RUL预测生成的备件需求建议。
    """
    __tablename__ = 'sc_spare_part_demands'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    demand_no = Column(String(50), unique=True, nullable=False, comment='需求单号')
    source_type = Column(String(20), default='rul', comment='需求来源 rul/alert/work_order/manual')
    source_id = Column(String(100), comment='来源ID（RUL记录ID/告警ID/工单ID）')
    node_type = Column(String(20), comment='节点类型 bolt/flange')
    node_id = Column(String(100), comment='节点ID')
    bolt_model = Column(String(100), comment='螺栓型号')
    sku_code = Column(String(100), nullable=False, comment='备件SKU编码')
    sku_name = Column(String(200), comment='备件名称')
    required_quantity = Column(Integer, default=1, comment='需求数量')
    urgency = Column(String(20), default='normal', comment='紧急程度 normal/urgent/critical')
    priority = Column(Integer, default=3, comment='优先级 1-5')
    rul_days = Column(Float, comment='RUL剩余天数')
    rul_threshold = Column(Float, comment='RUL阈值')
    estimated_failure_date = Column(DateTime, comment='预计故障日期')
    required_date = Column(DateTime, comment='需求日期')
    stock_status = Column(String(20), default='checking', comment='库存状态 checking/in_stock/out_of_stock/partial')
    available_quantity = Column(Integer, comment='可用库存数量')
    shortage_quantity = Column(Integer, comment='短缺数量')
    work_order_id = Column(BigInteger, comment='关联工单ID')
    work_order_priority_upgraded = Column(Boolean, default=False, comment='是否已升级工单优先级')
    status = Column(String(20), default='pending', comment='状态 pending/approved/fulfilled/cancelled')
    approved_by = Column(String(50), comment='审批人ID')
    approved_name = Column(String(100), comment='审批人姓名')
    approved_time = Column(DateTime, comment='审批时间')
    fulfilled_time = Column(DateTime, comment='完成时间')
    remarks = Column(String(500), comment='备注')
    extra_info = Column(Text, comment='扩展信息 JSON')
    device_id = Column(String(100), comment='装置ID')
    device_name = Column(String(200), comment='装置名称')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_demand_no', 'demand_no', unique=True),
        Index('idx_demand_sku', 'sku_code'),
        Index('idx_demand_node', 'node_type', 'node_id'),
        Index('idx_demand_status', 'status'),
        Index('idx_demand_urgency', 'urgency'),
        Index('idx_demand_date', 'required_date'),
        Index('idx_demand_device', 'device_id'),
        Index('idx_demand_tenant', 'tenant_id'),
        Index('idx_demand_source', 'source_type', 'source_id'),
    )


class SparePartDemandSummary(Base):
    """
    批量装置备件需求汇总报表模型

    对应数据库表: sc_spare_part_demand_summaries
    存储按装置维度汇总的备件需求报表。
    """
    __tablename__ = 'sc_spare_part_demand_summaries'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    summary_no = Column(String(50), unique=True, nullable=False, comment='汇总报表编号')
    device_id = Column(String(100), comment='装置ID')
    device_name = Column(String(200), comment='装置名称')
    summary_period = Column(String(20), default='monthly', comment='汇总周期 weekly/monthly/quarterly/custom')
    period_start = Column(DateTime, nullable=False, comment='统计周期开始')
    period_end = Column(DateTime, nullable=False, comment='统计周期结束')
    total_demand_count = Column(Integer, default=0, comment='需求项总数')
    total_quantity = Column(Integer, default=0, comment='需求总数量')
    total_estimated_value = Column(Float, default=0, comment='预估总金额')
    urgent_count = Column(Integer, default=0, comment='紧急需求项数')
    critical_count = Column(Integer, default=0, comment='特急需求项数')
    out_of_stock_count = Column(Integer, default=0, comment='缺货项数')
    partial_stock_count = Column(Integer, default=0, comment='部分缺货项数')
    in_stock_count = Column(Integer, default=0, comment='现货充足项数')
    affected_node_count = Column(Integer, default=0, comment='受影响节点数')
    demand_details = Column(Text, comment='需求明细 JSON')
    stock_analysis = Column(Text, comment='库存分析 JSON')
    recommendations = Column(Text, comment='采购建议 JSON')
    status = Column(String(20), default='draft', comment='状态 draft/confirmed/archived')
    generated_by = Column(String(50), comment='生成人ID')
    generated_name = Column(String(100), comment='生成人姓名')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_summary_no', 'summary_no', unique=True),
        Index('idx_summary_device', 'device_id'),
        Index('idx_summary_period', 'period_start', 'period_end'),
        Index('idx_summary_status', 'status'),
        Index('idx_summary_tenant', 'tenant_id'),
    )


class SparePartStockTransaction(Base):
    """
    备件库存交易记录表模型

    对应数据库表: sc_spare_part_stock_transactions
    存储备件出入库的交易记录。
    """
    __tablename__ = 'sc_spare_part_stock_transactions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_no = Column(String(50), unique=True, nullable=False, comment='交易单号')
    transaction_type = Column(String(20), nullable=False, comment='交易类型 receipt/issue/transfer/adjustment')
    sku_code = Column(String(100), nullable=False, comment='备件SKU编码')
    sku_name = Column(String(200), comment='备件名称')
    warehouse_code = Column(String(50), comment='仓库编码')
    quantity = Column(Integer, nullable=False, comment='交易数量（正入库负出库）')
    unit_price = Column(Float, comment='单价')
    total_amount = Column(Float, comment='总金额')
    balance_after = Column(Integer, comment='交易后库存数量')
    related_demand_id = Column(BigInteger, comment='关联需求单ID')
    related_work_order_id = Column(BigInteger, comment='关联工单ID')
    batch_no = Column(String(100), comment='批次号')
    operator_id = Column(String(50), comment='操作人ID')
    operator_name = Column(String(100), comment='操作人姓名')
    remarks = Column(String(500), comment='备注')
    extra_info = Column(Text, comment='扩展信息 JSON')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_trans_no', 'transaction_no', unique=True),
        Index('idx_trans_sku', 'sku_code'),
        Index('idx_trans_type', 'transaction_type'),
        Index('idx_trans_time', 'create_time'),
        Index('idx_trans_tenant', 'tenant_id'),
    )


class PurchaseCycleConfig(Base):
    """
    采购周期与安全库存配置表模型

    对应数据库表: sc_purchase_cycle_configs
    存储各类备件的采购周期和安全库存配置。
    """
    __tablename__ = 'sc_purchase_cycle_configs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sku_code = Column(String(100), unique=True, nullable=False, comment='备件SKU编码')
    sku_name = Column(String(200), comment='备件名称')
    abc_category = Column(String(1), comment='ABC分类')
    lead_time_days = Column(Integer, default=7, comment='采购提前期(天)')
    review_period_days = Column(Integer, default=30, comment='盘点周期(天)')
    avg_daily_consumption = Column(Float, default=0, comment='平均日消耗量')
    max_daily_consumption = Column(Float, default=0, comment='最大日消耗量')
    safety_stock_days = Column(Integer, default=7, comment='安全库存天数')
    calculated_safety_stock = Column(Integer, default=0, comment='计算安全库存量')
    reorder_point = Column(Integer, default=0, comment='再订货点')
    economic_order_qty = Column(Integer, default=0, comment='经济订货批量EOQ')
    min_order_qty = Column(Integer, default=1, comment='最小订货量')
    max_order_qty = Column(Integer, comment='最大订货量')
    order_cost = Column(Float, default=100, comment='单次订货成本')
    holding_cost_rate = Column(Float, default=0.15, comment='年持有成本率')
    unit_price = Column(Float, comment='单价')
    service_level = Column(Float, default=0.95, comment='服务水平 0-1')
    demand_variability = Column(Float, comment='需求变异系数')
    lead_time_variability = Column(Float, comment='提前期变异系数')
    is_active = Column(Boolean, default=True, comment='是否启用')
    description = Column(String(500), comment='备注')
    extra_info = Column(Text, comment='扩展信息 JSON')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_pc_sku', 'sku_code', unique=True),
        Index('idx_pc_abc', 'abc_category'),
        Index('idx_pc_active', 'is_active'),
        Index('idx_pc_tenant', 'tenant_id'),
    )


class HPOTrial(Base):
    """
    HPO试验记录表模型

    对应数据库表: sc_hpo_trials
    存储每次超参优化试验的配置和结果。

    Attributes:
        id: 主键
        trial_id: 试验唯一ID
        study_id: 研究ID（一组试验共享）
        model_type: 模型类型：bolt/flange
        node_id: 节点ID（为空表示全局）
        node_type: 节点类型
        framework: 优化框架：optuna/ray_tune/ax
        status: 状态：running/completed/failed/pruned
        trial_number: 试验序号
        num_layers: 层数
        hidden_size: 隐藏层大小
        dropout_rate: Dropout率
        learning_rate: 学习率
        sequence_length: 序列长度
        params: 完整超参JSON
        val_f1_score: 验证集F1分数
        val_precision: 验证集精确率
        val_recall: 验证集召回率
        val_accuracy: 验证集准确率
        false_positive_rate: 误报率
        false_negative_rate: 漏报率
        inference_latency_ms: 推理延迟（毫秒）
        training_time_seconds: 训练耗时（秒）
        objective_value: 综合优化目标值
        latency_constraint_violated: 是否违反延迟约束
        f1_constraint_violated: 是否违反F1约束
        training_session_id: 关联的训练会话ID
        model_version: 模型版本
        error_message: 错误信息
        pruned_reason: 被修剪原因
        tenant_id: 租户ID
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_hpo_trials'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    trial_id = Column(String(64), unique=True, nullable=False, comment='试验唯一ID')
    study_id = Column(String(64), nullable=False, comment='研究ID')
    model_type = Column(String(20), nullable=False, comment='模型类型：bolt/flange')
    node_id = Column(String(100), comment='节点ID')
    node_type = Column(String(20), comment='节点类型')
    framework = Column(String(20), nullable=False, comment='优化框架')
    status = Column(String(20), default='running', comment='状态')
    trial_number = Column(Integer, comment='试验序号')

    num_layers = Column(Integer, comment='层数')
    hidden_size = Column(Integer, comment='隐藏层大小')
    dropout_rate = Column(Float, comment='Dropout率')
    learning_rate = Column(Float, comment='学习率')
    sequence_length = Column(Integer, comment='序列长度')
    params = Column(Text, comment='完整超参JSON')

    val_f1_score = Column(Float, comment='验证集F1分数')
    val_precision = Column(Float, comment='验证集精确率')
    val_recall = Column(Float, comment='验证集召回率')
    val_accuracy = Column(Float, comment='验证集准确率')
    false_positive_rate = Column(Float, comment='误报率')
    false_negative_rate = Column(Float, comment='漏报率')
    inference_latency_ms = Column(Float, comment='推理延迟（毫秒）')
    training_time_seconds = Column(Float, comment='训练耗时（秒）')
    objective_value = Column(Float, comment='综合优化目标值')

    latency_constraint_violated = Column(Boolean, default=False, comment='是否违反延迟约束')
    f1_constraint_violated = Column(Boolean, default=False, comment='是否违反F1约束')

    training_session_id = Column(String(100), comment='关联的训练会话ID')
    model_version = Column(String(50), comment='模型版本')
    error_message = Column(Text, comment='错误信息')
    pruned_reason = Column(String(200), comment='被修剪原因')

    tenant_id = Column(BigInteger, default=0, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_study', 'study_id'),
        Index('idx_model_node', 'model_type', 'node_id'),
        Index('idx_status', 'status'),
        Index('idx_objective', 'objective_value'),
        Index('idx_f1', 'val_f1_score'),
        Index('idx_tenant', 'tenant_id'),
        Index('idx_create_time', 'create_time'),
    )


class HPOStudy(Base):
    """
    HPO研究配置表模型

    对应数据库表: sc_hpo_studies
    存储超参优化研究的配置和状态。

    Attributes:
        id: 主键
        study_id: 研究唯一ID
        study_name: 研究名称
        model_type: 模型类型
        node_id: 节点ID
        node_type: 节点类型
        search_space: 搜索空间定义JSON
        objective_config: 优化目标配置JSON
        f1_weight: F1权重
        false_positive_penalty: 误报惩罚系数
        latency_threshold_ms: 推理延迟阈值
        latency_weight: 延迟权重
        framework: 优化框架
        optimizer: 优化算法
        max_trials: 最大试验次数
        max_concurrent_trials: 最大并发试验数
        min_trials_to_prune: 最小试验数后开启剪枝
        pruner_type: 剪枝类型
        constraints: 约束条件JSON
        status: 状态
        best_trial_id: 最佳试验ID
        best_params: 最佳超参JSON
        best_objective_value: 最佳目标值
        per_node_hpo_enabled: 是否启用per-node超参
        node_scope: 节点范围
        tenant_id: 租户ID
        created_by: 创建人
        start_time: 开始时间
        end_time: 结束时间
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_hpo_studies'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    study_id = Column(String(64), unique=True, nullable=False, comment='研究唯一ID')
    study_name = Column(String(200), nullable=False, comment='研究名称')
    model_type = Column(String(20), nullable=False, comment='模型类型')
    node_id = Column(String(100), comment='节点ID')
    node_type = Column(String(20), comment='节点类型')

    search_space = Column(Text, nullable=False, comment='搜索空间定义JSON')
    objective_config = Column(Text, nullable=False, comment='优化目标配置JSON')
    f1_weight = Column(Float, default=1.0, comment='F1权重')
    false_positive_penalty = Column(Float, default=0.5, comment='误报惩罚系数')
    latency_threshold_ms = Column(Float, default=100.0, comment='推理延迟阈值')
    latency_weight = Column(Float, default=0.3, comment='延迟权重')

    framework = Column(String(20), default='optuna', comment='优化框架')
    optimizer = Column(String(20), default='tpe', comment='优化算法')
    max_trials = Column(Integer, default=50, comment='最大试验次数')
    max_concurrent_trials = Column(Integer, default=2, comment='最大并发试验数')
    min_trials_to_prune = Column(Integer, default=5, comment='最小试验数后开启剪枝')
    pruner_type = Column(String(20), default='median', comment='剪枝类型')

    constraints = Column(Text, comment='约束条件JSON')

    status = Column(String(20), default='pending', comment='状态')
    best_trial_id = Column(String(64), comment='最佳试验ID')
    best_params = Column(Text, comment='最佳超参JSON')
    best_objective_value = Column(Float, comment='最佳目标值')

    per_node_hpo_enabled = Column(Boolean, default=False, comment='是否启用per-node超参')
    node_scope = Column(String(20), default='global', comment='节点范围')

    tenant_id = Column(BigInteger, default=0, comment='租户ID')
    created_by = Column(String(100), comment='创建人')
    start_time = Column(DateTime, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_study_id', 'study_id'),
        Index('idx_model_node', 'model_type', 'node_id'),
        Index('idx_status', 'status'),
        Index('idx_tenant', 'tenant_id'),
    )


class HPONodeOverride(Base):
    """
    HPO节点超参覆盖配置表模型

    对应数据库表: sc_hpo_node_overrides
    存储每个节点的超参覆盖配置和最佳结果。

    Attributes:
        id: 主键
        study_id: 研究ID
        node_id: 节点ID
        node_type: 节点类型
        search_space_override: 覆盖的搜索空间JSON
        fixed_params: 固定超参值JSON
        best_params: 该节点最佳超参
        best_trial_id: 该节点最佳试验ID
        best_objective_value: 该节点最佳目标值
        applied_to_training: 是否已应用到训练
        applied_time: 应用时间
        tenant_id: 租户ID
        create_time: 创建时间
        update_time: 更新时间
    """
    __tablename__ = 'sc_hpo_node_overrides'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    study_id = Column(String(64), nullable=False, comment='研究ID')
    node_id = Column(String(100), nullable=False, comment='节点ID')
    node_type = Column(String(20), nullable=False, comment='节点类型')

    search_space_override = Column(Text, comment='覆盖的搜索空间JSON')
    fixed_params = Column(Text, comment='固定超参值JSON')

    best_params = Column(Text, comment='该节点最佳超参')
    best_trial_id = Column(String(64), comment='该节点最佳试验ID')
    best_objective_value = Column(Float, comment='该节点最佳目标值')

    applied_to_training = Column(Boolean, default=False, comment='是否已应用到训练')
    applied_time = Column(DateTime, comment='应用时间')

    tenant_id = Column(BigInteger, default=0, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('uk_study_node', 'study_id', 'node_id', unique=True),
        Index('idx_node', 'node_id'),
        Index('idx_tenant', 'tenant_id'),
    )


# ============================================================
# 采集器/传感器设备健康监控模块 ORM 模型
# ============================================================

class CollectorHeartbeat(Base):
    """
    采集器心跳表模型

    对应数据库表: sc_collector_heartbeat
    存储采集器/传感器的心跳状态，包括最后数据时间、预期采样间隔、连续缺失次数等。
    用于判定设备离线、卡死、跳变等异常。
    """
    __tablename__ = 'sc_collector_heartbeat'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    collector_id = Column(String(100), nullable=False, comment='采集器ID')
    sensor_id = Column(String(100), nullable=False, comment='传感器/螺栓ID')
    device_type = Column(String(20), default='collector', comment='设备类型 collector/sensor')
    device_name = Column(String(200), comment='设备名称')

    last_data_time = Column(DateTime, comment='最后收到数据的时间')
    expected_interval_seconds = Column(Float, default=60.0, comment='预期采样间隔（秒）')
    consecutive_missing_count = Column(Integer, default=0, comment='连续缺失次数')

    last_value = Column(Float, comment='最后一次采样的数值')
    previous_value = Column(Float, comment='倒数第二次采样的数值')
    stuck_count = Column(Integer, default=0, comment='连续数值不变次数')
    jump_count = Column(Integer, default=0, comment='跳变次数')

    health_status = Column(String(20), default='healthy', comment='健康状态 healthy/offline/stuck/jump/degraded')
    fault_types = Column(Text, comment='当前故障类型列表 JSON，如 ["offline","jump"]')
    last_fault_time = Column(DateTime, comment='最近一次故障发生时间')
    recovery_time = Column(DateTime, comment='最近一次恢复时间')

    confidence_penalty = Column(Float, default=1.0, comment='置信度惩罚系数 0-1，1=无惩罚')
    excluded_from_training = Column(Boolean, default=False, comment='是否排除出训练数据')

    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_hb_collector', 'collector_id'),
        Index('idx_hb_sensor', 'sensor_id'),
        Index('idx_hb_collector_sensor', 'collector_id', 'sensor_id', unique=True),
        Index('idx_hb_status', 'health_status'),
        Index('idx_hb_last_data', 'last_data_time'),
        Index('idx_hb_excluded', 'excluded_from_training'),
        Index('idx_hb_tenant', 'tenant_id'),
    )


class DeviceFaultAlert(Base):
    """
    设备故障告警表模型

    对应数据库表: sc_device_fault_alerts
    存储 device_fault 类型的设备异常告警，与预紧力预警区分。
    告警类型包括离线(offline)、卡死(stuck)、跳变(jump)。
    """
    __tablename__ = 'sc_device_fault_alerts'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    alert_no = Column(String(50), unique=True, comment='告警编号')
    collector_id = Column(String(100), nullable=False, comment='采集器ID')
    sensor_id = Column(String(100), nullable=False, comment='传感器/螺栓ID')

    fault_type = Column(String(20), nullable=False, comment='故障类型 offline/stuck/jump')
    fault_level = Column(Integer, default=2, comment='故障级别 1=提示 2=警告 3=严重 4=紧急')

    title = Column(String(200), comment='告警标题')
    content = Column(Text, comment='告警内容')
    evidence = Column(Text, comment='故障证据 JSON')

    last_value = Column(Float, comment='最后采样值')
    expected_value_range = Column(String(100), comment='期望值范围 JSON')
    offline_duration_seconds = Column(Float, comment='离线时长（秒）')
    consecutive_missing = Column(Integer, comment='连续缺失次数')
    stuck_count = Column(Integer, comment='卡死次数')
    jump_magnitude = Column(Float, comment='跳变幅度')

    status = Column(String(20), default='pending', comment='状态 pending/acknowledged/resolved/ignored')
    handler_id = Column(String(50), comment='处理人ID')
    handler_name = Column(String(100), comment='处理人姓名')
    handle_time = Column(DateTime, comment='处理时间')
    handle_note = Column(Text, comment='处理备注')

    silence_until = Column(DateTime, comment='静默截止时间')
    is_auto_resolved = Column(Boolean, default=False, comment='是否自动恢复')

    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_dfa_collector', 'collector_id'),
        Index('idx_dfa_sensor', 'sensor_id'),
        Index('idx_dfa_fault_type', 'fault_type'),
        Index('idx_dfa_status', 'status'),
        Index('idx_dfa_time', 'create_time'),
        Index('idx_dfa_level', 'fault_level'),
        Index('idx_dfa_tenant', 'tenant_id'),
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


from app.utils.db_pool import db_pool


@contextmanager
def get_db(read_only: bool = False) -> Generator[Optional[Session], None, None]:
    """
    获取数据库会话的上下文管理器

    统一委托给 DatabasePool 单例，所有 Repository / Service 经同一入口获取 Session。

    Args:
        read_only: 是否使用只读从库（需启用读写分离）

    Yields:
        Session: 数据库会话，如果不可用则为None

    Example:
        with get_db() as db:
            if db is not None:
                data = db.query(BoltData).all()

        with get_db(read_only=True) as db:
            data = db.query(BoltData).all()
    """
    with db_pool.get_session(read_only=read_only) as session:
        yield session


def get_bolt_recent_data(sensor_id: int, limit: int = 100) -> List[BoltData]:
    """
    获取螺栓最近的预紧力数据（双数据源策略）

    - 若启用了时序库，优先时序库读取（包装成 BoltData 兼容对象）
    - 否则从 MySQL 读取

    Args:
        sensor_id: 螺栓/传感器ID
        limit: 获取记录数量，默认100

    Returns:
        List[BoltData]: 预紧力数据列表（兼容对象）
    """
    if _is_timeseries_enabled_for_history():
        try:
            result = _get_bolt_recent_from_timeseries(sensor_id=sensor_id, limit=limit)
            if result:
                logger.debug(f"get_bolt_recent_data [{sensor_id}]: 时序库读取 {len(result)} 条")
                return result
        except Exception as e:
            logger.warning(f"时序库读取螺栓 {sensor_id} 最近数据失败，回退 MySQL: {e}")

    return _get_bolt_recent_from_mysql(sensor_id=sensor_id, limit=limit)


def _get_bolt_recent_from_mysql(sensor_id: int, limit: int) -> List[BoltData]:
    """从 MySQL 获取螺栓最近数据（原始实现）"""
    with get_db() as db:
        return db.query(BoltData).filter(
            BoltData.sensor_id == sensor_id
        ).order_by(
            BoltData.create_time.desc()
        ).limit(limit).all()


def _get_bolt_recent_from_timeseries(sensor_id: int, limit: int) -> List:
    """从时序库获取螺栓最近数据（包装为 BoltData 兼容对象）"""
    from app.timeseries.factory import create_timeseries_repository

    repo = create_timeseries_repository()
    if repo is None:
        return []

    window = repo.query_prediction_window(sensor_id=str(sensor_id), window_size=limit)
    if window is None or len(window['data']) == 0:
        return []

    values = window['data']
    timestamps = window['timestamps']

    # 时序库返回升序，BoltData调用方通常习惯create_time DESC
    result = []
    for i in range(len(values) - 1, -1, -1):
        obj = _BoltDataCompat(
            sensor_id=int(sensor_id),
            ptf=float(values[i]),
            create_time=timestamps[i] if hasattr(timestamps[i], 'year') else datetime.fromisoformat(str(timestamps[i]))
        )
        result.append(obj)
    return result


def get_flange_recent_data(flange_id: str, limit_per_bolt: int = 200) -> List[BoltData]:
    """
    获取法兰面所有螺栓最近的预紧力数据（双数据源策略）

    - 若启用了时序库，优先时序库读取
    - 否则从 MySQL 读取

    Args:
        flange_id: 法兰面ID (格式: collector_id-splitter_num-position)
        limit_per_bolt: 每个螺栓获取的记录数量，默认200

    Returns:
        List[BoltData]: 预紧力数据列表
    """
    if _is_timeseries_enabled_for_history():
        try:
            result = _get_flange_recent_from_timeseries(
                flange_id=flange_id, limit_per_bolt=limit_per_bolt
            )
            if result:
                logger.debug(f"get_flange_recent_data [{flange_id}]: 时序库读取 {len(result)} 条")
                return result
        except Exception as e:
            logger.warning(f"时序库读取法兰面 {flange_id} 最近数据失败，回退 MySQL: {e}")

    return _get_flange_recent_from_mysql(flange_id=flange_id, limit_per_bolt=limit_per_bolt)


def _get_flange_recent_from_mysql(flange_id: str, limit_per_bolt: int) -> List:
    """从 MySQL 获取法兰面最近数据（原始实现）"""
    parts = flange_id.split('-')
    if len(parts) < 3:
        raise ValueError(f"无效的法兰面ID格式: {flange_id}")

    collector_id = int(parts[0])
    splitter_num = int(parts[1])
    position = '-'.join(parts[2:])

    with get_db() as db:
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


def _get_flange_recent_from_timeseries(flange_id: str, limit_per_bolt: int) -> List:
    """从时序库获取法兰面数据（需先从MySQL查到螺栓ID列表）"""
    from app.timeseries.factory import create_timeseries_repository

    repo = create_timeseries_repository()
    if repo is None:
        return []

    # 从 MySQL 查询该法兰面的 bolt sensor_id 列表
    parts = flange_id.split('-')
    if len(parts) < 3:
        raise ValueError(f"无效的法兰面ID格式: {flange_id}")
    collector_id = int(parts[0])
    splitter_num = int(parts[1])
    position = '-'.join(parts[2:])

    with get_db() as db:
        from sqlalchemy import text
        q = text("""
            SELECT DISTINCT sensor_id
            FROM sc_bolt_data
            WHERE collector_id = :c AND splitter_num = :s AND position = :p
        """)
        rows = db.execute(q, {'c': collector_id, 's': splitter_num, 'p': position}).fetchall()
        sensor_ids = [str(r.sensor_id) for r in rows]

    result = []
    for sid in sensor_ids:
        try:
            window = repo.query_prediction_window(sensor_id=sid, window_size=limit_per_bolt)
            if window is None:
                continue
            values = window['data']
            timestamps = window['timestamps']
            for i in range(len(values) - 1, -1, -1):
                ts = timestamps[i] if hasattr(timestamps[i], 'year') else datetime.fromisoformat(str(timestamps[i]))
                obj = _BoltDataCompat(
                    sensor_id=int(sid),
                    ptf=float(values[i]),
                    create_time=ts,
                    collector_id=collector_id,
                    splitter_num=splitter_num,
                    position=position,
                )
                result.append(obj)
        except Exception as e:
            logger.warning(f"时序库读取法兰面 {flange_id} 下螺栓 {sid} 失败: {e}")
    return result


# ============================================================
# 时序库启用判断 & 兼容对象（内部实现）
# ============================================================

def _is_timeseries_enabled_for_history() -> bool:
    """检查是否启用了时序库用于历史查询"""
    return bool(config.get('timeseries.enabled', False))


class _BoltDataCompat:
    """
    BoltData 兼容对象（Duck Typing）

    包装时序库返回的数据点，使其具备与 SQLAlchemy BoltData ORM 对象
    相同的属性访问接口（.sensor_id / .ptf / .create_time 等），
    从而让历史调用方无需任何改动即可使用时序库数据。
    """

    __slots__ = ('sensor_id', 'ptf', 'create_time', 'id',
                 'collector_id', 'splitter_num', 'position',
                 'temperature', 'humidity', 'vibration',
                 'torque', 'pressure', 'data_quality')

    def __init__(self, **kwargs):
        self.sensor_id = kwargs.get('sensor_id')
        self.ptf = kwargs.get('ptf')
        self.create_time = kwargs.get('create_time')
        self.id = kwargs.get('id')
        self.collector_id = kwargs.get('collector_id')
        self.splitter_num = kwargs.get('splitter_num')
        self.position = kwargs.get('position')
        self.temperature = kwargs.get('temperature')
        self.humidity = kwargs.get('humidity')
        self.vibration = kwargs.get('vibration')
        self.torque = kwargs.get('torque')
        self.pressure = kwargs.get('pressure')
        self.data_quality = kwargs.get('data_quality', 'full')

    def __repr__(self):
        return (f"<_BoltDataCompat sensor_id={self.sensor_id} "
                f"ptf={self.ptf} create_time={self.create_time}>")


# ============================================================
# 时序数据冷热归档与分区模块 ORM 模型
# ============================================================

class ArchivePartitionKey(Base):
    """
    归档分区键定义表模型

    对应数据库表: sc_archive_partition_keys
    定义按月分区的分区键信息，用于 MySQL 按月分区表的元数据管理。
    每个分区代表一个自然月的数据。
    """
    __tablename__ = 'sc_archive_partition_keys'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, comment='租户ID')
    table_name = Column(String(100), nullable=False, comment='源表名，如 sc_bolt_data')
    partition_name = Column(String(100), nullable=False, comment='分区名，如 p202501')
    partition_key = Column(String(7), nullable=False, comment='年月分区键 YYYY-MM')
    partition_value = Column(Integer, nullable=False, comment='分区数值 YYYYMM')
    start_date = Column(DateTime, nullable=False, comment='分区起始时间（含）')
    end_date = Column(DateTime, nullable=False, comment='分区结束时间（不含）')
    row_count = Column(BigInteger, default=0, comment='分区内数据行数')
    data_size_bytes = Column(BigInteger, default=0, comment='分区数据大小（字节）')
    archive_status = Column(String(20), default='hot', comment='归档状态: hot=热数据, archiving=归档中, archived=已归档, restored=已回迁, purged=已清理')
    archive_time = Column(DateTime, comment='归档完成时间')
    purge_time = Column(DateTime, comment='从MySQL清理时间')
    retention_expire_time = Column(DateTime, comment='保留期限到期时间（超期后从冷存储删除）')
    is_active = Column(Boolean, default=True, comment='分区是否有效')
    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('uk_tenant_table_partition', 'tenant_id', 'table_name', 'partition_name', unique=True),
        Index('idx_tenant_table', 'tenant_id', 'table_name'),
        Index('idx_archive_status', 'archive_status'),
        Index('idx_partition_key', 'partition_key'),
        Index('idx_retention_expire', 'retention_expire_time'),
        Index('idx_archive_time', 'archive_time'),
        Index('idx_tenant', 'tenant_id'),
    )


class ArchiveMetadata(Base):
    """
    归档元数据索引表模型

    对应数据库表: sc_archive_metadata
    记录每个归档文件（Parquet）的元数据索引，仍保存在 MySQL 中。
    用于快速定位冷数据在对象存储中的位置，实现透明查询路由。
    """
    __tablename__ = 'sc_archive_metadata'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    archive_id = Column(String(64), unique=True, nullable=False, comment='归档唯一ID (UUID)')
    tenant_id = Column(BigInteger, nullable=False, comment='租户ID')
    source_table = Column(String(100), nullable=False, comment='源表名')
    partition_name = Column(String(100), comment='关联的分区名')
    partition_key = Column(String(7), comment='年月分区键 YYYY-MM')

    sensor_id = Column(String(100), comment='传感器/螺栓ID（单传感器归档则有值）')
    sensor_ids = Column(Text, comment='包含的传感器ID列表 JSON（批量归档）')
    data_start_time = Column(DateTime, nullable=False, comment='归档数据起始时间（含）')
    data_end_time = Column(DateTime, nullable=False, comment='归档数据结束时间（含）')
    row_count = Column(BigInteger, nullable=False, comment='归档数据行数')
    file_size_bytes = Column(BigInteger, nullable=False, comment='Parquet文件大小（字节）')

    storage_type = Column(String(20), default='s3', comment='冷存储类型: s3/oss/minio/local_filesystem/timescaledb_cold')
    storage_bucket = Column(String(200), comment='存储桶名')
    storage_path = Column(String(500), nullable=False, comment='对象存储路径或文件路径')
    file_checksum = Column(String(128), comment='文件校验和 (SHA256)')
    compression = Column(String(20), default='snappy', comment='压缩算法: snappy/gzip/zstd/none')
    schema_version = Column(String(20), default='v1', comment='Parquet Schema版本')

    aggregation_level = Column(String(20), default='raw', comment='数据聚合级别: raw/minute/hour')
    fields = Column(Text, comment='包含的字段列表 JSON')
    tags = Column(Text, comment='标签维度 JSON')
    statistics = Column(Text, comment='统计摘要 JSON: min/max/mean/count/null_count per field')

    job_id = Column(String(64), comment='关联的归档任务ID')
    status = Column(String(20), default='active', comment='状态: active/deleted/restored/corrupted')
    restore_time = Column(DateTime, comment='最近一次回迁时间')
    restore_count = Column(Integer, default=0, comment='回迁次数')
    last_access_time = Column(DateTime, comment='最后访问时间（懒加载记录）')
    access_count = Column(Integer, default=0, comment='访问次数')

    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_tenant_table_range', 'tenant_id', 'source_table', 'data_start_time', 'data_end_time'),
        Index('idx_tenant_sensor_range', 'tenant_id', 'sensor_id', 'data_start_time', 'data_end_time'),
        Index('idx_partition_key', 'partition_key'),
        Index('idx_storage_path', 'storage_bucket', 'storage_path'),
        Index('idx_archive_status', 'status'),
        Index('idx_last_access', 'last_access_time'),
        Index('idx_archive_id', 'archive_id'),
        Index('idx_tenant', 'tenant_id'),
    )


class ArchiveJob(Base):
    """
    归档任务执行日志表模型

    对应数据库表: sc_archive_jobs
    记录每次归档任务的执行详情，包括配置、进度、结果、错误信息。
    """
    __tablename__ = 'sc_archive_jobs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, comment='任务唯一ID (UUID)')
    tenant_id = Column(BigInteger, comment='租户ID，空表示全局任务')
    job_name = Column(String(200), nullable=False, comment='任务名称')
    job_type = Column(String(30), nullable=False, comment='任务类型: archive_monthly/archive_custom/purge_expired/restore/verify')
    trigger_type = Column(String(20), default='scheduled', comment='触发类型: scheduled/manual/api')

    source_table = Column(String(100), comment='源表名')
    target_storage = Column(String(20), comment='目标存储类型')
    partition_key = Column(String(7), comment='目标分区键 YYYY-MM')
    partitions = Column(Text, comment='涉及的分区键列表 JSON')
    sensor_ids = Column(Text, comment='指定传感器ID列表 JSON，空表示全部')

    hot_threshold_days = Column(Integer, comment='热数据保留天数（超过此天数的归档）')
    retention_days = Column(Integer, comment='总保留天数（超期从冷存储删除）')
    delete_from_hot = Column(Boolean, default=True, comment='归档后是否从MySQL删除热数据')

    status = Column(String(20), default='pending', comment='状态: pending/running/completed/failed/cancelled/paused')
    start_time = Column(DateTime, nullable=False, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    duration_seconds = Column(Integer, comment='执行时长（秒）')

    total_partitions = Column(Integer, default=0, comment='总分区数')
    processed_partitions = Column(Integer, default=0, comment='已处理分区数')
    total_rows = Column(BigInteger, default=0, comment='总数据行数')
    archived_rows = Column(BigInteger, default=0, comment='已归档行数')
    failed_rows = Column(BigInteger, default=0, comment='失败行数')
    deleted_rows = Column(BigInteger, default=0, comment='从热库删除行数')

    archive_size_bytes = Column(BigInteger, default=0, comment='归档数据总大小（字节）')
    archive_file_count = Column(Integer, default=0, comment='生成的归档文件数')
    storage_cost_saved = Column(Float, comment='估算节省的存储成本（元）')

    error_count = Column(Integer, default=0, comment='错误数')
    error_summary = Column(Text, comment='错误摘要 JSON')
    error_details = Column(Text, comment='详细错误信息 JSON')

    config_snapshot = Column(Text, comment='任务配置快照 JSON')
    created_by = Column(String(100), comment='创建人（手动触发时）')
    cron_expression = Column(String(100), comment='关联的 cron 表达式（定时任务）')

    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_job_id', 'job_id'),
        Index('idx_tenant_job_type', 'tenant_id', 'job_type'),
        Index('idx_job_status', 'status'),
        Index('idx_job_start_time', 'start_time'),
        Index('idx_partition_key', 'partition_key'),
        Index('idx_tenant', 'tenant_id'),
    )


class TenantRetentionPolicy(Base):
    """
    租户级保留策略表模型

    对应数据库表: sc_tenant_retention_policies
    定义每个租户的冷热数据保留策略：
    - 合规要求（如7年） vs 运营要求（如1年）
    - 可按数据表和聚合级别分别设置
    """
    __tablename__ = 'sc_tenant_retention_policies'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, nullable=False, comment='租户ID')
    policy_name = Column(String(200), nullable=False, comment='策略名称')
    policy_type = Column(String(30), nullable=False, comment='策略类型: compliance=合规策略/operations=运营策略/custom=自定义')
    description = Column(String(500), comment='策略描述')

    is_default = Column(Boolean, default=False, comment='是否为默认策略')
    is_active = Column(Boolean, default=True, comment='是否启用')
    priority = Column(Integer, default=0, comment='优先级（数值大优先）')

    scope_table = Column(String(100), comment='适用表名，空表示全部时序表')
    scope_sensor_ids = Column(Text, comment='适用传感器ID列表 JSON，空表示全部')
    scope_aggregation_level = Column(String(20), comment='适用聚合级别: raw/minute/hour/all')

    hot_retention_days = Column(Integer, nullable=False, default=90, comment='热数据保留天数（MySQL中保留的天数）')
    cold_retention_days = Column(Integer, nullable=False, default=365, comment='冷数据保留天数（对象存储中总保留天数）')
    compliance_retention_years = Column(Integer, comment='合规要求保留年数（如7年，超期后彻底删除）')

    archive_cron = Column(String(50), default='0 3 1 * *', comment='归档任务 cron 表达式，默认每月1日凌晨3点')
    purge_cron = Column(String(50), default='0 4 1 * *', comment='过期清理任务 cron 表达式')
    auto_delete_hot = Column(Boolean, default=True, comment='归档完成后自动删除热数据')
    lazy_load_enabled = Column(Boolean, default=True, comment='是否启用冷数据懒加载')

    storage_class = Column(String(20), default='standard_ia', comment='冷存储等级: standard/standard_ia/glacier/deep_archive')
    compression_algo = Column(String(20), default='snappy', comment='Parquet压缩算法')
    encryption_enabled = Column(Boolean, default=True, comment='是否加密归档文件')

    effective_from = Column(DateTime, comment='生效起始时间')
    effective_to = Column(DateTime, comment='生效截止时间')
    version = Column(Integer, default=1, comment='策略版本号')
    change_reason = Column(String(500), comment='变更原因')

    created_by = Column(String(100), comment='创建人')
    approved_by = Column(String(100), comment='审批人（合规策略需要审批）')
    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('uk_tenant_policy_name', 'tenant_id', 'policy_name', unique=True),
        Index('idx_tenant_policy_type', 'tenant_id', 'policy_type', 'is_active'),
        Index('idx_policy_active', 'is_active'),
        Index('idx_default_policy', 'tenant_id', 'is_default'),
        Index('idx_policy_table', 'scope_table'),
        Index('idx_tenant', 'tenant_id'),
    )


class ColdDataLoadRequest(Base):
    """
    冷数据懒加载请求记录表模型

    对应数据库表: sc_cold_data_load_requests
    记录历史分析API触发的冷数据懒加载请求，用于审计和性能统计。
    支持异步加载 + 状态追踪。
    """
    __tablename__ = 'sc_cold_data_load_requests'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, nullable=False, comment='请求唯一ID (UUID)')
    tenant_id = Column(BigInteger, nullable=False, comment='租户ID')
    user_id = Column(String(100), comment='触发用户ID')
    user_type = Column(String(20), default='api', comment='触发来源: api/user/training/analysis')
    api_endpoint = Column(String(200), comment='触发的 API 端点')

    source_table = Column(String(100), nullable=False, comment='查询的源表名')
    sensor_id = Column(String(100), comment='传感器ID')
    sensor_ids = Column(Text, comment='传感器ID列表 JSON')
    query_start_time = Column(DateTime, nullable=False, comment='查询起始时间')
    query_end_time = Column(DateTime, nullable=False, comment='查询结束时间')
    aggregation_level = Column(String(20), default='raw', comment='请求的聚合级别')

    hot_data_range = Column(Text, comment='命中热数据的时间范围 JSON')
    cold_data_ranges = Column(Text, comment='需要懒加载的冷数据时间范围列表 JSON')
    archive_ids = Column(Text, comment='涉及的归档ID列表 JSON')
    partition_keys = Column(Text, comment='涉及的分区键列表 JSON')

    status = Column(String(20), default='pending', comment='状态: pending/loading/completed/failed/partial')
    priority = Column(String(10), default='normal', comment='优先级: low/normal/high/critical')
    async_mode = Column(Boolean, default=False, comment='是否异步加载')

    start_time = Column(DateTime, comment='开始加载时间')
    end_time = Column(DateTime, comment='加载完成时间')
    duration_seconds = Column(Float, comment='加载耗时（秒）')

    hot_row_count = Column(BigInteger, default=0, comment='热数据行数')
    cold_row_count = Column(BigInteger, default=0, comment='冷数据行数（已加载）')
    total_row_count = Column(BigInteger, default=0, comment='总数据行数')
    cold_file_count = Column(Integer, default=0, comment='读取的冷文件数')
    cold_bytes_loaded = Column(BigInteger, default=0, comment='从冷存储读取的字节数')

    restore_to_hot = Column(Boolean, default=False, comment='是否将冷数据回迁到热库')
    restore_expire_hours = Column(Integer, default=72, comment='回迁数据在热库的过期时间（小时）')
    cache_hit = Column(Boolean, default=False, comment='是否命中回迁缓存')

    error_message = Column(Text, comment='错误信息')
    request_params = Column(Text, comment='原始请求参数 JSON')
    extra_info = Column(Text, comment='扩展信息 JSON')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_request_id', 'request_id'),
        Index('idx_tenant_user', 'tenant_id', 'user_id'),
        Index('idx_tenant_query_range', 'tenant_id', 'source_table', 'query_start_time', 'query_end_time'),
        Index('idx_load_status', 'status'),
        Index('idx_load_priority', 'priority'),
        Index('idx_create_time', 'create_time'),
        Index('idx_sensor_range', 'sensor_id', 'query_start_time', 'query_end_time'),
        Index('idx_tenant', 'tenant_id'),
    )


class FeatureSchemaVersion(Base):
    """
    特征 Schema 版本表模型

    对应数据库表: sc_feature_schema_versions
    管理特征向量的结构定义，保证训练和推理使用一致的特征结构。
    """
    __tablename__ = 'sc_feature_schema_versions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    version = Column(String(20), nullable=False, unique=True, comment='特征版本号，如 v1.0, v1.1')
    dimension = Column(Integer, nullable=False, comment='特征维度数量')
    feature_names = Column(Text, nullable=False, comment='特征名称列表 JSON，按顺序排列')
    feature_types = Column(Text, comment='特征类型列表 JSON，如 ["numeric", "numeric", "categorical"]')
    description = Column(Text, comment='版本变更说明')
    is_active = Column(Boolean, default=True, comment='是否为当前活跃版本')
    compatible_versions = Column(Text, comment='兼容的旧版本列表 JSON，如 ["v1.0"]')
    breaking_change = Column(Boolean, default=False, comment='是否为不兼容变更')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_schema_version', 'version'),
        Index('idx_schema_active', 'is_active'),
        Index('idx_schema_tenant', 'tenant_id'),
    )


class FeatureSnapshot(Base):
    """
    特征快照表模型

    对应数据库表: sc_feature_snapshots
    存储每次计算的特征向量快照，用于训练复现和推理分析。
    """
    __tablename__ = 'sc_feature_snapshots'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    node_id = Column(String(100), nullable=False, comment='节点ID（螺栓ID或法兰面ID')
    node_type = Column(String(20), nullable=False, comment='节点类型 bolt/flange')
    compute_time = Column(DateTime, nullable=False, comment='特征计算时间（对应数据窗口的结束时间）')
    feature_version = Column(String(20), nullable=False, comment='特征版本号')
    vector = Column(Text, comment='特征向量 JSON 格式（便于调试）')
    vector_bin = Column(BINARY, comment='特征向量二进制格式（节省存储空间）')
    vector_dim = Column(Integer, comment='特征维度，用于快速校验')
    source_window_hash = Column(String(64), comment='输入数据窗口的哈希值，用于数据溯源和去重')
    source_window_start = Column(DateTime, comment='输入数据窗口起始时间')
    source_window_end = Column(DateTime, comment='输入数据窗口结束时间')
    data_source = Column(String(50), comment='数据来源：training/inference/debug')
    model_version = Column(String(50), comment='关联的模型版本（推理时）')
    prediction_result = Column(Text, comment='关联的预测结果快照 JSON（推理时）')
    is_used_for_training = Column(Boolean, default=False, comment='是否已用于训练')
    training_session_id = Column(String(100), comment='关联的训练会话ID')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_feature_node', 'node_type', 'node_id'),
        Index('idx_feature_compute_time', 'compute_time'),
        Index('idx_feature_version', 'feature_version'),
        Index('idx_feature_window_hash', 'source_window_hash'),
        Index('idx_feature_source', 'data_source'),
        Index('idx_feature_training', 'is_used_for_training', 'training_session_id'),
        Index('idx_feature_tenant_node', 'tenant_id', 'node_type', 'node_id'),
        Index('idx_feature_tenant_time', 'tenant_id', 'create_time'),
        Index('idx_feature_unique', 'node_id', 'compute_time', 'feature_version', 'source_window_hash', unique=True),
    )


# ============================================================
# 模型漂移检测模块 ORM 模型
# ============================================================

class ModelDriftConfig(Base):
    """
    模型漂移检测配置表模型

    对应数据库表: sc_model_drift_config
    定义每个模型的漂移检测参数和响应策略。
    """
    __tablename__ = 'sc_model_drift_config'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_id = Column(String(100), nullable=False, comment='模型标识')
    model_type = Column(String(20), nullable=False, comment='模型类型 bolt/flange')
    version = Column(String(20), comment='版本号，NULL表示对所有版本生效')
    enabled = Column(Boolean, default=True, comment='是否启用漂移检测')
    response_strategy = Column(String(20), default='notify', comment='响应策略: notify/shadow_retrain/auto_retrain')
    psi_threshold = Column(Float, default=0.2, comment='PSI(数据分布漂移)阈值')
    ks_threshold = Column(Float, default=0.05, comment='KS检验p值阈值(低于则判定漂移)')
    confidence_drift_threshold = Column(Float, default=0.15, comment='置信度分布漂移阈值(KS统计量)')
    false_positive_rate_threshold = Column(Float, default=0.10, comment='误报率阈值')
    false_positive_window_days = Column(Integer, default=7, comment='误报率统计窗口(天)')
    feature_mean_shift_threshold = Column(Float, default=0.10, comment='特征均值偏移阈值(标准差倍数)')
    composite_score_threshold = Column(Float, default=0.6, comment='综合漂移分数阈值')
    consecutive_days_alert = Column(Integer, default=2, comment='连续N天超阈值才触发响应')
    shadow_retrain_quality_bar = Column(Float, default=0.9, comment='Shadow模型最低质量门槛(相对当前版本%)')
    auto_retrain_min_days = Column(Integer, default=7, comment='自动重训最小间隔天数')
    weights_json = Column(Text, comment='各维度权重配置 JSON')
    notify_channels = Column(Text, comment='通知渠道列表 JSON')
    notify_targets = Column(Text, comment='通知目标列表 JSON')
    extra_config = Column(Text, comment='扩展配置 JSON')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_drift_config_model', 'model_id', 'model_type', 'version', 'tenant_id', unique=True),
        Index('idx_drift_config_tenant', 'tenant_id'),
        Index('idx_drift_config_enabled', 'enabled'),
    )

    @property
    def weights(self) -> Dict[str, float]:
        """解析 weights_json 为字典"""
        import json as _json
        try:
            return _json.loads(self.weights_json) if self.weights_json else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def thresholds(self) -> Dict[str, float]:
        """聚合各阈值字段为字典（供API返回）"""
        return {
            "psi": self.psi_threshold,
            "ks_p_value": self.ks_threshold,
            "confidence_drift": self.confidence_drift_threshold,
            "false_positive_rate": self.false_positive_rate_threshold,
            "false_positive_window_days": self.false_positive_window_days,
            "feature_mean_shift": self.feature_mean_shift_threshold,
            "composite_score": self.composite_score_threshold,
        }

    @property
    def notify_channels_list(self) -> List[str]:
        """解析 notify_channels 为列表"""
        import json as _json
        try:
            return _json.loads(self.notify_channels) if self.notify_channels else []
        except (_json.JSONDecodeError, TypeError):
            return []

    @property
    def created_at(self):
        """create_time 的别名"""
        return self.create_time

    @property
    def updated_at(self):
        """update_time 的别名"""
        return self.update_time


class ModelDriftBaseline(Base):
    """
    模型漂移基线表模型

    对应数据库表: sc_model_drift_baselines
    存储模型训练时的基准分布，用于漂移对比。
    """
    __tablename__ = 'sc_model_drift_baselines'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_id = Column(String(100), nullable=False, comment='模型标识')
    model_type = Column(String(20), nullable=False, comment='模型类型 bolt/flange')
    version = Column(String(20), nullable=False, comment='版本号')
    baseline_type = Column(String(30), nullable=False, comment='基线类型: data_distribution/confidence_distribution/feature_stats')
    feature_name = Column(String(100), comment='特征名(per-feature基线)')
    bins_json = Column(Text, comment='分箱边界和计数 JSON')
    stats_json = Column(Text, comment='统计量 JSON(均值/方差/分位数等)')
    sample_count = Column(Integer, comment='基线样本量')
    computed_at = Column(DateTime, comment='基线计算时间')
    data_window_start = Column(DateTime, comment='基线数据窗口起始')
    data_window_end = Column(DateTime, comment='基线数据窗口结束')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_drift_baseline_unique', 'model_id', 'model_type', 'version', 'baseline_type', 'feature_name', 'tenant_id', unique=True),
        Index('idx_drift_baseline_model', 'model_id', 'model_type', 'version'),
        Index('idx_drift_baseline_tenant', 'tenant_id'),
    )

    @property
    def stats(self) -> Dict:
        """解析 stats_json 为字典"""
        import json as _json
        try:
            return _json.loads(self.stats_json) if self.stats_json else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def bins(self) -> Dict:
        """解析 bins_json 为字典"""
        import json as _json
        try:
            return _json.loads(self.bins_json) if self.bins_json else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def created_at(self):
        """create_time 的别名"""
        return self.create_time


class ModelDriftEvent(Base):
    """
    模型漂移事件表模型

    对应数据库表: sc_model_drift_events
    记录每次漂移检测的结果和触发的响应。
    """
    __tablename__ = 'sc_model_drift_events'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_no = Column(String(50), unique=True, comment='事件编号')
    model_id = Column(String(100), nullable=False, comment='模型标识')
    model_type = Column(String(20), nullable=False, comment='模型类型 bolt/flange')
    version = Column(String(20), comment='模型版本')
    detection_date = Column(Date, nullable=False, comment='检测日期(批处理日期)')
    psi_score = Column(Float, comment='PSI分数(数据分布漂移)')
    ks_p_value = Column(Float, comment='KS检验p值')
    ks_statistic = Column(Float, comment='KS检验统计量')
    confidence_drift_score = Column(Float, comment='置信度分布漂移分数(KS统计量)')
    confidence_ks_p_value = Column(Float, comment='置信度分布KS检验p值')
    false_positive_rate = Column(Float, comment='误报率')
    false_positive_count = Column(Integer, comment='误报样本数')
    total_prediction_count = Column(Integer, comment='总预测样本数')
    feature_drift_json = Column(Text, comment='各特征漂移详情 JSON')
    feature_mean_shift_count = Column(Integer, comment='特征均值偏移的特征数')
    composite_drift_score = Column(Float, comment='综合漂移分数(加权平均)')
    drift_level = Column(String(20), default='none', comment='漂移等级: none/low/medium/high/critical')
    triggered_dims = Column(Text, comment='触发告警的漂移维度 JSON')
    consecutive_days = Column(Integer, default=1, comment='连续超阈值天数')
    response_action = Column(String(20), default='none', comment='实际执行的响应动作: none/notify/shadow_retrain/auto_retrain')
    response_status = Column(String(20), default='pending', comment='响应状态: pending/running/completed/failed/skipped')
    response_details = Column(Text, comment='响应详情 JSON(训练会话ID等)')
    notification_sent = Column(Boolean, default=False, comment='是否已发送通知')
    retrain_session_id = Column(String(100), comment='重训会话ID')
    new_version = Column(String(20), comment='重训产生的新版本号')
    alert_level = Column(Integer, default=2, comment='告警级别 1-4')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_drift_event_model_date', 'model_id', 'model_type', 'detection_date'),
        Index('idx_drift_event_date', 'detection_date'),
        Index('idx_drift_event_level', 'drift_level'),
        Index('idx_drift_event_action', 'response_action', 'response_status'),
        Index('idx_drift_event_tenant_date', 'tenant_id', 'detection_date'),
        Index('idx_drift_event_tenant_model', 'tenant_id', 'model_id', 'model_type'),
    )

    @property
    def feature_drift(self) -> Dict:
        """解析 feature_drift_json 为字典"""
        import json as _json
        try:
            return _json.loads(self.feature_drift_json) if self.feature_drift_json else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def triggered_dimensions(self) -> List[str]:
        """解析 triggered_dims 为列表"""
        import json as _json
        try:
            return _json.loads(self.triggered_dims) if self.triggered_dims else []
        except (_json.JSONDecodeError, TypeError):
            return []

    @property
    def response_detail_dict(self) -> Dict:
        """解析 response_details 为字典"""
        import json as _json
        try:
            return _json.loads(self.response_details) if self.response_details else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def composite_score(self) -> Optional[float]:
        """composite_drift_score 的别名"""
        return self.composite_drift_score

    @property
    def is_alert(self) -> bool:
        """是否告警（drift_level != 'none' 且 triggered_dimensions 非空）"""
        if self.drift_level and self.drift_level != "none":
            return True
        return bool(self.triggered_dimensions)

    @property
    def response_strategy(self) -> str:
        """response_action 的别名"""
        return self.response_action or "none"

    @property
    def dimension_scores(self) -> List[Dict]:
        """聚合各维度分数供 API 返回"""
        dims = []
        if self.psi_score is not None:
            dims.append({
                "dimension": "psi",
                "score": self.psi_score,
                "threshold": None,
                "is_alert": self.psi_score > 0.2 if self.psi_score else False,
                "details": {},
            })
        if self.ks_statistic is not None or self.ks_p_value is not None:
            dims.append({
                "dimension": "ks",
                "score": self.ks_statistic or 0.0,
                "threshold": None,
                "is_alert": (self.ks_p_value or 1.0) < 0.05,
                "details": {"ks_p_value": self.ks_p_value},
            })
        if self.confidence_drift_score is not None:
            dims.append({
                "dimension": "confidence",
                "score": self.confidence_drift_score,
                "threshold": None,
                "is_alert": self.confidence_drift_score > 0.15 if self.confidence_drift_score else False,
                "details": {"ks_p_value": self.confidence_ks_p_value},
            })
        if self.false_positive_rate is not None:
            dims.append({
                "dimension": "false_positive",
                "score": self.false_positive_rate,
                "threshold": None,
                "is_alert": self.false_positive_rate > 0.10 if self.false_positive_rate else False,
                "details": {
                    "false_positive_count": self.false_positive_count,
                    "total_prediction_count": self.total_prediction_count,
                },
            })
        if self.feature_mean_shift_count is not None and self.feature_mean_shift_count > 0:
            dims.append({
                "dimension": "feature_shift",
                "score": min(1.0, self.feature_mean_shift_count / 10.0) if self.feature_mean_shift_count else 0.0,
                "threshold": None,
                "is_alert": self.feature_mean_shift_count > 0,
                "details": {"shifted_feature_count": self.feature_mean_shift_count},
            })
        return dims

    @property
    def created_at(self):
        """create_time 的别名"""
        return self.create_time

    @property
    def updated_at(self):
        """update_time 的别名"""
        return self.update_time


class ShadowComparison(Base):
    """
    影子模式预测对比记录表模型

    对应数据库表: sc_shadow_comparison
    记录主版本与影子版本的预测结果对比，用于A/B测试与版本晋升评估。
    """
    __tablename__ = 'sc_shadow_comparison'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
    model_type = Column(String(20), nullable=False, comment='模型类型: bolt/flange')
    node_id = Column(String(100), nullable=False, comment='节点ID（螺栓ID或法兰ID）')
    node_type = Column(String(20), comment='节点类型: bolt/flange')
    main_version = Column(String(20), nullable=False, comment='主版本号')
    shadow_version = Column(String(20), nullable=False, comment='影子版本号')

    main_status_code = Column(Integer, nullable=False, comment='主版本状态码 0-4')
    main_status = Column(String(50), comment='主版本状态文本')
    main_confidence = Column(Float, comment='主版本置信度 0-1')

    shadow_status_code = Column(Integer, nullable=False, comment='影子版本状态码 0-4')
    shadow_status = Column(String(50), comment='影子版本状态文本')
    shadow_confidence = Column(Float, comment='影子版本置信度 0-1')

    is_agreement = Column(Boolean, default=False, comment='是否预测一致（状态码相同）')
    is_shadow_more_sensitive = Column(Boolean, default=False, comment='影子版本是否更敏感')
    is_shadow_more_conservative = Column(Boolean, default=False, comment='影子版本是否更保守')

    main_latency_ms = Column(Integer, comment='主版本预测耗时(毫秒)')
    shadow_latency_ms = Column(Integer, comment='影子版本预测耗时(毫秒)')

    prediction_time = Column(DateTime, comment='预测时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_tenant_version_shadow', 'tenant_id', 'model_type', 'main_version', 'shadow_version'),
        Index('idx_node_shadow', 'node_type', 'node_id'),
        Index('idx_prediction_time_shadow', 'prediction_time'),
        Index('idx_agreement_shadow', 'is_agreement'),
        Index('idx_sensitive_shadow', 'is_shadow_more_sensitive'),
        Index('idx_conservative_shadow', 'is_shadow_more_conservative'),
        Index('idx_create_time_shadow', 'create_time'),
        Index('idx_tenant_model_shadow', 'tenant_id', 'model_type'),
    )

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'model_type': self.model_type,
            'node_id': self.node_id,
            'node_type': self.node_type,
            'main_version': self.main_version,
            'shadow_version': self.shadow_version,
            'main_status_code': self.main_status_code,
            'main_status': self.main_status,
            'main_confidence': self.main_confidence,
            'shadow_status_code': self.shadow_status_code,
            'shadow_status': self.shadow_status,
            'shadow_confidence': self.shadow_confidence,
            'is_agreement': self.is_agreement,
            'is_shadow_more_sensitive': self.is_shadow_more_sensitive,
            'is_shadow_more_conservative': self.is_shadow_more_conservative,
            'main_latency_ms': self.main_latency_ms,
            'shadow_latency_ms': self.shadow_latency_ms,
            'prediction_time': self.prediction_time,
            'create_time': self.create_time,
        }


class ModelPromotionSuggestion(Base):
    """
    模型版本晋升建议工单表模型

    对应数据库表: sc_model_promotion_suggestions
    当影子版本满足晋升条件时自动生成的晋升建议工单。
    """
    __tablename__ = 'sc_model_promotion_suggestions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
    model_type = Column(String(20), nullable=False, comment='模型类型: bolt/flange')
    model_id = Column(String(100), nullable=False, comment='模型标识（节点ID）')
    main_version = Column(String(20), nullable=False, comment='当前主版本号')
    shadow_version = Column(String(20), nullable=False, comment='待晋升影子版本号')

    suggestion_no = Column(String(64), unique=True, nullable=False, comment='建议工单编号')
    status = Column(String(20), default='pending', comment='状态: pending/approved/rejected/executed')

    agreement_rate = Column(Float, comment='预测一致率 0-1')
    shadow_more_sensitive_rate = Column(Float, comment='影子版本更敏感率 0-1')
    shadow_more_conservative_rate = Column(Float, comment='影子版本更保守率 0-1')

    main_false_negative_rate = Column(Float, comment='主版本漏报率')
    shadow_false_negative_rate = Column(Float, comment='影子版本漏报率')
    false_negative_improvement_rate = Column(Float, comment='漏报率下降比例')

    shadow_run_days = Column(Integer, comment='影子运行天数')
    total_comparisons = Column(Integer, comment='总对比样本数')

    per_status_stats = Column(Text, comment='按状态分桶统计结果 JSON')
    latency_stats = Column(Text, comment='延迟对比统计 JSON')

    work_order_id = Column(BigInteger, comment='关联的系统工单ID')

    approver_id = Column(String(50), comment='审批人ID')
    approver_name = Column(String(100), comment='审批人姓名')
    approve_time = Column(DateTime, comment='审批时间')
    approve_note = Column(Text, comment='审批备注')

    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_tenant_model_promo', 'tenant_id', 'model_type', 'model_id'),
        Index('idx_versions_promo', 'main_version', 'shadow_version'),
        Index('idx_status_promo', 'status'),
        Index('idx_create_time_promo', 'create_time'),
        Index('idx_tenant_status_promo', 'tenant_id', 'status'),
    )

    @property
    def per_status_stats_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.per_status_stats) if self.per_status_stats else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def latency_stats_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.latency_stats) if self.latency_stats else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'model_type': self.model_type,
            'model_id': self.model_id,
            'main_version': self.main_version,
            'shadow_version': self.shadow_version,
            'suggestion_no': self.suggestion_no,
            'status': self.status,
            'agreement_rate': self.agreement_rate,
            'shadow_more_sensitive_rate': self.shadow_more_sensitive_rate,
            'shadow_more_conservative_rate': self.shadow_more_conservative_rate,
            'main_false_negative_rate': self.main_false_negative_rate,
            'shadow_false_negative_rate': self.shadow_false_negative_rate,
            'false_negative_improvement_rate': self.false_negative_improvement_rate,
            'shadow_run_days': self.shadow_run_days,
            'total_comparisons': self.total_comparisons,
            'per_status_stats': self.per_status_stats_dict,
            'latency_stats': self.latency_stats_dict,
            'work_order_id': self.work_order_id,
            'approver_id': self.approver_id,
            'approver_name': self.approver_name,
            'approve_time': self.approve_time,
            'approve_note': self.approve_note,
            'create_time': self.create_time,
            'update_time': self.update_time,
        }


# ============================================================
# 灾备备份与恢复模块 ORM 模型
# ============================================================

class BackupRecord(Base):
    """
    备份记录表模型

    对应数据库表: sc_backup_records
    存储每次备份的元数据信息，包括大小、组件、checksum、保留策略等。
    """
    __tablename__ = 'sc_backup_records'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键')
    backup_id = Column(String(100), unique=True, nullable=False, comment='备份唯一ID')
    backup_type = Column(String(20), nullable=False, comment='备份类型: incremental(增量)/full(全量)/snapshot(快照)')
    backup_scope = Column(String(50), comment='备份范围: models_config/models_config_db/all')

    status = Column(String(20), default='pending', comment='状态: pending/running/completed/failed/uploading/uploaded')
    progress_percent = Column(Float, default=0.0, comment='进度百分比 0-100')

    size_bytes = Column(BigInteger, default=0, comment='备份文件总大小（字节）')
    compressed_size_bytes = Column(BigInteger, default=0, comment='压缩后大小（字节）')
    component_list = Column(Text, comment='包含的组件列表 JSON, 如 ["models","config","database"]')
    component_sizes = Column(Text, comment='各组件大小明细 JSON')
    file_count = Column(Integer, default=0, comment='文件总数')

    checksum_sha256 = Column(String(128), comment='整体备份包 SHA256 校验和')
    checksum_md5 = Column(String(64), comment='整体备份包 MD5 校验和')
    checksums_detail = Column(Text, comment='单文件校验和明细 JSON')

    retention_policy = Column(String(30), default='standard', comment='保留策略: standard/weekly/monthly/yearly/permanent')
    retention_days = Column(Integer, default=30, comment='保留天数，0=永久')
    expire_time = Column(DateTime, comment='过期时间')

    base_backup_id = Column(String(100), comment='增量备份的基准备份ID')
    backup_chain_id = Column(String(100), comment='备份链ID（同一周内的增量+全量共享）')
    incremental_since = Column(DateTime, comment='增量备份的起始时间点')

    storage_location = Column(String(20), default='local', comment='存储位置: local/s3/minio/oss')
    local_path = Column(String(500), comment='本地存储路径')
    remote_bucket = Column(String(200), comment='远程存储桶名')
    remote_object_key = Column(String(500), comment='远程对象Key')
    remote_endpoint = Column(String(500), comment='远程服务端点')
    remote_upload_status = Column(String(20), comment='远程上传状态: pending/uploading/success/failed')
    remote_upload_time = Column(DateTime, comment='远程上传完成时间')
    remote_upload_retries = Column(Integer, default=0, comment='远程上传重试次数')

    database_dump_info = Column(Text, comment='数据库dump信息 JSON (表数量、行数等)')
    model_versions = Column(Text, comment='模型版本清单 JSON')
    config_snapshot = Column(Text, comment='配置快照摘要 JSON')

    trigger_type = Column(String(20), default='scheduled', comment='触发类型: scheduled/manual/pre_restore')
    trigger_source = Column(String(100), comment='触发来源 (调度器/用户/恢复操作)')
    operator_id = Column(String(50), comment='操作人ID (手动触发时)')
    operator_name = Column(String(100), comment='操作人姓名')

    error_message = Column(Text, comment='错误信息 (失败时)')
    error_stack = Column(Text, comment='错误堆栈')
    duration_seconds = Column(Integer, comment='执行时长（秒）')

    restore_count = Column(Integer, default=0, comment='被恢复次数')
    last_restore_time = Column(DateTime, comment='最后一次恢复时间')

    pre_restore_snapshot_id = Column(String(100), comment='恢复前创建的快照备份ID')

    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    complete_time = Column(DateTime, comment='完成时间')

    __table_args__ = (
        Index('idx_backup_id', 'backup_id'),
        Index('idx_backup_type', 'backup_type'),
        Index('idx_backup_status', 'status'),
        Index('idx_backup_retention', 'retention_policy', 'expire_time'),
        Index('idx_backup_chain', 'backup_chain_id'),
        Index('idx_backup_storage', 'storage_location'),
        Index('idx_backup_create_time', 'create_time'),
        Index('idx_backup_trigger', 'trigger_type'),
        Index('idx_backup_tenant', 'tenant_id'),
        Index('idx_backup_tenant_time', 'tenant_id', 'create_time'),
    )

    @property
    def component_list_dict(self) -> List[str]:
        import json as _json
        try:
            return _json.loads(self.component_list) if self.component_list else []
        except (_json.JSONDecodeError, TypeError):
            return []

    @property
    def component_sizes_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.component_sizes) if self.component_sizes else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def checksums_detail_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.checksums_detail) if self.checksums_detail else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def database_dump_info_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.database_dump_info) if self.database_dump_info else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def model_versions_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.model_versions) if self.model_versions else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def config_snapshot_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.config_snapshot) if self.config_snapshot else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'backup_id': self.backup_id,
            'backup_type': self.backup_type,
            'backup_scope': self.backup_scope,
            'status': self.status,
            'progress_percent': self.progress_percent,
            'size_bytes': self.size_bytes,
            'size_mb': round((self.size_bytes or 0) / (1024 * 1024), 2),
            'compressed_size_bytes': self.compressed_size_bytes,
            'components': self.component_list_dict,
            'component_sizes': self.component_sizes_dict,
            'file_count': self.file_count,
            'checksum_sha256': self.checksum_sha256,
            'checksum_md5': self.checksum_md5,
            'retention_policy': self.retention_policy,
            'retention_days': self.retention_days,
            'expire_time': self.expire_time.isoformat() if self.expire_time else None,
            'base_backup_id': self.base_backup_id,
            'backup_chain_id': self.backup_chain_id,
            'incremental_since': self.incremental_since.isoformat() if self.incremental_since else None,
            'storage_location': self.storage_location,
            'local_path': self.local_path,
            'remote_bucket': self.remote_bucket,
            'remote_object_key': self.remote_object_key,
            'remote_endpoint': self.remote_endpoint,
            'remote_upload_status': self.remote_upload_status,
            'remote_upload_time': self.remote_upload_time.isoformat() if self.remote_upload_time else None,
            'database_dump_info': self.database_dump_info_dict,
            'model_versions': self.model_versions_dict,
            'config_snapshot': self.config_snapshot_dict,
            'trigger_type': self.trigger_type,
            'trigger_source': self.trigger_source,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'error_message': self.error_message,
            'duration_seconds': self.duration_seconds,
            'restore_count': self.restore_count,
            'last_restore_time': self.last_restore_time.isoformat() if self.last_restore_time else None,
            'pre_restore_snapshot_id': self.pre_restore_snapshot_id,
            'tenant_id': self.tenant_id,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'complete_time': self.complete_time.isoformat() if self.complete_time else None,
        }


class BackupRestoreLog(Base):
    """
    备份恢复日志表模型

    对应数据库表: sc_backup_restore_logs
    记录每次备份恢复操作的详细日志。
    """
    __tablename__ = 'sc_backup_restore_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键')
    restore_id = Column(String(100), unique=True, nullable=False, comment='恢复操作唯一ID')
    backup_id = Column(String(100), nullable=False, comment='源备份ID')
    backup_record_id = Column(BigInteger, comment='关联备份记录ID')

    status = Column(String(20), default='pending', comment='状态: pending/pre_snapshot/restoring/refresh_cache/completed/failed')
    progress_percent = Column(Float, default=0.0, comment='进度百分比')

    restore_scope = Column(String(50), comment='恢复范围: models/config/database/all')
    restore_options = Column(Text, comment='恢复选项 JSON')

    pre_snapshot_backup_id = Column(String(100), comment='恢复前创建的快照备份ID')
    pre_snapshot_path = Column(String(500), comment='恢复前快照路径')

    restored_components = Column(Text, comment='已恢复组件 JSON')
    restored_file_count = Column(Integer, default=0, comment='已恢复文件数')
    restored_size_bytes = Column(BigInteger, default=0, comment='已恢复数据大小')

    cache_refresh_status = Column(String(20), comment='模型缓存刷新状态: pending/running/success/failed/skipped')
    cache_refresh_detail = Column(Text, comment='缓存刷新详情 JSON')
    models_reloaded = Column(Text, comment='重新加载的模型列表 JSON')

    trigger_type = Column(String(20), default='manual', comment='触发类型: manual/auto/drill')
    operator_id = Column(String(50), comment='操作人ID')
    operator_name = Column(String(100), comment='操作人姓名')
    operator_note = Column(String(500), comment='操作备注')

    validation_result = Column(Text, comment='恢复后校验结果 JSON')
    validation_passed = Column(Boolean, comment='校验是否通过')

    error_message = Column(Text, comment='错误信息')
    error_stack = Column(Text, comment='错误堆栈')
    duration_seconds = Column(Integer, comment='执行时长（秒）')

    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    complete_time = Column(DateTime, comment='完成时间')

    __table_args__ = (
        Index('idx_restore_id', 'restore_id'),
        Index('idx_restore_backup_id', 'backup_id'),
        Index('idx_restore_status', 'status'),
        Index('idx_restore_create_time', 'create_time'),
        Index('idx_restore_tenant', 'tenant_id'),
    )

    @property
    def restore_options_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.restore_options) if self.restore_options else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def restored_components_dict(self) -> List[str]:
        import json as _json
        try:
            return _json.loads(self.restored_components) if self.restored_components else []
        except (_json.JSONDecodeError, TypeError):
            return []

    @property
    def cache_refresh_detail_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.cache_refresh_detail) if self.cache_refresh_detail else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @property
    def models_reloaded_list(self) -> List[str]:
        import json as _json
        try:
            return _json.loads(self.models_reloaded) if self.models_reloaded else []
        except (_json.JSONDecodeError, TypeError):
            return []

    @property
    def validation_result_dict(self) -> Dict:
        import json as _json
        try:
            return _json.loads(self.validation_result) if self.validation_result else {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'restore_id': self.restore_id,
            'backup_id': self.backup_id,
            'status': self.status,
            'progress_percent': self.progress_percent,
            'restore_scope': self.restore_scope,
            'restore_options': self.restore_options_dict,
            'pre_snapshot_backup_id': self.pre_snapshot_backup_id,
            'pre_snapshot_path': self.pre_snapshot_path,
            'restored_components': self.restored_components_dict,
            'restored_file_count': self.restored_file_count,
            'restored_size_bytes': self.restored_size_bytes,
            'cache_refresh_status': self.cache_refresh_status,
            'cache_refresh_detail': self.cache_refresh_detail_dict,
            'models_reloaded': self.models_reloaded_list,
            'trigger_type': self.trigger_type,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'operator_note': self.operator_note,
            'validation_result': self.validation_result_dict,
            'validation_passed': self.validation_passed,
            'error_message': self.error_message,
            'duration_seconds': self.duration_seconds,
            'tenant_id': self.tenant_id,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'complete_time': self.complete_time.isoformat() if self.complete_time else None,
        }


class NodeThreshold(Base):
    __tablename__ = 'sc_node_thresholds'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    node_type = Column(String(20), nullable=False, comment='节点类型 bolt/flange')
    node_id = Column(String(100), nullable=False, comment='节点ID')
    scope = Column(String(20), nullable=False, default='node', comment='作用域 global/flange/node')
    source = Column(String(30), nullable=False, default='design', comment='来源: design/statistical/manual')
    threshold_type = Column(String(50), nullable=False, comment='阈值类型: preload/risk/health_index/confidence')
    parameters = Column(Text, nullable=False, comment='阈值参数 JSON')
    version = Column(Integer, nullable=False, default=1, comment='版本号')
    is_active = Column(Boolean, default=True, comment='是否为当前生效版本')
    description = Column(String(500), comment='变更说明')
    design_value = Column(Float, comment='设计值')
    deviation_ratio = Column(Float, comment='偏差比例')
    statistical_mean = Column(Float, comment='统计均值')
    statistical_std = Column(Float, comment='统计标准差')
    statistical_sample_count = Column(Integer, comment='统计样本数')
    statistical_window_days = Column(Integer, comment='统计窗口天数')
    operator_id = Column(String(50), comment='操作人ID')
    operator_name = Column(String(100), comment='操作人姓名')
    tenant_id = Column(BigInteger, comment='租户ID')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_nt_scope', 'scope'),
        Index('idx_nt_node_type', 'node_type'),
        Index('idx_nt_source', 'source'),
        Index('idx_nt_version', 'node_type', 'node_id', 'threshold_type', 'version'),
        Index('idx_nt_tenant', 'tenant_id'),
    )


class ThresholdAuditLog(Base):
    __tablename__ = 'sc_threshold_audit_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    threshold_id = Column(BigInteger, nullable=False, comment='关联阈值配置ID')
    node_type = Column(String(20), nullable=False, comment='节点类型')
    node_id = Column(String(100), nullable=False, comment='节点ID')
    scope = Column(String(20), nullable=False, comment='作用域')
    threshold_type = Column(String(50), nullable=False, comment='阈值类型')
    source = Column(String(30), nullable=False, comment='来源')
    action = Column(String(30), nullable=False, comment='操作类型 create/update/delete/rollback')
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
        Index('idx_tal_threshold', 'threshold_id'),
        Index('idx_tal_scope', 'scope', 'node_type', 'node_id'),
        Index('idx_tal_action', 'action'),
        Index('idx_tal_time', 'create_time'),
        Index('idx_tal_operator', 'operator_id'),
        Index('idx_tal_tenant', 'tenant_id'),
    )
