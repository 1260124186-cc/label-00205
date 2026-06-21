-- ============================================================
-- 螺栓预紧力机器学习预测系统 - 数据库初始化脚本
-- ============================================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS bolt_preload
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE bolt_preload;

-- ============================================================
-- 螺栓预紧力数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_bolt_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    sensor_id BIGINT NOT NULL COMMENT '通道ID/螺栓ID',
    collector_id BIGINT COMMENT '采集器ID',
    splitter_num BIGINT COMMENT '分线器ID',
    position VARCHAR(200) COMMENT '安装位置',
    ptf DOUBLE COMMENT '预紧力',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_sensor_time (sensor_id, create_time),
    INDEX idx_collector (collector_id, splitter_num, position),
    INDEX idx_tenant_sensor_time (tenant_id, sensor_id, create_time),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='螺栓预紧力数据表';

-- ============================================================
-- 异常预测结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS sci_abnormal_prediction (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '序号主键',
    bolt_id BIGINT COMMENT '螺栓编码',
    flm_id VARCHAR(100) COMMENT '法兰面组编码',
    node_type VARCHAR(6) COMMENT '节点类型：螺栓、法兰面',
    year_month CHAR(6) COMMENT '年月',
    pw_type VARCHAR(10) COMMENT '预警预测类型：正常、关注级预警、检查级预警、紧急级预警、故障',
    begin_time DATETIME COMMENT '预计发生起始时间',
    end_time DATETIME COMMENT '预计发生结束时间',
    confidence FLOAT COMMENT '预测置信度',
    rec_measures VARCHAR(1000) COMMENT '推荐措施',
    recent_time DATETIME COMMENT '状态时间',
    fault_type VARCHAR(10) COMMENT '故障类型：loosening/overload/fracture/fatigue/corrosion',
    fault_confidence FLOAT COMMENT '故障分类置信度',
    fault_evidence TEXT COMMENT '故障证据JSON',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_node_type (node_type),
    INDEX idx_bolt_id (bolt_id),
    INDEX idx_flm_id (flm_id),
    INDEX idx_year_month (year_month),
    INDEX idx_fault_type (fault_type),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_node_type (tenant_id, node_type),
    INDEX idx_tenant_bolt_id (tenant_id, bolt_id),
    INDEX idx_tenant_flm_id (tenant_id, flm_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='异常预测结果表';

-- ============================================================
-- 月度预测结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS ci_month_prediction_details (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '序号主键',
    bolt_id BIGINT COMMENT '螺栓编码',
    flm_id VARCHAR(100) COMMENT '法兰面组编码',
    node_type VARCHAR(6) COMMENT '节点类型：螺栓、法兰面',
    year_month CHAR(6) COMMENT '年月',
    pw_type VARCHAR(10) COMMENT '预警预测类型：正常、关注级预警、检查级预警、紧急级预警、故障',
    begin_time DATETIME COMMENT '预计发生起始时间',
    end_time DATETIME COMMENT '预计发生结束时间',
    confidence FLOAT COMMENT '预测置信度',
    rec_measures VARCHAR(1000) COMMENT '推荐措施',
    fault_type VARCHAR(10) COMMENT '故障类型：loosening/overload/fracture/fatigue/corrosion',
    fault_confidence FLOAT COMMENT '故障分类置信度',
    fault_evidence TEXT COMMENT '故障证据JSON',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_node_type (node_type),
    INDEX idx_bolt_id (bolt_id),
    INDEX idx_flm_id (flm_id),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_bolt (tenant_id, bolt_id),
    INDEX idx_tenant_flm (tenant_id, flm_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='月度预测结果表';

-- ============================================================
-- 异常数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_anomaly_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    sensor_id VARCHAR(50) COMMENT '传感器/螺栓ID',
    anomaly_value DOUBLE COMMENT '异常值',
    anomaly_type VARCHAR(50) COMMENT '异常类型：isolation_forest, zscore, iqr, sudden_change, out_of_range',
    anomaly_score DOUBLE COMMENT '异常评分',
    original_time DATETIME COMMENT '原始数据时间',
    details TEXT COMMENT '详细信息JSON',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_sensor (sensor_id),
    INDEX idx_type (anomaly_type),
    INDEX idx_time (create_time),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='异常数据表';

-- ============================================================
-- 模型版本表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_model_versions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    model_id VARCHAR(100) COMMENT '模型标识',
    model_type VARCHAR(20) COMMENT '模型类型：bolt, flange',
    version VARCHAR(20) COMMENT '版本号',
    file_path VARCHAR(500) COMMENT '模型文件路径',
    file_hash VARCHAR(64) COMMENT '文件哈希',
    metrics TEXT COMMENT '训练指标JSON',
    config TEXT COMMENT '训练配置JSON',
    is_active TINYINT DEFAULT 0 COMMENT '是否为活动版本',
    description VARCHAR(500) COMMENT '版本描述',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_model (model_id),
    INDEX idx_active (is_active),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型版本表';

-- ============================================================
-- 训练日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_training_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    session_id VARCHAR(100) COMMENT '会话ID',
    model_id VARCHAR(100) COMMENT '模型标识',
    model_type VARCHAR(20) COMMENT '模型类型',
    status VARCHAR(20) COMMENT '状态：pending, running, completed, failed',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    total_epochs INT COMMENT '总epoch数',
    best_val_acc FLOAT COMMENT '最佳验证准确率',
    best_val_loss FLOAT COMMENT '最佳验证损失',
    config TEXT COMMENT '训练配置JSON',
    error_message TEXT COMMENT '错误信息',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_session (session_id),
    INDEX idx_model (model_id),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='训练日志表';

-- ============================================================
-- 插入示例数据
-- ============================================================

-- 插入示例螺栓数据
INSERT INTO sc_bolt_data (sensor_id, collector_id, splitter_num, position, ptf, create_time) VALUES
(1001, 123, 456, 'A面', 605.23, '2025-04-23 19:00:02'),
(1001, 123, 456, 'A面', 608.88, '2025-04-23 19:01:03'),
(1001, 123, 456, 'A面', 612.53, '2025-04-23 19:02:04'),
(1001, 123, 456, 'A面', 609.73, '2025-04-23 19:03:06'),
(1002, 123, 456, 'A面', 598.37, '2025-04-23 19:00:01'),
(1002, 123, 456, 'A面', 596.35, '2025-04-23 19:01:01'),
(1002, 123, 456, 'A面', 601.97, '2025-04-23 19:02:01'),
(1003, 123, 456, 'B面', 682.23, '2025-04-23 19:00:02'),
(1003, 123, 456, 'B面', 687.88, '2025-04-23 19:01:03'),
(1003, 123, 456, 'B面', 688.53, '2025-04-23 19:02:04'),
(1004, 123, 456, 'B面', 456.37, '2025-04-28 07:00:01'),
(1004, 123, 456, 'B面', 526.35, '2025-04-28 07:01:01'),
(1004, 123, 456, 'B面', 458.97, '2025-04-28 07:02:01');

-- 生成更多测试数据（100条）
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS generate_test_data()
BEGIN
    DECLARE i INT DEFAULT 0;
    DECLARE base_time DATETIME DEFAULT '2025-04-01 00:00:00';

    WHILE i < 100 DO
        INSERT INTO sc_bolt_data (sensor_id, collector_id, splitter_num, position, ptf, create_time)
        VALUES (
            1001,
            123,
            456,
            'A面',
            600 + (RAND() * 40 - 20),
            DATE_ADD(base_time, INTERVAL i MINUTE)
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL generate_test_data();
DROP PROCEDURE IF EXISTS generate_test_data;

-- ============================================================
-- 告警规则表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_alert_rules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    rule_name VARCHAR(200) NOT NULL COMMENT '规则名称',
    alert_level INT NOT NULL COMMENT '告警级别 1-4',
    node_type VARCHAR(20) DEFAULT 'all' COMMENT '节点类型 bolt/flange/all',
    node_ids TEXT COMMENT '节点ID列表 JSON',
    min_confidence FLOAT DEFAULT 0.0 COMMENT '最低置信度',
    silence_period INT DEFAULT 30 COMMENT '静默期（分钟）',
    enable_upgrade TINYINT(1) DEFAULT 1 COMMENT '是否启用自动升级',
    upgrade_minutes INT DEFAULT 30 COMMENT '未处理升级时间（分钟）',
    upgrade_to_level INT COMMENT '升级到的级别',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    description VARCHAR(500) COMMENT '规则描述',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_alert_level (alert_level),
    INDEX idx_enabled (enabled),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_level (tenant_id, alert_level),
    INDEX idx_tenant_enabled (tenant_id, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警规则表';

-- ============================================================
-- 告警事件表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_alert_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    alert_no VARCHAR(50) UNIQUE COMMENT '告警编号',
    rule_id BIGINT COMMENT '关联规则ID',
    alert_level INT NOT NULL COMMENT '当前告警级别',
    original_level INT COMMENT '原始告警级别',
    node_type VARCHAR(20) COMMENT '节点类型',
    node_id VARCHAR(100) COMMENT '节点ID',
    title VARCHAR(200) COMMENT '告警标题',
    content TEXT COMMENT '告警内容',
    confidence FLOAT COMMENT '置信度',
    risk_score FLOAT COMMENT '风险评分',
    recommendations TEXT COMMENT '推荐措施 JSON',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态 pending/processing/resolved/ignored',
    handler_id VARCHAR(50) COMMENT '处理人ID',
    handler_name VARCHAR(100) COMMENT '处理人姓名',
    handle_time DATETIME COMMENT '处理时间',
    handle_note TEXT COMMENT '处理备注',
    is_upgraded TINYINT(1) DEFAULT 0 COMMENT '是否已升级',
    upgrade_count INT DEFAULT 0 COMMENT '升级次数',
    last_upgrade_time DATETIME COMMENT '最后升级时间',
    work_order_id BIGINT COMMENT '关联工单ID',
    source_prediction_id BIGINT COMMENT '来源预测记录ID',
    silence_until DATETIME COMMENT '静默截止时间',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_status (status),
    INDEX idx_level (alert_level),
    INDEX idx_node (node_type, node_id),
    INDEX idx_create_time (create_time),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_status (tenant_id, status),
    INDEX idx_tenant_level (tenant_id, alert_level),
    INDEX idx_tenant_node (tenant_id, node_type, node_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警事件表';

-- ============================================================
-- 维护窗口表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_maintenance_windows (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    window_no VARCHAR(50) UNIQUE COMMENT '窗口编号',
    window_name VARCHAR(200) NOT NULL COMMENT '窗口名称',
    node_scope VARCHAR(20) NOT NULL COMMENT '作用范围 device/flange/bolt',
    node_type VARCHAR(20) COMMENT '节点类型 bolt/flange',
    node_ids TEXT COMMENT '节点ID列表 JSON',
    device_id VARCHAR(100) COMMENT '装置ID',
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME NOT NULL COMMENT '结束时间',
    actual_end_time DATETIME COMMENT '实际结束时间',
    window_type VARCHAR(20) NOT NULL DEFAULT 'planned' COMMENT '窗口类型 planned/temporary',
    suppress_level VARCHAR(20) NOT NULL DEFAULT 'all' COMMENT '静默级别 all/non_emergency',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态 pending/active/ended/cancelled',
    reason VARCHAR(500) COMMENT '维护原因/说明',
    operator_id VARCHAR(50) COMMENT '操作人ID',
    operator_name VARCHAR(100) COMMENT '操作人姓名',
    suppressed_count INT DEFAULT 0 COMMENT '被静默的告警数量',
    extra_info TEXT COMMENT '扩展信息 JSON',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_mw_status (status),
    INDEX idx_mw_scope (node_scope),
    INDEX idx_mw_type (window_type),
    INDEX idx_mw_time_range (start_time, end_time),
    INDEX idx_mw_device (device_id),
    INDEX idx_mw_tenant_status (tenant_id, status),
    INDEX idx_mw_tenant_time (tenant_id, start_time, end_time),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='维护窗口表';

-- ============================================================
-- 告警订阅管理表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_alert_subscriptions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    subscriber_type VARCHAR(20) NOT NULL COMMENT '订阅者类型 role/user/device',
    subscriber_id VARCHAR(100) NOT NULL COMMENT '订阅者ID',
    subscriber_name VARCHAR(200) COMMENT '订阅者名称',
    min_alert_level INT DEFAULT 1 COMMENT '最低订阅级别',
    alert_levels TEXT COMMENT '订阅的告警级别列表 JSON',
    node_type VARCHAR(20) DEFAULT 'all' COMMENT '节点类型过滤',
    node_ids TEXT COMMENT '节点ID列表 JSON',
    notify_channels TEXT COMMENT '通知渠道 JSON',
    notify_targets TEXT COMMENT '通知目标 JSON',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_subscriber (subscriber_type, subscriber_id),
    INDEX idx_enabled (enabled),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_subscriber (tenant_id, subscriber_type, subscriber_id),
    INDEX idx_tenant_enabled (tenant_id, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='告警订阅管理表';

-- ============================================================
-- 通知渠道配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_notification_channels (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    channel_type VARCHAR(50) NOT NULL COMMENT '渠道类型',
    channel_name VARCHAR(200) COMMENT '渠道名称',
    config TEXT COMMENT '渠道配置 JSON',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    is_default TINYINT(1) DEFAULT 0 COMMENT '是否默认渠道',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_channel_type (channel_type),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_channel_type (tenant_id, channel_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知渠道配置表';

-- ============================================================
-- 通知发送日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_notification_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    alert_id BIGINT COMMENT '关联告警ID',
    channel_type VARCHAR(50) COMMENT '通知渠道',
    subscriber_id VARCHAR(100) COMMENT '接收者ID',
    subscriber_name VARCHAR(200) COMMENT '接收者名称',
    target VARCHAR(500) COMMENT '发送目标',
    title VARCHAR(200) COMMENT '通知标题',
    content TEXT COMMENT '通知内容',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '发送状态',
    error_message TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    tenant_id BIGINT COMMENT '租户ID',
    send_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
    INDEX idx_alert_id (alert_id),
    INDEX idx_status (status),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_alert (tenant_id, alert_id),
    INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知发送日志表';

-- ============================================================
-- 工单表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_work_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    order_no VARCHAR(50) UNIQUE COMMENT '工单编号',
    alert_id BIGINT COMMENT '关联告警ID',
    title VARCHAR(200) NOT NULL COMMENT '工单标题',
    description TEXT COMMENT '工单描述',
    priority VARCHAR(20) DEFAULT 'medium' COMMENT '优先级',
    status VARCHAR(20) DEFAULT 'open' COMMENT '状态',
    node_type VARCHAR(20) COMMENT '节点类型',
    node_id VARCHAR(100) COMMENT '节点ID',
    alert_level INT COMMENT '告警级别',
    risk_score FLOAT COMMENT '风险评分',
    assignee_id VARCHAR(50) COMMENT '处理人ID',
    assignee_name VARCHAR(100) COMMENT '处理人姓名',
    creator_id VARCHAR(50) COMMENT '创建人ID',
    creator_name VARCHAR(100) COMMENT '创建人姓名',
    due_time DATETIME COMMENT '截止时间',
    resolve_time DATETIME COMMENT '解决时间',
    resolve_note TEXT COMMENT '解决备注',
    recommendations TEXT COMMENT '推荐措施 JSON',
    extra_info TEXT COMMENT '扩展信息 JSON',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_alert_id (alert_id),
    INDEX idx_assignee (assignee_id),
    INDEX idx_create_time (create_time),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_status (tenant_id, status),
    INDEX idx_tenant_priority (tenant_id, priority),
    INDEX idx_tenant_node (tenant_id, node_type, node_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工单表';

-- ============================================================
-- 插入默认告警规则数据
-- ============================================================
INSERT INTO sc_alert_rules (rule_name, alert_level, node_type, min_confidence, silence_period, enable_upgrade, upgrade_minutes, upgrade_to_level, description) VALUES
('关注级预警规则', 1, 'all', 0.7, 60, 0, 30, 2, '关注级预警，静默期60分钟，不自动升级'),
('检查级预警规则', 2, 'all', 0.7, 30, 1, 30, 3, '检查级预警，30分钟未处理升级为紧急级'),
('紧急级预警规则', 3, 'all', 0.7, 15, 1, 30, 4, '紧急级预警，15分钟静默期，30分钟未处理升级为故障级'),
('故障级告警规则', 4, 'all', 0.5, 10, 0, 30, 4, '故障级告警，最高级别，静默期10分钟');

-- ============================================================
-- 插入默认通知渠道配置（示例）
-- ============================================================
INSERT INTO sc_notification_channels (channel_type, channel_name, config, enabled, is_default) VALUES
('email', '邮件通知', '{"smtp_host":"smtp.example.com","smtp_port":587,"username":"alert@example.com","password":"","use_tls":true}', 1, 1),
('sms', '短信通知', '{"api_url":"https://sms.example.com/api","api_key":""}', 1, 0),
('webhook', 'Webhook回调', '{"url":""}', 0, 0);

-- ============================================================
-- 插入默认订阅配置（管理员角色订阅全部级别）
-- ============================================================
INSERT INTO sc_alert_subscriptions (subscriber_type, subscriber_id, subscriber_name, min_alert_level, alert_levels, notify_channels, notify_targets) VALUES
('role', 'admin', '系统管理员', 1, '[1,2,3,4]', '["email"]', '{"email":["admin@example.com"]}'),
('role', 'operator', '运维工程师', 2, '[2,3,4]', '["email","sms"]', '{"email":["ops@example.com"],"sms":["13800000000"]}'),
('role', 'manager', '部门经理', 3, '[3,4]', '["email"]', '{"email":["manager@example.com"]}');

-- ============================================================
-- 数据质量检查表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_data_quality_checks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    sensor_id VARCHAR(50) NOT NULL COMMENT '传感器/螺栓ID',
    total_points INT COMMENT '总数据点数',
    valid_points INT COMMENT '有效数据点数',
    overall_score FLOAT COMMENT '综合质量评分',
    completeness_score FLOAT COMMENT '完整性评分',
    consistency_score FLOAT COMMENT '一致性评分',
    validity_score FLOAT COMMENT '有效性评分',
    stability_score FLOAT COMMENT '稳定性评分',
    rule_scores TEXT COMMENT '各规则评分 JSON',
    violations TEXT COMMENT '规则违反记录 JSON',
    quality_level VARCHAR(20) COMMENT '质量等级 excellent/good/fair/poor/critical',
    valid_for_training TINYINT DEFAULT 1 COMMENT '是否适合训练',
    confidence_adjustment FLOAT DEFAULT 1.0 COMMENT '置信度调整系数',
    tenant_id BIGINT COMMENT '租户ID',
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '检查时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_dqc_sensor (sensor_id),
    INDEX idx_dqc_time (check_time),
    INDEX idx_dqc_score (overall_score),
    INDEX idx_dqc_level (quality_level),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_sensor (tenant_id, sensor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据质量检查表';

-- ============================================================
-- 质量报告表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_quality_reports (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    report_date DATETIME NOT NULL COMMENT '报告日期',
    total_sensors INT COMMENT '总传感器数',
    average_score FLOAT COMMENT '平均质量评分',
    quality_distribution TEXT COMMENT '质量分布 JSON',
    problem_sensors TEXT COMMENT '问题传感器排行 JSON',
    recommendations TEXT COMMENT '修复建议 JSON',
    anomaly_statistics TEXT COMMENT '异常统计 JSON',
    quality_trend TEXT COMMENT '质量趋势 JSON',
    summary TEXT COMMENT '报告摘要',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY idx_qr_date (report_date),
    INDEX idx_qr_create (create_time),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_date (tenant_id, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='质量报告表';

-- ============================================================
-- 扩展 sc_anomaly_data 表，添加异常分类字段
-- ============================================================
-- 检查并添加 classification 字段
SET @dbname = DATABASE();
SET @tablename = 'sc_anomaly_data';
SET @columnname = 'classification';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(20) COMMENT ''异常分类: true_anomaly/collection_anomaly/uncertain/mixed''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 classification_confidence 字段
SET @columnname = 'classification_confidence';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' FLOAT COMMENT ''分类置信度''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 collection_subtype 字段
SET @columnname = 'collection_subtype';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(20) COMMENT ''采集异常子类型''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 true_anomaly_subtype 字段
SET @columnname = 'true_anomaly_subtype';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(20) COMMENT ''真异常子类型''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 classification_evidence 字段
SET @columnname = 'classification_evidence';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT COMMENT ''分类证据 JSON''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加分类索引
SET @indexname = 'idx_anomaly_classification';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND index_name = @indexname) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, ' (classification)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- ============================================================
-- API审计日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_api_audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    key_id VARCHAR(50) COMMENT 'API密钥ID',
    key_name VARCHAR(200) COMMENT '密钥名称',
    method VARCHAR(10) COMMENT 'HTTP方法 GET/POST/PUT/DELETE',
    path VARCHAR(500) COMMENT '请求路径',
    status_code INT COMMENT '响应状态码',
    client_ip VARCHAR(50) COMMENT '客户端IP',
    request_id VARCHAR(64) COMMENT '请求ID',
    extra_info TEXT COMMENT '扩展信息 JSON',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_api_audit_key (key_id),
    INDEX idx_api_audit_path (path),
    INDEX idx_api_audit_status (status_code),
    INDEX idx_api_audit_time (create_time),
    INDEX idx_api_audit_method (method),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_key (tenant_id, key_id),
    INDEX idx_tenant_time (tenant_id, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API审计日志表';

-- ============================================================
-- 故障类型细分 - 扩展预测结果表字段
-- ============================================================

SET @dbname = DATABASE();

-- sci_abnormal_prediction: fault_type
SET @tablename = 'sci_abnormal_prediction';
SET @columnname = 'fault_type';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(10) COMMENT ''故障类型：loosening/overload/fracture/fatigue/corrosion''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- sci_abnormal_prediction: fault_confidence
SET @columnname = 'fault_confidence';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' FLOAT COMMENT ''故障分类置信度''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- sci_abnormal_prediction: fault_evidence
SET @columnname = 'fault_evidence';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT COMMENT ''故障证据JSON''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- sci_abnormal_prediction: fault_type index
SET @indexname = 'idx_fault_type';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND index_name = @indexname) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, ' (fault_type)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- ci_month_prediction_details: fault_type
SET @tablename = 'ci_month_prediction_details';
SET @columnname = 'fault_type';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(10) COMMENT ''故障类型：loosening/overload/fracture/fatigue/corrosion''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- ci_month_prediction_details: fault_confidence
SET @columnname = 'fault_confidence';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' FLOAT COMMENT ''故障分类置信度''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- ci_month_prediction_details: fault_evidence
SET @columnname = 'fault_evidence';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT COMMENT ''故障证据JSON''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 显示创建的表
SHOW TABLES;

-- ============================================================
-- 多租户与组织架构
-- ============================================================

CREATE TABLE IF NOT EXISTS sc_tenants (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_code VARCHAR(64) UNIQUE NOT NULL COMMENT '租户编码',
    tenant_name VARCHAR(200) NOT NULL COMMENT '租户名称',
    contact_email VARCHAR(200) COMMENT '联系邮箱',
    contact_phone VARCHAR(50) COMMENT '联系电话',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/suspended/deleted',
    settings TEXT COMMENT '租户配置 JSON',
    expire_time DATETIME COMMENT '到期时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_tenant_code (tenant_code),
    INDEX idx_tenant_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户表';

CREATE TABLE IF NOT EXISTS sc_org_nodes (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL COMMENT '所属租户ID',
    parent_id BIGINT COMMENT '父节点ID',
    node_code VARCHAR(100) COMMENT '节点编码',
    node_name VARCHAR(200) NOT NULL COMMENT '节点名称',
    node_type VARCHAR(20) NOT NULL COMMENT '节点类型 group/factory/unit/flange/bolt',
    path VARCHAR(500) COMMENT '层级路径 /id/id/...',
    level INT DEFAULT 0 COMMENT '层级深度 0=集团 1=工厂 2=装置 3=法兰面 4=螺栓',
    sort_order INT DEFAULT 0 COMMENT '排序序号',
    extra_info TEXT COMMENT '扩展信息 JSON',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/inactive',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_org_tenant (tenant_id),
    INDEX idx_org_parent (parent_id),
    INDEX idx_org_type (tenant_id, node_type),
    INDEX idx_org_path (path)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='组织架构节点表';

CREATE TABLE IF NOT EXISTS sc_tenant_quotas (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT UNIQUE NOT NULL COMMENT '租户ID',
    max_models INT DEFAULT 10 COMMENT '最大模型数',
    max_api_calls_per_day INT DEFAULT 10000 COMMENT '每日最大API调用次数',
    max_storage_mb INT DEFAULT 5120 COMMENT '存储上限 MB',
    max_users INT DEFAULT 50 COMMENT '最大用户数',
    max_org_nodes INT DEFAULT 500 COMMENT '最大组织节点数',
    max_training_concurrency INT DEFAULT 2 COMMENT '最大训练并发数',
    current_model_count INT DEFAULT 0 COMMENT '当前模型数',
    current_api_calls_today INT DEFAULT 0 COMMENT '今日API调用次数',
    current_storage_mb DOUBLE DEFAULT 0.0 COMMENT '当前存储用量 MB',
    current_user_count INT DEFAULT 0 COMMENT '当前用户数',
    current_org_node_count INT DEFAULT 0 COMMENT '当前组织节点数',
    current_training_concurrency INT DEFAULT 0 COMMENT '当前训练并发数',
    api_call_reset_date VARCHAR(10) COMMENT 'API调用计数重置日期 YYYY-MM-DD',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_quota_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户配额表';

CREATE TABLE IF NOT EXISTS sc_tenant_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL COMMENT '所属租户ID',
    username VARCHAR(100) NOT NULL COMMENT '用户名',
    password_hash VARCHAR(128) COMMENT '密码哈希',
    display_name VARCHAR(200) COMMENT '显示名称',
    email VARCHAR(200) COMMENT '邮箱',
    phone VARCHAR(50) COMMENT '手机号',
    role VARCHAR(30) DEFAULT 'viewer' COMMENT '角色 tenant_admin/admin/operator/viewer',
    org_node_id BIGINT COMMENT '关联组织节点ID',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/disabled',
    last_login_time DATETIME COMMENT '最后登录时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_tenant (tenant_id),
    UNIQUE KEY idx_user_tenant_username (tenant_id, username),
    INDEX idx_user_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户用户表';

CREATE TABLE IF NOT EXISTS sc_tenant_api_keys (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL COMMENT '所属租户ID',
    api_key VARCHAR(64) UNIQUE NOT NULL COMMENT 'API密钥(哈希)',
    key_name VARCHAR(200) COMMENT '密钥名称',
    permissions TEXT COMMENT '权限列表 JSON',
    rate_limit INT DEFAULT 1000 COMMENT '速率限制 每分钟',
    user_id BIGINT COMMENT '关联用户ID',
    expires_at DATETIME COMMENT '过期时间',
    last_used_at DATETIME COMMENT '最后使用时间',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/revoked',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_apikey_tenant (tenant_id),
    INDEX idx_apikey_key (api_key),
    INDEX idx_apikey_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户API Key表';

-- 插入默认租户
INSERT INTO sc_tenants (tenant_code, tenant_name, contact_email, status) VALUES
('default', '默认租户', 'admin@example.com', 'active');

-- 插入默认配额
INSERT INTO sc_tenant_quotas (tenant_id, max_models, max_api_calls_per_day, max_storage_mb, max_users, max_org_nodes) VALUES
(1, 10, 10000, 5120, 50, 500);

-- ============================================================
-- 数字孪生与健康度评分模块
-- ============================================================

-- ============================================================
-- 螺栓健康度历史表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_bolt_health_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    bolt_id VARCHAR(50) NOT NULL COMMENT '螺栓ID',
    flange_id VARCHAR(100) COMMENT '法兰面ID',
    hi_score FLOAT NOT NULL COMMENT '综合健康度指数 0-100',
    hi_level VARCHAR(20) NOT NULL COMMENT '健康等级 excellent/good/fair/poor/critical',
    preload_stability_score FLOAT COMMENT '预紧力稳定性得分',
    alert_frequency_score FLOAT COMMENT '预警频率得分',
    fault_history_score FLOAT COMMENT '故障历史得分',
    environmental_stress_score FLOAT COMMENT '环境应力得分',
    service_age_score FLOAT COMMENT '使用年限得分',
    factors_detail TEXT COMMENT '各因子得分详情 JSON',
    trend VARCHAR(20) COMMENT '健康趋势 improving/stable/declining',
    trend_rate FLOAT COMMENT '趋势变化率',
    current_preload FLOAT COMMENT '当前预紧力',
    nominal_preload FLOAT COMMENT '额定预紧力',
    preload_deviation FLOAT COMMENT '预紧力偏差率',
    last_maintenance_date DATETIME COMMENT '上次维护日期',
    working_condition TEXT COMMENT '工况信息 JSON',
    data_source VARCHAR(50) DEFAULT 'automatic' COMMENT '数据来源 automatic/manual',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_bolt_health_bolt (bolt_id),
    INDEX idx_bolt_health_flange (flange_id),
    INDEX idx_bolt_health_time (create_time),
    INDEX idx_bolt_health_score (hi_score),
    INDEX idx_bolt_health_level (hi_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='螺栓健康度历史表';

-- ============================================================
-- 法兰面健康度历史表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_flange_health_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    flange_id VARCHAR(100) NOT NULL COMMENT '法兰面ID',
    hi_score FLOAT NOT NULL COMMENT '综合健康度指数 0-100',
    hi_level VARCHAR(20) NOT NULL COMMENT '健康等级',
    worst_bolt_hi FLOAT COMMENT '最差螺栓健康度',
    worst_bolt_id VARCHAR(50) COMMENT '最差螺栓ID',
    average_bolt_hi FLOAT COMMENT '平均螺栓健康度',
    median_bolt_hi FLOAT COMMENT '螺栓健康度中位数',
    degradation_rate FLOAT COMMENT '劣化速率（HI/天）',
    bolt_count INT COMMENT '螺栓总数',
    healthy_bolt_count INT COMMENT '健康螺栓数(HI>=70)',
    warning_bolt_count INT COMMENT '预警螺栓数(50<=HI<70)',
    critical_bolt_count INT COMMENT '危险螺栓数(HI<50)',
    bolts_summary TEXT COMMENT '螺栓健康度摘要 JSON',
    trend VARCHAR(20) COMMENT '健康趋势',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_flange_health_flange (flange_id),
    INDEX idx_flange_health_time (create_time),
    INDEX idx_flange_health_score (hi_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='法兰面健康度历史表';

-- ============================================================
-- RUL预测结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_rul_predictions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    node_id VARCHAR(100) NOT NULL COMMENT '节点ID',
    node_type VARCHAR(20) NOT NULL COMMENT '节点类型 bolt/flange',
    current_hi FLOAT COMMENT '当前健康度',
    rul_days FLOAT COMMENT '预测剩余使用寿命（天）',
    rul_lower_bound FLOAT COMMENT 'RUL下限（天）',
    rul_upper_bound FLOAT COMMENT 'RUL上限（天）',
    rul_confidence FLOAT COMMENT 'RUL预测置信度',
    failure_threshold FLOAT DEFAULT 30 COMMENT '故障阈值 HI',
    warning_threshold FLOAT DEFAULT 50 COMMENT '预警阈值 HI',
    days_to_warning FLOAT COMMENT '距离预警的天数',
    historical_hi TEXT COMMENT '历史HI序列 JSON',
    forecast_series TEXT COMMENT '预测序列 JSON',
    degradation_model VARCHAR(50) COMMENT '劣化模型类型 linear/exponential/polynomial',
    model_params TEXT COMMENT '模型参数 JSON',
    model_r_squared FLOAT COMMENT '模型拟合优度 R²',
    tenant_id BIGINT COMMENT '租户ID',
    prediction_date DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '预测日期',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_rul_node (node_type, node_id),
    INDEX idx_rul_time (prediction_date),
    INDEX idx_rul_rul (rul_days)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RUL预测结果表';

-- ============================================================
-- 产线/装置健康度汇总报表表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_health_rollup_reports (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    report_no VARCHAR(50) UNIQUE COMMENT '报表编号',
    line_id VARCHAR(100) NOT NULL COMMENT '产线/装置ID',
    line_name VARCHAR(200) COMMENT '产线/装置名称',
    line_type VARCHAR(50) COMMENT '产线类型 production_line/device/unit',
    overall_hi FLOAT NOT NULL COMMENT '整体健康度',
    overall_level VARCHAR(20) NOT NULL COMMENT '整体健康等级',
    total_flange_count INT COMMENT '法兰面总数',
    total_bolt_count INT COMMENT '螺栓总数',
    healthy_flange_count INT COMMENT '健康法兰面数',
    warning_flange_count INT COMMENT '预警法兰面数',
    critical_flange_count INT COMMENT '危险法兰面数',
    healthy_bolt_count INT COMMENT '健康螺栓数',
    warning_bolt_count INT COMMENT '预警螺栓数',
    critical_bolt_count INT COMMENT '危险螺栓数',
    worst_flange_hi FLOAT COMMENT '最差法兰面健康度',
    worst_flange_id VARCHAR(100) COMMENT '最差法兰面ID',
    average_degradation_rate FLOAT COMMENT '平均劣化速率',
    flanges_summary TEXT COMMENT '法兰面健康度摘要 JSON',
    risk_summary TEXT COMMENT '风险汇总 JSON',
    maintenance_priorities TEXT COMMENT '维护优先级排序 JSON',
    report_date DATE COMMENT '报告日期',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_rollup_line (line_id),
    INDEX idx_rollup_date (report_date),
    INDEX idx_rollup_time (create_time),
    UNIQUE KEY idx_rollup_line_date (line_id, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='产线/装置健康度汇总报表表';

-- ============================================================
-- 劣化曲线数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_degradation_curves (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    node_id VARCHAR(100) NOT NULL COMMENT '节点ID',
    node_type VARCHAR(20) NOT NULL COMMENT '节点类型 bolt/flange',
    curve_data TEXT COMMENT '曲线数据点 JSON',
    degradation_rate FLOAT COMMENT '劣化速率',
    acceleration_rate FLOAT COMMENT '劣化加速度',
    model_type VARCHAR(50) COMMENT '拟合模型类型',
    model_params TEXT COMMENT '模型参数 JSON',
    r_squared FLOAT COMMENT '拟合优度 R²',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_degradation_node (node_type, node_id),
    INDEX idx_degradation_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='劣化曲线数据表';

-- ============================================================
-- 健康度配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_health_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    config_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值 JSON',
    config_type VARCHAR(50) COMMENT '配置类型 weights/thresholds/aging_model',
    description VARCHAR(500) COMMENT '配置描述',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_health_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='健康度配置表';

-- ============================================================
-- 插入健康度默认配置
-- ============================================================
INSERT INTO sc_health_config (config_key, config_value, config_type, description) VALUES
('health_weights',
 '{"preload_stability": 0.30, "alert_frequency": 0.20, "fault_history": 0.20, "environmental_stress": 0.15, "service_age": 0.15}',
 'weights',
 '健康度各因子权重配置，总和为1'),
('health_thresholds',
 '{"excellent": 90, "good": 70, "fair": 50, "poor": 30, "critical": 0}',
 'thresholds',
 '健康等级划分阈值'),
('aging_model',
 '{"design_life_years": 15, "inflection_point_years": 8, "aging_rate": 0.05}',
 'aging_model',
 '使用年限老化模型参数');

-- 显示健康度模块新增的表
SHOW TABLES LIKE 'sc_%health%';
SHOW TABLES LIKE 'sc_%rul%';
SHOW TABLES LIKE 'sc_%rollup%';
SHOW TABLES LIKE 'sc_%degradation%';

-- ============================================================
-- 任务调度与编排扩展
-- ============================================================

-- ============================================================
-- 任务执行日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_job_execution_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    job_name VARCHAR(100) NOT NULL COMMENT '任务名称',
    job_type VARCHAR(50) NOT NULL COMMENT '任务类型: training/prediction/monthly_prediction/alert_upgrade/audit_cleanup',
    trigger_type VARCHAR(20) DEFAULT 'scheduled' COMMENT '触发类型: scheduled/manual',
    status VARCHAR(20) DEFAULT 'running' COMMENT '状态: running/completed/failed/skipped',
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_seconds INT COMMENT '执行时长（秒）',
    total_nodes INT DEFAULT 0 COMMENT '处理节点总数',
    success_count INT DEFAULT 0 COMMENT '成功处理节点数',
    failed_count INT DEFAULT 0 COMMENT '失败节点数',
    skipped_count INT DEFAULT 0 COMMENT '跳过节点数',
    shard_index INT COMMENT '分片索引',
    shard_total INT COMMENT '总分片数',
    bolt_id_min VARCHAR(100) COMMENT '处理的最小bolt_id',
    bolt_id_max VARCHAR(100) COMMENT '处理的最大bolt_id',
    error_summary TEXT COMMENT '错误摘要 JSON',
    error_details TEXT COMMENT '详细错误信息 JSON',
    instance_id VARCHAR(100) COMMENT '执行实例ID',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_job_name (job_name),
    INDEX idx_job_type (job_type),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time),
    INDEX idx_instance (instance_id),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行日志表';

-- ============================================================
-- 调度器Leader选举表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_scheduler_leader (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    leader_key VARCHAR(100) NOT NULL UNIQUE COMMENT 'Leader锁键',
    leader_id VARCHAR(100) NOT NULL COMMENT '当前Leader实例ID',
    lease_expire_time DATETIME NOT NULL COMMENT '租约过期时间',
    last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '最后心跳时间',
    version BIGINT DEFAULT 0 COMMENT '版本号（乐观锁）',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_leader_key (leader_key),
    INDEX idx_lease_expire (lease_expire_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='调度器Leader选举表';

-- ============================================================
-- 任务分片信息表（可选，用于跟踪分片状态）
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_job_shards (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    job_execution_id BIGINT NOT NULL COMMENT '关联的任务执行日志ID',
    shard_index INT NOT NULL COMMENT '分片索引',
    shard_total INT NOT NULL COMMENT '总分片数',
    bolt_id_min VARCHAR(100) COMMENT '分片最小bolt_id',
    bolt_id_max VARCHAR(100) COMMENT '分片最大bolt_id',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '分片状态: pending/running/completed/failed',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    total_nodes INT DEFAULT 0 COMMENT '节点总数',
    success_count INT DEFAULT 0 COMMENT '成功数',
    failed_count INT DEFAULT 0 COMMENT '失败数',
    error_message TEXT COMMENT '错误信息',
    worker_id VARCHAR(100) COMMENT '处理Worker ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_job_execution (job_execution_id),
    INDEX idx_shard_status (status),
    INDEX idx_worker (worker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务分片信息表';

-- 显示调度扩展新增的表
SHOW TABLES LIKE 'sc_job%';
SHOW TABLES LIKE 'sc_scheduler%';

-- ============================================================
-- 定时调度与任务编排扩展
-- ============================================================

-- ============================================================
-- 任务执行日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_job_execution_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    job_name VARCHAR(100) NOT NULL COMMENT '任务名称',
    job_type VARCHAR(50) NOT NULL COMMENT '任务类型: training/prediction/monthly_prediction/alert_upgrade/audit_cleanup',
    trigger_type VARCHAR(20) DEFAULT 'scheduled' COMMENT '触发类型: scheduled/manual',
    status VARCHAR(20) DEFAULT 'running' COMMENT '状态: running/completed/failed/skipped',
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_seconds INT COMMENT '执行时长（秒）',
    total_nodes INT DEFAULT 0 COMMENT '处理节点总数',
    success_count INT DEFAULT 0 COMMENT '成功处理节点数',
    failed_count INT DEFAULT 0 COMMENT '失败节点数',
    skipped_count INT DEFAULT 0 COMMENT '跳过节点数',
    shard_index INT COMMENT '分片索引（分片执行时）',
    shard_total INT COMMENT '总分片数',
    bolt_id_min VARCHAR(100) COMMENT '处理的最小bolt_id',
    bolt_id_max VARCHAR(100) COMMENT '处理的最大bolt_id',
    error_summary TEXT COMMENT '错误摘要（JSON格式，包含主要错误类型和数量）',
    error_details TEXT COMMENT '详细错误信息（JSON格式）',
    instance_id VARCHAR(100) COMMENT '执行实例ID（用于集群环境）',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_job_name (job_name),
    INDEX idx_job_type (job_type),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time),
    INDEX idx_instance (instance_id),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行日志表';

-- ============================================================
-- 调度器Leader选举表（大集群场景）
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_scheduler_leader (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    leader_key VARCHAR(100) NOT NULL UNIQUE COMMENT 'Leader锁键（如 prediction_job）',
    leader_id VARCHAR(100) NOT NULL COMMENT '当前Leader实例ID',
    lease_expire_time DATETIME NOT NULL COMMENT '租约过期时间',
    last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '最后心跳时间',
    version BIGINT DEFAULT 0 COMMENT '版本号（用于乐观锁）',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_leader_key (leader_key),
    INDEX idx_lease_expire (lease_expire_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='调度器Leader选举表';

-- 初始化Leader选举记录（为每个需要选举的任务创建一条记录）
INSERT IGNORE INTO sc_scheduler_leader (leader_key, leader_id, lease_expire_time, version) VALUES
('prediction_job', '', DATE_SUB(NOW(), INTERVAL 1 HOUR), 0),
('training_job', '', DATE_SUB(NOW(), INTERVAL 1 HOUR), 0),
('monthly_prediction_job', '', DATE_SUB(NOW(), INTERVAL 1 HOUR), 0);

-- 显示调度模块新增的表
SHOW TABLES LIKE 'sc_%job%';
SHOW TABLES LIKE 'sc_%scheduler%';

-- ============================================================
-- 异常检测增强与闭环 - 扩展 sc_anomaly_data 表
-- ============================================================

-- 检查并添加 is_confirmed 字段
SET @dbname = DATABASE();
SET @tablename = 'sc_anomaly_data';
SET @columnname = 'is_confirmed';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TINYINT(1) DEFAULT 0 COMMENT ''是否已确认''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 is_false_positive 字段
SET @columnname = 'is_false_positive';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TINYINT(1) DEFAULT 0 COMMENT ''是否为误报''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 confirmed_by 字段
SET @columnname = 'confirmed_by';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(50) COMMENT ''确认人ID''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 confirmed_time 字段
SET @columnname = 'confirmed_time';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DATETIME COMMENT ''确认时间''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 confirm_note 字段
SET @columnname = 'confirm_note';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT COMMENT ''确认备注''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 tenant_id 字段
SET @columnname = 'tenant_id';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' BIGINT COMMENT ''租户ID''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 update_time 字段
SET @columnname = 'update_time';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT ''更新时间''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加确认相关索引
SET @indexname = 'idx_anomaly_confirmed';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND index_name = @indexname) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, ' (is_confirmed)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加误报索引
SET @indexname = 'idx_anomaly_false_positive';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND index_name = @indexname) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, ' (is_false_positive)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 update_time 索引
SET @indexname = 'idx_anomaly_update_time';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND index_name = @indexname) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, ' (update_time)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 显示异常表字段
SHOW COLUMNS FROM sc_anomaly_data;

-- ============================================================
-- 预警策略动态配置与持久化
-- ============================================================

CREATE TABLE IF NOT EXISTS sc_strategy_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    scope VARCHAR(20) NOT NULL DEFAULT 'global' COMMENT '作用域 global/bolt/flange/production_line',
    node_type VARCHAR(20) COMMENT '节点类型 bolt/flange/production_line，global时为NULL',
    node_id VARCHAR(100) COMMENT '节点ID，global时为NULL',
    strategy_type INT NOT NULL DEFAULT 1 COMMENT '策略类型 1=应报尽报 2=精准报警',
    confidence_threshold DOUBLE NOT NULL DEFAULT 0.7 COMMENT '置信度阈值 0-1',
    false_positive_threshold DOUBLE COMMENT '误报容忍度 0-1',
    false_negative_threshold DOUBLE COMMENT '漏报容忍度 0-1',
    version INT NOT NULL DEFAULT 1 COMMENT '版本号，每次更新自增',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否为当前生效版本',
    description VARCHAR(500) COMMENT '变更说明',
    operator_id VARCHAR(50) COMMENT '操作人ID',
    operator_name VARCHAR(100) COMMENT '操作人姓名',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_strategy_scope (scope, node_type, node_id),
    INDEX idx_strategy_active (is_active),
    INDEX idx_strategy_version (scope, node_type, node_id, version),
    INDEX idx_strategy_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预警策略配置表';

CREATE TABLE IF NOT EXISTS sc_strategy_audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    config_id BIGINT NOT NULL COMMENT '关联策略配置ID',
    scope VARCHAR(20) NOT NULL COMMENT '作用域 global/bolt/flange/production_line',
    node_type VARCHAR(20) COMMENT '节点类型',
    node_id VARCHAR(100) COMMENT '节点ID',
    action VARCHAR(30) NOT NULL COMMENT '操作类型 create/update/rollback',
    old_value TEXT COMMENT '变更前值 JSON',
    new_value TEXT COMMENT '变更后值 JSON',
    version_before INT COMMENT '变更前版本号',
    version_after INT COMMENT '变更后版本号',
    change_summary VARCHAR(500) COMMENT '变更摘要',
    operator_id VARCHAR(50) COMMENT '操作人ID',
    operator_name VARCHAR(100) COMMENT '操作人姓名',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_audit_config (config_id),
    INDEX idx_audit_scope (scope, node_type, node_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_time (create_time),
    INDEX idx_audit_operator (operator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预警策略审计日志表';

INSERT INTO sc_strategy_config (scope, strategy_type, confidence_threshold, false_positive_threshold, false_negative_threshold, version, is_active, description) VALUES
('global', 1, 0.7, 0.05, NULL, 1, 1, '默认全局策略：应报尽报'),
('global', 2, 0.95, NULL, 0.10, 1, 0, '默认全局策略：精准报警（备用）');

-- ============================================================
-- 多变量/多传感器耦合预测模块
-- ============================================================

-- 扩展 sc_bolt_data 表，添加辅传感器字段
SET @dbname = DATABASE();
SET @tablename = 'sc_bolt_data';

-- 添加温度字段
SET @columnname = 'temperature';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DOUBLE COMMENT ''环境温度 (°C)''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加湿度字段
SET @columnname = 'humidity';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DOUBLE COMMENT ''环境湿度 (%)''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加振动字段
SET @columnname = 'vibration';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DOUBLE COMMENT ''振动加速度 (g)''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加扭矩字段
SET @columnname = 'torque';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DOUBLE COMMENT ''拧紧扭矩 (N·m)''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加压力字段
SET @columnname = 'pressure';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DOUBLE COMMENT ''介质压力 (MPa)''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加数据质量字段
SET @columnname = 'data_quality';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(20) DEFAULT ''full'' COMMENT ''数据质量: full=完整, partial=部分缺失, degraded=降级单变量''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加缺失通道标记字段
SET @columnname = 'missing_channels';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT COMMENT ''缺失通道列表 JSON''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- ============================================================
-- 多变量传感器时序数据表（独立存储高精度传感器数据）
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_bolt_multivariate_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    sensor_id BIGINT NOT NULL COMMENT '通道ID/螺栓ID',
    collector_id BIGINT COMMENT '采集器ID',
    splitter_num BIGINT COMMENT '分线器ID',
    position VARCHAR(200) COMMENT '安装位置',
    timestamp DATETIME NOT NULL COMMENT '采集时间戳',
    preload DOUBLE COMMENT '预紧力 (kN)',
    temperature DOUBLE COMMENT '环境温度 (°C)',
    humidity DOUBLE COMMENT '环境湿度 (%)',
    vibration_x DOUBLE COMMENT 'X轴振动加速度 (g)',
    vibration_y DOUBLE COMMENT 'Y轴振动加速度 (g)',
    vibration_z DOUBLE COMMENT 'Z轴振动加速度 (g)',
    torque DOUBLE COMMENT '拧紧扭矩 (N·m)',
    pressure DOUBLE COMMENT '介质压力 (MPa)',
    axial_force DOUBLE COMMENT '轴向力 (kN)',
    strain DOUBLE COMMENT '应变 (με)',
    rpm DOUBLE COMMENT '转速 (RPM)',
    extra_channels TEXT COMMENT '扩展通道数据 JSON',
    data_quality VARCHAR(20) DEFAULT 'full' COMMENT '数据质量: full/partial/degraded',
    missing_channels TEXT COMMENT '缺失通道列表 JSON',
    interpolation_flags TEXT COMMENT '插值标记 JSON，标记哪些通道值是插值填充的',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_sensor_time (sensor_id, timestamp),
    INDEX idx_collector (collector_id, splitter_num, position),
    INDEX idx_quality (data_quality),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='螺栓多变量传感器时序数据表';

-- ============================================================
-- 多变量训练数据集配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_multivariate_training_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    model_id VARCHAR(100) NOT NULL COMMENT '模型标识（bolt_id 或 flange_id）',
    model_type VARCHAR(20) NOT NULL COMMENT '模型类型: bolt/flange',
    input_channels TEXT NOT NULL COMMENT '输入通道配置 JSON，如: ["preload","temperature","humidity"]',
    target_channel VARCHAR(50) DEFAULT 'preload' COMMENT '预测目标通道',
    sequence_length INT DEFAULT 100 COMMENT '输入序列长度',
    interpolation_method VARCHAR(20) DEFAULT 'linear' COMMENT '插值方法: linear/spline/time_aware',
    allow_degraded_training TINYINT(1) DEFAULT 1 COMMENT '是否允许降级训练（缺失辅传感器时仅用预紧力）',
    min_complete_ratio FLOAT DEFAULT 0.5 COMMENT '最低完整数据比例（低于此比例降级）',
    data_normalization VARCHAR(20) DEFAULT 'channel_wise' COMMENT '归一化方式: channel_wise/global/none',
    extra_params TEXT COMMENT '扩展参数 JSON',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否为活动配置',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY idx_model_config (model_id, model_type, is_active),
    INDEX idx_model_type (model_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='多变量训练数据集配置表';

-- 插入默认多变量配置
INSERT INTO sc_multivariate_training_config (model_id, model_type, input_channels, target_channel, sequence_length, interpolation_method, allow_degraded_training, min_complete_ratio, data_normalization, description) VALUES
('default', 'bolt', '["preload","temperature","humidity","vibration","torque"]', 'preload', 100, 'linear', 1, 0.5, 'channel_wise', '默认螺栓多变量配置'),
('default', 'flange', '["preload","temperature","humidity","pressure"]', 'preload', 100, 'linear', 1, 0.5, 'channel_wise', '默认法兰面多变量配置');

-- 显示新增的多变量相关表
SHOW TABLES LIKE '%multivariate%';
SHOW COLUMNS FROM sc_bolt_data LIKE '%temper%';
SHOW COLUMNS FROM sc_bolt_data LIKE '%humid%';
SHOW COLUMNS FROM sc_bolt_data LIKE '%vibra%';
SHOW COLUMNS FROM sc_bolt_data LIKE '%torque%';

-- ============================================================
-- 备件库存与 RUL 联动模块 - 数据表
-- ============================================================

-- ============================================================
-- 螺栓型号与 SKU 映射表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_bolt_sku_mapping (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT DEFAULT 0 COMMENT '租户ID',
    bolt_model VARCHAR(100) NOT NULL COMMENT '螺栓型号',
    bolt_spec VARCHAR(200) COMMENT '螺栓规格',
    material VARCHAR(100) COMMENT '材质',
    standard VARCHAR(50) COMMENT '标准（如GB/T、ISO、ANSI等）',
    diameter DECIMAL(10,3) COMMENT '直径（mm）',
    length DECIMAL(10,3) COMMENT '长度（mm）',
    performance_grade VARCHAR(20) COMMENT '性能等级（如8.8级、10.9级等）',
    sku_code VARCHAR(100) NOT NULL COMMENT '备件SKU编码',
    sku_name VARCHAR(200) NOT NULL COMMENT '备件名称',
    unit VARCHAR(20) DEFAULT '个' COMMENT '单位',
    unit_price DECIMAL(15,4) COMMENT '单价（元）',
    supplier VARCHAR(200) COMMENT '供应商',
    manufacturer VARCHAR(200) COMMENT '厂家',
    purchase_cycle_days INT COMMENT '采购周期（天）',
    min_order_quantity INT DEFAULT 1 COMMENT '最小订货量',
    description TEXT COMMENT '备注说明',
    extra_info JSON COMMENT '扩展信息',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_bolt_model_sku (bolt_model, sku_code, tenant_id),
    INDEX idx_sku_code (sku_code),
    INDEX idx_bolt_model (bolt_model),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='螺栓型号与SKU映射表';

-- ============================================================
-- 备件库存表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_spare_part_inventory (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT DEFAULT 0 COMMENT '租户ID',
    sku_code VARCHAR(100) NOT NULL COMMENT '备件SKU编码',
    sku_name VARCHAR(200) COMMENT '备件名称',
    warehouse_code VARCHAR(50) DEFAULT 'default' COMMENT '仓库编码',
    warehouse_name VARCHAR(100) COMMENT '仓库名称',
    location_code VARCHAR(50) COMMENT '库位编码',
    current_stock INT DEFAULT 0 COMMENT '现有库存数量',
    reserved_stock INT DEFAULT 0 COMMENT '预留库存数量（已分配未出库）',
    available_stock INT DEFAULT 0 COMMENT '可用库存数量（现有-预留）',
    in_transit_stock INT DEFAULT 0 COMMENT '在途库存数量',
    reorder_point INT DEFAULT 0 COMMENT '再订货点',
    safety_stock INT DEFAULT 0 COMMENT '安全库存数量',
    abc_category CHAR(1) COMMENT 'ABC分类：A/B/C',
    turnover_rate DECIMAL(10,4) COMMENT '周转率',
    last_receipt_date DATE COMMENT '最近入库日期',
    last_issue_date DATE COMMENT '最近出库日期',
    unit_price DECIMAL(15,4) COMMENT '单价（元）',
    total_value DECIMAL(18,4) COMMENT '库存总价值',
    min_stock INT DEFAULT 0 COMMENT '最低库存预警',
    max_stock INT COMMENT '最高库存限制',
    stock_status VARCHAR(20) DEFAULT 'normal' COMMENT '库存状态：normal/shortage/out_of_stock/overstock',
    description TEXT COMMENT '备注',
    extra_info JSON COMMENT '扩展信息',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_sku_warehouse (sku_code, warehouse_code, tenant_id),
    INDEX idx_sku_code (sku_code),
    INDEX idx_warehouse (warehouse_code),
    INDEX idx_stock_status (stock_status),
    INDEX idx_abc_category (abc_category),
    INDEX idx_available (available_stock),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='备件库存表';

-- ============================================================
-- 备件需求建议表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_spare_part_demand (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT DEFAULT 0 COMMENT '租户ID',
    demand_no VARCHAR(50) NOT NULL COMMENT '需求单号',
    source_type VARCHAR(30) NOT NULL COMMENT '需求来源：rul_prediction/manual/work_order',
    source_id VARCHAR(100) COMMENT '来源记录ID',
    node_id BIGINT COMMENT '节点ID（螺栓或法兰面）',
    node_type VARCHAR(20) COMMENT '节点类型：bolt/flange',
    device_id VARCHAR(100) COMMENT '所属装置ID',
    device_name VARCHAR(200) COMMENT '所属装置名称',
    bolt_model VARCHAR(100) COMMENT '螺栓型号',
    bolt_spec VARCHAR(200) COMMENT '螺栓规格',
    sku_code VARCHAR(100) COMMENT '备件SKU编码',
    sku_name VARCHAR(200) COMMENT '备件名称',
    required_quantity INT NOT NULL DEFAULT 1 COMMENT '需求数量',
    urgency_level VARCHAR(20) NOT NULL DEFAULT 'normal' COMMENT '紧急程度：normal/urgent/critical',
    priority VARCHAR(20) COMMENT '优先级：low/medium/high/urgent',
    rul_days INT COMMENT 'RUL剩余寿命天数',
    current_hi DECIMAL(10,4) COMMENT '当前健康度指数',
    predicted_failure_date DATE COMMENT '预计故障日期',
    demand_date DATE COMMENT '需求日期（期望到货日期）',
    stock_status VARCHAR(20) COMMENT '库存状态：sufficient/shortage/out_of_stock',
    available_quantity INT COMMENT '可用库存数量',
    short_quantity INT COMMENT '短缺数量',
    work_order_id BIGINT COMMENT '关联工单ID',
    work_order_upgraded TINYINT(1) DEFAULT 0 COMMENT '工单是否已升级优先级',
    demand_status VARCHAR(20) DEFAULT 'pending' COMMENT '需求状态：pending/approved/rejected/fulfilled/cancelled',
    approver_id BIGINT COMMENT '审批人ID',
    approve_time DATETIME COMMENT '审批时间',
    approve_comment VARCHAR(500) COMMENT '审批意见',
    fulfill_time DATETIME COMMENT '完成时间',
    fulfill_quantity INT DEFAULT 0 COMMENT '已完成数量',
    description TEXT COMMENT '需求说明',
    extra_info JSON COMMENT '扩展信息',
    create_by BIGINT COMMENT '创建人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_demand_no (demand_no, tenant_id),
    INDEX idx_source (source_type, source_id),
    INDEX idx_sku_code (sku_code),
    INDEX idx_device (device_id),
    INDEX idx_status (demand_status),
    INDEX idx_urgency (urgency_level),
    INDEX idx_demand_date (demand_date),
    INDEX idx_node (node_id, node_type),
    INDEX idx_work_order (work_order_id),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='备件需求建议表';

-- ============================================================
-- 装置备件需求汇总报表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_spare_part_demand_summary (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT DEFAULT 0 COMMENT '租户ID',
    summary_no VARCHAR(50) NOT NULL COMMENT '汇总编号',
    device_id VARCHAR(100) COMMENT '装置ID',
    device_name VARCHAR(200) COMMENT '装置名称',
    report_period VARCHAR(20) COMMENT '报告周期：weekly/monthly/quarterly/custom',
    start_date DATE COMMENT '统计开始日期',
    end_date DATE COMMENT '统计结束日期',
    total_sku_types INT DEFAULT 0 COMMENT 'SKU种类数',
    total_quantity INT DEFAULT 0 COMMENT '总需求数量',
    total_value DECIMAL(18,4) DEFAULT 0 COMMENT '总价值（元）',
    shortage_sku_count INT DEFAULT 0 COMMENT '缺货SKU数',
    critical_count INT DEFAULT 0 COMMENT '特急需求数',
    urgent_count INT DEFAULT 0 COMMENT '紧急需求数',
    normal_count INT DEFAULT 0 COMMENT '普通需求数',
    demand_details JSON COMMENT '需求明细JSON',
    inventory_analysis JSON COMMENT '库存分析JSON',
    purchase_recommendation JSON COMMENT '采购建议JSON',
    report_status VARCHAR(20) DEFAULT 'draft' COMMENT '报表状态：draft/confirmed/archived',
    description TEXT COMMENT '备注',
    extra_info JSON COMMENT '扩展信息',
    create_by BIGINT COMMENT '创建人ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_summary_no (summary_no, tenant_id),
    INDEX idx_device (device_id),
    INDEX idx_period (report_period),
    INDEX idx_date (start_date, end_date),
    INDEX idx_status (report_status),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='装置备件需求汇总报表';

-- ============================================================
-- 库存交易记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_spare_part_stock_transaction (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT DEFAULT 0 COMMENT '租户ID',
    transaction_no VARCHAR(50) NOT NULL COMMENT '交易单号',
    transaction_type VARCHAR(30) NOT NULL COMMENT '交易类型：receipt/issue/transfer/adjustment/reserve/cancel_reserve',
    sku_code VARCHAR(100) NOT NULL COMMENT '备件SKU编码',
    sku_name VARCHAR(200) COMMENT '备件名称',
    warehouse_code VARCHAR(50) DEFAULT 'default' COMMENT '仓库编码',
    location_code VARCHAR(50) COMMENT '库位编码',
    quantity INT NOT NULL COMMENT '交易数量（正数入库，负数出库）',
    unit_price DECIMAL(15,4) COMMENT '单价',
    total_amount DECIMAL(18,4) COMMENT '总金额',
    balance_before INT COMMENT '交易前库存',
    balance_after INT COMMENT '交易后库存',
    related_order_no VARCHAR(50) COMMENT '关联单据号（需求单、采购单等）',
    related_order_type VARCHAR(30) COMMENT '关联单据类型',
    operator_id BIGINT COMMENT '操作人ID',
    operator_name VARCHAR(100) COMMENT '操作人姓名',
    transaction_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '交易时间',
    description TEXT COMMENT '备注',
    extra_info JSON COMMENT '扩展信息',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_transaction_no (transaction_no),
    INDEX idx_type (transaction_type),
    INDEX idx_sku (sku_code),
    INDEX idx_warehouse (warehouse_code),
    INDEX idx_time (transaction_time),
    INDEX idx_related_order (related_order_no),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='库存交易记录表';

-- ============================================================
-- 采购周期与安全库存配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_purchase_cycle_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT DEFAULT 0 COMMENT '租户ID',
    sku_code VARCHAR(100) NOT NULL COMMENT '备件SKU编码',
    sku_name VARCHAR(200) COMMENT '备件名称',
    lead_time_days INT COMMENT '采购提前期（天）',
    lead_time_std_dev DECIMAL(10,2) COMMENT '提前期标准差（天）',
    count_cycle_days INT DEFAULT 30 COMMENT '盘点周期（天）',
    avg_daily_demand DECIMAL(12,4) COMMENT '日均消耗量',
    demand_std_dev DECIMAL(12,4) COMMENT '需求标准差',
    demand_variation_coeff DECIMAL(10,4) COMMENT '需求变异系数',
    safety_stock_method VARCHAR(20) DEFAULT 'statistical' COMMENT '安全库存计算方法：statistical/days_coverage',
    safety_stock_days INT DEFAULT 7 COMMENT '安全库存天数（days_coverage方法）',
    service_level DECIMAL(5,4) DEFAULT 0.95 COMMENT '服务水平（0.90-0.999）',
    calculated_safety_stock INT COMMENT '计算得出的安全库存数量',
    reorder_point INT COMMENT '再订货点',
    eoq INT COMMENT '经济订货批量EOQ',
    abc_category CHAR(1) COMMENT 'ABC分类',
    annual_demand INT COMMENT '年需求量',
    order_cost DECIMAL(12,2) DEFAULT 500.00 COMMENT '单次订货成本（元）',
    holding_cost_rate DECIMAL(10,4) DEFAULT 0.25 COMMENT '年持有成本率',
    unit_price DECIMAL(15,4) COMMENT '单价',
    last_calculated_time DATETIME COMMENT '上次计算时间',
    description TEXT COMMENT '备注',
    extra_info JSON COMMENT '扩展信息',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_sku_config (sku_code, tenant_id),
    INDEX idx_sku (sku_code),
    INDEX idx_abc (abc_category),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='采购周期与安全库存配置表';

-- ============================================================
-- 初始化示例数据
-- ============================================================

-- 插入螺栓-SKU映射示例数据
INSERT INTO sc_bolt_sku_mapping (bolt_model, bolt_spec, material, standard, diameter, length, performance_grade, sku_code, sku_name, unit, unit_price, supplier, purchase_cycle_days, min_order_quantity, description) VALUES
('M20-8.8', 'M20×100', '35CrMoA', 'GB/T 5782', 20.0, 100.0, '8.8级', 'SKU-BOLT-0001', '六角头螺栓 M20×100 8.8级', '个', 25.50, '标准件供应商A', 7, 50, '常用高强度螺栓'),
('M24-10.9', 'M24×150', '42CrMoA', 'GB/T 5782', 24.0, 150.0, '10.9级', 'SKU-BOLT-0002', '六角头螺栓 M24×150 10.9级', '个', 45.80, '标准件供应商A', 10, 30, '法兰连接用高强度螺栓'),
('M30-10.9', 'M30×200', '42CrMoA', 'GB/T 5783', 30.0, 200.0, '10.9级', 'SKU-BOLT-0003', '全螺纹螺栓 M30×200 10.9级', '个', 78.20, '标准件供应商B', 14, 20, '压力容器用全螺纹螺栓'),
('M16-8.8', 'M16×80', '35#', 'GB/T 5782', 16.0, 80.0, '8.8级', 'SKU-BOLT-0004', '六角头螺栓 M16×80 8.8级', '个', 12.30, '标准件供应商A', 5, 100, '普通连接螺栓');

-- 插入备件库存示例数据
INSERT INTO sc_spare_part_inventory (sku_code, sku_name, warehouse_code, warehouse_name, current_stock, reserved_stock, available_stock, safety_stock, reorder_point, abc_category, unit_price, total_value, min_stock, stock_status) VALUES
('SKU-BOLT-0001', '六角头螺栓 M20×100 8.8级', 'WH001', '中心仓库', 120, 20, 100, 50, 80, 'B', 25.50, 3060.00, 30, 'normal'),
('SKU-BOLT-0002', '六角头螺栓 M24×150 10.9级', 'WH001', '中心仓库', 15, 5, 10, 30, 40, 'A', 45.80, 687.00, 20, 'shortage'),
('SKU-BOLT-0003', '全螺纹螺栓 M30×200 10.9级', 'WH001', '中心仓库', 0, 0, 0, 20, 25, 'A', 78.20, 0.00, 10, 'out_of_stock'),
('SKU-BOLT-0004', '六角头螺栓 M16×80 8.8级', 'WH001', '中心仓库', 500, 50, 450, 100, 150, 'C', 12.30, 6150.00, 80, 'normal');

-- 显示新增的备件库存相关表
SHOW TABLES LIKE '%spare%';
SHOW TABLES LIKE '%bolt_sku%';
SHOW TABLES LIKE '%purchase%';

-- ============================================================
-- 超参优化（HPO）模块
-- ============================================================

-- ============================================================
-- HPO 试验表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_hpo_trials (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    trial_id VARCHAR(64) UNIQUE NOT NULL COMMENT '试验唯一ID',
    study_id VARCHAR(64) NOT NULL COMMENT '研究ID（一组试验共享）',
    model_type VARCHAR(20) NOT NULL COMMENT '模型类型：bolt/flange',
    node_id VARCHAR(100) COMMENT '节点ID（为空表示全局）',
    node_type VARCHAR(20) COMMENT '节点类型：bolt/flange',
    framework VARCHAR(20) NOT NULL COMMENT '优化框架：optuna/ray_tune/ax',
    status VARCHAR(20) DEFAULT 'running' COMMENT '状态：running/completed/failed/pruned',
    trial_number INT COMMENT '试验序号',

    -- 超参配置
    num_layers INT COMMENT '层数',
    hidden_size INT COMMENT '隐藏层大小',
    dropout_rate FLOAT COMMENT 'Dropout率',
    learning_rate FLOAT COMMENT '学习率',
    sequence_length INT COMMENT '序列长度',
    params JSON COMMENT '完整超参JSON',

    -- 指标结果
    val_f1_score FLOAT COMMENT '验证集F1分数',
    val_precision FLOAT COMMENT '验证集精确率',
    val_recall FLOAT COMMENT '验证集召回率',
    val_accuracy FLOAT COMMENT '验证集准确率',
    false_positive_rate FLOAT COMMENT '误报率',
    false_negative_rate FLOAT COMMENT '漏报率',
    inference_latency_ms FLOAT COMMENT '推理延迟（毫秒）',
    training_time_seconds FLOAT COMMENT '训练耗时（秒）',
    objective_value FLOAT COMMENT '综合优化目标值',

    -- 约束违反
    latency_constraint_violated TINYINT(1) DEFAULT 0 COMMENT '是否违反延迟约束',
    f1_constraint_violated TINYINT(1) DEFAULT 0 COMMENT '是否违反F1约束',

    -- 元数据
    training_session_id VARCHAR(100) COMMENT '关联的训练会话ID',
    model_version VARCHAR(50) COMMENT '模型版本',
    error_message TEXT COMMENT '错误信息',
    pruned_reason VARCHAR(200) COMMENT '被修剪原因',

    tenant_id BIGINT DEFAULT 0 COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_study (study_id),
    INDEX idx_model_node (model_type, node_id),
    INDEX idx_status (status),
    INDEX idx_objective (objective_value),
    INDEX idx_f1 (val_f1_score),
    INDEX idx_tenant (tenant_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='HPO试验记录表';

-- ============================================================
-- HPO 研究配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_hpo_studies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    study_id VARCHAR(64) UNIQUE NOT NULL COMMENT '研究唯一ID',
    study_name VARCHAR(200) NOT NULL COMMENT '研究名称',
    model_type VARCHAR(20) NOT NULL COMMENT '模型类型：bolt/flange',
    node_id VARCHAR(100) COMMENT '节点ID（为空表示全局）',
    node_type VARCHAR(20) COMMENT '节点类型',

    -- 搜索空间配置
    search_space JSON NOT NULL COMMENT '搜索空间定义JSON',

    -- 优化目标配置
    objective_config JSON NOT NULL COMMENT '优化目标配置JSON',
    f1_weight FLOAT DEFAULT 1.0 COMMENT 'F1权重',
    false_positive_penalty FLOAT DEFAULT 0.5 COMMENT '误报惩罚系数',
    latency_threshold_ms FLOAT DEFAULT 100.0 COMMENT '推理延迟阈值（毫秒）',
    latency_weight FLOAT DEFAULT 0.3 COMMENT '延迟权重',

    -- 优化配置
    framework VARCHAR(20) DEFAULT 'optuna' COMMENT '优化框架',
    optimizer VARCHAR(20) DEFAULT 'tpe' COMMENT '优化算法：tpe/random/grid/bo',
    max_trials INT DEFAULT 50 COMMENT '最大试验次数',
    max_concurrent_trials INT DEFAULT 2 COMMENT '最大并发试验数',
    min_trials_to_prune INT DEFAULT 5 COMMENT '最小试验数后开启剪枝',
    pruner_type VARCHAR(20) DEFAULT 'median' COMMENT '剪枝类型：median/halver/none',

    -- 约束配置
    constraints JSON COMMENT '约束条件JSON',

    -- 状态
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态：pending/running/completed/failed',
    best_trial_id VARCHAR(64) COMMENT '最佳试验ID',
    best_params JSON COMMENT '最佳超参JSON',
    best_objective_value FLOAT COMMENT '最佳目标值',

    -- 每节点超参
    per_node_hpo_enabled TINYINT(1) DEFAULT 0 COMMENT '是否启用per-node超参',
    node_scope VARCHAR(20) DEFAULT 'global' COMMENT '节点范围：global/group/single',

    tenant_id BIGINT DEFAULT 0 COMMENT '租户ID',
    created_by VARCHAR(100) COMMENT '创建人',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_study_id (study_id),
    INDEX idx_model_node (model_type, node_id),
    INDEX idx_status (status),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='HPO研究配置表';

-- ============================================================
-- HPO per-node 超参配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_hpo_node_overrides (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    study_id VARCHAR(64) NOT NULL COMMENT '研究ID',
    node_id VARCHAR(100) NOT NULL COMMENT '节点ID',
    node_type VARCHAR(20) NOT NULL COMMENT '节点类型',

    -- 覆盖的搜索空间
    search_space_override JSON COMMENT '覆盖的搜索空间JSON',

    -- 覆盖的超参值（固定值）
    fixed_params JSON COMMENT '固定超参值JSON',

    -- 该节点找到的最佳配置
    best_params JSON COMMENT '该节点最佳超参',
    best_trial_id VARCHAR(64) COMMENT '该节点最佳试验ID',
    best_objective_value FLOAT COMMENT '该节点最佳目标值',

    -- 是否已应用到训练
    applied_to_training TINYINT(1) DEFAULT 0 COMMENT '是否已应用到训练',
    applied_time DATETIME COMMENT '应用时间',

    tenant_id BIGINT DEFAULT 0 COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_study_node (study_id, node_id),
    INDEX idx_node (node_id),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='HPO节点超参覆盖配置表';

-- 显示 HPO 相关表
SHOW TABLES LIKE '%hpo%';

-- ============================================================
-- 采集器/传感器设备健康监控模块
-- ============================================================

-- ============================================================
-- 采集器心跳表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_collector_heartbeat (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    collector_id VARCHAR(100) NOT NULL COMMENT '采集器ID',
    sensor_id VARCHAR(100) NOT NULL COMMENT '传感器/螺栓ID',
    device_type VARCHAR(20) DEFAULT 'collector' COMMENT '设备类型 collector/sensor',
    device_name VARCHAR(200) COMMENT '设备名称',

    last_data_time DATETIME COMMENT '最后收到数据的时间',
    expected_interval_seconds DOUBLE DEFAULT 60.0 COMMENT '预期采样间隔（秒）',
    consecutive_missing_count INT DEFAULT 0 COMMENT '连续缺失次数',

    last_value DOUBLE COMMENT '最后一次采样的数值',
    previous_value DOUBLE COMMENT '倒数第二次采样的数值',
    stuck_count INT DEFAULT 0 COMMENT '连续数值不变次数',
    jump_count INT DEFAULT 0 COMMENT '跳变次数',

    health_status VARCHAR(20) DEFAULT 'healthy' COMMENT '健康状态 healthy/offline/stuck/jump/degraded',
    fault_types TEXT COMMENT '当前故障类型列表 JSON，如 ["offline","jump"]',
    last_fault_time DATETIME COMMENT '最近一次故障发生时间',
    recovery_time DATETIME COMMENT '最近一次恢复时间',

    confidence_penalty DOUBLE DEFAULT 1.0 COMMENT '置信度惩罚系数 0-1，1=无惩罚',
    excluded_from_training TINYINT(1) DEFAULT 0 COMMENT '是否排除出训练数据',

    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY idx_hb_collector_sensor (collector_id, sensor_id),
    INDEX idx_hb_collector (collector_id),
    INDEX idx_hb_sensor (sensor_id),
    INDEX idx_hb_status (health_status),
    INDEX idx_hb_last_data (last_data_time),
    INDEX idx_hb_excluded (excluded_from_training),
    INDEX idx_hb_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='采集器心跳表';

-- ============================================================
-- 设备故障告警表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_device_fault_alerts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    alert_no VARCHAR(50) UNIQUE COMMENT '告警编号',
    collector_id VARCHAR(100) NOT NULL COMMENT '采集器ID',
    sensor_id VARCHAR(100) NOT NULL COMMENT '传感器/螺栓ID',

    fault_type VARCHAR(20) NOT NULL COMMENT '故障类型 offline/stuck/jump',
    fault_level INT DEFAULT 2 COMMENT '故障级别 1=提示 2=警告 3=严重 4=紧急',

    title VARCHAR(200) COMMENT '告警标题',
    content TEXT COMMENT '告警内容',
    evidence TEXT COMMENT '故障证据 JSON',

    last_value DOUBLE COMMENT '最后采样值',
    expected_value_range VARCHAR(100) COMMENT '期望值范围 JSON',
    offline_duration_seconds DOUBLE COMMENT '离线时长（秒）',
    consecutive_missing INT COMMENT '连续缺失次数',
    stuck_count INT COMMENT '卡死次数',
    jump_magnitude DOUBLE COMMENT '跳变幅度',

    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态 pending/acknowledged/resolved/ignored',
    handler_id VARCHAR(50) COMMENT '处理人ID',
    handler_name VARCHAR(100) COMMENT '处理人姓名',
    handle_time DATETIME COMMENT '处理时间',
    handle_note TEXT COMMENT '处理备注',

    silence_until DATETIME COMMENT '静默截止时间',
    is_auto_resolved TINYINT(1) DEFAULT 0 COMMENT '是否自动恢复',

    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_dfa_collector (collector_id),
    INDEX idx_dfa_sensor (sensor_id),
    INDEX idx_dfa_fault_type (fault_type),
    INDEX idx_dfa_status (status),
    INDEX idx_dfa_time (create_time),
    INDEX idx_dfa_level (fault_level),
    INDEX idx_dfa_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备故障告警表';

-- 显示设备健康监控模块新增的表
SHOW TABLES LIKE '%heartbeat%';
SHOW TABLES LIKE '%device_fault%';

-- ============================================================
-- 跨装置风险传播与聚合分析模块
-- ============================================================

-- ============================================================
-- 扩展 sc_org_nodes 表 - 增加装置关联属性字段
-- ============================================================

-- 检查并添加 pipeline_id 字段
SET @dbname = DATABASE();
SET @tablename = 'sc_org_nodes';
SET @columnname = 'pipeline_id';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(100) COMMENT ''管线ID''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 vibration_source 字段
SET @columnname = 'vibration_source';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(100) COMMENT ''振动源标识''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 shifts 字段
SET @columnname = 'shifts';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT COMMENT ''运行班次列表 JSON''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 latitude 字段
SET @columnname = 'latitude';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DOUBLE COMMENT ''纬度''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 检查并添加 longitude 字段
SET @columnname = 'longitude';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = @tablename
     AND table_schema = @dbname
     AND column_name = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DOUBLE COMMENT ''经度''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- ============================================================
-- 装置关联关系表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_device_associations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT COMMENT '租户ID',
    device_a_id VARCHAR(100) NOT NULL COMMENT '装置A ID',
    device_b_id VARCHAR(100) NOT NULL COMMENT '装置B ID',

    same_pipeline_weight DOUBLE DEFAULT 0.0 COMMENT '同管线权重 0-1',
    same_vibration_weight DOUBLE DEFAULT 0.0 COMMENT '同振动源权重 0-1',
    same_shift_weight DOUBLE DEFAULT 0.0 COMMENT '同班次权重 0-1',
    co_fault_weight DOUBLE DEFAULT 0.0 COMMENT '共故障权重 0-1',
    physical_weight DOUBLE DEFAULT 0.0 COMMENT '物理邻接权重 0-1',
    composite_weight DOUBLE DEFAULT 0.0 COMMENT '综合权重 0-1',

    association_types TEXT COMMENT '关联类型列表 JSON',
    co_fault_count INT DEFAULT 0 COMMENT '共故障次数',
    extra_info TEXT COMMENT '扩展信息 JSON',

    status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/inactive',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_device_pair (device_a_id, device_b_id, tenant_id),
    INDEX idx_device_a (device_a_id),
    INDEX idx_device_b (device_b_id),
    INDEX idx_composite_weight (composite_weight),
    INDEX idx_tenant (tenant_id),
    INDEX idx_update_time (update_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='装置关联关系表';

-- ============================================================
-- 风险传播历史表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_risk_propagation_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT COMMENT '租户ID',

    source_device_id VARCHAR(100) NOT NULL COMMENT '源装置ID',
    source_flange_id VARCHAR(100) COMMENT '源法兰ID',
    source_risk_score DOUBLE COMMENT '源装置风险评分',
    source_risk_level VARCHAR(20) COMMENT '源装置风险等级',

    propagation_time DATETIME NOT NULL COMMENT '传播发生时间',
    propagation_depth INT COMMENT '传播深度',
    total_weight_sum DOUBLE COMMENT '传播权重总和',

    affected_device_count INT COMMENT '影响装置数量',

    propagation_result TEXT COMMENT '传播结果 JSON（各装置上调系数）',
    propagation_paths TEXT COMMENT '传播路径 JSON',

    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_source_device (source_device_id),
    INDEX idx_propagation_time (propagation_time),
    INDEX idx_tenant (tenant_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='风险传播历史表';

-- ============================================================
-- 关联图更新任务日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_association_graph_update_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT COMMENT '租户ID',

    job_name VARCHAR(100) NOT NULL COMMENT '任务名称',
    trigger_type VARCHAR(20) DEFAULT 'scheduled' COMMENT '触发类型 scheduled/manual',
    status VARCHAR(20) DEFAULT 'running' COMMENT '状态 running/completed/failed',

    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_seconds INT COMMENT '执行时长（秒）',

    device_count INT DEFAULT 0 COMMENT '处理装置数',
    edge_count INT DEFAULT 0 COMMENT '生成关联边数',
    updated_edge_count INT DEFAULT 0 COMMENT '更新关联边数',

    error_message TEXT COMMENT '错误信息',
    extra_info TEXT COMMENT '扩展信息 JSON',

    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_job_name (job_name),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='关联图更新任务日志表';

-- 显示风险传播模块新增的表
SHOW TABLES LIKE '%device_association%';
SHOW TABLES LIKE '%risk_propagation%';
SHOW TABLES LIKE '%association_graph%';
SHOW COLUMNS FROM sc_org_nodes LIKE '%pipeline%';
SHOW COLUMNS FROM sc_org_nodes LIKE '%vibration%';

-- ============================================================
-- 智能复检周期排程模块
-- ============================================================

-- ============================================================
-- 检验排程任务表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_inspection_schedules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    schedule_id VARCHAR(64) NOT NULL COMMENT '排程任务ID',
    node_id VARCHAR(100) COMMENT '节点ID（螺栓/法兰ID）',
    node_type VARCHAR(20) COMMENT '节点类型: bolt/flange',
    device_name VARCHAR(200) COMMENT '设备名称',
    scheduled_date DATETIME COMMENT '计划开始日期',
    end_date DATETIME COMMENT '计划结束日期',
    priority VARCHAR(20) COMMENT '优先级: routine/attention/urgent/immediate',
    priority_score FLOAT COMMENT '优先级分数 (0-100)',
    status VARCHAR(20) COMMENT '状态: planned/confirmed/in_progress/completed/cancelled/conflict',
    team_id VARCHAR(50) COMMENT '负责班组ID',
    team_name VARCHAR(100) COMMENT '负责班组名称',
    assignee_id VARCHAR(50) COMMENT '负责人ID',
    assignee_name VARCHAR(100) COMMENT '负责人姓名',
    inspection_type VARCHAR(50) COMMENT '检验类型: routine/enhanced/special/special_emergency',
    title VARCHAR(500) COMMENT '任务标题',
    description TEXT COMMENT '任务描述',
    estimated_hours FLOAT COMMENT '预估工时（小时）',
    standard_codes TEXT COMMENT '检验标准代号列表 JSON',
    prerequisites TEXT COMMENT '前置条件 JSON',
    conflict_detected BOOLEAN DEFAULT FALSE COMMENT '是否检测到冲突',
    conflict_details TEXT COMMENT '冲突详情列表 JSON',
    calculation_result TEXT COMMENT '排程计算原始结果 JSON',
    work_order_id BIGINT COMMENT '关联工单ID',
    cmms_external_id VARCHAR(100) COMMENT 'CMMS系统外部ID',
    extra_info TEXT COMMENT '扩展信息 JSON',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_schedule_id (schedule_id),
    INDEX idx_team_date (team_id, scheduled_date),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_node (node_type, node_id),
    INDEX idx_scheduled_date (scheduled_date),
    INDEX idx_work_order (work_order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='智能检验排程任务表';

-- ============================================================
-- 班组产能配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_team_capacity (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    team_id VARCHAR(50) NOT NULL COMMENT '班组ID',
    team_name VARCHAR(100) COMMENT '班组名称',
    daily_max_tasks INT DEFAULT 5 COMMENT '每日最大任务数',
    daily_max_hours FLOAT DEFAULT 40.0 COMMENT '每日最大工时（小时）',
    weekly_max_tasks INT DEFAULT 25 COMMENT '每周最大任务数',
    member_count INT DEFAULT 5 COMMENT '班组人数',
    working_days VARCHAR(50) DEFAULT '0,1,2,3,4' COMMENT '工作日 (0=周一, 6=周日)',
    holidays TEXT COMMENT '节假日列表 JSON',
    special_schedules TEXT COMMENT '特殊排班配置 JSON',
    extra_info TEXT COMMENT '扩展信息 JSON',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_team_id (team_id),
    INDEX idx_team_name (team_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='班组产能配置表';

-- ============================================================
-- 排程同步日志表（CMMS推送）
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_schedule_sync_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    schedule_id VARCHAR(64) NOT NULL COMMENT '排程任务ID',
    sync_type VARCHAR(30) COMMENT '同步类型: cmms_push/ics_export/calendar_subscribe',
    sync_target VARCHAR(100) COMMENT '同步目标: CMMS配置ID/文件名等',
    status VARCHAR(20) COMMENT '状态: pending/success/failed',
    external_id VARCHAR(100) COMMENT '外部系统ID',
    request_data TEXT COMMENT '请求数据 JSON',
    response_data TEXT COMMENT '响应数据 JSON',
    error_message TEXT COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_schedule_id (schedule_id),
    INDEX idx_sync_type (sync_type),
    INDEX idx_status (status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='排程同步日志表';

-- 显示智能复检排程模块的表
SHOW TABLES LIKE '%inspection_schedule%';
SHOW TABLES LIKE '%team_capacity%';
SHOW TABLES LIKE '%schedule_sync%';

-- ============================================================
-- 时序数据冷热归档与分区模块
-- ============================================================

-- ============================================================
-- 归档分区键定义表
-- 记录按月分区的分区键信息，管理热数据分区的生命周期
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_archive_partition_keys (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL COMMENT '租户ID',
    table_name VARCHAR(100) NOT NULL COMMENT '源表名，如sc_bolt_data',
    partition_name VARCHAR(100) NOT NULL COMMENT '分区名称，如p202501',
    partition_key VARCHAR(20) NOT NULL COMMENT '分区键值，格式YYYYMM，如202501',
    partition_start DATETIME NOT NULL COMMENT '分区开始时间',
    partition_end DATETIME NOT NULL COMMENT '分区结束时间（不含）',
    record_count BIGINT DEFAULT 0 COMMENT '分区内记录数',
    data_size_bytes BIGINT DEFAULT 0 COMMENT '分区数据大小（字节）',
    archive_status VARCHAR(20) DEFAULT 'hot' COMMENT '归档状态: hot/archiving/archived/purged',
    archive_job_id BIGINT COMMENT '关联归档任务ID',
    archive_time DATETIME COMMENT '完成归档时间',
    retention_expire_time DATETIME COMMENT '保留到期时间（冷存储删除时间）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_tenant_table_partition (tenant_id, table_name, partition_name),
    INDEX idx_tenant_status (tenant_id, archive_status),
    INDEX idx_partition_key (partition_key),
    INDEX idx_archive_time (archive_time),
    INDEX idx_retention_expire (retention_expire_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='归档分区键定义表';

-- ============================================================
-- 归档元数据索引表
-- 记录每个Parquet文件的元数据，用于快速定位冷数据
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_archive_metadata (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL COMMENT '租户ID',
    source_table VARCHAR(100) NOT NULL COMMENT '源表名',
    partition_key VARCHAR(20) NOT NULL COMMENT '分区键 YYYYMM',
    archive_job_id BIGINT COMMENT '关联归档任务ID',
    storage_type VARCHAR(20) NOT NULL DEFAULT 's3' COMMENT '冷存储类型: s3/oss/minio/influxdb/timescaledb',
    storage_bucket VARCHAR(200) COMMENT '存储桶名/数据库名',
    storage_path VARCHAR(500) NOT NULL COMMENT '存储路径/表名',
    file_name VARCHAR(200) NOT NULL COMMENT '文件名/分片名',
    file_format VARCHAR(20) DEFAULT 'parquet' COMMENT '文件格式: parquet/csv/orc',
    file_size_bytes BIGINT DEFAULT 0 COMMENT '文件大小（字节）',
    record_count BIGINT DEFAULT 0 COMMENT '记录数',
    row_group_count INT DEFAULT 0 COMMENT 'Parquet行组数',
    min_time DATETIME COMMENT '最小数据时间',
    max_time DATETIME COMMENT '最大数据时间',
    sensor_ids TEXT COMMENT '包含的传感器/螺栓ID列表 JSON',
    compression_codec VARCHAR(30) DEFAULT 'snappy' COMMENT '压缩编码: snappy/gzip/zstd',
    schema_version VARCHAR(20) DEFAULT '1.0' COMMENT 'Parquet Schema版本',
    checksum VARCHAR(128) COMMENT '文件校验和（SHA256）',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/restoring/deleted/corrupted',
    restored_count INT DEFAULT 0 COMMENT '被懒加载恢复次数',
    last_restored_time DATETIME COMMENT '最后恢复时间',
    tags TEXT COMMENT '标签 JSON，用于检索',
    extra_metadata TEXT COMMENT '扩展元数据 JSON',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_tenant_table (tenant_id, source_table),
    INDEX idx_tenant_partition (tenant_id, partition_key),
    INDEX idx_storage_path (storage_bucket, storage_path),
    INDEX idx_time_range (min_time, max_time),
    INDEX idx_status (status),
    INDEX idx_last_restored (last_restored_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='归档元数据索引表';

-- ============================================================
-- 归档任务执行日志表
-- 记录每次归档任务的执行详情
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_archive_jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL COMMENT '租户ID',
    job_name VARCHAR(200) NOT NULL COMMENT '任务名称',
    job_type VARCHAR(30) NOT NULL COMMENT '任务类型: hot_to_cold/retention_cleanup/restore/verify',
    trigger_type VARCHAR(20) DEFAULT 'scheduled' COMMENT '触发类型: scheduled/manual',
    cron_expression VARCHAR(100) COMMENT '使用的Cron表达式',
    status VARCHAR(20) DEFAULT 'running' COMMENT '状态: pending/running/completed/failed/paused/cancelled',
    source_tables TEXT COMMENT '归档的源表列表 JSON',
    partition_keys TEXT COMMENT '归档的分区键列表 JSON',
    storage_config TEXT COMMENT '使用的存储配置 JSON',
    hot_threshold_days INT DEFAULT 90 COMMENT '热数据阈值（天）',
    retention_days INT DEFAULT 365 COMMENT '运营保留天数',
    compliance_retention_days INT DEFAULT 2555 COMMENT '合规保留天数（7年=2555天）',
    total_records BIGINT DEFAULT 0 COMMENT '总记录数',
    archived_records BIGINT DEFAULT 0 COMMENT '成功归档记录数',
    failed_records BIGINT DEFAULT 0 COMMENT '失败记录数',
    deleted_records BIGINT DEFAULT 0 COMMENT '从热库删除的记录数',
    total_files INT DEFAULT 0 COMMENT '生成的文件总数',
    total_bytes BIGINT DEFAULT 0 COMMENT '归档总字节数',
    compression_ratio FLOAT COMMENT '压缩比率 原始/压缩',
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_seconds INT COMMENT '执行时长（秒）',
    error_code VARCHAR(50) COMMENT '错误码',
    error_message TEXT COMMENT '错误信息',
    error_stack TEXT COMMENT '错误堆栈',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    parent_job_id BIGINT COMMENT '父任务ID（重试链）',
    instance_id VARCHAR(100) COMMENT '执行实例ID',
    operator_id VARCHAR(50) COMMENT '操作人ID（手动触发时）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_tenant (tenant_id),
    INDEX idx_job_type (job_type),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time),
    INDEX idx_tenant_status (tenant_id, status),
    INDEX idx_instance (instance_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='归档任务执行日志表';

-- ============================================================
-- 租户级保留策略表
-- 支持合规/运营/自定义三种策略类型的差异化保留周期
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_tenant_retention_policies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL UNIQUE COMMENT '租户ID（一租户一策略）',
    policy_name VARCHAR(200) NOT NULL COMMENT '策略名称',
    policy_type VARCHAR(30) NOT NULL DEFAULT 'standard' COMMENT '策略类型: compliance(合规7年)/operations(运营1年)/custom(自定义)',
    hot_data_days INT DEFAULT 90 COMMENT '热数据保留天数（MySQL）',
    warm_data_days INT DEFAULT 365 COMMENT '温数据保留天数（快速冷存储，低延迟）',
    cold_data_days INT DEFAULT 2555 COMMENT '冷数据保留天数（归档存储，7年=2555天）',
    total_retention_days INT DEFAULT 2555 COMMENT '总保留天数（到期永久删除）',
    archive_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用自动归档',
    archive_cron VARCHAR(100) DEFAULT '0 2 * * *' COMMENT '归档调度Cron，默认每天凌晨2点',
    archive_batch_size INT DEFAULT 10000 COMMENT '归档批处理大小',
    archive_parallelism INT DEFAULT 2 COMMENT '归档并行度',
    archive_storage_type VARCHAR(20) DEFAULT 's3' COMMENT '默认冷存储类型',
    archive_compression VARCHAR(20) DEFAULT 'snappy' COMMENT '归档压缩编码',
    cleanup_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用到期清理',
    cleanup_cron VARCHAR(100) DEFAULT '0 3 1 * *' COMMENT '清理调度Cron，默认每月1号凌晨3点',
    delete_permanently TINYINT(1) DEFAULT 0 COMMENT '到期是否永久删除（0=仅标记，1=物理删除）',
    lazy_load_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用冷数据懒加载',
    lazy_load_cache_days INT DEFAULT 7 COMMENT '懒加载缓存天数（加载到热区后保留）',
    lazy_load_max_concurrent INT DEFAULT 3 COMMENT '最大并发懒加载任务数',
    predict_read_tier VARCHAR(20) DEFAULT 'hot' COMMENT '预测任务读取层级: hot_only/hot_warm/all',
    training_read_tier VARCHAR(20) DEFAULT 'hot' COMMENT '训练任务读取层级: hot_only/hot_warm/all',
    analysis_read_tier VARCHAR(20) DEFAULT 'hot_warm' COMMENT '分析任务读取层级: hot_only/hot_warm/all',
    priority_tables TEXT COMMENT '优先归档的表 JSON',
    exclude_tables TEXT COMMENT '排除归档的表 JSON',
    version INT DEFAULT 1 COMMENT '策略版本号（乐观锁）',
    effective_time DATETIME COMMENT '生效时间',
    description VARCHAR(500) COMMENT '策略描述',
    create_by VARCHAR(50) COMMENT '创建人',
    update_by VARCHAR(50) COMMENT '更新人',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_tenant (tenant_id),
    INDEX idx_policy_type (policy_type),
    INDEX idx_archive_enabled (archive_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户级保留策略表';

-- ============================================================
-- 冷数据懒加载请求记录表
-- 审计历史分析API触发的冷数据按需加载
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_cold_data_load_requests (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT NOT NULL COMMENT '租户ID',
    request_id VARCHAR(64) UNIQUE NOT NULL COMMENT '请求唯一ID',
    source_api VARCHAR(200) COMMENT '触发的API路径',
    source_type VARCHAR(30) NOT NULL COMMENT '来源类型: analysis_api/training_api/user_manual/admin_operation',
    operator_id VARCHAR(50) COMMENT '操作人/调用方ID',
    operator_name VARCHAR(200) COMMENT '操作人/调用方名称',
    source_table VARCHAR(100) NOT NULL COMMENT '源表名',
    sensor_ids TEXT COMMENT '查询的传感器/螺栓ID JSON',
    time_start DATETIME NOT NULL COMMENT '查询开始时间',
    time_end DATETIME NOT NULL COMMENT '查询结束时间',
    required_partitions TEXT COMMENT '需要加载的分区键 JSON',
    archive_metadata_ids TEXT COMMENT '关联的归档元数据ID列表 JSON',
    load_priority VARCHAR(20) DEFAULT 'normal' COMMENT '优先级: low/normal/high/urgent',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/loading/completed/failed/cancelled/expired',
    cache_target VARCHAR(20) DEFAULT 'hot_partition' COMMENT '缓存目标: hot_partition/temporary_table/in_memory',
    cache_expire_time DATETIME COMMENT '缓存过期时间',
    total_records_expected BIGINT COMMENT '预期记录数',
    total_records_loaded BIGINT COMMENT '实际加载记录数',
    total_bytes_loaded BIGINT COMMENT '实际加载字节数',
    estimated_wait_seconds INT COMMENT '预估等待时间（秒）',
    start_time DATETIME COMMENT '开始加载时间',
    end_time DATETIME COMMENT '完成加载时间',
    duration_seconds INT COMMENT '加载耗时（秒）',
    hit_count INT DEFAULT 0 COMMENT '加载后被访问次数',
    last_hit_time DATETIME COMMENT '最后访问时间',
    error_code VARCHAR(50) COMMENT '错误码',
    error_message TEXT COMMENT '错误信息',
    callback_url VARCHAR(500) COMMENT '加载完成回调URL',
    callback_status VARCHAR(20) COMMENT '回调状态: pending/success/failed',
    extra_info TEXT COMMENT '扩展信息 JSON',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_tenant (tenant_id),
    INDEX idx_status (status),
    INDEX idx_request_id (request_id),
    INDEX idx_time_range (time_start, time_end),
    INDEX idx_source_table (tenant_id, source_table),
    INDEX idx_create_time (create_time),
    INDEX idx_cache_expire (cache_expire_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='冷数据懒加载请求记录表';

-- ============================================================
-- 插入默认租户保留策略
-- ============================================================
INSERT INTO sc_tenant_retention_policies (
    tenant_id, policy_name, policy_type,
    hot_data_days, warm_data_days, cold_data_days, total_retention_days,
    archive_enabled, archive_cron,
    cleanup_enabled, cleanup_cron, delete_permanently,
    lazy_load_enabled, lazy_load_cache_days,
    predict_read_tier, training_read_tier, analysis_read_tier,
    description, create_by
) VALUES (
    1, '默认标准策略', 'operations',
    90, 365, 365, 365,
    1, '0 2 * * *',
    1, '0 3 1 * *', 0,
    1, 7,
    'hot_only', 'hot_only', 'hot_warm',
    '默认运营级策略：热数据90天，总保留1年', 'system'
), (
    0, '全局合规策略模板', 'compliance',
    90, 365, 2555, 2555,
    1, '0 1 * * *',
    1, '0 2 1 * *', 0,
    1, 14,
    'hot_only', 'hot_warm', 'all',
    '合规级策略模板：7年完整保留，适用于法规要求场景（tenant_id=0为模板）', 'system'
) ON DUPLICATE KEY UPDATE update_time = CURRENT_TIMESTAMP;

-- 初始化分区键（为已存在的测试数据创建分区记录）
INSERT INTO sc_archive_partition_keys (
    tenant_id, table_name, partition_name, partition_key,
    partition_start, partition_end, record_count, archive_status
)
SELECT
    1 as tenant_id,
    'sc_bolt_data' as table_name,
    CONCAT('p', DATE_FORMAT(create_time, '%Y%m')) as partition_name,
    DATE_FORMAT(create_time, '%Y%m') as partition_key,
    DATE_FORMAT(DATE_FORMAT(create_time, '%Y-%m-01'), '%Y-%m-%d 00:00:00') as partition_start,
    DATE_FORMAT(DATE_ADD(DATE_FORMAT(create_time, '%Y-%m-01'), INTERVAL 1 MONTH), '%Y-%m-%d 00:00:00') as partition_end,
    COUNT(*) as record_count,
    'hot' as archive_status
FROM sc_bolt_data
GROUP BY DATE_FORMAT(create_time, '%Y%m')
ON DUPLICATE KEY UPDATE record_count = VALUES(record_count);

-- 显示归档模块新增的表
SHOW TABLES LIKE '%archive%';
SHOW TABLES LIKE '%retention%';
SHOW TABLES LIKE '%cold_data%';

-- ============================================================
-- Webhook 出站订阅模块
-- ============================================================

CREATE TABLE IF NOT EXISTS sc_webhook_subscriptions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT COMMENT '租户ID',
    name VARCHAR(200) NOT NULL COMMENT '订阅名称',
    url VARCHAR(500) NOT NULL COMMENT 'Webhook URL',
    secret VARCHAR(200) COMMENT 'HMAC签名密钥',
    event_types TEXT COMMENT '订阅事件类型 JSON: ["status_changed","risk_high","fault_detected"]',
    filter_node_types TEXT COMMENT '节点类型过滤 JSON: ["bolt","flange"]',
    filter_node_ids TEXT COMMENT '节点ID范围过滤 JSON: ["B001","B002"]',
    min_level INT DEFAULT 0 COMMENT '最低等级过滤 (0=不过滤, 1-4)',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    max_retries INT DEFAULT 5 COMMENT '最大重试次数',
    timeout_seconds INT DEFAULT 10 COMMENT 'HTTP超时秒数',
    enable_digest TINYINT(1) DEFAULT 0 COMMENT '是否启用批量合并',
    digest_window_seconds INT DEFAULT 300 COMMENT '合并窗口秒数（默认5分钟）',
    description VARCHAR(500) COMMENT '描述',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_whsub_tenant (tenant_id),
    INDEX idx_whsub_enabled (enabled),
    INDEX idx_whsub_tenant_enabled (tenant_id, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Webhook订阅配置表';

CREATE TABLE IF NOT EXISTS sc_webhook_delivery_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT COMMENT '租户ID',
    subscription_id BIGINT NOT NULL COMMENT '关联订阅ID',
    event_id VARCHAR(64) COMMENT '事件ID',
    event_type VARCHAR(50) COMMENT '事件类型',
    node_type VARCHAR(20) COMMENT '节点类型',
    node_id VARCHAR(100) COMMENT '节点ID',
    payload TEXT COMMENT '请求体 JSON',
    hmac_signature VARCHAR(128) COMMENT 'HMAC-SHA256签名',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态 pending/success/failed/dead_letter',
    http_status_code INT COMMENT 'HTTP响应状态码',
    response_body TEXT COMMENT 'HTTP响应体（截断）',
    retry_count INT DEFAULT 0 COMMENT '已重试次数',
    next_retry_at DATETIME COMMENT '下次重试时间',
    error_message TEXT COMMENT '错误信息',
    is_digest TINYINT(1) DEFAULT 0 COMMENT '是否为合并推送',
    digest_event_count INT DEFAULT 0 COMMENT '合并的事件数量',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_whlog_tenant (tenant_id),
    INDEX idx_whlog_sub (subscription_id),
    INDEX idx_whlog_status (status),
    INDEX idx_whlog_event (event_id),
    INDEX idx_whlog_node (node_type, node_id),
    INDEX idx_whlog_tenant_sub (tenant_id, subscription_id),
    INDEX idx_whlog_tenant_status (tenant_id, status),
    INDEX idx_whlog_retry (status, next_retry_at),
    INDEX idx_whlog_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Webhook投递日志表';

CREATE TABLE IF NOT EXISTS sc_webhook_dead_letters (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT COMMENT '租户ID',
    subscription_id BIGINT NOT NULL COMMENT '关联订阅ID',
    event_id VARCHAR(64) COMMENT '原始事件ID',
    event_type VARCHAR(50) COMMENT '事件类型',
    node_type VARCHAR(20) COMMENT '节点类型',
    node_id VARCHAR(100) COMMENT '节点ID',
    original_payload TEXT COMMENT '原始请求体 JSON',
    last_error TEXT COMMENT '最后一次错误信息',
    total_retries INT DEFAULT 0 COMMENT '总重试次数',
    dead_letter_reason VARCHAR(200) COMMENT '进入死信队列原因',
    original_created_at DATETIME COMMENT '原始事件创建时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_whdl_tenant (tenant_id),
    INDEX idx_whdl_sub (subscription_id),
    INDEX idx_whdl_event (event_id),
    INDEX idx_whdl_node (node_type, node_id),
    INDEX idx_whdl_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Webhook死信队列表';

SHOW TABLES LIKE '%webhook%';

-- ============================================================
-- 特征存储模块 - Feature Store
-- ============================================================

-- ============================================================
-- 特征 Schema 版本表
-- 管理特征向量的结构定义，保证训练和推理使用一致的特征结构
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_feature_schema_versions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    version VARCHAR(20) NOT NULL UNIQUE COMMENT '特征版本号，如 v1.0, v1.1',
    dimension INT NOT NULL COMMENT '特征维度数量',
    feature_names TEXT NOT NULL COMMENT '特征名称列表 JSON，按顺序排列',
    feature_types TEXT COMMENT '特征类型列表 JSON，如 ["numeric", "numeric", "categorical"]',
    description TEXT COMMENT '版本变更说明',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否为当前活跃版本',
    compatible_versions TEXT COMMENT '兼容的旧版本列表 JSON，如 ["v1.0"]',
    breaking_change TINYINT(1) DEFAULT 0 COMMENT '是否为不兼容变更',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_schema_version (version),
    INDEX idx_schema_active (is_active),
    INDEX idx_schema_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='特征Schema版本表';

-- ============================================================
-- 特征快照表
-- 存储每次计算的特征向量快照，用于训练复现和推理分析
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_feature_snapshots (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    node_id VARCHAR(100) NOT NULL COMMENT '节点ID（螺栓ID或法兰面ID）',
    node_type VARCHAR(20) NOT NULL COMMENT '节点类型 bolt/flange',
    compute_time DATETIME NOT NULL COMMENT '特征计算时间（对应数据窗口的结束时间）',
    feature_version VARCHAR(20) NOT NULL COMMENT '特征版本号，关联 sc_feature_schema_versions.version',
    vector JSON COMMENT '特征向量 JSON 格式（便于调试）',
    vector_bin BLOB COMMENT '特征向量二进制格式（节省存储空间）',
    vector_dim INT COMMENT '特征维度，用于快速校验',
    source_window_hash VARCHAR(64) COMMENT '输入数据窗口的哈希值，用于数据溯源和去重',
    source_window_start DATETIME COMMENT '输入数据窗口起始时间',
    source_window_end DATETIME COMMENT '输入数据窗口结束时间',
    data_source VARCHAR(50) COMMENT '数据来源：training/inference/debug',
    model_version VARCHAR(50) COMMENT '关联的模型版本（推理时）',
    prediction_result TEXT COMMENT '关联的预测结果快照 JSON（推理时）',
    is_used_for_training TINYINT(1) DEFAULT 0 COMMENT '是否已用于训练',
    training_session_id VARCHAR(100) COMMENT '关联的训练会话ID',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_feature_node (node_type, node_id),
    INDEX idx_feature_compute_time (compute_time),
    INDEX idx_feature_version (feature_version),
    INDEX idx_feature_window_hash (source_window_hash),
    INDEX idx_feature_source (data_source),
    INDEX idx_feature_training (is_used_for_training, training_session_id),
    INDEX idx_feature_tenant_node (tenant_id, node_type, node_id),
    INDEX idx_feature_tenant_time (tenant_id, compute_time),
    UNIQUE KEY idx_feature_unique (node_id, compute_time, feature_version, source_window_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='特征快照表';

-- ============================================================
-- 初始化特征 Schema 版本
-- ============================================================

-- v1.0: 58维基础特征
INSERT INTO sc_feature_schema_versions (
    version, dimension, feature_names, feature_types,
    description, is_active, compatible_versions, breaking_change
) VALUES (
    'v1.0',
    58,
    '["rolling_mean_5","rolling_std_5","rolling_max_5","rolling_min_5","rolling_mean_10","rolling_std_10","rolling_max_10","rolling_min_10","rolling_mean_20","rolling_std_20","rolling_max_20","rolling_min_20","rolling_mean_50","rolling_std_50","rolling_max_50","rolling_min_50","trend_slope","trend_intercept","fft_dominant_freq","fft_dominant_amplitude","fft_second_freq","fft_second_amplitude","autocorr_lag1","autocorr_lag5","mean","std","median","skewness","kurtosis","max_value","min_value","range","mean_abs_change","change_std","max_increase","max_decrease","q25","q75","iqr","zero_crossing_rate","signal_energy","safety_deviation_ratio","below_min_ratio","above_max_ratio","warning_zone_ratio","critical_zone_ratio","has_sudden_drop","recent_trend_slope","volatility_increase","consecutive_below_ratio","recovery_count","coefficient_of_variation"]',
    '["numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric"]',
    '初始版本，包含58维时序统计特征和领域特征',
    1,
    '[]',
    0
);

-- v1.1: 新增工况特征，共65维（不兼容旧版本）
INSERT INTO sc_feature_schema_versions (
    version, dimension, feature_names, feature_types,
    description, is_active, compatible_versions, breaking_change
) VALUES (
    'v1.1',
    65,
    '["rolling_mean_5","rolling_std_5","rolling_max_5","rolling_min_5","rolling_mean_10","rolling_std_10","rolling_max_10","rolling_min_10","rolling_mean_20","rolling_std_20","rolling_max_20","rolling_min_20","rolling_mean_50","rolling_std_50","rolling_max_50","rolling_min_50","trend_slope","trend_intercept","fft_dominant_freq","fft_dominant_amplitude","fft_second_freq","fft_second_amplitude","autocorr_lag1","autocorr_lag5","mean","std","median","skewness","kurtosis","max_value","min_value","range","mean_abs_change","change_std","max_increase","max_decrease","q25","q75","iqr","zero_crossing_rate","signal_energy","safety_deviation_ratio","below_min_ratio","above_max_ratio","warning_zone_ratio","critical_zone_ratio","has_sudden_drop","recent_trend_slope","volatility_increase","consecutive_below_ratio","recovery_count","coefficient_of_variation","wc_temperature_level","wc_humidity_level","wc_pressure_level","wc_vibration_level","wc_operating_mode","wc_load_factor","wc_seasonal_factor"]',
    '["numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric","numeric"]',
    '新增7维工况特征：温度等级、湿度等级、压力等级、振动等级、运行模式、负载系数、季节因子。维度从58增加到65，为不兼容变更。',
    1,
    '[]',
    1
);

-- 显示特征存储相关表
SHOW TABLES LIKE '%feature%';
SHOW COLUMNS FROM sc_feature_snapshots;
SHOW COLUMNS FROM sc_feature_schema_versions;

-- ============================================================
-- 模型漂移检测模块
-- ============================================================

-- ============================================================
-- 模型漂移配置表
-- 定义每个模型的漂移检测参数和响应策略
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_model_drift_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    model_id VARCHAR(100) NOT NULL COMMENT '模型标识',
    model_type VARCHAR(20) NOT NULL COMMENT '模型类型 bolt/flange',
    version VARCHAR(20) COMMENT '版本号，NULL表示对所有版本生效',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用漂移检测',
    response_strategy VARCHAR(20) DEFAULT 'notify' COMMENT '响应策略: notify/shadow_retrain/auto_retrain',
    psi_threshold FLOAT DEFAULT 0.2 COMMENT 'PSI(数据分布漂移)阈值',
    ks_threshold FLOAT DEFAULT 0.05 COMMENT 'KS检验p值阈值(低于则判定漂移)',
    confidence_drift_threshold FLOAT DEFAULT 0.15 COMMENT '置信度分布漂移阈值(KS统计量)',
    false_positive_rate_threshold FLOAT DEFAULT 0.10 COMMENT '误报率阈值',
    false_positive_window_days INT DEFAULT 7 COMMENT '误报率统计窗口(天)',
    feature_mean_shift_threshold FLOAT DEFAULT 0.10 COMMENT '特征均值偏移阈值(标准差倍数)',
    composite_score_threshold FLOAT DEFAULT 0.6 COMMENT '综合漂移分数阈值',
    consecutive_days_alert INT DEFAULT 2 COMMENT '连续N天超阈值才触发响应',
    shadow_retrain_quality_bar FLOAT DEFAULT 0.9 COMMENT 'Shadow模型最低质量门槛(相对当前版本%)',
    auto_retrain_min_days INT DEFAULT 7 COMMENT '自动重训最小间隔天数',
    weights_json TEXT COMMENT '各维度权重配置 JSON',
    notify_channels TEXT COMMENT '通知渠道列表 JSON',
    notify_targets TEXT COMMENT '通知目标列表 JSON',
    extra_config TEXT COMMENT '扩展配置 JSON',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY idx_drift_config_model (model_id, model_type, version, tenant_id),
    INDEX idx_drift_config_tenant (tenant_id),
    INDEX idx_drift_config_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型漂移检测配置表';

-- ============================================================
-- 模型漂移基线表
-- 存储模型训练时的基准分布，用于漂移对比
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_model_drift_baselines (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    model_id VARCHAR(100) NOT NULL COMMENT '模型标识',
    model_type VARCHAR(20) NOT NULL COMMENT '模型类型 bolt/flange',
    version VARCHAR(20) NOT NULL COMMENT '版本号',
    baseline_type VARCHAR(30) NOT NULL COMMENT '基线类型: data_distribution/confidence_distribution/feature_stats',
    feature_name VARCHAR(100) COMMENT '特征名(per-feature基线)',
    bins_json TEXT COMMENT '分箱边界和计数 JSON',
    stats_json TEXT COMMENT '统计量 JSON(均值/方差/分位数等)',
    sample_count INT COMMENT '基线样本量',
    computed_at DATETIME COMMENT '基线计算时间',
    data_window_start DATETIME COMMENT '基线数据窗口起始',
    data_window_end DATETIME COMMENT '基线数据窗口结束',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY idx_drift_baseline_unique (model_id, model_type, version, baseline_type, feature_name, tenant_id),
    INDEX idx_drift_baseline_model (model_id, model_type, version),
    INDEX idx_drift_baseline_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型漂移基线表';

-- ============================================================
-- 模型漂移事件表
-- 记录每次漂移检测的结果和触发的响应
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_model_drift_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    event_no VARCHAR(50) UNIQUE COMMENT '事件编号',
    model_id VARCHAR(100) NOT NULL COMMENT '模型标识',
    model_type VARCHAR(20) NOT NULL COMMENT '模型类型 bolt/flange',
    version VARCHAR(20) COMMENT '模型版本',
    detection_date DATE NOT NULL COMMENT '检测日期(批处理日期)',
    psi_score FLOAT COMMENT 'PSI分数(数据分布漂移)',
    ks_p_value FLOAT COMMENT 'KS检验p值',
    ks_statistic FLOAT COMMENT 'KS检验统计量',
    confidence_drift_score FLOAT COMMENT '置信度分布漂移分数(KS统计量)',
    confidence_ks_p_value FLOAT COMMENT '置信度分布KS检验p值',
    false_positive_rate FLOAT COMMENT '误报率',
    false_positive_count INT COMMENT '误报样本数',
    total_prediction_count INT COMMENT '总预测样本数',
    feature_drift_json TEXT COMMENT '各特征漂移详情 JSON',
    feature_mean_shift_count INT COMMENT '特征均值偏移的特征数',
    composite_drift_score FLOAT COMMENT '综合漂移分数(加权平均)',
    drift_level VARCHAR(20) DEFAULT 'none' COMMENT '漂移等级: none/low/medium/high/critical',
    triggered_dims TEXT COMMENT '触发告警的漂移维度 JSON',
    consecutive_days INT DEFAULT 1 COMMENT '连续超阈值天数',
    response_action VARCHAR(20) DEFAULT 'none' COMMENT '实际执行的响应动作: none/notify/shadow_retrain/auto_retrain',
    response_status VARCHAR(20) DEFAULT 'pending' COMMENT '响应状态: pending/running/completed/failed/skipped',
    response_details TEXT COMMENT '响应详情 JSON(训练会话ID等)',
    notification_sent TINYINT(1) DEFAULT 0 COMMENT '是否已发送通知',
    retrain_session_id VARCHAR(100) COMMENT '重训会话ID',
    new_version VARCHAR(20) COMMENT '重训产生的新版本号',
    alert_level INT DEFAULT 2 COMMENT '告警级别 1-4',
    tenant_id BIGINT COMMENT '租户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_drift_event_model_date (model_id, model_type, detection_date),
    INDEX idx_drift_event_date (detection_date),
    INDEX idx_drift_event_level (drift_level),
    INDEX idx_drift_event_action (response_action, response_status),
    INDEX idx_drift_event_tenant_date (tenant_id, detection_date),
    INDEX idx_drift_event_tenant_model (tenant_id, model_id, model_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型漂移事件表';

-- ============================================================
-- 插入默认漂移配置
-- ============================================================
INSERT INTO sc_model_drift_config (
    model_id, model_type, version, enabled, response_strategy,
    psi_threshold, ks_threshold, confidence_drift_threshold,
    false_positive_rate_threshold, false_positive_window_days,
    feature_mean_shift_threshold, composite_score_threshold,
    consecutive_days_alert, shadow_retrain_quality_bar, auto_retrain_min_days,
    weights_json, notify_channels, notify_targets
) VALUES (
    'default', 'bolt', NULL, 1, 'notify',
    0.2, 0.05, 0.15,
    0.10, 7,
    0.10, 0.6,
    2, 0.9, 7,
    '{"psi":0.25,"ks":0.20,"confidence":0.25,"false_positive":0.20,"feature_shift":0.10}',
    '["email"]',
    '{"email":["admin@example.com"]}'
), (
    'default', 'flange', NULL, 1, 'notify',
    0.2, 0.05, 0.15,
    0.10, 7,
    0.10, 0.6,
    2, 0.9, 7,
    '{"psi":0.25,"ks":0.20,"confidence":0.25,"false_positive":0.20,"feature_shift":0.10}',
    '["email"]',
    '{"email":["admin@example.com"]}'
);

-- 显示漂移检测模块表
SHOW TABLES LIKE 'sc_model_drift%';

-- ============================================================
-- 影子模式对比记录表
-- 记录主版本与影子版本的预测结果对比，用于A/B测试与版本晋升评估
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_shadow_comparison (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT COMMENT '租户ID',
    model_type VARCHAR(20) NOT NULL COMMENT '模型类型: bolt/flange',
    node_id VARCHAR(100) NOT NULL COMMENT '节点ID（螺栓ID或法兰ID）',
    node_type VARCHAR(20) COMMENT '节点类型: bolt/flange（冗余字段便于查询）',
    main_version VARCHAR(20) NOT NULL COMMENT '主版本号',
    shadow_version VARCHAR(20) NOT NULL COMMENT '影子版本号',

    main_status_code INT NOT NULL COMMENT '主版本状态码 0-4',
    main_status VARCHAR(50) COMMENT '主版本状态文本',
    main_confidence FLOAT COMMENT '主版本置信度 0-1',

    shadow_status_code INT NOT NULL COMMENT '影子版本状态码 0-4',
    shadow_status VARCHAR(50) COMMENT '影子版本状态文本',
    shadow_confidence FLOAT COMMENT '影子版本置信度 0-1',

    is_agreement TINYINT(1) DEFAULT 0 COMMENT '是否预测一致（状态码相同）',
    is_shadow_more_sensitive TINYINT(1) DEFAULT 0 COMMENT '影子版本是否更敏感（影子检测到异常而主版本没有）',
    is_shadow_more_conservative TINYINT(1) DEFAULT 0 COMMENT '影子版本是否更保守（主版本检测到异常而影子版本没有）',

    main_latency_ms INT COMMENT '主版本预测耗时(毫秒)',
    shadow_latency_ms INT COMMENT '影子版本预测耗时(毫秒)',

    prediction_time DATETIME COMMENT '预测时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_tenant_version (tenant_id, model_type, main_version, shadow_version),
    INDEX idx_node (node_type, node_id),
    INDEX idx_prediction_time (prediction_time),
    INDEX idx_agreement (is_agreement),
    INDEX idx_sensitive (is_shadow_more_sensitive),
    INDEX idx_conservative (is_shadow_more_conservative),
    INDEX idx_create_time (create_time),
    INDEX idx_tenant_model (tenant_id, model_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='影子模式预测对比记录表';

-- ============================================================
-- 模型版本晋升建议工单表
-- 当影子版本满足晋升条件时自动生成的晋升建议工单
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_model_promotion_suggestions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    tenant_id BIGINT COMMENT '租户ID',
    model_type VARCHAR(20) NOT NULL COMMENT '模型类型: bolt/flange',
    model_id VARCHAR(100) NOT NULL COMMENT '模型标识（节点ID）',
    main_version VARCHAR(20) NOT NULL COMMENT '当前主版本号',
    shadow_version VARCHAR(20) NOT NULL COMMENT '待晋升影子版本号',

    suggestion_no VARCHAR(64) UNIQUE NOT NULL COMMENT '建议工单编号',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending待审批/approved已批准/rejected已拒绝/executed已执行',

    agreement_rate FLOAT COMMENT '预测一致率 0-1',
    shadow_more_sensitive_rate FLOAT COMMENT '影子版本更敏感率 0-1',
    shadow_more_conservative_rate FLOAT COMMENT '影子版本更保守率 0-1',

    main_false_negative_rate FLOAT COMMENT '主版本漏报率（主版本0而影子>0的比例）',
    shadow_false_negative_rate FLOAT COMMENT '影子版本漏报率（影子0而主版本>0的比例，用于反向验证）',
    false_negative_improvement_rate FLOAT COMMENT '漏报率下降比例 (main_fn - shadow_fn) / main_fn',

    shadow_run_days INT COMMENT '影子运行天数',
    total_comparisons INT COMMENT '总对比样本数',

    per_status_stats TEXT COMMENT '按状态分桶统计结果 JSON',
    latency_stats TEXT COMMENT '延迟对比统计 JSON',

    work_order_id BIGINT COMMENT '关联的系统工单ID（sc_work_orders）',

    approver_id VARCHAR(50) COMMENT '审批人ID',
    approver_name VARCHAR(100) COMMENT '审批人姓名',
    approve_time DATETIME COMMENT '审批时间',
    approve_note TEXT COMMENT '审批备注',

    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE KEY uk_suggestion_no (suggestion_no),
    INDEX idx_tenant_model (tenant_id, model_type, model_id),
    INDEX idx_versions (main_version, shadow_version),
    INDEX idx_status (status),
    INDEX idx_create_time (create_time),
    INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型版本晋升建议工单表';

-- 显示影子模式模块表
SHOW TABLES LIKE 'sc_shadow%';
SHOW TABLES LIKE 'sc_model_promotion%';

-- ============================================================
-- 灾备备份与恢复 - 备份记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_backup_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    backup_id VARCHAR(64) NOT NULL UNIQUE COMMENT '备份唯一ID（BU+时间戳+随机）',
    backup_type VARCHAR(20) NOT NULL COMMENT '备份类型: full全量/incremental增量/snapshot快照',
    backup_scope VARCHAR(50) NOT NULL COMMENT '备份范围: model_config仅模型配置/full_with_db含数据库',
    status VARCHAR(20) DEFAULT 'running' COMMENT '状态: running/completed/failed/uploaded/purged',
    progress_percent TINYINT DEFAULT 0 COMMENT '进度百分比 0-100',
    error_message TEXT COMMENT '失败错误信息',
    stack_trace TEXT COMMENT '异常堆栈（debug用）',

    size_bytes BIGINT DEFAULT 0 COMMENT '原始未压缩总大小（字节）',
    compressed_size_bytes BIGINT DEFAULT 0 COMMENT '压缩后归档大小（字节）',
    component_list TEXT COMMENT '包含的组件列表 JSON: ["models","config","database"]',
    component_sizes TEXT COMMENT '各组件大小明细 JSON: {"models":123456,"config":...}',
    file_count INT DEFAULT 0 COMMENT '包含文件总数',

    checksum_sha256 VARCHAR(64) COMMENT '归档整体 SHA256 哈希',
    checksum_md5 VARCHAR(32) COMMENT '归档整体 MD5 哈希',
    checksums_detail MEDIUMTEXT COMMENT '组件级文件清单哈希 JSON: {"models":{"file1":"sha256",...}}',

    retention_policy VARCHAR(20) DEFAULT 'weekly' COMMENT '保留策略: incremental/weekly/monthly/snapshot',
    retention_days INT DEFAULT 90 COMMENT '实际保留天数',
    expire_time DATETIME COMMENT '过期时间（到期自动purge）',

    base_backup_id VARCHAR(64) COMMENT '基础全量备份ID（增量关联用）',
    backup_chain_id VARCHAR(64) COMMENT '备份链ID（每周一条链，如 chain_2025_W25）',
    incremental_since DATETIME COMMENT '增量备份的mtime起点（上次备份完成时间）',

    storage_location VARCHAR(20) DEFAULT 'local' COMMENT '存储位置: local/remote/both',
    local_path VARCHAR(1024) COMMENT '本地归档文件绝对路径',
    remote_bucket VARCHAR(256) COMMENT '远程存储桶名',
    remote_object_key VARCHAR(1024) COMMENT '远程对象存储Key',
    remote_endpoint VARCHAR(512) COMMENT '远程Endpoint（标识不同S3兼容服务）',
    remote_upload_status VARCHAR(20) COMMENT '远程上传状态: pending/uploading/success/failed/skipped',
    remote_upload_error TEXT COMMENT '远程上传错误信息',
    remote_upload_retries TINYINT DEFAULT 0 COMMENT '远程上传重试次数',

    database_dump_info TEXT COMMENT '数据库dump信息 JSON: {"tables":N,"rows":M,"dump_file":"..."}',
    model_versions TEXT COMMENT '模型版本快照 JSON: {"bolt":{"v1.2":"path",...}}',
    config_snapshot TEXT COMMENT '关键配置快照 JSON（config.yaml摘要+版本号）',

    trigger_type VARCHAR(20) DEFAULT 'manual' COMMENT '触发类型: scheduled/manual/pre_restore',
    trigger_source VARCHAR(256) COMMENT '触发来源（scheduler任务名/API用户/操作入口）',
    operator_id VARCHAR(100) COMMENT '操作人ID（scheduled为system:scheduler）',
    operator_name VARCHAR(200) COMMENT '操作人姓名',
    operator_note TEXT COMMENT '操作备注（manual时填写）',

    start_time DATETIME COMMENT '备份开始时间',
    complete_time DATETIME COMMENT '备份完成时间',
    duration_seconds INT COMMENT '备份耗时（秒）',

    restore_count INT DEFAULT 0 COMMENT '被用于恢复的次数',
    last_restore_time DATETIME COMMENT '最近一次恢复时间',
    pre_restore_snapshot_id VARCHAR(64) COMMENT '恢复产生的快照备份ID（关联反向）',

    tenant_id BIGINT COMMENT '租户ID（预留，目前全局备份）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_backup_type_status (backup_type, status),
    INDEX idx_chain_id (backup_chain_id),
    INDEX idx_base_backup (base_backup_id),
    INDEX idx_retention_expire (retention_policy, expire_time),
    INDEX idx_status_progress (status, progress_percent),
    INDEX idx_storage_location (storage_location, remote_upload_status),
    INDEX idx_trigger (trigger_type, trigger_source),
    INDEX idx_complete_time (complete_time),
    INDEX idx_tenant (tenant_id),
    INDEX idx_tenant_status_time (tenant_id, status, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='灾备备份记录表';

-- ============================================================
-- 灾备备份与恢复 - 恢复操作日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS sc_backup_restore_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    restore_id VARCHAR(64) NOT NULL UNIQUE COMMENT '恢复操作唯一ID',
    backup_id VARCHAR(64) NOT NULL COMMENT '来源备份ID（关联sc_backup_records）',

    status VARCHAR(20) DEFAULT 'running' COMMENT '状态: running/pre_snapshot/restoring/refreshing/completed/failed/rolled_back',
    progress_percent TINYINT DEFAULT 0 COMMENT '进度百分比 0-100',
    error_message TEXT COMMENT '失败错误信息',
    stack_trace TEXT COMMENT '异常堆栈',

    restore_scope VARCHAR(50) COMMENT '恢复范围: models/config/database/combined',
    restore_models TINYINT(1) DEFAULT 1 COMMENT '是否恢复模型',
    restore_config TINYINT(1) DEFAULT 1 COMMENT '是否恢复配置',
    restore_database TINYINT(1) DEFAULT 0 COMMENT '是否恢复数据库（高危，默认关闭）',

    pre_snapshot_backup_id VARCHAR(64) COMMENT '恢复前自动创建的pre-restore快照ID',
    pre_snapshot_path VARCHAR(1024) COMMENT 'pre-restore快照本地路径',

    restored_components TEXT COMMENT '已恢复组件列表 JSON',
    restore_details MEDIUMTEXT COMMENT '恢复详细步骤与结果 JSON',
    original_paths_backup TEXT COMMENT '原目录重命名备份路径 JSON: {"models":"/path.pre_restore_ts"}',

    cache_refresh_status VARCHAR(20) DEFAULT 'pending' COMMENT '模型缓存刷新状态: pending/running/success/failed/skipped',
    cache_refresh_detail TEXT COMMENT '缓存刷新细节 JSON',
    models_reloaded TEXT COMMENT '重载成功的模型列表 JSON',
    cache_refresh_duration_seconds INT COMMENT '缓存刷新耗时',

    validation_passed TINYINT(1) COMMENT '恢复后完整性校验是否通过',
    validation_detail TEXT COMMENT '校验详情 JSON（checksum比对）',

    trigger_type VARCHAR(20) DEFAULT 'manual' COMMENT '触发类型: manual/api/scheduled',
    operator_id VARCHAR(100) COMMENT '操作人ID',
    operator_name VARCHAR(200) COMMENT '操作人姓名',
    operator_note TEXT COMMENT '恢复原因/备注',

    skip_pre_snapshot TINYINT(1) DEFAULT 0 COMMENT '是否跳过pre-restore快照（不建议）',
    skip_cache_refresh TINYINT(1) DEFAULT 0 COMMENT '是否跳过缓存刷新',

    start_time DATETIME COMMENT '恢复开始时间',
    complete_time DATETIME COMMENT '恢复完成时间',
    duration_seconds INT COMMENT '总耗时（秒）',

    tenant_id BIGINT COMMENT '租户ID（预留）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_backup_id (backup_id),
    INDEX idx_status_progress (status, progress_percent),
    INDEX idx_pre_snapshot (pre_snapshot_backup_id),
    INDEX idx_trigger_operator (trigger_type, operator_id),
    INDEX idx_complete_time (complete_time),
    INDEX idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='灾备恢复操作日志表';

-- 初始化备份调度相关的 Leader 选举记录（避免首次运行无行）
INSERT IGNORE INTO sc_scheduler_leader (leader_key, leader_id, lease_expire_time, version) VALUES
('daily_incremental_backup_job', '', DATE_SUB(NOW(), INTERVAL 1 HOUR), 0),
('weekly_full_backup_job', '', DATE_SUB(NOW(), INTERVAL 1 HOUR), 0);

-- 显示灾备模块表
SHOW TABLES LIKE 'sc_backup%';
SHOW TABLES LIKE 'sc_%restore%';
