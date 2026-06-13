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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_sensor_time (sensor_id, create_time),
    INDEX idx_collector (collector_id, splitter_num, position)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_node_type (node_type),
    INDEX idx_bolt_id (bolt_id),
    INDEX idx_flm_id (flm_id),
    INDEX idx_year_month (year_month)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_node_type (node_type),
    INDEX idx_bolt_id (bolt_id),
    INDEX idx_flm_id (flm_id)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_sensor (sensor_id),
    INDEX idx_type (anomaly_type),
    INDEX idx_time (create_time)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_model (model_id),
    INDEX idx_active (is_active)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_session (session_id),
    INDEX idx_model (model_id)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_alert_level (alert_level),
    INDEX idx_enabled (enabled)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_status (status),
    INDEX idx_level (alert_level),
    INDEX idx_node (node_type, node_id),
    INDEX idx_create_time (create_time)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_subscriber (subscriber_type, subscriber_id),
    INDEX idx_enabled (enabled)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_channel_type (channel_type)
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
    send_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
    INDEX idx_alert_id (alert_id),
    INDEX idx_status (status)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_alert_id (alert_id),
    INDEX idx_assignee (assignee_id),
    INDEX idx_create_time (create_time)
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
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '检查时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_dqc_sensor (sensor_id),
    INDEX idx_dqc_time (check_time),
    INDEX idx_dqc_score (overall_score),
    INDEX idx_dqc_level (quality_level)
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY idx_qr_date (report_date),
    INDEX idx_qr_create (create_time)
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
    current_model_count INT DEFAULT 0 COMMENT '当前模型数',
    current_api_calls_today INT DEFAULT 0 COMMENT '今日API调用次数',
    current_storage_mb DOUBLE DEFAULT 0.0 COMMENT '当前存储用量 MB',
    current_user_count INT DEFAULT 0 COMMENT '当前用户数',
    current_org_node_count INT DEFAULT 0 COMMENT '当前组织节点数',
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
