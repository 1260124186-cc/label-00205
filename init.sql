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

-- 显示创建的表
SHOW TABLES;
