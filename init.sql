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

-- 显示创建的表
SHOW TABLES;
