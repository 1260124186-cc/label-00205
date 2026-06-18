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
