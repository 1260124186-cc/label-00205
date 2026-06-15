/** APIAuditLogListResponse */
export interface ApiAuditLogListResponse {
  /** 总数 */
  total: number;
  /** 审计日志列表 */
  items?: ApiAuditLogResponse[];
}

/** APIAuditLogResponse */
export interface ApiAuditLogResponse {
  id: number;
  /** API密钥ID */
  // OpenAPI name: key_id
  keyId?: string;
  /** 密钥名称 */
  // OpenAPI name: key_name
  keyName?: string;
  /** HTTP方法 */
  method?: string;
  /** 请求路径 */
  path?: string;
  /** 响应状态码 */
  // OpenAPI name: status_code
  statusCode?: number;
  /** 客户端IP */
  // OpenAPI name: client_ip
  clientIp?: string;
  /** 请求ID */
  // OpenAPI name: request_id
  requestId?: string;
  /** 扩展信息 */
  // OpenAPI name: extra_info
  extraInfo?: Record<string, any>;
  // OpenAPI name: create_time
  createTime: Date | string;
}

/** APIKeyCreateRequest */
export interface ApiKeyCreateRequest {
  /** 密钥名称 */
  name: string;
  /** 权限列表: read/write/admin */
  permissions?: string[];
  /** 每小时请求限制 */
  // OpenAPI name: rate_limit
  rateLimit?: number;
  /** 有效期（小时），None表示永不过期 */
  // OpenAPI name: expires_hours
  expiresHours?: any;
}

/** APIKeyCreateResponse */
export interface ApiKeyCreateResponse {
  /** 生成的API密钥（仅创建时返回完整密钥） */
  key: string;
  /** 密钥ID */
  // OpenAPI name: key_id
  keyId: string;
  /** 密钥名称 */
  name: string;
  /** 权限列表 */
  permissions?: string[];
  /** 速率限制 */
  // OpenAPI name: rate_limit
  rateLimit?: number;
  /** 过期时间 */
  // OpenAPI name: expires_at
  expiresAt?: any;
  /** 创建时间 */
  // OpenAPI name: created_at
  createdAt: string;
}

/** APIKeyInfoResponse */
export interface ApiKeyInfoResponse {
  /** 密钥ID */
  // OpenAPI name: key_id
  keyId: string;
  /** 密钥预览（前8后4位） */
  // OpenAPI name: key_preview
  keyPreview: string;
  /** 密钥名称 */
  name: string;
  /** 权限列表 */
  permissions?: string[];
  /** 速率限制 */
  // OpenAPI name: rate_limit
  rateLimit?: number;
  /** 是否已过期 */
  // OpenAPI name: is_expired
  isExpired?: boolean;
  /** 过期时间 */
  // OpenAPI name: expires_at
  expiresAt?: any;
  /** 创建时间 */
  // OpenAPI name: created_at
  createdAt?: any;
}

/** APIKeyListResponse */
export interface ApiKeyListResponse {
  /** 总数 */
  total: number;
  /** 密钥列表 */
  items?: ApiKeyInfoResponse[];
}

/** APIKeyRevokeResponse */
export interface ApiKeyRevokeResponse {
  /** 被吊销的密钥ID */
  // OpenAPI name: key_id
  keyId: string;
  /** 是否成功吊销 */
  revoked?: boolean;
}

/** APIKeyRotateResponse */
export interface ApiKeyRotateResponse {
  /** 旧密钥ID */
  // OpenAPI name: old_key_id
  oldKeyId: string;
  /** 新密钥（仅轮换时返回完整密钥） */
  // OpenAPI name: new_key
  newKey: string;
  /** 新密钥ID */
  // OpenAPI name: new_key_id
  newKeyId: string;
  /** 旧密钥宽限期截止时间 */
  // OpenAPI name: old_key_grace_expires
  oldKeyGraceExpires: Date | string;
  /** 权限列表（继承旧密钥） */
  permissions?: string[];
  /** 速率限制 */
  // OpenAPI name: rate_limit
  rateLimit?: number;
}

/** 告警事件响应 */
export interface AlertEventResponse {
  id: number;
  // OpenAPI name: alert_no
  alertNo: string;
  // OpenAPI name: rule_id
  ruleId?: any;
  // OpenAPI name: alert_level
  alertLevel: number;
  // OpenAPI name: original_level
  originalLevel?: any;
  // OpenAPI name: node_type
  nodeType?: any;
  // OpenAPI name: node_id
  nodeId?: any;
  title?: any;
  content?: any;
  confidence?: any;
  // OpenAPI name: risk_score
  riskScore?: any;
  recommendations?: any;
  status: string;
  // OpenAPI name: handler_id
  handlerId?: any;
  // OpenAPI name: handler_name
  handlerName?: any;
  // OpenAPI name: handle_time
  handleTime?: any;
  // OpenAPI name: handle_note
  handleNote?: any;
  // OpenAPI name: is_upgraded
  isUpgraded?: boolean;
  // OpenAPI name: upgrade_count
  upgradeCount?: number;
  // OpenAPI name: last_upgrade_time
  lastUpgradeTime?: any;
  // OpenAPI name: work_order_id
  workOrderId?: any;
  // OpenAPI name: source_prediction_id
  sourcePredictionId?: any;
  // OpenAPI name: silence_until
  silenceUntil?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** 处理告警请求 */
export interface AlertHandleRequest {
  /** 处理动作: acknowledge/resolve/ignore */
  action: string;
  /** 处理人ID */
  // OpenAPI name: handler_id
  handlerId?: any;
  /** 处理人姓名 */
  // OpenAPI name: handler_name
  handlerName?: any;
  /** 处理备注 */
  // OpenAPI name: handle_note
  handleNote?: any;
  /** 忽略时的静默期（分钟） */
  // OpenAPI name: silence_minutes
  silenceMinutes?: any;
}

/** 告警列表响应 */
export interface AlertListResponse {
  total: number;
  items: AlertEventResponse[];
}

/** 创建告警规则请求 */
export interface AlertRuleCreate {
  /** 规则名称 */
  // OpenAPI name: rule_name
  ruleName: string;
  /** 告警级别 1-4 */
  // OpenAPI name: alert_level
  alertLevel: number;
  /** 节点类型 bolt/flange/all */
  // OpenAPI name: node_type
  nodeType?: string;
  /** 节点ID列表，空表示全部 */
  // OpenAPI name: node_ids
  nodeIds?: any;
  /** 最低置信度 */
  // OpenAPI name: min_confidence
  minConfidence?: number;
  /** 静默期（分钟） */
  // OpenAPI name: silence_period
  silencePeriod?: number;
  /** 是否启用自动升级 */
  // OpenAPI name: enable_upgrade
  enableUpgrade?: boolean;
  /** 未处理升级时间（分钟） */
  // OpenAPI name: upgrade_minutes
  upgradeMinutes?: number;
  /** 升级到的级别 */
  // OpenAPI name: upgrade_to_level
  upgradeToLevel?: any;
  /** 是否启用 */
  enabled?: boolean;
  /** 规则描述 */
  description?: any;
}

/** 告警规则响应 */
export interface AlertRuleResponse {
  /** 规则名称 */
  // OpenAPI name: rule_name
  ruleName: string;
  /** 告警级别 1-4 */
  // OpenAPI name: alert_level
  alertLevel: number;
  /** 节点类型 bolt/flange/all */
  // OpenAPI name: node_type
  nodeType?: string;
  /** 节点ID列表，空表示全部 */
  // OpenAPI name: node_ids
  nodeIds?: any;
  /** 最低置信度 */
  // OpenAPI name: min_confidence
  minConfidence?: number;
  /** 静默期（分钟） */
  // OpenAPI name: silence_period
  silencePeriod?: number;
  /** 是否启用自动升级 */
  // OpenAPI name: enable_upgrade
  enableUpgrade?: boolean;
  /** 未处理升级时间（分钟） */
  // OpenAPI name: upgrade_minutes
  upgradeMinutes?: number;
  /** 升级到的级别 */
  // OpenAPI name: upgrade_to_level
  upgradeToLevel?: any;
  /** 是否启用 */
  enabled?: boolean;
  /** 规则描述 */
  description?: any;
  id: number;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** 更新告警规则请求 */
export interface AlertRuleUpdate {
  // OpenAPI name: rule_name
  ruleName?: any;
  // OpenAPI name: alert_level
  alertLevel?: any;
  // OpenAPI name: node_type
  nodeType?: any;
  // OpenAPI name: node_ids
  nodeIds?: any;
  // OpenAPI name: min_confidence
  minConfidence?: any;
  // OpenAPI name: silence_period
  silencePeriod?: any;
  // OpenAPI name: enable_upgrade
  enableUpgrade?: any;
  // OpenAPI name: upgrade_minutes
  upgradeMinutes?: any;
  // OpenAPI name: upgrade_to_level
  upgradeToLevel?: any;
  enabled?: any;
  description?: any;
}

/** 创建订阅请求 */
export interface AlertSubscriptionCreate {
  /** 订阅者类型 role/user/device */
  // OpenAPI name: subscriber_type
  subscriberType: string;
  /** 订阅者ID */
  // OpenAPI name: subscriber_id
  subscriberId: string;
  /** 订阅者名称 */
  // OpenAPI name: subscriber_name
  subscriberName?: any;
  /** 最低订阅级别 */
  // OpenAPI name: min_alert_level
  minAlertLevel?: number;
  /** 订阅的告警级别列表 */
  // OpenAPI name: alert_levels
  alertLevels?: any;
  /** 节点类型过滤 bolt/flange/all */
  // OpenAPI name: node_type
  nodeType?: string;
  /** 节点ID列表 */
  // OpenAPI name: node_ids
  nodeIds?: any;
  /** 通知渠道列表 */
  // OpenAPI name: notify_channels
  notifyChannels?: any;
  /** 通知目标 {渠道: [目标]} */
  // OpenAPI name: notify_targets
  notifyTargets?: any;
  /** 是否启用 */
  enabled?: boolean;
}

/** 订阅响应 */
export interface AlertSubscriptionResponse {
  /** 订阅者类型 role/user/device */
  // OpenAPI name: subscriber_type
  subscriberType: string;
  /** 订阅者ID */
  // OpenAPI name: subscriber_id
  subscriberId: string;
  /** 订阅者名称 */
  // OpenAPI name: subscriber_name
  subscriberName?: any;
  /** 最低订阅级别 */
  // OpenAPI name: min_alert_level
  minAlertLevel?: number;
  /** 订阅的告警级别列表 */
  // OpenAPI name: alert_levels
  alertLevels?: any;
  /** 节点类型过滤 bolt/flange/all */
  // OpenAPI name: node_type
  nodeType?: string;
  /** 节点ID列表 */
  // OpenAPI name: node_ids
  nodeIds?: any;
  /** 通知渠道列表 */
  // OpenAPI name: notify_channels
  notifyChannels?: any;
  /** 通知目标 {渠道: [目标]} */
  // OpenAPI name: notify_targets
  notifyTargets?: any;
  /** 是否启用 */
  enabled?: boolean;
  id: number;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** 更新订阅请求 */
export interface AlertSubscriptionUpdate {
  // OpenAPI name: subscriber_type
  subscriberType?: any;
  // OpenAPI name: subscriber_id
  subscriberId?: any;
  // OpenAPI name: subscriber_name
  subscriberName?: any;
  // OpenAPI name: min_alert_level
  minAlertLevel?: any;
  // OpenAPI name: alert_levels
  alertLevels?: any;
  // OpenAPI name: node_type
  nodeType?: any;
  // OpenAPI name: node_ids
  nodeIds?: any;
  // OpenAPI name: notify_channels
  notifyChannels?: any;
  // OpenAPI name: notify_targets
  notifyTargets?: any;
  enabled?: any;
}

/** 手动触发告警升级响应 */
export interface AlertUpgradeTriggerResponse {
  // OpenAPI name: upgraded_count
  upgradedCount: number;
  message: string;
}

/** 批量确认异常请求 */
export interface AnomalyBatchConfirmRequest {
  /** 异常记录ID列表 */
  // OpenAPI name: anomaly_ids
  anomalyIds: number[];
  /** 确认人ID */
  // OpenAPI name: confirmed_by
  confirmedBy?: any;
  /** 确认备注 */
  // OpenAPI name: confirm_note
  confirmNote?: any;
}

/** 批量标注误报请求 */
export interface AnomalyBatchFalsePositiveRequest {
  /** 异常记录ID列表 */
  // OpenAPI name: anomaly_ids
  anomalyIds: number[];
  /** 标注人ID */
  // OpenAPI name: confirmed_by
  confirmedBy?: any;
  /** 标注备注 */
  // OpenAPI name: confirm_note
  confirmNote?: any;
}

/** 批量操作结果响应 */
export interface AnomalyBatchResultResponse {
  /** 总数量 */
  total?: number;
  /** 成功数量 */
  success?: number;
  /** 失败数量 */
  failed?: number;
  /** 失败的ID列表 */
  // OpenAPI name: failed_ids
  failedIds?: number[];
}

/** 异常分类结果 */
export interface AnomalyClassificationSchema {
  // OpenAPI name: anomaly_id
  anomalyId?: any;
  // OpenAPI name: sensor_id
  sensorId: string;
  // OpenAPI name: anomaly_value
  anomalyValue: number;
  // OpenAPI name: anomaly_type
  anomalyType: string;
  classification: string;
  // OpenAPI name: classification_confidence
  classificationConfidence: number;
  // OpenAPI name: collection_subtype
  collectionSubtype?: any;
  // OpenAPI name: true_anomaly_subtype
  trueAnomalySubtype?: any;
  evidence: Record<string, any>;
  // OpenAPI name: original_time
  originalTime?: any;
}

/** 确认异常请求

将异常标记为真实异常。 */
export interface AnomalyConfirmRequest {
  /** 异常记录ID */
  // OpenAPI name: anomaly_id
  anomalyId: number;
  /** 确认人ID */
  // OpenAPI name: confirmed_by
  confirmedBy?: any;
  /** 确认备注 */
  // OpenAPI name: confirm_note
  confirmNote?: any;
}

/** 异常数据响应模型

对应 sc_anomaly_data 表的完整字段，
包含异常信息、分类、确认标注等。 */
export interface AnomalyDataResponse {
  id: number;
  // OpenAPI name: sensor_id
  sensorId: string;
  // OpenAPI name: anomaly_value
  anomalyValue?: any;
  // OpenAPI name: anomaly_type
  anomalyType?: any;
  // OpenAPI name: anomaly_score
  anomalyScore?: any;
  // OpenAPI name: original_time
  originalTime?: any;
  details?: any;
  classification?: any;
  // OpenAPI name: classification_confidence
  classificationConfidence?: any;
  // OpenAPI name: collection_subtype
  collectionSubtype?: any;
  // OpenAPI name: true_anomaly_subtype
  trueAnomalySubtype?: any;
  // OpenAPI name: classification_evidence
  classificationEvidence?: any;
  // OpenAPI name: is_confirmed
  isConfirmed?: boolean;
  // OpenAPI name: is_false_positive
  isFalsePositive?: boolean;
  // OpenAPI name: confirmed_by
  confirmedBy?: any;
  // OpenAPI name: confirmed_time
  confirmedTime?: any;
  // OpenAPI name: confirm_note
  confirmNote?: any;
  // OpenAPI name: tenant_id
  tenantId?: any;
  // OpenAPI name: create_time
  createTime?: any;
  // OpenAPI name: update_time
  updateTime?: any;
}

/** 标注误报请求

将异常标记为误报。 */
export interface AnomalyFalsePositiveRequest {
  /** 异常记录ID */
  // OpenAPI name: anomaly_id
  anomalyId: number;
  /** 标注人ID */
  // OpenAPI name: confirmed_by
  confirmedBy?: any;
  /** 标注备注 */
  // OpenAPI name: confirm_note
  confirmNote?: any;
}

/** 异常联动结果 */
export interface AnomalyLinkResultSchema {
  // OpenAPI name: sensor_id
  sensorId: string;
  // OpenAPI name: total_anomalies
  totalAnomalies: number;
  // OpenAPI name: true_anomalies
  trueAnomalies: number;
  // OpenAPI name: collection_anomalies
  collectionAnomalies: number;
  // OpenAPI name: uncertain_anomalies
  uncertainAnomalies: number;
  // OpenAPI name: mixed_anomalies
  mixedAnomalies: number;
  // OpenAPI name: classified_anomalies
  classifiedAnomalies: AnomalyClassificationSchema[];
}

/** 异常列表响应 */
export interface AnomalyListResponse {
  /** 总记录数 */
  total: number;
  /** 异常数据列表 */
  items: AnomalyDataResponse[];
}

/** 异常查询请求

支持按 sensor_id、时间范围、类型、确认状态等多维度查询。 */
export interface AnomalyQueryRequest {
  /** 传感器/螺栓ID */
  // OpenAPI name: sensor_id
  sensorId?: any;
  /** 开始时间 */
  // OpenAPI name: start_time
  startTime?: any;
  /** 结束时间 */
  // OpenAPI name: end_time
  endTime?: any;
  /** 异常类型 */
  // OpenAPI name: anomaly_type
  anomalyType?: any;
  /** 异常分类 */
  classification?: any;
  /** 是否已确认 */
  // OpenAPI name: is_confirmed
  isConfirmed?: any;
  /** 是否为误报 */
  // OpenAPI name: is_false_positive
  isFalsePositive?: any;
  /** 最低异常评分 */
  // OpenAPI name: min_score
  minScore?: any;
  /** 最高异常评分 */
  // OpenAPI name: max_score
  maxScore?: any;
  /** 返回数量限制 */
  limit?: number;
  /** 偏移量 */
  offset?: number;
  /** 排序字段 */
  // OpenAPI name: sort_by
  sortBy?: string;
  /** 排序方向 asc/desc */
  // OpenAPI name: sort_order
  sortOrder?: string;
}

/** 异常统计响应 */
export interface AnomalyStatisticsResponse {
  /** 异常总数 */
  // OpenAPI name: total_count
  totalCount?: number;
  /** 已确认数 */
  // OpenAPI name: confirmed_count
  confirmedCount?: number;
  /** 未确认数 */
  // OpenAPI name: unconfirmed_count
  unconfirmedCount?: number;
  /** 误报数 */
  // OpenAPI name: false_positive_count
  falsePositiveCount?: number;
  /** 真实异常数 */
  // OpenAPI name: true_anomaly_count
  trueAnomalyCount?: number;
  /** 误报率 */
  // OpenAPI name: false_positive_rate
  falsePositiveRate?: number;
  // OpenAPI name: type_distribution
  typeDistribution?: any;
  // OpenAPI name: classification_distribution
  classificationDistribution?: any;
  // OpenAPI name: time_range
  timeRange?: any;
}

/** 异常对预警等级影响分析响应 */
export interface AnomalyWarningImpactResponse {
  // OpenAPI name: sensor_id
  sensorId: string;
  /** 是否需要提升预警等级 */
  // OpenAPI name: should_upgrade
  shouldUpgrade?: boolean;
  /** 原始预警等级 */
  // OpenAPI name: original_level
  originalLevel: number;
  /** 提升后的预警等级 */
  // OpenAPI name: upgraded_level
  upgradedLevel: number;
  /** 时间窗口内的异常数 */
  // OpenAPI name: anomaly_count
  anomalyCount?: number;
  /** 异常数阈值 */
  threshold?: number;
  /** 时间窗口（分钟） */
  // OpenAPI name: window_minutes
  windowMinutes?: number;
}

/** 清理过期审计记录响应 */
export interface AuditCleanupResponse {
  // OpenAPI name: cleaned_count
  cleanedCount: number;
  message: string;
}

/** 审计导出请求 */
export interface AuditExportRequest {
  /** 起始时间 */
  // OpenAPI name: start_time
  startTime: Date | string;
  /** 结束时间 */
  // OpenAPI name: end_time
  endTime: Date | string;
  /** 节点类型过滤 bolt/flange */
  // OpenAPI name: node_type
  nodeType?: any;
  /** 节点ID过滤 */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 导出格式 csv/pdf */
  format?: string;
}

/** 审计记录列表响应 */
export interface AuditListResponse {
  total: number;
  items: AuditRecordResponse[];
}

/** 审计记录响应 */
export interface AuditRecordResponse {
  id: number;
  // OpenAPI name: prediction_id
  predictionId: string;
  // OpenAPI name: node_type
  nodeType: string;
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: input_hash
  inputHash?: any;
  // OpenAPI name: model_version
  modelVersion?: any;
  // OpenAPI name: model_type
  modelType?: any;
  // OpenAPI name: feature_summary
  featureSummary?: any;
  // OpenAPI name: intermediate_results
  intermediateResults?: any;
  // OpenAPI name: final_decision
  finalDecision?: any;
  // OpenAPI name: strategy_version
  strategyVersion?: any;
  // OpenAPI name: strategy_type
  strategyType?: any;
  explainability?: any;
  // OpenAPI name: retention_years
  retentionYears?: number;
  // OpenAPI name: expire_time
  expireTime?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
}

/** 更新审计记录保留年限请求 */
export interface AuditRetentionUpdateRequest {
  /** 保留年限 */
  // OpenAPI name: retention_years
  retentionYears: number;
}

/** 批量生成报告请求 */
export interface BatchReportGenerateRequest {
  /** 节点类型：bolt/flange */
  // OpenAPI name: node_type
  nodeType: string;
  /** 节点ID列表 */
  // OpenAPI name: node_ids
  nodeIds: string[];
  /** 报告类型：weekly/monthly */
  // OpenAPI name: report_type
  reportType?: string;
}

/** 批量报告响应 */
export interface BatchReportResponse {
  /** 总数 */
  total?: number;
  /** 成功数量 */
  success?: number;
  /** 失败数量 */
  failed?: number;
  /** 成功的报告列表 */
  results?: PeriodicReportResponse[];
  /** 失败的节点及错误信息 */
  errors?: Record<string, string>;
}

/** 螺栓集成学习预测调试请求 */
export interface BoltEnsemblePredictionRequest {
  /** 螺栓唯一标识 */
  // OpenAPI name: bolt_id
  boltId: string;
  /** 预紧力时序数据 */
  data: number[];
  /** 模型版本号 */
  version?: any;
  /** 投票策略: hard / soft / weighted */
  method?: any;
  /** 自定义权重 */
  weights?: any;
}

/** 螺栓集成学习预测调试响应

Attributes:
    bolt_id: 螺栓ID
    prediction_source: 预测来源
    ensemble_method: 集成方法: hard / soft / weighted
    final_status: 最终状态
    final_status_code: 最终状态代码
    final_confidence: 最终置信度
    final_probs: 最终概率分布
    weights: 各预测器权重
    individual_results: 各子模型分项结果
    individual_probs: 各子模型概率分布
    model_version: 模型版本
    duration_ms: 预测耗时(ms)
    ema_accuracy: EMA准确率
    performance_history: 历史表现记录 */
export interface BoltEnsemblePredictionResponse {
  // OpenAPI name: bolt_id
  boltId: string;
  // OpenAPI name: prediction_source
  predictionSource: string;
  // OpenAPI name: ensemble_method
  ensembleMethod: string;
  // OpenAPI name: final_status
  finalStatus: string;
  // OpenAPI name: final_status_code
  finalStatusCode: number;
  // OpenAPI name: final_confidence
  finalConfidence: number;
  // OpenAPI name: final_probs
  finalProbs?: any;
  weights: Record<string, number>;
  // OpenAPI name: individual_results
  individualResults: Record<string, any>[];
  // OpenAPI name: individual_probs
  individualProbs: Record<string, any>;
  // OpenAPI name: model_version
  modelVersion: string;
  // OpenAPI name: duration_ms
  durationMs: number;
  // OpenAPI name: ema_accuracy
  emaAccuracy: Record<string, number>;
  // OpenAPI name: performance_history
  performanceHistory: Record<string, number[]>;
}

/** 螺栓健康度指数 */
export interface BoltHealthIndexSchema {
  /** 综合健康度指数 0-100 */
  // OpenAPI name: hi_score
  hiScore: number;
  /** 健康等级 excellent/good/fair/poor/critical */
  // OpenAPI name: hi_level
  hiLevel: string;
  /** 各因子得分详情 */
  factors: HealthIndexFactorSchema[];
  /** 预紧力稳定性得分 */
  // OpenAPI name: preload_stability_score
  preloadStabilityScore: number;
  /** 预警频率得分 */
  // OpenAPI name: alert_frequency_score
  alertFrequencyScore: number;
  /** 故障历史得分 */
  // OpenAPI name: fault_history_score
  faultHistoryScore: number;
  /** 环境应力得分 */
  // OpenAPI name: environmental_stress_score
  environmentalStressScore: number;
  /** 使用年限得分 */
  // OpenAPI name: service_age_score
  serviceAgeScore: number;
  /** 健康趋势 improving/stable/declining */
  trend?: any;
  /** 趋势变化率 */
  // OpenAPI name: trend_rate
  trendRate?: any;
  // OpenAPI name: calculate_time
  calculateTime: Date | string;
  // OpenAPI name: bolt_id
  boltId: string;
  // OpenAPI name: bolt_name
  boltName?: any;
  // OpenAPI name: current_preload
  currentPreload?: any;
  // OpenAPI name: nominal_preload
  nominalPreload?: any;
  // OpenAPI name: preload_deviation
  preloadDeviation?: any;
  // OpenAPI name: last_maintenance_date
  lastMaintenanceDate?: any;
}

/** 螺栓多变量耦合预测请求

请求支持两种数据格式：
1. channels 分开提供（各通道时间戳可以不同，服务端会自动对齐插值）
2. aligned_data 统一提供（各通道已在同一时间网格上，仅需缺失值插值）

Attributes:
    bolt_id: 螺栓唯一标识
    channels: 分通道提供的时序数据 {通道名: [[时间, 值], ...]}
    aligned_data: 已对齐的多通道数据 [[时间, 通道1, 通道2, ...], ...]
    aligned_channel_names: 使用 aligned_data 时必须提供，对应列的通道名称（不含时间列）
    timestamps: 可选，统一目标时间网格
    apply_temp_compensation: 是否执行温度耦合补偿（默认 True）
    enable_degradation: 缺失严重时是否降级为单变量预测（默认 True）
    version: 模型版本号（可选） */
export interface BoltMultivariatePredictionRequest {
  /** 螺栓唯一标识 */
  // OpenAPI name: bolt_id
  boltId: string;
  /** 分通道数据 {channel_name: [[timestamp, value], ...]}，时间戳可不对齐 */
  channels?: any;
  /** 已对齐的多通道数据（首列为时间戳），形状(N, 1 + C) */
  // OpenAPI name: aligned_data
  alignedData?: any;
  /** aligned_data 除去时间列后的各通道名，顺序与列对应 */
  // OpenAPI name: aligned_channel_names
  alignedChannelNames?: any;
  /** 目标时间戳列表（可选），不填则自动推导统一时间网格 */
  timestamps?: any;
  /** 是否执行温度耦合补偿 */
  // OpenAPI name: apply_temp_compensation
  applyTempCompensation?: boolean;
  /** 缺失严重时是否自动降级为单变量预测 */
  // OpenAPI name: enable_degradation
  enableDegradation?: boolean;
  /** 模型版本号 */
  version?: any;
}

/** 螺栓多变量耦合预测响应

在标准螺栓预测响应基础上，新增：
- data_quality: 数据质量评估（含降级信息）
- channels_info: 实际使用的通道元数据
- temp_compensation: 温度耦合补偿详情
- feature_importance: 各通道特征重要性（可解释性） */
export interface BoltMultivariatePredictionResponse {
  // OpenAPI name: bolt_id
  boltId: string;
  status: string;
  // OpenAPI name: status_code
  statusCode: number;
  confidence: number;
  // OpenAPI name: risk_score
  riskScore: number;
  // OpenAPI name: risk_level
  riskLevel: string;
  diagnosis: string;
  recommendations: string[];
  // OpenAPI name: prediction_time
  predictionTime: Date | string;
  /** 模型版本号 */
  // OpenAPI name: model_version
  modelVersion?: any;
  /** 实际输入模型的通道数 */
  // OpenAPI name: input_dim_actual
  inputDimActual: number;
  /** 实际使用的通道元数据 */
  // OpenAPI name: channels_info
  channelsInfo?: MultivariateChannelSchema[];
  /** 数据质量评估与降级信息 */
  // OpenAPI name: data_quality
  dataQuality: DataQualityInfo;
  /** 温度耦合补偿详情 */
  // OpenAPI name: temp_compensation
  tempCompensation?: any;
  /** 各通道特征重要性（可解释性） */
  // OpenAPI name: feature_importance
  featureImportance?: any;
  /** 实际送入模型的序列长度 */
  // OpenAPI name: sequence_length_used
  sequenceLengthUsed?: number;
  /** 预测来源: multivariate_lstm / degraded_univariate / fallback */
  // OpenAPI name: prediction_source
  predictionSource?: string;
  /** 故障类型细分详情 */
  // OpenAPI name: fault_detail
  faultDetail?: any;
  /** Shadow模式版本号 */
  // OpenAPI name: shadow_version
  shadowVersion?: any;
  /** Shadow模式预测结果 */
  // OpenAPI name: shadow_result
  shadowResult?: any;
}

/** 螺栓预测请求

Attributes:
    螺栓id: 螺栓唯一标识
    data: 预紧力时序数据 [[时间, 预紧力], ...] */
export interface BoltPredictionRequest {
  /** 螺栓唯一标识 */
  // OpenAPI name: bolt_id
  boltId: string;
  /** 预紧力时序数据，每个元素为[时间字符串, 预紧力值] */
  data: any[][];
}

/** 螺栓预测响应

Attributes:
    bolt_id: 螺栓ID
    status: 预测状态
    status_code: 状态代码
    confidence: 置信度
    risk_score: 风险评分
    risk_level: 风险等级
    diagnosis: 诊断结论
    recommendations: 推荐措施
    prediction_time: 预测时间
    model_version: 模型版本号
    shadow_version: Shadow模式版本号（如有）
    shadow_result: Shadow模式预测结果（如有） */
export interface BoltPredictionResponse {
  // OpenAPI name: bolt_id
  boltId: string;
  status: string;
  // OpenAPI name: status_code
  statusCode: number;
  confidence: number;
  // OpenAPI name: risk_score
  riskScore: number;
  // OpenAPI name: risk_level
  riskLevel: string;
  diagnosis: string;
  recommendations: string[];
  // OpenAPI name: prediction_time
  predictionTime: Date | string;
  /** 模型版本号 */
  // OpenAPI name: model_version
  modelVersion?: any;
  /** Shadow模式版本号 */
  // OpenAPI name: shadow_version
  shadowVersion?: any;
  /** Shadow模式预测结果 */
  // OpenAPI name: shadow_result
  shadowResult?: any;
  /** 故障类型细分详情 */
  // OpenAPI name: fault_detail
  faultDetail?: any;
  /** 预测来源: lstm / ensemble / rule */
  // OpenAPI name: prediction_source
  predictionSource?: any;
  /** Ensemble集成学习详情（触发时返回） */
  ensemble?: any;
}

/** 碳排模型系数配置响应 */
export interface CarbonModelConfigResponse {
  degradation: DegradationParamsSchema;
  leakage: LeakageParamsSchema;
  /** 能耗与碳排模型参数 */
  // OpenAPI name: energy_carbon
  energyCarbon: EnergyCarbonParamsSchema;
}

/** 碳排模型系数配置更新请求 */
export interface CarbonModelConfigUpdateRequest {
  /** 预紧力劣化模型参数（可选更新） */
  degradation?: any;
  /** 泄漏率估算模型参数（可选更新） */
  leakage?: any;
  /** 能耗与碳排模型参数（可选更新） */
  // OpenAPI name: energy_carbon
  energyCarbon?: any;
  /** 操作人ID */
  // OpenAPI name: operator_id
  operatorId?: any;
  /** 操作人姓名 */
  // OpenAPI name: operator_name
  operatorName?: any;
  /** 变更说明 */
  description?: any;
}

/** 装置级月度碳排风险排行请求 */
export interface CarbonMonthlyRankingRequest {
  /** 节点数据列表，每项包含: node_id, node_type(可选), node_name(可选), hi_score, hi_level, preload_history, timestamps(可选), service_age_months(可选), avg_temperature(可选), seal_age_years(可选), operating_pressure_mpa(可选), energy_source(可选) */
  nodes: Record<string, any>[];
  /** 返回前N名，None表示全部 */
  // OpenAPI name: top_n
  topN?: any;
}

/** 装置级月度碳排风险排行响应 */
export interface CarbonMonthlyRankingResponse {
  /** 报告月份 YYYY-MM */
  // OpenAPI name: report_month
  reportMonth: string;
  /** 分析节点总数 */
  // OpenAPI name: total_nodes
  totalNodes: number;
  /** 月度碳排增量合计 (kgCO₂e) */
  // OpenAPI name: total_monthly_carbon_increment_kg
  totalMonthlyCarbonIncrementKg: number;
  /** 月度泄漏量合计 (m³) */
  // OpenAPI name: total_monthly_leakage_volume_m3
  totalMonthlyLeakageVolumeM3: number;
  /** 风险等级分布 {critical, high, medium, low} */
  // OpenAPI name: risk_distribution
  riskDistribution: Record<string, number>;
  /** 按优先级排序的碳排风险列表 */
  // OpenAPI name: ranked_items
  rankedItems: CarbonRiskItemSchema[];
  /** 生成时间 */
  // OpenAPI name: generated_at
  generatedAt: Date | string;
}

/** 碳排风险排行单项 */
export interface CarbonRiskItemSchema {
  /** 排名 */
  rank?: any;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 节点类型 bolt/flange/device */
  // OpenAPI name: node_type
  nodeType: string;
  /** 节点名称 */
  // OpenAPI name: node_name
  nodeName: string;
  /** 健康度指数 HI 0-100 */
  // OpenAPI name: hi_score
  hiScore: number;
  /** HI等级 excellent/good/fair/poor/critical */
  // OpenAPI name: hi_level
  hiLevel: string;
  /** 碳排风险评分 0-100 */
  // OpenAPI name: carbon_risk_score
  carbonRiskScore: number;
  /** 碳排风险等级 low/medium/high/critical */
  // OpenAPI name: carbon_risk_level
  carbonRiskLevel: string;
  /** 月度估算泄漏量 (m³) */
  // OpenAPI name: monthly_leakage_volume_m3
  monthlyLeakageVolumeM3: number;
  /** 月度碳排增量 (kgCO₂e) */
  // OpenAPI name: monthly_carbon_increment_kg
  monthlyCarbonIncrementKg: number;
  /** 综合优先级评分 */
  // OpenAPI name: priority_score
  priorityScore: number;
  /** 趋势 stable/gradual_decline/accelerating_decline/recovering */
  trend: string;
  /** 推荐措施 */
  recommendations?: string[];
}

/** 案例审核请求 */
export interface CaseReviewRequest {
  /** 审核结果 approved/rejected/revision_required */
  // OpenAPI name: review_result
  reviewResult: string;
  /** 审核意见 */
  // OpenAPI name: review_comment
  reviewComment?: any;
  /** 审核人ID */
  // OpenAPI name: reviewer_id
  reviewerId?: any;
  /** 审核人姓名 */
  // OpenAPI name: reviewer_name
  reviewerName?: any;
  /** 审核级别 1-3 */
  // OpenAPI name: review_level
  reviewLevel?: number;
}

/** 案例相似度检索请求 */
export interface CaseSimilaritySearchRequest {
  /** 节点类型 bolt/flange */
  // OpenAPI name: node_type
  nodeType?: any;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 故障类型 */
  // OpenAPI name: fault_type
  faultType?: any;
  /** 故障级别 */
  // OpenAPI name: fault_level
  faultLevel?: any;
  /** 传感器时序数据 */
  // OpenAPI name: sensor_data
  sensorData?: any;
  /** 传感器特征 */
  // OpenAPI name: sensor_features
  sensorFeatures?: any;
  /** 特征向量 */
  // OpenAPI name: feature_vector
  featureVector?: any;
  /** 标签过滤 */
  tags?: any;
  /** 返回Top-K相似案例 */
  // OpenAPI name: top_k
  topK?: number;
  /** 最低相似度阈值 */
  // OpenAPI name: min_similarity
  minSimilarity?: number;
  /** 只返回已审核通过的案例 */
  // OpenAPI name: only_approved
  onlyApproved?: boolean;
  /** 租户ID过滤 */
  // OpenAPI name: tenant_id
  tenantId?: any;
}

/** 因果图边 */
export interface CausalGraphEdgeSchema {
  source: string;
  target: string;
  // OpenAPI name: source_idx
  sourceIdx: number;
  // OpenAPI name: target_idx
  targetIdx: number;
  weight: number;
  correlation: number;
  // OpenAPI name: p_value
  pValue?: any;
  // OpenAPI name: f_stat
  fStat?: any;
  lag?: any;
  type: string;
}

/** 因果图节点 */
export interface CausalGraphNodeSchema {
  id: string;
  index: number;
  // OpenAPI name: in_degree
  inDegree: number;
  // OpenAPI name: out_degree
  outDegree: number;
  // OpenAPI name: total_degree
  totalDegree: number;
  centrality: number;
}

/** 因果图 */
export interface CausalGraphSchema {
  nodes: CausalGraphNodeSchema[];
  edges: CausalGraphEdgeSchema[];
  // OpenAPI name: adjacency_matrix
  adjacencyMatrix: number[][];
  // OpenAPI name: edge_weights
  edgeWeights: number[][];
  // OpenAPI name: bolt_ids
  boltIds: string[];
}

/** 类别不平衡处理配置 */
export interface ClassImbalanceConfig {
  /** 不平衡处理策略: weighted_loss/oversampling/none */
  strategy?: string;
  /** 过采样倍率 */
  // OpenAPI name: oversampling_ratio
  oversamplingRatio?: any;
}

/** 创建CMMS配置请求 */
export interface CmmsConfigCreate {
  /** 系统名称 */
  // OpenAPI name: system_name
  systemName: string;
  /** 系统类型 maximo/sap_eam/infor/eam/other */
  // OpenAPI name: system_type
  systemType?: any;
  /** 系统基础URL */
  // OpenAPI name: base_url
  baseUrl?: any;
  /** 认证类型 basic/api_key/oauth2/token */
  // OpenAPI name: auth_type
  authType?: any;
  /** 认证配置 */
  // OpenAPI name: auth_config
  authConfig?: any;
  /** 是否同步工单 */
  // OpenAPI name: work_order_sync
  workOrderSync?: any;
  /** 工单Webhook URL */
  // OpenAPI name: work_order_webhook_url
  workOrderWebhookUrl?: any;
  /** 工单推送URL */
  // OpenAPI name: work_order_push_url
  workOrderPushUrl?: any;
  /** 状态映射 */
  // OpenAPI name: status_mapping
  statusMapping?: any;
  /** 优先级映射 */
  // OpenAPI name: priority_mapping
  priorityMapping?: any;
  /** 字段映射 */
  // OpenAPI name: field_mapping
  fieldMapping?: any;
  /** 是否启用 */
  enabled?: any;
  /** 同步方向 push/pull/bidirectional */
  // OpenAPI name: sync_direction
  syncDirection?: any;
  /** 同步间隔 分钟 */
  // OpenAPI name: sync_interval
  syncInterval?: any;
  /** 租户ID */
  // OpenAPI name: tenant_id
  tenantId?: any;
  /** 扩展信息 */
  // OpenAPI name: extra_info
  extraInfo?: any;
}

/** CMMS配置列表响应 */
export interface CmmsConfigListResponse {
  total: number;
  items: CmmsConfigResponse[];
}

/** CMMS配置响应 */
export interface CmmsConfigResponse {
  id: number;
  // OpenAPI name: system_name
  systemName: string;
  // OpenAPI name: system_type
  systemType?: any;
  // OpenAPI name: base_url
  baseUrl?: any;
  // OpenAPI name: auth_type
  authType?: any;
  // OpenAPI name: work_order_sync
  workOrderSync?: any;
  // OpenAPI name: work_order_webhook_url
  workOrderWebhookUrl?: any;
  // OpenAPI name: work_order_push_url
  workOrderPushUrl?: any;
  // OpenAPI name: status_mapping
  statusMapping?: any;
  // OpenAPI name: priority_mapping
  priorityMapping?: any;
  // OpenAPI name: field_mapping
  fieldMapping?: any;
  enabled?: any;
  // OpenAPI name: sync_direction
  syncDirection?: any;
  // OpenAPI name: last_sync_time
  lastSyncTime?: any;
  // OpenAPI name: sync_interval
  syncInterval?: any;
  // OpenAPI name: tenant_id
  tenantId?: any;
  // OpenAPI name: extra_info
  extraInfo?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** 更新CMMS配置请求 */
export interface CmmsConfigUpdate {
  // OpenAPI name: system_name
  systemName?: any;
  // OpenAPI name: system_type
  systemType?: any;
  // OpenAPI name: base_url
  baseUrl?: any;
  // OpenAPI name: auth_type
  authType?: any;
  // OpenAPI name: auth_config
  authConfig?: any;
  // OpenAPI name: work_order_sync
  workOrderSync?: any;
  // OpenAPI name: work_order_webhook_url
  workOrderWebhookUrl?: any;
  // OpenAPI name: work_order_push_url
  workOrderPushUrl?: any;
  // OpenAPI name: status_mapping
  statusMapping?: any;
  // OpenAPI name: priority_mapping
  priorityMapping?: any;
  // OpenAPI name: field_mapping
  fieldMapping?: any;
  enabled?: any;
  // OpenAPI name: sync_direction
  syncDirection?: any;
  // OpenAPI name: sync_interval
  syncInterval?: any;
  // OpenAPI name: extra_info
  extraInfo?: any;
}

/** CMMS同步日志列表响应 */
export interface CmmsSyncLogListResponse {
  total: number;
  items: CmmsSyncLogResponse[];
}

/** CMMS同步日志响应 */
export interface CmmsSyncLogResponse {
  id: number;
  // OpenAPI name: config_id
  configId?: any;
  // OpenAPI name: sync_type
  syncType?: any;
  // OpenAPI name: sync_direction
  syncDirection?: any;
  // OpenAPI name: work_order_id
  workOrderId?: any;
  // OpenAPI name: external_id
  externalId?: any;
  status?: any;
  // OpenAPI name: error_message
  errorMessage?: any;
  // OpenAPI name: retry_count
  retryCount?: any;
  // OpenAPI name: sync_time
  syncTime?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
}

/** CMMS同步请求 */
export interface CmmsSyncRequest {
  /** CMMS配置ID */
  // OpenAPI name: config_id
  configId: number;
  /** 同步类型 */
  // OpenAPI name: sync_type
  syncType?: string;
  /** 工单ID */
  // OpenAPI name: work_order_id
  workOrderId?: any;
}

/** CMMS同步响应 */
export interface CmmsSyncResponse {
  success: boolean;
  // OpenAPI name: sync_log_id
  syncLogId?: any;
  // OpenAPI name: external_id
  externalId?: any;
  message?: any;
}

/** CMMS Webhook响应 */
export interface CmmsWebhookResponse {
  success: boolean;
  message: string;
  // OpenAPI name: processed_count
  processedCount?: any;
}

/** 置信度调整请求 */
export interface ConfidenceAdjustmentRequest {
  /** 传感器ID */
  // OpenAPI name: sensor_id
  sensorId: string;
  /** 原始置信度 */
  // OpenAPI name: original_confidence
  originalConfidence: number;
  /** 时序数据 */
  data: any[][];
}

/** 置信度调整响应 */
export interface ConfidenceAdjustmentResponse {
  // OpenAPI name: sensor_id
  sensorId: string;
  // OpenAPI name: original_confidence
  originalConfidence: number;
  // OpenAPI name: adjusted_confidence
  adjustedConfidence: number;
  // OpenAPI name: quality_score
  qualityScore: number;
  // OpenAPI name: quality_level
  qualityLevel: string;
  // OpenAPI name: adjustment_factor
  adjustmentFactor: number;
  reasons: string[];
}

/** 配置中心整体响应 */
export interface ConfigCenterResponse {
  // OpenAPI name: warning_strategy
  warningStrategy: WarningStrategyConfigSchema;
  thresholds: ThresholdConfigSchema;
  // OpenAPI name: scheduled_jobs
  scheduledJobs: ScheduledJobSchema[];
  // OpenAPI name: updated_at
  updatedAt: Date | string;
}

/** 每日质量报告 */
export interface DailyQualityReportSchema {
  // OpenAPI name: report_date
  reportDate: Date | string;
  // OpenAPI name: total_sensors
  totalSensors: number;
  // OpenAPI name: average_quality_score
  averageQualityScore: number;
  // OpenAPI name: quality_distribution
  qualityDistribution: Record<string, number>;
  // OpenAPI name: problem_sensors
  problemSensors: ProblemSensorRankingSchema[];
  recommendations: RepairRecommendationSchema[];
  // OpenAPI name: anomaly_statistics
  anomalyStatistics: Record<string, any>;
  // OpenAPI name: quality_trend
  qualityTrend: Record<string, any>[];
  summary: string;
  // OpenAPI name: generated_at
  generatedAt: Date | string;
}

/** 批量数据质量检查请求 */
export interface DataQualityCheckBatchRequest {
  /** 传感器数据字典 {sensor_id: [[时间, 数值], ...]} */
  // OpenAPI name: sensors_data
  sensorsData: Record<string, any[][]>;
}

/** 数据质量检查请求 */
export interface DataQualityCheckRequest {
  /** 传感器/螺栓ID */
  // OpenAPI name: sensor_id
  sensorId: string;
  /** 时序数据，每个元素为[时间字符串, 数值] */
  data: any[][];
  /** 是否包含异常分类 */
  // OpenAPI name: include_anomaly_classification
  includeAnomalyClassification?: boolean;
}

/** 获取质量历史请求 */
export interface DataQualityHistoryRequest {
  /** 传感器ID */
  // OpenAPI name: sensor_id
  sensorId: string;
  /** 开始时间 */
  // OpenAPI name: start_time
  startTime?: any;
  /** 结束时间 */
  // OpenAPI name: end_time
  endTime?: any;
  /** 返回数量限制 */
  limit?: number;
}

/** 数据质量评估结果

Attributes:
    level: 数据质量等级 full=完整, partial=部分缺失, degraded=降级单变量
    complete_ratio: 完整数据占比 (0-1)
    missing_channels: 被丢弃/降级时缺失的通道列表
    interpolation_count: 插值填充的总数据点数
    interpolation_flags: 可选，每个时间点每通道的插值标记（1=插值 0=原始）
    degradation_applied: 是否触发了降级策略 */
export interface DataQualityInfo {
  /** 数据质量等级: full / partial / degraded */
  level?: string;
  /** 完整数据占比 0-1 */
  // OpenAPI name: complete_ratio
  completeRatio?: number;
  /** 缺失或降级丢弃的通道列表 */
  // OpenAPI name: missing_channels
  missingChannels?: string[];
  /** 插值填充的总点数 */
  // OpenAPI name: interpolation_count
  interpolationCount?: number;
  /** 是否因缺失严重触发了单变量降级 */
  // OpenAPI name: degradation_applied
  degradationApplied?: boolean;
  /** 实际参与模型计算的通道 */
  // OpenAPI name: actual_channels_used
  actualChannelsUsed?: string[];
}

/** 预紧力劣化模型参数 */
export interface DegradationParamsSchema {
  /** 额定预紧力 (kN) */
  // OpenAPI name: nominal_preload
  nominalPreload?: number;
  /** 最小有效压紧比阈值 */
  // OpenAPI name: min_effective_preload_ratio
  minEffectivePreloadRatio?: number;
  /** 自然松弛月速率 */
  // OpenAPI name: relaxation_rate_per_month
  relaxationRatePerMonth?: number;
  /** 高温加速因子 (每°C高于40) */
  // OpenAPI name: temperature_acceleration_factor
  temperatureAccelerationFactor?: number;
  /** 振动加速因子 */
  // OpenAPI name: vibration_acceleration_factor
  vibrationAccelerationFactor?: number;
  /** 压力循环加速因子 */
  // OpenAPI name: cycle_acceleration_factor
  cycleAccelerationFactor?: number;
}

/** 单次诊断报告生成请求 */
export interface DiagnosisReportRequest {
  /** 状态：正常/关注级预警/检查级预警/紧急级预警/故障 */
  status: string;
  /** 风险评分(0-10)，分数越低风险越高 */
  // OpenAPI name: risk_score
  riskScore: number;
  /** 节点类型：bolt/flange */
  // OpenAPI name: node_type
  nodeType?: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 故障类型：loosening/preload_decrease/severe_anomaly/failure */
  // OpenAPI name: fault_type
  faultType?: any;
  /** 趋势：stable/decreasing/increasing/fluctuating */
  trend?: any;
  /** 近期预紧力数值列表 */
  // OpenAPI name: recent_values
  recentValues?: any;
  /** 历史同类事件数 */
  // OpenAPI name: historical_incidents
  historicalIncidents?: any;
}

/** 诊断报告响应 */
export interface DiagnosisReportResponse {
  /** 诊断摘要（200字内） */
  // OpenAPI name: diagnosis_summary
  diagnosisSummary: string;
  /** 推荐处置措施（分步骤） */
  // OpenAPI name: recommended_actions
  recommendedActions: string[];
  /** 紧急程度：low/medium/high/critical */
  // OpenAPI name: urgency_level
  urgencyLevel: string;
  /** 使用的模型 */
  model: string;
  /** Token用量 */
  // OpenAPI name: tokens_used
  tokensUsed?: number;
  /** 生成延迟（毫秒） */
  // OpenAPI name: latency_ms
  latencyMs?: number;
  /** 是否使用降级模板 */
  // OpenAPI name: is_fallback
  isFallback?: boolean;
}

/** 创建处置记录请求 */
export interface DisposalRecordCreate {
  /** 关联工单ID */
  // OpenAPI name: work_order_id
  workOrderId: number;
  /** 处置类型 torque_adjustment/replacement/inspection/other */
  // OpenAPI name: disposal_type
  disposalType: string;
  /** 处置内容描述 */
  // OpenAPI name: disposal_content
  disposalContent: string;
  /** 处置时间 */
  // OpenAPI name: disposal_time
  disposalTime?: any;
  /** 操作人ID */
  // OpenAPI name: operator_id
  operatorId?: any;
  /** 操作人姓名 */
  // OpenAPI name: operator_name
  operatorName?: any;
  /** 处置前值 */
  // OpenAPI name: before_value
  beforeValue?: any;
  /** 处置后值 */
  // OpenAPI name: after_value
  afterValue?: any;
  /** 使用材料列表 */
  // OpenAPI name: materials_used
  materialsUsed?: any;
  /** 现场照片URL列表 */
  photos?: any;
  /** 备注 */
  notes?: any;
  /** 扩展信息 */
  // OpenAPI name: extra_info
  extraInfo?: any;
}

/** 处置记录列表响应 */
export interface DisposalRecordListResponse {
  total: number;
  items: DisposalRecordResponse[];
}

/** 处置记录响应 */
export interface DisposalRecordResponse {
  id: number;
  // OpenAPI name: work_order_id
  workOrderId: number;
  // OpenAPI name: disposal_type
  disposalType?: any;
  // OpenAPI name: disposal_content
  disposalContent?: any;
  // OpenAPI name: disposal_time
  disposalTime?: any;
  // OpenAPI name: operator_id
  operatorId?: any;
  // OpenAPI name: operator_name
  operatorName?: any;
  // OpenAPI name: before_value
  beforeValue?: any;
  // OpenAPI name: after_value
  afterValue?: any;
  // OpenAPI name: materials_used
  materialsUsed?: any;
  photos?: any;
  notes?: any;
  // OpenAPI name: extra_info
  extraInfo?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
}

/** 更新处置记录请求 */
export interface DisposalRecordUpdate {
  // OpenAPI name: disposal_type
  disposalType?: any;
  // OpenAPI name: disposal_content
  disposalContent?: any;
  // OpenAPI name: disposal_time
  disposalTime?: any;
  // OpenAPI name: operator_id
  operatorId?: any;
  // OpenAPI name: operator_name
  operatorName?: any;
  // OpenAPI name: before_value
  beforeValue?: any;
  // OpenAPI name: after_value
  afterValue?: any;
  // OpenAPI name: materials_used
  materialsUsed?: any;
  photos?: any;
  notes?: any;
  // OpenAPI name: extra_info
  extraInfo?: any;
}

/** ESG报表片段导出请求 */
export interface EsgReportExportRequest {
  /** 节点数据列表，格式同 CarbonMonthlyRankingRequest */
  nodes: Record<string, any>[];
  /** 导出格式 json/csv/html */
  format?: string;
  /** 是否包含方法学说明 */
  // OpenAPI name: include_methodology
  includeMethodology?: boolean;
  /** 返回前N名高风险装置 */
  // OpenAPI name: top_n
  topN?: any;
}

/** ESG报表片段响应 */
export interface EsgReportFragmentResponse {
  /** 报告期 */
  // OpenAPI name: report_period
  reportPeriod: string;
  /** 生成时间 */
  // OpenAPI name: generated_at
  generatedAt: Date | string;
  /** 汇总数据 */
  summary: EsgReportSummarySchema;
  /** 高风险装置列表 */
  // OpenAPI name: top_risk_items
  topRiskItems: CarbonRiskItemSchema[];
  /** 趋势分析 */
  // OpenAPI name: trend_analysis
  trendAnalysis: EsgTrendAnalysisSchema;
  /** 建议措施 */
  recommendations: string[];
  /** 方法学说明 */
  // OpenAPI name: methodology_note
  methodologyNote?: any;
  /** CSV格式内容（format=csv时返回） */
  // OpenAPI name: csv_content
  csvContent?: any;
}

/** ESG报表汇总数据 */
export interface EsgReportSummarySchema {
  /** 报告期 */
  // OpenAPI name: reporting_period
  reportingPeriod: string;
  /** 分析装置总数 */
  // OpenAPI name: total_devices_analyzed
  totalDevicesAnalyzed: number;
  /** 月度碳排增量估算 (kgCO₂e) */
  // OpenAPI name: estimated_monthly_carbon_increment_kg
  estimatedMonthlyCarbonIncrementKg: number;
  /** 月度碳排增量估算 (吨CO₂e) */
  // OpenAPI name: estimated_monthly_carbon_increment_tons
  estimatedMonthlyCarbonIncrementTons: number;
  /** 月度泄漏量估算 (m³) */
  // OpenAPI name: estimated_monthly_leakage_m3
  estimatedMonthlyLeakageM3: number;
  /** 单装置平均月度碳排增量 (kgCO₂e) */
  // OpenAPI name: average_carbon_per_device_kg
  averageCarbonPerDeviceKg: number;
  /** 碳排风险严重度 高/中/低 */
  // OpenAPI name: carbon_risk_severity
  carbonRiskSeverity: string;
  /** Top5装置碳排贡献占比 */
  // OpenAPI name: top5_contribution_ratio
  top5ContributionRatio: number;
  /** 风险分布 */
  // OpenAPI name: risk_distribution
  riskDistribution: Record<string, number>;
}

/** ESG趋势分析 */
export interface EsgTrendAnalysisSchema {
  /** 整体趋势 deteriorating/stable/improving */
  // OpenAPI name: overall_trend
  overallTrend: string;
  /** 改善装置数 */
  // OpenAPI name: improving_count
  improvingCount: number;
  /** 稳定装置数 */
  // OpenAPI name: stable_count
  stableCount: number;
  /** 劣化装置数 */
  // OpenAPI name: declining_count
  decliningCount: number;
  /** 关键观察结论 */
  // OpenAPI name: key_observation
  keyObservation: string;
}

/** 早停配置 */
export interface EarlyStoppingConfig {
  /** 是否启用早停 */
  enabled?: boolean;
  /** 耐心轮数，连续多少轮无提升则停止 */
  patience?: number;
  /** 最小改进阈值 */
  // OpenAPI name: min_delta
  minDelta?: number;
  /** 监控模式 min=损失最小化/max=准确率最大化 */
  mode?: string;
}

/** EdgeDeviceHeartbeatRequest */
export interface EdgeDeviceHeartbeatRequest {
  // OpenAPI name: device_id
  deviceId: string;
  // OpenAPI name: model_version
  modelVersion?: any;
  // OpenAPI name: cache_size
  cacheSize?: number;
  // OpenAPI name: unsynced_count
  unsyncedCount?: number;
}

/** EdgeDeviceHeartbeatResponse */
export interface EdgeDeviceHeartbeatResponse {
  // OpenAPI name: device_id
  deviceId: string;
  // OpenAPI name: latest_model_version
  latestModelVersion?: any;
  // OpenAPI name: force_sync
  forceSync?: boolean;
  // OpenAPI name: server_time
  serverTime: string;
}

/** EdgeDeviceRegisterRequest */
export interface EdgeDeviceRegisterRequest {
  /** 边缘设备ID */
  // OpenAPI name: device_id
  deviceId: string;
  /** 设备名称 */
  // OpenAPI name: device_name
  deviceName?: any;
  /** 设备类型 */
  // OpenAPI name: device_type
  deviceType?: any;
  /** 设备位置 */
  location?: any;
  /** 设备能力 */
  capabilities?: any;
}

/** EdgeDeviceRegisterResponse */
export interface EdgeDeviceRegisterResponse {
  // OpenAPI name: device_id
  deviceId: string;
  status: string;
  message: string;
  // OpenAPI name: registered_at
  registeredAt: string;
}

/** EdgeModelExportRequest */
export interface EdgeModelExportRequest {
  /** 模型类型 bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 导出格式 onnx/torchscript */
  // OpenAPI name: export_format
  exportFormat?: string;
  /** 指定版本，None则使用最新 */
  version?: any;
}

/** EdgeModelExportResponse */
export interface EdgeModelExportResponse {
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId?: any;
  version: string;
  // OpenAPI name: export_format
  exportFormat: string;
  // OpenAPI name: package_url
  packageUrl: string;
  // OpenAPI name: file_hash
  fileHash: string;
  // OpenAPI name: file_size
  fileSize: number;
  // OpenAPI name: includes_preprocessing
  includesPreprocessing?: boolean;
  // OpenAPI name: includes_signature
  includesSignature?: boolean;
  // OpenAPI name: exported_at
  exportedAt: string;
}

/** EdgeModelLatestRequest */
export interface EdgeModelLatestRequest {
  /** 模型类型 bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 边缘设备ID */
  // OpenAPI name: edge_device_id
  edgeDeviceId?: any;
}

/** EdgeModelLatestResponse */
export interface EdgeModelLatestResponse {
  version: string;
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId?: any;
  // OpenAPI name: download_url
  downloadUrl: string;
  // OpenAPI name: file_hash
  fileHash: string;
  // OpenAPI name: file_size
  fileSize: number;
  // OpenAPI name: created_at
  createdAt: string;
  metrics?: any;
}

/** EdgePredictionUploadRequest */
export interface EdgePredictionUploadRequest {
  /** 边缘设备ID */
  // OpenAPI name: device_id
  deviceId: string;
  /** 预测结果列表 */
  predictions: Record<string, any>[];
}

/** EdgePredictionUploadResponse */
export interface EdgePredictionUploadResponse {
  // OpenAPI name: device_id
  deviceId: string;
  // OpenAPI name: received_count
  receivedCount: number;
  status: string;
  message: string;
}

/** 效果评估 */
export interface EffectEvaluationSchema {
  /** 整体评价 excellent/good/fair/poor */
  // OpenAPI name: overall_rating
  overallRating?: any;
  /** 效果评分 0-100 */
  // OpenAPI name: effectiveness_score
  effectivenessScore?: any;
  /** 故障是否解决 */
  // OpenAPI name: fault_resolved
  faultResolved?: any;
  /** 多少天内复发 */
  // OpenAPI name: recurrence_within_days
  recurrenceWithinDays?: any;
  /** 实际成本 */
  // OpenAPI name: actual_cost
  actualCost?: any;
  /** 实际耗时（分钟） */
  // OpenAPI name: actual_duration_minutes
  actualDurationMinutes?: any;
  /** 副作用/不良影响 */
  // OpenAPI name: side_effects
  sideEffects?: any;
  /** 改进指标 */
  // OpenAPI name: improvement_metrics
  improvementMetrics?: any;
  /** 备注 */
  notes?: any;
}

/** 当前生效策略响应（含全局和节点覆盖） */
export interface EffectiveStrategyResponse {
  // OpenAPI name: global_config
  globalConfig: StrategyConfigItemResponse;
  // OpenAPI name: node_overrides
  nodeOverrides?: StrategyConfigItemResponse[];
  effective: StrategyConfigItemResponse;
}

/** 能耗与碳排增量模型参数 */
export interface EnergyCarbonParamsSchema {
  /** 单位泄漏能耗 (kWh/m³) */
  // OpenAPI name: energy_per_leakage_unit
  energyPerLeakageUnit?: number;
  /** 电力排放因子 (kgCO₂e/kWh) */
  // OpenAPI name: carbon_factor_electricity
  carbonFactorElectricity?: number;
  /** 天然气排放因子 (kgCO₂e/kWh) */
  // OpenAPI name: carbon_factor_natural_gas
  carbonFactorNaturalGas?: number;
  /** 蒸汽排放因子 (kgCO₂e/kWh) */
  // OpenAPI name: carbon_factor_steam
  carbonFactorSteam?: number;
  /** 压缩机效率 0-1 */
  // OpenAPI name: compressor_efficiency
  compressorEfficiency?: number;
  /** 泄漏回收率 0-1 */
  // OpenAPI name: recovery_rate
  recoveryRate?: number;
  /** 基准月度能耗 (kWh) */
  // OpenAPI name: base_monthly_energy_kwh
  baseMonthlyEnergyKwh?: number;
  /** 基准月度碳排 (kgCO₂e) */
  // OpenAPI name: base_monthly_carbon_kg
  baseMonthlyCarbonKg?: number;
}

/** 增强版模型训练请求 */
export interface EnhancedTrainingRequest {
  /** 模型类型: bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID，空则训练所有 */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 是否强制重新训练 */
  // OpenAPI name: force_retrain
  forceRetrain?: boolean;
  /** 数据来源: db/csv/manual */
  // OpenAPI name: data_source
  dataSource?: string;
  /** 是否增量训练 */
  // OpenAPI name: is_incremental
  isIncremental?: boolean;
  /** 增量训练的基础版本 */
  // OpenAPI name: base_model_version
  baseModelVersion?: any;
  /** 冻结的层名称 */
  // OpenAPI name: freeze_layers
  freezeLayers?: any;
  /** 详细训练配置 */
  // OpenAPI name: training_config
  trainingConfig?: any;
}

/** 增强版模型训练响应 */
export interface EnhancedTrainingResponse {
  /** 训练会话ID，用于查询状态 */
  // OpenAPI name: session_id
  sessionId: string;
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId: any;
  /** 启动状态: started/error */
  status: string;
  /** 描述信息 */
  message: string;
  /** 是否增量训练 */
  // OpenAPI name: is_incremental
  isIncremental?: boolean;
}

/** Epoch指标 */
export interface EpochMetricsSchema {
  epoch: number;
  // OpenAPI name: train_loss
  trainLoss: number;
  // OpenAPI name: val_loss
  valLoss?: any;
  // OpenAPI name: train_acc
  trainAcc?: any;
  // OpenAPI name: val_acc
  valAcc?: any;
  // OpenAPI name: learning_rate
  learningRate?: any;
  // OpenAPI name: duration_seconds
  durationSeconds?: number;
  timestamp: string;
}

/** 可解释性报告响应 */
export interface ExplainabilityReportResponse {
  // OpenAPI name: prediction_id
  predictionId: string;
  // OpenAPI name: attention_weights
  attentionWeights?: any;
  // OpenAPI name: key_timesteps
  keyTimesteps?: any;
  // OpenAPI name: risk_factor_decomposition
  riskFactorDecomposition?: any;
  // OpenAPI name: rule_hits
  ruleHits?: any;
  // OpenAPI name: strategy_adjustment
  strategyAdjustment?: any;
}

/** FactorContributionSchema */
export interface FactorContributionSchema {
  /** 因子名称 */
  name: string;
  /** 因子显示名 */
  // OpenAPI name: display_name
  displayName: string;
  /** 原始评分 */
  // OpenAPI name: raw_score
  rawScore: number;
  /** 权重 */
  weight: number;
  /** 加权评分 */
  // OpenAPI name: weighted_score
  weightedScore: number;
  /** 贡献度占比 */
  // OpenAPI name: contribution_ratio
  contributionRatio: number;
  /** 方向: risk_up/risk_down */
  direction: string;
}

/** 故障类型细分详情 */
export interface FaultDetailSchema {
  /** 故障类型: loosening/overload/fracture/fatigue/corrosion */
  // OpenAPI name: fault_type
  faultType: string;
  /** 故障分类置信度 */
  // OpenAPI name: fault_confidence
  faultConfidence: number;
  /** 故障类型中文名 */
  // OpenAPI name: fault_name
  faultName: string;
  /** 严重程度 1-10 */
  severity: number;
  /** 判定依据 */
  evidence?: string[];
  /** 故障类型差异化推荐措施 */
  recommendations?: string[];
  /** 故障模式特征证据 */
  pattern?: any;
}

/** 故障模式特征 */
export interface FaultPatternSchema {
  /** 趋势斜率 */
  // OpenAPI name: trend_slope
  trendSlope: number;
  /** 波动率 */
  volatility: number;
  /** 骤降/突变点数量 */
  // OpenAPI name: sudden_changes
  suddenChanges: number;
  /** 最小值 */
  // OpenAPI name: min_value
  minValue: number;
  /** 最大值 */
  // OpenAPI name: max_value
  maxValue: number;
  /** 平均值 */
  // OpenAPI name: mean_value
  meanValue: number;
}

/** 特征重要性分析（各通道对预测结果的贡献度） */
export interface FeatureImportanceInfo {
  /** 预紧力通道重要性 */
  preload?: number;
  /** 温度通道重要性 */
  temperature?: number;
  /** 湿度通道重要性 */
  humidity?: number;
  /** 振动通道重要性 */
  vibration?: number;
  /** 扭矩通道重要性 */
  torque?: number;
  /** 其他扩展通道的重要性 */
  others?: Record<string, number>;
}

/** 聚合器配置 */
export interface FederatedAggregatorConfig {
  /** 聚合策略: fedavg/weighted_avg/median/trimmed_mean/fedprox/fedopt */
  strategy?: string;
  /** 修剪均值比例 */
  // OpenAPI name: trim_ratio
  trimRatio?: number;
  /** FedProx近端项系数 */
  mu?: number;
  /** 服务器学习率 */
  // OpenAPI name: server_learning_rate
  serverLearningRate?: number;
  /** 每轮最少客户端数 */
  // OpenAPI name: min_clients_per_round
  minClientsPerRound?: number;
  /** 是否启用异常值检测 */
  // OpenAPI name: enable_outlier_detection
  enableOutlierDetection?: boolean;
}

/** 联邦学习客户端注册请求 */
export interface FederatedClientRegisterRequest {
  /** 客户端/厂区ID */
  // OpenAPI name: client_id
  clientId: string;
  /** 厂区名称 */
  // OpenAPI name: factory_name
  factoryName?: any;
  /** 厂区位置 */
  location?: any;
  /** 客户端附加信息 */
  // OpenAPI name: client_info
  clientInfo?: any;
}

/** 联邦学习客户端注册响应 */
export interface FederatedClientRegisterResponse {
  // OpenAPI name: client_id
  clientId: string;
  status: string;
  message: string;
  // OpenAPI name: registered_at
  registeredAt: Date | string;
}

/** 客户端状态响应 */
export interface FederatedClientStatusResponse {
  // OpenAPI name: client_id
  clientId: string;
  // OpenAPI name: factory_id
  factoryId: string;
  // OpenAPI name: model_type
  modelType: any;
  // OpenAPI name: node_id
  nodeId: any;
  // OpenAPI name: current_round
  currentRound: number;
  // OpenAPI name: has_global_model
  hasGlobalModel: boolean;
  // OpenAPI name: has_local_model
  hasLocalModel: boolean;
  // OpenAPI name: training_count
  trainingCount: number;
  // OpenAPI name: privacy_mechanism
  privacyMechanism: string;
  // OpenAPI name: update_type
  updateType: string;
  // OpenAPI name: two_level_arch_enabled
  twoLevelArchEnabled: boolean;
  // OpenAPI name: last_update_time
  lastUpdateTime: any;
}

/** 获取全局模型请求 */
export interface FederatedGlobalModelRequest {
  /** 客户端ID */
  // OpenAPI name: client_id
  clientId: string;
  /** 模型类型: bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
}

/** 获取全局模型响应 */
export interface FederatedGlobalModelResponse {
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: round_id
  roundId: number;
  version?: any;
  weights: Record<string, any>;
  // OpenAPI name: server_time
  serverTime: Date | string;
  // OpenAPI name: enable_two_level_arch
  enableTwoLevelArch?: boolean;
  metrics?: any;
}

/** 本地训练请求 */
export interface FederatedLocalTrainRequest {
  /** 客户端ID */
  // OpenAPI name: client_id
  clientId: string;
  /** 模型类型: bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 本地训练轮数 */
  // OpenAPI name: local_epochs
  localEpochs?: any;
  /** 是否执行本地微调（第二层） */
  // OpenAPI name: fine_tune
  fineTune?: boolean;
  /** 训练数据（可选，自动加载） */
  // OpenAPI name: train_data
  trainData?: any;
  /** 训练标签（可选，自动加载） */
  // OpenAPI name: train_labels
  trainLabels?: any;
}

/** 本地训练响应 */
export interface FederatedLocalTrainResponse {
  // OpenAPI name: client_id
  clientId: string;
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId: string;
  status: string;
  message: string;
  // OpenAPI name: num_samples
  numSamples: number;
  // OpenAPI name: training_time
  trainingTime: number;
  metrics: Record<string, number>;
}

/** 获取模型历史响应 */
export interface FederatedModelHistoryResponse {
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId: string;
  history: Record<string, any>[];
}

/** 隐私保护配置 */
export interface FederatedPrivacyConfig {
  /** 隐私机制: none/dp/secagg/combined */
  mechanism?: string;
  /** 差分隐私epsilon */
  epsilon?: number;
  /** 差分隐私delta */
  delta?: number;
  /** 噪声缩放系数 */
  // OpenAPI name: noise_scale
  noiseScale?: number;
  /** 梯度裁剪范数 */
  // OpenAPI name: clip_norm
  clipNorm?: number;
  /** 安全聚合参与方数量 */
  // OpenAPI name: num_parties
  numParties?: number;
  /** 秘密共享阈值 */
  // OpenAPI name: secret_share_threshold
  secretShareThreshold?: number;
}

/** 聚合模型更新请求 */
export interface FederatedRoundAggregateRequest {
  /** 模型类型: bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
}

/** 聚合模型更新响应 */
export interface FederatedRoundAggregateResponse {
  // OpenAPI name: round_id
  roundId: number;
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId: string;
  status: string;
  message: string;
  // OpenAPI name: num_clients_aggregated
  numClientsAggregated: number;
  version?: any;
  metrics?: any;
  // OpenAPI name: aggregated_at
  aggregatedAt: Date | string;
}

/** 开始联邦学习轮次请求 */
export interface FederatedRoundStartRequest {
  /** 模型类型: bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 期望参与的客户端列表 */
  // OpenAPI name: expected_clients
  expectedClients?: any;
}

/** 开始联邦学习轮次响应 */
export interface FederatedRoundStartResponse {
  // OpenAPI name: round_id
  roundId: number;
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId: string;
  status: string;
  // OpenAPI name: expected_clients
  expectedClients: string[];
  // OpenAPI name: started_at
  startedAt: Date | string;
}

/** 联邦学习服务器状态响应 */
export interface FederatedServerStatusResponse {
  // OpenAPI name: registered_clients
  registeredClients: number;
  // OpenAPI name: active_clients
  activeClients: number;
  // OpenAPI name: total_rounds
  totalRounds: number;
  // OpenAPI name: completed_rounds
  completedRounds: number;
  // OpenAPI name: failed_rounds
  failedRounds: number;
  // OpenAPI name: aggregation_strategy
  aggregationStrategy: string;
  // OpenAPI name: managed_models
  managedModels: string[];
  // OpenAPI name: current_round
  currentRound?: any;
}

/** 上传模型更新请求 */
export interface FederatedUpdateUploadRequest {
  /** 客户端ID */
  // OpenAPI name: client_id
  clientId: string;
  /** 模型类型: bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 联邦学习轮次ID */
  // OpenAPI name: round_id
  roundId: number;
  /** 模型更新（权重或差异） */
  weights: Record<string, any>;
  /** 训练样本数量 */
  // OpenAPI name: num_samples
  numSamples: number;
  /** 训练指标 */
  metrics?: any;
  /** 是否加密 */
  encrypted?: boolean;
  /** 加密后的更新（Base64编码） */
  // OpenAPI name: encrypted_update
  encryptedUpdate?: any;
  /** 更新类型: weights/gradients/difference */
  // OpenAPI name: update_type
  updateType?: string;
}

/** 上传模型更新响应 */
export interface FederatedUpdateUploadResponse {
  // OpenAPI name: client_id
  clientId: string;
  // OpenAPI name: round_id
  roundId: number;
  status: string;
  message: string;
  // OpenAPI name: received_at
  receivedAt: Date | string;
}

/** 过滤结果 */
export interface FilteredDataResultSchema {
  // OpenAPI name: original_count
  originalCount: number;
  // OpenAPI name: filtered_count
  filteredCount: number;
  // OpenAPI name: removed_indices
  removedIndices: number[];
  // OpenAPI name: removal_reasons
  removalReasons: Record<string, string>;
  // OpenAPI name: filter_strategy
  filterStrategy: string;
  // OpenAPI name: confidence_multiplier
  confidenceMultiplier: number;
  // OpenAPI name: adjusted_confidence
  adjustedConfidence?: any;
}

/** 法兰面健康度指数（聚合） */
export interface FlangeHealthIndexSchema {
  // OpenAPI name: flange_id
  flangeId: string;
  // OpenAPI name: flange_name
  flangeName?: any;
  /** 法兰面综合健康度 */
  // OpenAPI name: hi_score
  hiScore: number;
  /** 健康等级 */
  // OpenAPI name: hi_level
  hiLevel: string;
  /** 最差螺栓健康度 */
  // OpenAPI name: worst_bolt_hi
  worstBoltHi: number;
  /** 最差螺栓ID */
  // OpenAPI name: worst_bolt_id
  worstBoltId: string;
  /** 平均螺栓健康度 */
  // OpenAPI name: average_bolt_hi
  averageBoltHi: number;
  /** 螺栓健康度中位数 */
  // OpenAPI name: median_bolt_hi
  medianBoltHi: number;
  /** 劣化速率（HI/天） */
  // OpenAPI name: degradation_rate
  degradationRate: number;
  /** 螺栓总数 */
  // OpenAPI name: bolt_count
  boltCount: number;
  /** 健康螺栓数(HI>=70) */
  // OpenAPI name: healthy_bolt_count
  healthyBoltCount: number;
  /** 预警螺栓数(50<=HI<70) */
  // OpenAPI name: warning_bolt_count
  warningBoltCount: number;
  /** 危险螺栓数(HI<50) */
  // OpenAPI name: critical_bolt_count
  criticalBoltCount: number;
  /** 各螺栓健康度详情 */
  // OpenAPI name: bolts_health
  boltsHealth: BoltHealthIndexSchema[];
  trend?: any;
  // OpenAPI name: calculate_time
  calculateTime: Date | string;
}

/** 法兰面预测请求

Attributes:
    法兰面id: 法兰面唯一标识
    data: 多螺栓预紧力时序数据 */
export interface FlangePredictionRequest {
  /** 法兰面唯一标识 */
  // OpenAPI name: flange_id
  flangeId: string;
  /** 多螺栓预紧力数据，三维数组[螺栓][时间点][时间,预紧力] */
  data: any[][][];
}

/** 法兰面预测响应 */
export interface FlangePredictionResponse {
  // OpenAPI name: flange_id
  flangeId: string;
  status: string;
  // OpenAPI name: status_code
  statusCode: number;
  confidence: number;
  // OpenAPI name: risk_score
  riskScore: number;
  // OpenAPI name: risk_level
  riskLevel: string;
  // OpenAPI name: bolt_count
  boltCount: number;
  // OpenAPI name: attention_weights
  attentionWeights?: any;
  diagnosis: string;
  recommendations: string[];
  // OpenAPI name: prediction_time
  predictionTime: Date | string;
  // OpenAPI name: correlation_matrix
  correlationMatrix?: any;
  // OpenAPI name: causal_graph
  causalGraph?: any;
  // OpenAPI name: leading_bolts
  leadingBolts?: any;
  // OpenAPI name: propagation_paths
  propagationPaths?: any;
  // OpenAPI name: root_cause_analysis
  rootCauseAnalysis?: any;
  // OpenAPI name: root_cause_measures
  rootCauseMeasures?: any;
  /** 模型版本号 */
  // OpenAPI name: model_version
  modelVersion?: any;
  /** Shadow模式版本号 */
  // OpenAPI name: shadow_version
  shadowVersion?: any;
  /** Shadow模式预测结果 */
  // OpenAPI name: shadow_result
  shadowResult?: any;
  /** 故障类型细分详情 */
  // OpenAPI name: fault_detail
  faultDetail?: any;
}

/** Focal Loss配置 */
export interface FocalLossConfig {
  /** 是否启用Focal Loss */
  enabled?: boolean;
  /** 聚焦参数gamma，难例加权系数 */
  gamma?: number;
  /** 类别权重alpha列表 */
  alpha?: any;
}

/** HI与碳排并列展示单项 */
export interface HiCarbonDualItemSchema {
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 节点类型 */
  // OpenAPI name: node_type
  nodeType: string;
  /** 节点名称 */
  // OpenAPI name: node_name
  nodeName: string;
  /** 健康度指数 0-100 */
  // OpenAPI name: hi_score
  hiScore: number;
  /** HI等级 */
  // OpenAPI name: hi_level
  hiLevel: string;
  /** HI趋势 improving/stable/declining */
  // OpenAPI name: hi_trend
  hiTrend: string;
  /** 预紧力月劣化速率 */
  // OpenAPI name: degradation_rate_per_month
  degradationRatePerMonth: number;
  /** 估算泄漏率 (m³/h) */
  // OpenAPI name: estimated_leakage_rate_m3_hour
  estimatedLeakageRateM3Hour: number;
  /** 月度碳排增量 (kgCO₂e) */
  // OpenAPI name: monthly_carbon_increment_kg
  monthlyCarbonIncrementKg: number;
  /** 碳排风险等级 low/medium/high/critical */
  // OpenAPI name: carbon_risk_level
  carbonRiskLevel: string;
  /** 碳排趋势 increasing/stable/decreasing */
  // OpenAPI name: carbon_trend
  carbonTrend: string;
}

/** HI rollup 与碳排并列展示请求 */
export interface HiCarbonDualViewRequest {
  /** 节点数据列表，每项包含: node_id, node_type(可选), node_name(可选), hi_score, hi_level, hi_trend(可选), preload_history, timestamps(可选), service_age_months(可选), avg_temperature(可选), seal_age_years(可选), operating_pressure_mpa(可选) */
  nodes: Record<string, any>[];
}

/** HI rollup 与碳排并列展示响应 */
export interface HiCarbonDualViewResponse {
  /** 报告月份 YYYY-MM */
  // OpenAPI name: report_month
  reportMonth: string;
  /** 节点总数 */
  // OpenAPI name: total_nodes
  totalNodes: number;
  /** HI与碳排并列数据列表 */
  items: HiCarbonDualItemSchema[];
  /** 生成时间 */
  // OpenAPI name: generated_at
  generatedAt: Date | string;
}

/** HTTPValidationError */
export interface HttpValidationError {
  detail?: ValidationError[];
}

/** 组件健康状态 */
export interface HealthComponentStatus {
  status: string;
  message?: any;
}

/** 批量健康度计算请求 */
export interface HealthIndexBatchCalculateRequest {
  /** 节点列表 [{node_id, node_type, data}, ...] */
  nodes: Record<string, any>[];
  // OpenAPI name: working_condition
  workingCondition?: any;
  // OpenAPI name: save_to_db
  saveToDb?: boolean;
}

/** 批量健康度计算响应 */
export interface HealthIndexBatchResponse {
  // OpenAPI name: total_count
  totalCount: number;
  // OpenAPI name: success_count
  successCount: number;
  // OpenAPI name: failed_count
  failedCount: number;
  results: Record<string, any>[];
  // OpenAPI name: calculate_time
  calculateTime: Date | string;
}

/** 健康度计算请求 */
export interface HealthIndexCalculateRequest {
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 节点类型 bolt/flange/line */
  // OpenAPI name: node_type
  nodeType: string;
  /** 预紧力时序数据 [[时间, 预紧力], ...] */
  data?: any;
  /** 工况信息 */
  // OpenAPI name: working_condition
  workingCondition?: any;
  /** 是否包含历史数据 */
  // OpenAPI name: include_history
  includeHistory?: boolean;
  /** 是否保存到数据库 */
  // OpenAPI name: save_to_db
  saveToDb?: boolean;
}

/** 健康度指数详情 */
export interface HealthIndexDetailSchema {
  /** 综合健康度指数 0-100 */
  // OpenAPI name: hi_score
  hiScore: number;
  /** 健康等级 excellent/good/fair/poor/critical */
  // OpenAPI name: hi_level
  hiLevel: string;
  /** 各因子得分详情 */
  factors: HealthIndexFactorSchema[];
  /** 预紧力稳定性得分 */
  // OpenAPI name: preload_stability_score
  preloadStabilityScore: number;
  /** 预警频率得分 */
  // OpenAPI name: alert_frequency_score
  alertFrequencyScore: number;
  /** 故障历史得分 */
  // OpenAPI name: fault_history_score
  faultHistoryScore: number;
  /** 环境应力得分 */
  // OpenAPI name: environmental_stress_score
  environmentalStressScore: number;
  /** 使用年限得分 */
  // OpenAPI name: service_age_score
  serviceAgeScore: number;
  /** 健康趋势 improving/stable/declining */
  trend?: any;
  /** 趋势变化率 */
  // OpenAPI name: trend_rate
  trendRate?: any;
  // OpenAPI name: calculate_time
  calculateTime: Date | string;
}

/** 健康度因子详情 */
export interface HealthIndexFactorSchema {
  /** 因子名称 */
  // OpenAPI name: factor_name
  factorName: string;
  /** 因子代码 */
  // OpenAPI name: factor_code
  factorCode: string;
  /** 因子得分 0-100 */
  score: number;
  /** 因子权重 */
  weight: number;
  /** 对总健康度的贡献 */
  contribution: number;
  /** 因子描述 */
  description?: any;
}

/** 健康度历史查询响应 */
export interface HealthIndexHistoryResponse {
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: node_type
  nodeType: string;
  total: number;
  history: Record<string, any>[];
  // OpenAPI name: trend_analysis
  trendAnalysis?: any;
}

/** 健康度计算响应 */
export interface HealthIndexResponse {
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: node_type
  nodeType: string;
  // OpenAPI name: health_data
  healthData: HealthIndexDetailSchema;
  saved: boolean;
  // OpenAPI name: calculate_time
  calculateTime: Date | string;
}

/** 健康检查响应 */
export interface HealthResponse {
  status?: string;
  version: string;
  timestamp: Date | string;
  components?: any;
}

/** 健康度汇总报表请求 */
export interface HealthRollupRequest {
  /** 产线/装置ID */
  // OpenAPI name: line_id
  lineId: string;
  // OpenAPI name: line_name
  lineName?: any;
  /** 产线类型 */
  // OpenAPI name: line_type
  lineType?: string;
  /** 报告日期，默认今日 */
  // OpenAPI name: report_date
  reportDate?: any;
  /** 是否包含详细数据 */
  // OpenAPI name: include_details
  includeDetails?: boolean;
}

/** 健康度汇总报表响应 */
export interface HealthRollupResponse {
  // OpenAPI name: report_id
  reportId?: any;
  // OpenAPI name: rollup_data
  rollupData: ProductionLineHealthRollupSchema;
  saved: boolean;
}

/** 增量训练配置 */
export interface IncrementalTrainingConfig {
  /** 是否增量训练 */
  enabled?: boolean;
  /** 冻结的层名称列表，如 ['lstm1', 'lstm2'] */
  // OpenAPI name: freeze_layers
  freezeLayers?: any;
  /** 基础模型版本号，None则使用最新版本 */
  // OpenAPI name: base_model_version
  baseModelVersion?: any;
}

/** 任务执行日志列表响应 */
export interface JobExecutionLogListResponse {
  /** 总记录数 */
  total: number;
  /** 日志列表 */
  items: JobExecutionLogSchema[];
}

/** 任务执行日志 */
export interface JobExecutionLogSchema {
  /** 日志ID */
  id: number;
  /** 任务名称 */
  // OpenAPI name: job_name
  jobName: string;
  /** 任务类型 */
  // OpenAPI name: job_type
  jobType: string;
  /** 触发类型 */
  // OpenAPI name: trigger_type
  triggerType: string;
  /** 状态 */
  status: string;
  /** 开始时间 */
  // OpenAPI name: start_time
  startTime: Date | string;
  /** 结束时间 */
  // OpenAPI name: end_time
  endTime?: any;
  /** 执行时长（秒） */
  // OpenAPI name: duration_seconds
  durationSeconds?: any;
  /** 处理节点总数 */
  // OpenAPI name: total_nodes
  totalNodes?: number;
  /** 成功节点数 */
  // OpenAPI name: success_count
  successCount?: number;
  /** 失败节点数 */
  // OpenAPI name: failed_count
  failedCount?: number;
  /** 跳过节点数 */
  // OpenAPI name: skipped_count
  skippedCount?: number;
  /** 分片索引 */
  // OpenAPI name: shard_index
  shardIndex?: any;
  /** 总分片数 */
  // OpenAPI name: shard_total
  shardTotal?: any;
  /** 最小bolt_id */
  // OpenAPI name: bolt_id_min
  boltIdMin?: any;
  /** 最大bolt_id */
  // OpenAPI name: bolt_id_max
  boltIdMax?: any;
  /** 执行实例ID */
  // OpenAPI name: instance_id
  instanceId?: any;
  /** 错误摘要 */
  // OpenAPI name: error_summary
  errorSummary?: any;
  /** 错误详情 */
  // OpenAPI name: error_details
  errorDetails?: any;
  /** 创建时间 */
  // OpenAPI name: create_time
  createTime: Date | string;
}

/** 创建案例请求 */
export interface KnowledgeCaseCreateRequest {
  /** 案例标题 */
  // OpenAPI name: case_title
  caseTitle: string;
  /** 节点类型 bolt/flange */
  // OpenAPI name: node_type
  nodeType?: any;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 故障类型 */
  // OpenAPI name: fault_type
  faultType?: any;
  /** 故障级别 1-4 */
  // OpenAPI name: fault_level
  faultLevel?: any;
  /** 工况信息 */
  // OpenAPI name: working_condition
  workingCondition?: any;
  /** 传感器时序数据 [[时间, 数值], ...] */
  // OpenAPI name: sensor_data
  sensorData?: any;
  /** 传感器特征 (58维特征名值对) */
  // OpenAPI name: sensor_features
  sensorFeatures?: any;
  /** 诊断结论 */
  diagnosis?: any;
  /** 根本原因分析 */
  // OpenAPI name: root_cause
  rootCause?: any;
  /** 处置方案 */
  // OpenAPI name: treatment_plan
  treatmentPlan?: any;
  /** 效果评估 */
  // OpenAPI name: effect_evaluation
  effectEvaluation?: any;
  /** 来源告警ID */
  // OpenAPI name: source_alert_id
  sourceAlertId?: any;
  /** 来源预测记录ID */
  // OpenAPI name: source_prediction_id
  sourcePredictionId?: any;
  /** 标签列表 */
  tags?: any;
  /** 创建人ID */
  // OpenAPI name: creator_id
  creatorId?: any;
  /** 创建人姓名 */
  // OpenAPI name: creator_name
  creatorName?: any;
  /** 租户ID */
  // OpenAPI name: tenant_id
  tenantId?: any;
  /** 是否提交审核 */
  // OpenAPI name: submit_for_review
  submitForReview?: boolean;
}

/** 案例列表响应 */
export interface KnowledgeCaseListResponse {
  total: number;
  items: KnowledgeCaseResponse[];
}

/** 案例响应 */
export interface KnowledgeCaseResponse {
  id: number;
  // OpenAPI name: case_no
  caseNo: string;
  // OpenAPI name: case_title
  caseTitle: string;
  // OpenAPI name: node_type
  nodeType?: any;
  // OpenAPI name: node_id
  nodeId?: any;
  // OpenAPI name: fault_type
  faultType?: any;
  // OpenAPI name: fault_level
  faultLevel?: any;
  // OpenAPI name: working_condition
  workingCondition?: any;
  // OpenAPI name: sensor_features
  sensorFeatures?: any;
  diagnosis?: any;
  // OpenAPI name: root_cause
  rootCause?: any;
  // OpenAPI name: treatment_plan
  treatmentPlan?: any;
  // OpenAPI name: effect_evaluation
  effectEvaluation?: any;
  // OpenAPI name: effectiveness_score
  effectivenessScore?: any;
  status: string;
  version: number;
  // OpenAPI name: tenant_id
  tenantId?: any;
  // OpenAPI name: creator_id
  creatorId?: any;
  // OpenAPI name: creator_name
  creatorName?: any;
  // OpenAPI name: reviewer_id
  reviewerId?: any;
  // OpenAPI name: reviewer_name
  reviewerName?: any;
  // OpenAPI name: review_time
  reviewTime?: any;
  // OpenAPI name: review_comment
  reviewComment?: any;
  // OpenAPI name: source_alert_id
  sourceAlertId?: any;
  // OpenAPI name: source_prediction_id
  sourcePredictionId?: any;
  tags?: any;
  // OpenAPI name: similarity_score
  similarityScore?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** 更新案例请求 */
export interface KnowledgeCaseUpdateRequest {
  /** 案例标题 */
  // OpenAPI name: case_title
  caseTitle?: any;
  /** 故障类型 */
  // OpenAPI name: fault_type
  faultType?: any;
  /** 故障级别 1-4 */
  // OpenAPI name: fault_level
  faultLevel?: any;
  /** 工况信息 */
  // OpenAPI name: working_condition
  workingCondition?: any;
  /** 传感器时序数据 */
  // OpenAPI name: sensor_data
  sensorData?: any;
  /** 传感器特征 */
  // OpenAPI name: sensor_features
  sensorFeatures?: any;
  /** 诊断结论 */
  diagnosis?: any;
  /** 根本原因分析 */
  // OpenAPI name: root_cause
  rootCause?: any;
  /** 处置方案 */
  // OpenAPI name: treatment_plan
  treatmentPlan?: any;
  /** 效果评估 */
  // OpenAPI name: effect_evaluation
  effectEvaluation?: any;
  /** 标签列表 */
  tags?: any;
  /** 变更说明 */
  // OpenAPI name: change_summary
  changeSummary?: any;
  /** 是否提交审核 */
  // OpenAPI name: submit_for_review
  submitForReview?: boolean;
  /** 操作人ID */
  // OpenAPI name: operator_id
  operatorId?: any;
  /** 操作人姓名 */
  // OpenAPI name: operator_name
  operatorName?: any;
}

/** 学习率调度器配置 */
export interface LrSchedulerConfig {
  /** 调度器类型: none/reduce_on_plateau/step/cosine */
  type?: string;
  /** reduce_on_plateau衰减因子 */
  factor?: any;
  /** reduce_on_plateau耐心轮数 */
  patience?: any;
  /** 最小学习率 */
  // OpenAPI name: min_lr
  minLr?: any;
  /** step衰减步长（epoch数） */
  // OpenAPI name: step_size
  stepSize?: any;
  /** step衰减因子 */
  gamma?: any;
  /** cosine最大迭代轮数 */
  // OpenAPI name: t_max
  tMax?: any;
  /** cosine最小学习率 */
  // OpenAPI name: eta_min
  etaMin?: any;
}

/** CSV标注导入请求 */
export interface LabelImportCsvRequest {
  /** CSV文件路径 */
  // OpenAPI name: csv_path
  csvPath: string;
  /** 节点类型: bolt/flange */
  // OpenAPI name: node_type
  nodeType: string;
  /** 标签列名，自动检测 */
  // OpenAPI name: label_column
  labelColumn?: any;
  /** 节点ID列名，自动检测 */
  // OpenAPI name: id_column
  idColumn?: any;
  /** 数据点列名 */
  // OpenAPI name: data_column
  dataColumn?: any;
  /** 时间戳列名 */
  // OpenAPI name: timestamp_column
  timestampColumn?: any;
  /** 标注人姓名 */
  // OpenAPI name: labeler_name
  labelerName?: any;
  /** 是否自动审核通过 */
  // OpenAPI name: auto_approve
  autoApprove?: boolean;
  /** 是否跳过错误行 */
  // OpenAPI name: skip_errors
  skipErrors?: boolean;
}

/** 数据库标注导入请求 */
export interface LabelImportDbRequest {
  /** 源表名 */
  // OpenAPI name: source_table
  sourceTable: string;
  /** 节点类型: bolt/flange */
  // OpenAPI name: node_type
  nodeType: string;
  /** 节点ID字段名 */
  // OpenAPI name: id_field
  idField: string;
  /** 标签字段名 */
  // OpenAPI name: label_field
  labelField: string;
  /** 数据点字段名 */
  // OpenAPI name: data_field
  dataField?: any;
  /** 时间戳字段名 */
  // OpenAPI name: timestamp_field
  timestampField?: any;
  /** WHERE条件，不带WHERE关键字 */
  // OpenAPI name: where_clause
  whereClause?: any;
  /** 标注人姓名 */
  // OpenAPI name: labeler_name
  labelerName?: any;
  /** 是否自动审核通过 */
  // OpenAPI name: auto_approve
  autoApprove?: boolean;
}

/** 可导入文件列表项 */
export interface LabelImportFileItemSchema {
  /** 文件名 */
  filename: string;
  /** 文件完整路径 */
  path: string;
  /** 文件大小（字节） */
  // OpenAPI name: size_bytes
  sizeBytes?: number;
  /** 修改时间 */
  // OpenAPI name: modified_time
  modifiedTime?: any;
}

/** 可导入文件列表响应 */
export interface LabelImportFileListResponse {
  /** 文件数量 */
  total: number;
  /** 文件列表 */
  items?: LabelImportFileItemSchema[];
}

/** 标注导入响应 */
export interface LabelImportResponse {
  /** 状态: success/error */
  status: string;
  /** 描述信息 */
  message: string;
  /** 导入结果统计 */
  result?: any;
}

/** 标注导入结果 */
export interface LabelImportResultSchema {
  /** 总行数 */
  total?: number;
  /** 成功导入数 */
  imported?: number;
  /** 跳过数 */
  skipped?: number;
  /** 重复数 */
  duplicates?: number;
  /** 错误数 */
  errors?: number;
  /** 错误详情 */
  // OpenAPI name: error_details
  errorDetails?: any;
}

/** Leader选举状态 */
export interface LeaderStatusSchema {
  /** Leader锁键 */
  // OpenAPI name: leader_key
  leaderKey: string;
  /** 当前Leader实例ID */
  // OpenAPI name: leader_id
  leaderId: string;
  /** 租约过期时间 */
  // OpenAPI name: lease_expire_time
  leaseExpireTime: Date | string;
  /** 最后心跳时间 */
  // OpenAPI name: last_heartbeat
  lastHeartbeat: Date | string;
  /** 版本号 */
  version: number;
  /** 租约是否已过期 */
  // OpenAPI name: is_expired
  isExpired: boolean;
  /** 当前实例是否为Leader */
  // OpenAPI name: is_current_instance
  isCurrentInstance: boolean;
}

/** 领先螺栓信息 */
export interface LeadingBoltSchema {
  // OpenAPI name: bolt_id
  boltId: string;
  index: number;
  // OpenAPI name: leading_score
  leadingScore: number;
  // OpenAPI name: out_degree
  outDegree: number;
  // OpenAPI name: in_degree
  inDegree: number;
  // OpenAPI name: net_degree
  netDegree: number;
  // OpenAPI name: out_strength
  outStrength: number;
  // OpenAPI name: in_strength
  inStrength: number;
  // OpenAPI name: net_strength
  netStrength: number;
  // OpenAPI name: trend_leadership
  trendLeadership: number;
  // OpenAPI name: is_leading
  isLeading: boolean;
}

/** 泄漏率估算模型参数 */
export interface LeakageParamsSchema {
  /** 基准泄漏率 (m³/h) */
  // OpenAPI name: base_leakage_rate_m3_per_hour
  baseLeakageRateM3PerHour?: number;
  /** 临界泄漏压紧比阈值 */
  // OpenAPI name: critical_leakage_threshold
  criticalLeakageThreshold?: number;
  /** 预紧力泄漏敏感度指数 */
  // OpenAPI name: preload_leakage_sensitivity
  preloadLeakageSensitivity?: number;
  /** 密封年老化系数 */
  // OpenAPI name: seal_aging_factor_per_year
  sealAgingFactorPerYear?: number;
  /** 压力敏感度 */
  // OpenAPI name: pressure_sensitivity
  pressureSensitivity?: number;
}

/** 模型信息响应 */
export interface ModelInfoResponse {
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: is_trained
  isTrained: boolean;
  // OpenAPI name: last_training_time
  lastTrainingTime: any;
  // OpenAPI name: training_samples
  trainingSamples: any;
  // OpenAPI name: validation_accuracy
  validationAccuracy: any;
  version?: any;
  // OpenAPI name: file_hash
  fileHash?: any;
  // OpenAPI name: create_time
  createTime?: any;
  // OpenAPI name: training_session_id
  trainingSessionId?: any;
  description?: any;
  // OpenAPI name: validation_samples
  validationSamples?: any;
  // OpenAPI name: is_incremental
  isIncremental?: any;
  // OpenAPI name: parent_version
  parentVersion?: any;
  metrics?: any;
  // OpenAPI name: version_history
  versionHistory?: any;
}

/** 激活/回滚模型版本请求 */
export interface ModelVersionActivateRequest {
  /** 模型类型 bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 目标版本号 */
  version: string;
}

/** 模型版本对比请求 */
export interface ModelVersionCompareRequest {
  version1: string;
  version2: string;
}

/** 模型版本对比响应 */
export interface ModelVersionCompareResponse {
  // OpenAPI name: model_id
  modelId: string;
  version1: string;
  version2: string;
  // OpenAPI name: metrics_comparison
  metricsComparison: Record<string, any>;
  // OpenAPI name: config_diff
  configDiff: Record<string, any>;
}

/** 模型版本列表响应 */
export interface ModelVersionListResponse {
  // OpenAPI name: model_id
  modelId: string;
  // OpenAPI name: model_type
  modelType: string;
  versions: ModelVersionSchema[];
}

/** 回滚模型版本请求 */
export interface ModelVersionRollbackRequest {
  /** 模型类型 bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 目标版本号，不填则回滚到上一版本 */
  version?: any;
}

/** 模型版本信息 */
export interface ModelVersionSchema {
  version: string;
  // OpenAPI name: model_id
  modelId: string;
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: created_at
  createdAt: Date | string;
  // OpenAPI name: file_path
  filePath: string;
  // OpenAPI name: file_hash
  fileHash: string;
  metrics?: Record<string, number>;
  config?: Record<string, any>;
  // OpenAPI name: is_active
  isActive?: boolean;
  description?: string;
}

/** 月度预测请求 */
export interface MonthlyForecastRequest {
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: node_type
  nodeType: string;
  // OpenAPI name: forecast_days
  forecastDays?: number;
}

/** 月度预测响应 */
export interface MonthlyForecastResponse {
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: node_type
  nodeType: string;
  // OpenAPI name: pw_type
  pwType: string;
  // OpenAPI name: fault_type
  faultType: any;
  // OpenAPI name: begin_time
  beginTime: any;
  // OpenAPI name: end_time
  endTime: any;
  confidence: number;
  // OpenAPI name: rec_measures
  recMeasures: string;
  // OpenAPI name: forecast_dates
  forecastDates: Date | string[];
  // OpenAPI name: forecast_values
  forecastValues: number[];
}

/** MTTR趋势点 */
export interface MttrTrendPoint {
  date: string;
  // OpenAPI name: mttr_hours
  mttrHours?: any;
  // OpenAPI name: work_order_count
  workOrderCount?: number;
}

/** MTTR趋势响应 */
export interface MttrTrendResponse {
  trend: MttrTrendPoint[];
  // OpenAPI name: overall_mttr_hours
  overallMttrHours?: any;
}

/** 单通道时序元数据

Attributes:
    name: 通道名称（如 preload / temperature / humidity / vibration / torque / pressure）
    unit: 物理单位（可选）
    description: 中文描述（可选） */
export interface MultivariateChannelSchema {
  /** 通道名称: preload/temperature/humidity/vibration/torque/pressure 或自定义 */
  name: string;
  /** 物理单位, 如 kN / °C / % / g / N·m / MPa */
  unit?: any;
  /** 通道中文描述 */
  description?: any;
}

/** 创建通知渠道请求 */
export interface NotificationChannelCreate {
  /** 渠道类型 email/sms/webhook/dingtalk/wechat */
  // OpenAPI name: channel_type
  channelType: string;
  /** 渠道名称 */
  // OpenAPI name: channel_name
  channelName?: any;
  /** 渠道配置 */
  config?: any;
  /** 是否启用 */
  enabled?: boolean;
  /** 是否默认渠道 */
  // OpenAPI name: is_default
  isDefault?: boolean;
}

/** 通知渠道响应 */
export interface NotificationChannelResponse {
  /** 渠道类型 email/sms/webhook/dingtalk/wechat */
  // OpenAPI name: channel_type
  channelType: string;
  /** 渠道名称 */
  // OpenAPI name: channel_name
  channelName?: any;
  /** 渠道配置 */
  config?: any;
  /** 是否启用 */
  enabled?: boolean;
  /** 是否默认渠道 */
  // OpenAPI name: is_default
  isDefault?: boolean;
  id: number;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** 更新通知渠道请求 */
export interface NotificationChannelUpdate {
  // OpenAPI name: channel_type
  channelType?: any;
  // OpenAPI name: channel_name
  channelName?: any;
  config?: any;
  enabled?: any;
  // OpenAPI name: is_default
  isDefault?: any;
}

/** 通知日志响应 */
export interface NotificationLogResponse {
  id: number;
  // OpenAPI name: alert_id
  alertId?: any;
  // OpenAPI name: channel_type
  channelType?: any;
  // OpenAPI name: subscriber_id
  subscriberId?: any;
  // OpenAPI name: subscriber_name
  subscriberName?: any;
  target?: any;
  title?: any;
  content?: any;
  status: string;
  // OpenAPI name: error_message
  errorMessage?: any;
  // OpenAPI name: retry_count
  retryCount?: number;
  // OpenAPI name: send_time
  sendTime: Date | string;
}

/** OrgNodeCreateRequest */
export interface OrgNodeCreateRequest {
  /** 所属租户ID */
  // OpenAPI name: tenant_id
  tenantId: number;
  /** 父节点ID, 空表示根节点 */
  // OpenAPI name: parent_id
  parentId?: any;
  /** 节点编码 */
  // OpenAPI name: node_code
  nodeCode?: any;
  /** 节点名称 */
  // OpenAPI name: node_name
  nodeName: string;
  /** 节点类型 group/factory/unit/flange/bolt */
  // OpenAPI name: node_type
  nodeType: string;
  /** 排序序号 */
  // OpenAPI name: sort_order
  sortOrder?: number;
  /** 扩展信息 */
  // OpenAPI name: extra_info
  extraInfo?: any;
}

/** OrgNodeResponse */
export interface OrgNodeResponse {
  id: number;
  // OpenAPI name: tenant_id
  tenantId: number;
  // OpenAPI name: parent_id
  parentId?: any;
  // OpenAPI name: node_code
  nodeCode?: any;
  // OpenAPI name: node_name
  nodeName: string;
  // OpenAPI name: node_type
  nodeType: string;
  path?: any;
  level: number;
  // OpenAPI name: sort_order
  sortOrder: number;
  // OpenAPI name: extra_info
  extraInfo?: any;
  status: string;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
  children?: any;
}

/** OrgNodeUpdateRequest */
export interface OrgNodeUpdateRequest {
  // OpenAPI name: node_name
  nodeName?: any;
  // OpenAPI name: node_code
  nodeCode?: any;
  // OpenAPI name: sort_order
  sortOrder?: any;
  // OpenAPI name: extra_info
  extraInfo?: any;
  /** 状态 active/inactive */
  status?: any;
}

/** OrgTreeResponse */
export interface OrgTreeResponse {
  // OpenAPI name: tenant_id
  tenantId: number;
  nodes: OrgNodeResponse[];
}

/** 周期报告响应（周报/月报） */
export interface PeriodicReportResponse {
  /** 报告类型：weekly/monthly */
  // OpenAPI name: report_type
  reportType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 节点类型 */
  // OpenAPI name: node_type
  nodeType: string;
  /** 统计周期开始时间 */
  // OpenAPI name: period_start
  periodStart: Date | string;
  /** 统计周期结束时间 */
  // OpenAPI name: period_end
  periodEnd: Date | string;
  /** 诊断摘要 */
  // OpenAPI name: diagnosis_summary
  diagnosisSummary: string;
  /** 推荐处置措施 */
  // OpenAPI name: recommended_actions
  recommendedActions: string[];
  /** 整体紧急程度：low/medium/high/critical */
  // OpenAPI name: urgency_level
  urgencyLevel: string;
  /** 统计数据 */
  statistics: ReportStatisticsSchema;
  /** 生成时间 */
  // OpenAPI name: generated_at
  generatedAt: Date | string;
  /** 使用的模型 */
  model: string;
  /** 是否使用降级模板 */
  // OpenAPI name: is_fallback
  isFallback?: boolean;
}

/** 预测对比列表响应 */
export interface PredictionCompareListResponse {
  total: number;
  items: PredictionCompareResponse[];
}

/** 预测对比响应 */
export interface PredictionCompareResponse {
  id: number;
  // OpenAPI name: work_order_id
  workOrderId: number;
  // OpenAPI name: retest_id
  retestId?: any;
  // OpenAPI name: original_prediction_id
  originalPredictionId?: any;
  // OpenAPI name: retest_prediction_id
  retestPredictionId?: any;
  // OpenAPI name: original_status
  originalStatus?: any;
  // OpenAPI name: retest_status
  retestStatus?: any;
  // OpenAPI name: original_risk_score
  originalRiskScore?: any;
  // OpenAPI name: retest_risk_score
  retestRiskScore?: any;
  // OpenAPI name: original_confidence
  originalConfidence?: any;
  // OpenAPI name: retest_confidence
  retestConfidence?: any;
  // OpenAPI name: risk_change
  riskChange?: any;
  // OpenAPI name: risk_delta
  riskDelta?: any;
  // OpenAPI name: status_match
  statusMatch?: any;
  // OpenAPI name: is_false_positive
  isFalsePositive?: any;
  // OpenAPI name: is_recurring
  isRecurring?: any;
  // OpenAPI name: comparison_detail
  comparisonDetail?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
}

/** 问题传感器排行 */
export interface ProblemSensorRankingSchema {
  rank: number;
  // OpenAPI name: sensor_id
  sensorId: string;
  // OpenAPI name: quality_score
  qualityScore: number;
  // OpenAPI name: quality_level
  qualityLevel: string;
  // OpenAPI name: problem_types
  problemTypes: string[];
  // OpenAPI name: violation_count
  violationCount: number;
  // OpenAPI name: anomaly_count
  anomalyCount: number;
  // OpenAPI name: collection_anomaly_ratio
  collectionAnomalyRatio: number;
  trend: string;
}

/** 产线/装置级健康度汇总报表 */
export interface ProductionLineHealthRollupSchema {
  // OpenAPI name: line_id
  lineId: string;
  // OpenAPI name: line_name
  lineName: string;
  /** 产线类型 production_line/device/unit */
  // OpenAPI name: line_type
  lineType: string;
  /** 整体健康度 */
  // OpenAPI name: overall_hi
  overallHi: number;
  /** 整体健康等级 */
  // OpenAPI name: overall_level
  overallLevel: string;
  /** 法兰面总数 */
  // OpenAPI name: total_flange_count
  totalFlangeCount: number;
  /** 螺栓总数 */
  // OpenAPI name: total_bolt_count
  totalBoltCount: number;
  /** 健康法兰面数 */
  // OpenAPI name: healthy_flange_count
  healthyFlangeCount: number;
  /** 预警法兰面数 */
  // OpenAPI name: warning_flange_count
  warningFlangeCount: number;
  /** 危险法兰面数 */
  // OpenAPI name: critical_flange_count
  criticalFlangeCount: number;
  /** 健康螺栓数 */
  // OpenAPI name: healthy_bolt_count
  healthyBoltCount: number;
  /** 预警螺栓数 */
  // OpenAPI name: warning_bolt_count
  warningBoltCount: number;
  /** 危险螺栓数 */
  // OpenAPI name: critical_bolt_count
  criticalBoltCount: number;
  /** 最差法兰面健康度 */
  // OpenAPI name: worst_flange_hi
  worstFlangeHi: number;
  /** 最差法兰面ID */
  // OpenAPI name: worst_flange_id
  worstFlangeId: string;
  /** 平均劣化速率 */
  // OpenAPI name: average_degradation_rate
  averageDegradationRate: number;
  /** 各法兰面健康度 */
  // OpenAPI name: flanges_health
  flangesHealth: FlangeHealthIndexSchema[];
  /** 风险汇总 */
  // OpenAPI name: risk_summary
  riskSummary: Record<string, any>;
  /** 维护优先级排序 */
  // OpenAPI name: maintenance_priorities
  maintenancePriorities: Record<string, any>[];
  // OpenAPI name: report_date
  reportDate: Date | string;
  // OpenAPI name: generate_time
  generateTime: Date | string;
}

/** 传播路径 */
export interface PropagationPathSchema {
  path: string[];
  // OpenAPI name: path_indices
  pathIndices: number[];
  depth: number;
  // OpenAPI name: total_weight
  totalWeight: number;
  // OpenAPI name: avg_weight
  avgWeight: number;
}

/** 传播路径分析结果 */
export interface PropagationPathsSchema {
  // OpenAPI name: source_bolt
  sourceBolt: string;
  // OpenAPI name: source_idx
  sourceIdx: number;
  paths: PropagationPathSchema[];
  // OpenAPI name: total_path_count
  totalPathCount: number;
  // OpenAPI name: reachable_bolts
  reachableBolts: string[];
  // OpenAPI name: propagation_distance
  propagationDistance: Record<string, any>;
  // OpenAPI name: max_depth
  maxDepth: number;
}

/** 质量检查结果 */
export interface QualityCheckResultSchema {
  // OpenAPI name: sensor_id
  sensorId: string;
  // OpenAPI name: total_points
  totalPoints: number;
  // OpenAPI name: valid_points
  validPoints: number;
  // OpenAPI name: overall_score
  overallScore: number;
  // OpenAPI name: rule_scores
  ruleScores: Record<string, number>;
  violations: RuleViolationSchema[];
  // OpenAPI name: violation_count
  violationCount: number;
  // OpenAPI name: check_time
  checkTime: Date | string;
}

/** 维度评分 */
export interface QualityDimensionScoreSchema {
  dimension: string;
  score: number;
  weight: number;
  // OpenAPI name: contributing_rules
  contributingRules: string[];
}

/** 质量评估完整响应 */
export interface QualityEvaluationResponse {
  // OpenAPI name: sensor_id
  sensorId: string;
  // OpenAPI name: quality_check
  qualityCheck: QualityCheckResultSchema;
  // OpenAPI name: quality_score
  qualityScore: SensorQualityScoreSchema;
  // OpenAPI name: filter_result
  filterResult: FilteredDataResultSchema;
  // OpenAPI name: anomaly_classification
  anomalyClassification?: any;
  // OpenAPI name: evaluate_time
  evaluateTime: Date | string;
}

/** 生成质量报告请求 */
export interface QualityReportRequest {
  /** 报告日期，默认今日 */
  // OpenAPI name: report_date
  reportDate?: any;
  /** 传感器ID列表，默认全部 */
  // OpenAPI name: sensor_ids
  sensorIds?: any;
  /** 是否保存到数据库 */
  // OpenAPI name: save_to_db
  saveToDb?: boolean;
}

/** QuotaResponse */
export interface QuotaResponse {
  // OpenAPI name: tenant_id
  tenantId: number;
  // OpenAPI name: max_models
  maxModels: number;
  // OpenAPI name: max_api_calls_per_day
  maxApiCallsPerDay: number;
  // OpenAPI name: max_storage_mb
  maxStorageMb: number;
  // OpenAPI name: max_users
  maxUsers: number;
  // OpenAPI name: max_org_nodes
  maxOrgNodes: number;
  // OpenAPI name: current_model_count
  currentModelCount: number;
  // OpenAPI name: current_api_calls_today
  currentApiCallsToday: number;
  // OpenAPI name: current_storage_mb
  currentStorageMb: number;
  // OpenAPI name: current_user_count
  currentUserCount: number;
  // OpenAPI name: current_org_node_count
  currentOrgNodeCount: number;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** QuotaUpdateRequest */
export interface QuotaUpdateRequest {
  // OpenAPI name: max_models
  maxModels?: any;
  // OpenAPI name: max_api_calls_per_day
  maxApiCallsPerDay?: any;
  // OpenAPI name: max_storage_mb
  maxStorageMb?: any;
  // OpenAPI name: max_users
  maxUsers?: any;
  // OpenAPI name: max_org_nodes
  maxOrgNodes?: any;
}

/** RUL预测点 */
export interface RulPredictionPointSchema {
  date: Date | string;
  // OpenAPI name: predicted_hi
  predictedHi: number;
  // OpenAPI name: lower_bound
  lowerBound: number;
  // OpenAPI name: upper_bound
  upperBound: number;
}

/** RUL预测请求 */
export interface RulPredictionRequest {
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 节点类型 bolt/flange */
  // OpenAPI name: node_type
  nodeType: string;
  /** 预测天数 */
  // OpenAPI name: forecast_days
  forecastDays?: number;
  /** 故障阈值 HI */
  // OpenAPI name: failure_threshold
  failureThreshold?: number;
  /** 预警阈值 HI */
  // OpenAPI name: warning_threshold
  warningThreshold?: number;
  /** 劣化模型类型，None则自动选择 */
  // OpenAPI name: model_type
  modelType?: any;
  /** 使用多少天历史数据 */
  // OpenAPI name: use_history_days
  useHistoryDays?: number;
}

/** RUL预测响应 */
export interface RulPredictionResponse {
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: node_type
  nodeType: string;
  // OpenAPI name: rul_data
  rulData: RulPredictionSchema;
  // OpenAPI name: calculate_time
  calculateTime: Date | string;
}

/** 剩余使用寿命预测 */
export interface RulPredictionSchema {
  // OpenAPI name: node_id
  nodeId: string;
  /** 节点类型 bolt/flange */
  // OpenAPI name: node_type
  nodeType: string;
  // OpenAPI name: current_hi
  currentHi: number;
  /** 预测剩余使用寿命（天） */
  // OpenAPI name: rul_days
  rulDays: number;
  /** RUL下限（天） */
  // OpenAPI name: rul_lower_bound
  rulLowerBound: number;
  /** RUL上限（天） */
  // OpenAPI name: rul_upper_bound
  rulUpperBound: number;
  /** RUL预测置信度 */
  // OpenAPI name: rul_confidence
  rulConfidence: number;
  /** 故障阈值 HI */
  // OpenAPI name: failure_threshold
  failureThreshold?: number;
  /** 预警阈值 HI */
  // OpenAPI name: warning_threshold
  warningThreshold?: number;
  /** 距离预警的天数 */
  // OpenAPI name: days_to_warning
  daysToWarning?: any;
  /** 历史HI序列 */
  // OpenAPI name: historical_hi
  historicalHi: Record<string, any>[];
  /** 预测序列 */
  // OpenAPI name: forecast_series
  forecastSeries: RulPredictionPointSchema[];
  /** 劣化模型类型 linear/exponential/polynomial */
  // OpenAPI name: degradation_model
  degradationModel: string;
  /** 模型参数 */
  // OpenAPI name: model_params
  modelParams: Record<string, any>;
  // OpenAPI name: prediction_date
  predictionDate: Date | string;
}

/** RateLimitStatusResponse */
export interface RateLimitStatusResponse {
  /** 密钥ID */
  // OpenAPI name: key_id
  keyId: string;
  /** 速率限制（请求/小时） */
  limit: number;
  /** 剩余请求次数 */
  remaining: number;
  /** 已使用请求次数 */
  used: number;
}

/** 修复建议 */
export interface RepairRecommendationSchema {
  // OpenAPI name: sensor_id
  sensorId: string;
  // OpenAPI name: problem_type
  problemType: string;
  description: string;
  recommendation: string;
  priority: string;
  // OpenAPI name: estimated_effort
  estimatedEffort: number;
  // OpenAPI name: affected_metrics
  affectedMetrics: string[];
  evidence: Record<string, any>;
}

/** 周期报告生成请求（周报/月报） */
export interface ReportGenerateRequest {
  /** 节点类型：bolt/flange */
  // OpenAPI name: node_type
  nodeType: string;
  /** 节点ID（螺栓ID或法兰面ID） */
  // OpenAPI name: node_id
  nodeId: string;
  /** 报告类型：weekly/monthly */
  // OpenAPI name: report_type
  reportType?: string;
  /** 是否使用LLM生成（默认True，不可用时自动降级） */
  // OpenAPI name: use_llm
  useLlm?: any;
}

/** 报告统计数据 */
export interface ReportStatisticsSchema {
  /** 预测次数 */
  // OpenAPI name: prediction_count
  predictionCount?: number;
  /** 平均风险评分 */
  // OpenAPI name: avg_risk_score
  avgRiskScore?: number;
  /** 最低风险评分（最高风险） */
  // OpenAPI name: min_risk_score
  minRiskScore?: number;
  /** 最高风险评分（最低风险） */
  // OpenAPI name: max_risk_score
  maxRiskScore?: number;
  /** 状态分布 */
  // OpenAPI name: status_distribution
  statusDistribution?: Record<string, number>;
  /** 整体趋势 */
  trend?: string;
  /** 周期内最高状态 */
  // OpenAPI name: max_status
  maxStatus?: string;
  /** 出现的故障类型 */
  // OpenAPI name: fault_types
  faultTypes?: string[];
}

/** 创建复测记录请求 */
export interface RetestRecordCreate {
  /** 关联工单ID */
  // OpenAPI name: work_order_id
  workOrderId: number;
  /** 复测时间 */
  // OpenAPI name: retest_time
  retestTime?: any;
  /** 复测人ID */
  // OpenAPI name: retester_id
  retesterId?: any;
  /** 复测人姓名 */
  // OpenAPI name: retester_name
  retesterName?: any;
  /** 复测结果 pass/fail/pending */
  // OpenAPI name: retest_result
  retestResult?: string;
  /** 复测测量值 */
  // OpenAPI name: measured_value
  measuredValue?: any;
  /** 复测数据点 时序数据 */
  // OpenAPI name: data_points
  dataPoints?: any;
  /** 复测前风险评分 */
  // OpenAPI name: before_risk_score
  beforeRiskScore?: any;
  /** 复测后风险评分 */
  // OpenAPI name: after_risk_score
  afterRiskScore?: any;
  /** 复测后状态 normal/warning/critical */
  // OpenAPI name: status_after_retest
  statusAfterRetest?: any;
  /** 复测置信度 */
  confidence?: any;
  /** 复测备注 */
  // OpenAPI name: retest_notes
  retestNotes?: any;
  /** 复测照片URL列表 */
  photos?: any;
  /** 扩展信息 */
  // OpenAPI name: extra_info
  extraInfo?: any;
  /** 是否自动再预测 */
  // OpenAPI name: auto_repredict
  autoRepredict?: any;
}

/** 复测记录列表响应 */
export interface RetestRecordListResponse {
  total: number;
  items: RetestRecordResponse[];
}

/** 复测记录响应 */
export interface RetestRecordResponse {
  id: number;
  // OpenAPI name: work_order_id
  workOrderId: number;
  // OpenAPI name: retest_time
  retestTime?: any;
  // OpenAPI name: retester_id
  retesterId?: any;
  // OpenAPI name: retester_name
  retesterName?: any;
  // OpenAPI name: retest_result
  retestResult?: any;
  // OpenAPI name: measured_value
  measuredValue?: any;
  // OpenAPI name: data_points
  dataPoints?: any;
  // OpenAPI name: before_risk_score
  beforeRiskScore?: any;
  // OpenAPI name: after_risk_score
  afterRiskScore?: any;
  // OpenAPI name: status_after_retest
  statusAfterRetest?: any;
  confidence?: any;
  // OpenAPI name: retest_notes
  retestNotes?: any;
  photos?: any;
  // OpenAPI name: extra_info
  extraInfo?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
}

/** 更新复测记录请求 */
export interface RetestRecordUpdate {
  // OpenAPI name: retest_time
  retestTime?: any;
  // OpenAPI name: retester_id
  retesterId?: any;
  // OpenAPI name: retester_name
  retesterName?: any;
  // OpenAPI name: retest_result
  retestResult?: any;
  // OpenAPI name: measured_value
  measuredValue?: any;
  // OpenAPI name: data_points
  dataPoints?: any;
  // OpenAPI name: before_risk_score
  beforeRiskScore?: any;
  // OpenAPI name: after_risk_score
  afterRiskScore?: any;
  // OpenAPI name: status_after_retest
  statusAfterRetest?: any;
  confidence?: any;
  // OpenAPI name: retest_notes
  retestNotes?: any;
  photos?: any;
  // OpenAPI name: extra_info
  extraInfo?: any;
}

/** RiskAssessExplainRequest */
export interface RiskAssessExplainRequest {
  /** 节点ID（螺栓或法兰面） */
  // OpenAPI name: node_id
  nodeId: string;
  /** 节点类型: bolt/flange */
  // OpenAPI name: node_type
  nodeType: string;
  /** 预紧力时序数据 */
  data: any[][];
}

/** RiskAssessExplainResponse */
export interface RiskAssessExplainResponse {
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: node_type
  nodeType: string;
  // OpenAPI name: risk_score
  riskScore: number;
  // OpenAPI name: risk_level
  riskLevel: string;
  // OpenAPI name: probability_distribution
  probabilityDistribution: RiskProbabilityDistributionSchema;
  // OpenAPI name: factor_contributions
  factorContributions: FactorContributionSchema[];
  /** 基准值（所有因子评分均值） */
  // OpenAPI name: base_value
  baseValue: number;
  /** 总贡献度偏移 */
  // OpenAPI name: total_contribution
  totalContribution: number;
  /** 可读性总结 */
  summary: string;
}

/** 风险评估请求 */
export interface RiskAssessmentRequest {
  /** 节点ID（螺栓或法兰面） */
  // OpenAPI name: node_id
  nodeId: string;
  /** 节点类型: bolt/flange */
  // OpenAPI name: node_type
  nodeType: string;
  /** 预紧力时序数据 */
  data: any[][];
}

/** 风险评估响应 */
export interface RiskAssessmentResponse {
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: node_type
  nodeType: string;
  // OpenAPI name: risk_score
  riskScore: number;
  // OpenAPI name: risk_level
  riskLevel: string;
  factors: string[];
  diagnosis: string;
  recommendations: string[];
  confidence: number;
  /** 风险概率分布 P(高/中/低) */
  // OpenAPI name: probability_distribution
  probabilityDistribution?: any;
  /** 各因子贡献度 */
  // OpenAPI name: factor_contributions
  factorContributions?: any;
}

/** RiskCalibrationResponse */
export interface RiskCalibrationResponse {
  // OpenAPI name: node_type
  nodeType: string;
  // OpenAPI name: node_id
  nodeId: string;
  // OpenAPI name: prior_weights
  priorWeights: Record<string, number>;
  // OpenAPI name: risk_thresholds
  riskThresholds: Record<string, any>;
  version?: number;
  // OpenAPI name: is_active
  isActive?: boolean;
  description?: any;
  // OpenAPI name: create_time
  createTime?: any;
}

/** RiskCalibrationUpdateRequest */
export interface RiskCalibrationUpdateRequest {
  /** 节点类型 bolt/flange/production_line */
  // OpenAPI name: node_type
  nodeType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 自定义权重覆盖 */
  // OpenAPI name: prior_weights
  priorWeights?: any;
  /** 自定义阈值覆盖 */
  // OpenAPI name: risk_thresholds
  riskThresholds?: any;
  /** 变更说明 */
  description?: any;
  /** 操作人ID */
  // OpenAPI name: operator_id
  operatorId?: any;
  /** 操作人姓名 */
  // OpenAPI name: operator_name
  operatorName?: any;
}

/** RiskProbabilityDistributionSchema */
export interface RiskProbabilityDistributionSchema {
  /** 高风险概率 */
  // OpenAPI name: p_high
  pHigh: number;
  /** 中风险概率 */
  // OpenAPI name: p_medium
  pMedium: number;
  /** 低风险概率 */
  // OpenAPI name: p_low
  pLow: number;
}

/** 根因分析结果 */
export interface RootCauseAnalysisSchema {
  // OpenAPI name: root_cause_bolt
  rootCauseBolt?: any;
  // OpenAPI name: root_cause_ranking
  rootCauseRanking: RootCauseBoltSchema[];
  // OpenAPI name: abnormal_bolts
  abnormalBolts: string[];
  // OpenAPI name: is_unbalanced_loosening
  isUnbalancedLoosening: boolean;
  // OpenAPI name: total_bolts
  totalBolts: number;
  // OpenAPI name: abnormal_count
  abnormalCount: number;
}

/** 根因螺栓信息 */
export interface RootCauseBoltSchema {
  // OpenAPI name: bolt_id
  boltId: string;
  index: number;
  // OpenAPI name: root_cause_score
  rootCauseScore: number;
  // OpenAPI name: status_code
  statusCode: number;
  // OpenAPI name: health_index
  healthIndex: number;
  // OpenAPI name: is_abnormal
  isAbnormal: boolean;
}

/** 规则违反详情 */
export interface RuleViolationSchema {
  // OpenAPI name: rule_type
  ruleType: string;
  // OpenAPI name: rule_name
  ruleName: string;
  severity: string;
  description: string;
  // OpenAPI name: violation_indices
  violationIndices: number[];
  // OpenAPI name: violation_values
  violationValues?: any;
  threshold?: any;
  // OpenAPI name: actual_value
  actualValue?: any;
}

/** 调度任务信息 */
export interface ScheduledJobSchema {
  /** 任务ID */
  id: string;
  /** 任务名称 */
  name: string;
  /** 是否启用 */
  enabled: boolean;
  /** Cron表达式 */
  cron: string;
  /** 下次执行时间 */
  // OpenAPI name: next_run
  nextRun?: any;
  /** 任务描述 */
  description?: any;
}

/** 调度任务更新请求 */
export interface SchedulerJobUpdateRequest {
  /** 是否启用 */
  enabled?: any;
  /** Cron表达式 */
  cron?: any;
}

/** 调度任务触发响应 */
export interface SchedulerTriggerResponse {
  /** 任务名称 */
  // OpenAPI name: job_name
  jobName: string;
  /** 状态: triggered/skipped */
  status: string;
  /** 消息 */
  message: string;
  /** 任务执行日志ID */
  // OpenAPI name: log_id
  logId?: any;
  /** 是否为Leader节点 */
  // OpenAPI name: is_leader
  isLeader?: any;
}

/** 传感器质量评分 */
export interface SensorQualityScoreSchema {
  // OpenAPI name: sensor_id
  sensorId: string;
  // OpenAPI name: overall_score
  overallScore: number;
  // OpenAPI name: overall_level
  overallLevel: string;
  dimensions: Record<string, QualityDimensionScoreSchema>;
  // OpenAPI name: valid_for_training
  validForTraining: boolean;
  // OpenAPI name: confidence_adjustment
  confidenceAdjustment: number;
  // OpenAPI name: rule_violations_count
  ruleViolationsCount: Record<string, number>;
  // OpenAPI name: calculate_time
  calculateTime: Date | string;
}

/** 策略审计日志列表响应 */
export interface StrategyAuditLogListResponse {
  total: number;
  items: StrategyAuditLogResponse[];
}

/** 策略审计日志响应 */
export interface StrategyAuditLogResponse {
  id: number;
  // OpenAPI name: config_id
  configId: number;
  scope: string;
  // OpenAPI name: node_type
  nodeType?: any;
  // OpenAPI name: node_id
  nodeId?: any;
  action: string;
  // OpenAPI name: old_value
  oldValue?: any;
  // OpenAPI name: new_value
  newValue?: any;
  // OpenAPI name: version_before
  versionBefore?: any;
  // OpenAPI name: version_after
  versionAfter?: any;
  // OpenAPI name: change_summary
  changeSummary?: any;
  // OpenAPI name: operator_id
  operatorId?: any;
  // OpenAPI name: operator_name
  operatorName?: any;
  // OpenAPI name: create_time
  createTime?: any;
}

/** 单条策略配置响应 */
export interface StrategyConfigItemResponse {
  id: number;
  scope?: string;
  // OpenAPI name: node_type
  nodeType?: any;
  // OpenAPI name: node_id
  nodeId?: any;
  // OpenAPI name: strategy_type
  strategyType: number;
  // OpenAPI name: confidence_threshold
  confidenceThreshold: number;
  // OpenAPI name: false_positive_threshold
  falsePositiveThreshold?: any;
  // OpenAPI name: false_negative_threshold
  falseNegativeThreshold?: any;
  version?: number;
  // OpenAPI name: is_active
  isActive?: boolean;
  description?: any;
  // OpenAPI name: operator_id
  operatorId?: any;
  // OpenAPI name: operator_name
  operatorName?: any;
  // OpenAPI name: create_time
  createTime?: any;
  // OpenAPI name: update_time
  updateTime?: any;
}

/** 策略配置列表响应 */
export interface StrategyConfigListResponse {
  total: number;
  items: StrategyConfigItemResponse[];
}

/** 预警策略动态配置更新请求 */
export interface StrategyConfigUpdateRequest {
  /** 作用域: global/bolt/flange/production_line */
  scope?: string;
  /** 节点类型 bolt/flange/production_line，scope非global时必填 */
  // OpenAPI name: node_type
  nodeType?: any;
  /** 节点ID，scope非global时必填 */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 策略类型: 1=应报尽报, 2=精准报警 */
  // OpenAPI name: strategy_type
  strategyType: number;
  /** 置信度阈值 */
  // OpenAPI name: confidence_threshold
  confidenceThreshold?: any;
  /** 误报容忍度 */
  // OpenAPI name: false_positive_threshold
  falsePositiveThreshold?: any;
  /** 漏报容忍度 */
  // OpenAPI name: false_negative_threshold
  falseNegativeThreshold?: any;
  /** 变更说明 */
  description?: any;
  /** 操作人ID */
  // OpenAPI name: operator_id
  operatorId?: any;
  /** 操作人姓名 */
  // OpenAPI name: operator_name
  operatorName?: any;
}

/** 删除节点级策略覆盖请求 */
export interface StrategyNodeOverrideDeleteRequest {
  /** 节点类型 bolt/flange/production_line */
  // OpenAPI name: node_type
  nodeType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 操作人ID */
  // OpenAPI name: operator_id
  operatorId?: any;
  /** 操作人姓名 */
  // OpenAPI name: operator_name
  operatorName?: any;
}

/** 策略回滚请求 */
export interface StrategyRollbackRequest {
  /** 回滚目标版本号 */
  // OpenAPI name: target_version
  targetVersion: number;
  /** 作用域 */
  scope?: string;
  /** 节点类型 */
  // OpenAPI name: node_type
  nodeType?: any;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 操作人ID */
  // OpenAPI name: operator_id
  operatorId?: any;
  /** 操作人姓名 */
  // OpenAPI name: operator_name
  operatorName?: any;
}

/** 批量流式数据注入请求 */
export interface StreamBatchIngestRequest {
  /** 消息列表，每个消息包含 node_type, node_id, value/timestamp 或 values/timestamps */
  messages: Record<string, any>[];
}

/** 批量流式数据注入响应 */
export interface StreamBatchIngestResponse {
  success: boolean;
  // OpenAPI name: total_count
  totalCount: number;
  // OpenAPI name: accepted_count
  acceptedCount: number;
  // OpenAPI name: rejected_count
  rejectedCount: number;
  messages?: Record<string, any>[];
}

/** 流式预测配置响应 */
export interface StreamConfigResponse {
  success: boolean;
  config: Record<string, any>;
  message: string;
}

/** 流式预测配置更新请求 */
export interface StreamConfigUpdateRequest {
  /** 窗口大小 */
  // OpenAPI name: window_size
  windowSize?: any;
  /** 最大并发流数 */
  // OpenAPI name: max_concurrent_streams
  maxConcurrentStreams?: any;
  /** 每个流的速率限制（每秒） */
  // OpenAPI name: rate_per_stream
  ratePerStream?: any;
}

/** 流式数据注入请求

支持单条或微批次数据注入 */
export interface StreamDataIngestRequest {
  /** 节点类型 bolt/flange */
  // OpenAPI name: node_type
  nodeType: string;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId: string;
  /** 单条预紧力值 */
  value?: any;
  /** 单条时间戳 */
  timestamp?: any;
  /** 批量预紧力值列表 */
  values?: any;
  /** 批量时间戳列表 */
  timestamps?: any;
  /** 时序数据 [[时间, 预紧力], ...] */
  data?: any;
  /** 元数据 */
  metadata?: any;
}

/** 流式数据注入响应 */
export interface StreamDataIngestResponse {
  success: boolean;
  message: string;
  // OpenAPI name: node_id
  nodeId?: any;
  // OpenAPI name: node_type
  nodeType?: any;
  // OpenAPI name: window_current_size
  windowCurrentSize?: any;
  // OpenAPI name: window_is_full
  windowIsFull?: any;
  accepted?: boolean;
}

/** 流式预测引擎状态响应 */
export interface StreamEngineStatusResponse {
  // OpenAPI name: is_running
  isRunning: boolean;
  mode: string;
  // OpenAPI name: active_streams
  activeStreams: number;
  // OpenAPI name: total_predictions
  totalPredictions: number;
  // OpenAPI name: status_changes
  statusChanges: number;
  // OpenAPI name: window_manager
  windowManager: Record<string, any>;
  backpressure: Record<string, any>;
  events: Record<string, any>;
  adapters: Record<string, any>[];
}

/** 流式预测模式切换请求 */
export interface StreamModeSwitchRequest {
  /** 预测模式: batch 或 stream */
  mode: string;
}

/** 流式预测模式切换响应 */
export interface StreamModeSwitchResponse {
  success: boolean;
  // OpenAPI name: current_mode
  currentMode: string;
  message: string;
}

/** 流式窗口状态响应 */
export interface StreamWindowStatusResponse {
  // OpenAPI name: bolt_id
  boltId: string;
  // OpenAPI name: window_size
  windowSize: number;
  // OpenAPI name: current_size
  currentSize: number;
  // OpenAPI name: is_full
  isFull: boolean;
  // OpenAPI name: last_updated
  lastUpdated?: any;
  // OpenAPI name: last_prediction_status
  lastPredictionStatus?: any;
  // OpenAPI name: prediction_count
  predictionCount?: any;
  // OpenAPI name: first_timestamp
  firstTimestamp?: any;
  // OpenAPI name: last_timestamp
  lastTimestamp?: any;
}

/** 温度耦合补偿信息

Attributes:
    applied: 是否执行了温度补偿
    temperature_coefficient: 估计的温度系数 α (kN/°C)
    correlation: 温度与预紧力的皮尔逊相关系数
    original_mean_preload: 补偿前平均预紧力
    compensated_mean_preload: 补偿后平均预紧力
    delta_t_mean: 平均温度波动 */
export interface TemperatureCompensationInfo {
  applied?: boolean;
  // OpenAPI name: temperature_coefficient
  temperatureCoefficient?: any;
  correlation?: any;
  // OpenAPI name: original_mean_preload
  originalMeanPreload?: any;
  // OpenAPI name: compensated_mean_preload
  compensatedMeanPreload?: any;
  // OpenAPI name: delta_t_mean
  deltaTMean?: any;
}

/** TenantAPIKeyCreateRequest */
export interface TenantApiKeyCreateRequest {
  /** 密钥名称 */
  // OpenAPI name: key_name
  keyName?: any;
  /** 权限列表 */
  permissions?: any;
  /** 速率限制 每分钟 */
  // OpenAPI name: rate_limit
  rateLimit?: number;
  /** 关联用户ID */
  // OpenAPI name: user_id
  userId?: any;
  /** 过期时间 */
  // OpenAPI name: expires_at
  expiresAt?: any;
}

/** TenantAPIKeyCreateResponse */
export interface TenantApiKeyCreateResponse {
  id: number;
  // OpenAPI name: tenant_id
  tenantId: number;
  // OpenAPI name: api_key
  apiKey: string;
  // OpenAPI name: key_name
  keyName?: any;
  permissions?: any;
  // OpenAPI name: rate_limit
  rateLimit: number;
  // OpenAPI name: user_id
  userId?: any;
  // OpenAPI name: expires_at
  expiresAt?: any;
  // OpenAPI name: last_used_at
  lastUsedAt?: any;
  status: string;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
  /** 明文密钥, 仅创建时返回一次 */
  // OpenAPI name: api_key_plain
  apiKeyPlain?: any;
}

/** TenantAPIKeyResponse */
export interface TenantApiKeyResponse {
  id: number;
  // OpenAPI name: tenant_id
  tenantId: number;
  // OpenAPI name: api_key
  apiKey: string;
  // OpenAPI name: key_name
  keyName?: any;
  permissions?: any;
  // OpenAPI name: rate_limit
  rateLimit: number;
  // OpenAPI name: user_id
  userId?: any;
  // OpenAPI name: expires_at
  expiresAt?: any;
  // OpenAPI name: last_used_at
  lastUsedAt?: any;
  status: string;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** TenantAPIKeyUpdateRequest */
export interface TenantApiKeyUpdateRequest {
  // OpenAPI name: key_name
  keyName?: any;
  permissions?: any;
  // OpenAPI name: rate_limit
  rateLimit?: any;
  /** 状态 active/revoked */
  status?: any;
  // OpenAPI name: expires_at
  expiresAt?: any;
}

/** TenantCreateRequest */
export interface TenantCreateRequest {
  /** 租户编码 */
  // OpenAPI name: tenant_code
  tenantCode: string;
  /** 租户名称 */
  // OpenAPI name: tenant_name
  tenantName: string;
  /** 联系邮箱 */
  // OpenAPI name: contact_email
  contactEmail?: any;
  /** 联系电话 */
  // OpenAPI name: contact_phone
  contactPhone?: any;
  /** 到期时间 */
  // OpenAPI name: expire_time
  expireTime?: any;
}

/** TenantListResponse */
export interface TenantListResponse {
  total: number;
  items: TenantResponse[];
}

/** TenantLoginRequest */
export interface TenantLoginRequest {
  /** 租户编码 */
  // OpenAPI name: tenant_code
  tenantCode: string;
  /** 用户名 */
  username: string;
  /** 密码 */
  password: string;
}

/** TenantLoginResponse */
export interface TenantLoginResponse {
  token: string;
  // OpenAPI name: tenant_id
  tenantId: number;
  // OpenAPI name: user_id
  userId: number;
  username: string;
  role: string;
  // OpenAPI name: expires_at
  expiresAt: Date | string;
}

/** TenantResponse */
export interface TenantResponse {
  id: number;
  // OpenAPI name: tenant_code
  tenantCode: string;
  // OpenAPI name: tenant_name
  tenantName: string;
  // OpenAPI name: contact_email
  contactEmail?: any;
  // OpenAPI name: contact_phone
  contactPhone?: any;
  status: string;
  settings?: any;
  // OpenAPI name: expire_time
  expireTime?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** TenantUpdateRequest */
export interface TenantUpdateRequest {
  // OpenAPI name: tenant_name
  tenantName?: any;
  // OpenAPI name: contact_email
  contactEmail?: any;
  // OpenAPI name: contact_phone
  contactPhone?: any;
  /** 状态 active/suspended/deleted */
  status?: any;
  // OpenAPI name: expire_time
  expireTime?: any;
  settings?: any;
}

/** TenantUserCreateRequest */
export interface TenantUserCreateRequest {
  /** 用户名 */
  username: string;
  /** 密码 */
  password: string;
  /** 显示名称 */
  // OpenAPI name: display_name
  displayName?: any;
  /** 邮箱 */
  email?: any;
  /** 手机号 */
  phone?: any;
  /** 角色 tenant_admin/admin/operator/viewer */
  role?: string;
  /** 关联组织节点ID */
  // OpenAPI name: org_node_id
  orgNodeId?: any;
}

/** TenantUserListResponse */
export interface TenantUserListResponse {
  total: number;
  items: TenantUserResponse[];
}

/** TenantUserPasswordRequest */
export interface TenantUserPasswordRequest {
  /** 新密码 */
  // OpenAPI name: new_password
  newPassword: string;
}

/** TenantUserResponse */
export interface TenantUserResponse {
  id: number;
  // OpenAPI name: tenant_id
  tenantId: number;
  username: string;
  // OpenAPI name: display_name
  displayName?: any;
  email?: any;
  phone?: any;
  role: string;
  // OpenAPI name: org_node_id
  orgNodeId?: any;
  status: string;
  // OpenAPI name: last_login_time
  lastLoginTime?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** TenantUserUpdateRequest */
export interface TenantUserUpdateRequest {
  // OpenAPI name: display_name
  displayName?: any;
  email?: any;
  phone?: any;
  /** 角色 tenant_admin/admin/operator/viewer */
  role?: any;
  // OpenAPI name: org_node_id
  orgNodeId?: any;
  /** 状态 active/disabled */
  status?: any;
}

/** 预警阈值配置 */
export interface ThresholdConfigSchema {
  /** 高风险阈值 */
  // OpenAPI name: high_risk_threshold
  highRiskThreshold?: number;
  /** 中风险阈值 */
  // OpenAPI name: medium_risk_threshold
  mediumRiskThreshold?: number;
  /** 正常预紧力最小值 */
  // OpenAPI name: min_normal_preload
  minNormalPreload?: number;
  /** 正常预紧力最大值 */
  // OpenAPI name: max_normal_preload
  maxNormalPreload?: number;
  /** 预警偏差比例 */
  // OpenAPI name: warning_deviation
  warningDeviation?: number;
  /** 紧急偏差比例 */
  // OpenAPI name: critical_deviation
  criticalDeviation?: number;
  /** 自动创建工单的最低告警级别 */
  // OpenAPI name: auto_create_work_order_level
  autoCreateWorkOrderLevel?: number;
  /** 默认未处理升级时间（分钟） */
  // OpenAPI name: default_upgrade_minutes
  defaultUpgradeMinutes?: number;
}

/** 完整训练配置 */
export interface TrainingConfigSchema {
  /** 总训练轮数 */
  epochs?: any;
  /** 批次大小 */
  // OpenAPI name: batch_size
  batchSize?: any;
  /** 初始学习率 */
  // OpenAPI name: learning_rate
  learningRate?: any;
  /** 验证集比例 */
  // OpenAPI name: validation_split
  validationSplit?: any;
  /** 早停配置 */
  // OpenAPI name: early_stopping
  earlyStopping?: any;
  /** 学习率调度配置 */
  // OpenAPI name: lr_scheduler
  lrScheduler?: any;
  /** 类别不平衡处理配置 */
  // OpenAPI name: class_imbalance
  classImbalance?: any;
  /** 增量训练配置 */
  incremental?: any;
  /** Focal Loss配置 */
  // OpenAPI name: focal_loss
  focalLoss?: any;
}

/** 模型训练请求 */
export interface TrainingRequest {
  /** 模型类型: bolt/flange */
  // OpenAPI name: model_type
  modelType: string;
  /** 节点ID，空则训练所有 */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 是否强制重新训练 */
  // OpenAPI name: force_retrain
  forceRetrain?: boolean;
}

/** 模型训练响应 */
export interface TrainingResponse {
  // OpenAPI name: model_type
  modelType: string;
  // OpenAPI name: node_id
  nodeId: any;
  status: string;
  message: string;
  // OpenAPI name: training_time
  trainingTime: number;
  metrics?: any;
}

/** 训练会话列表响应 */
export interface TrainingSessionListResponse {
  total: number;
  items: TrainingSessionSchema[];
}

/** 训练会话信息 */
export interface TrainingSessionSchema {
  // OpenAPI name: session_id
  sessionId: string;
  // OpenAPI name: model_id
  modelId: string;
  // OpenAPI name: model_type
  modelType: string;
  status: string;
  // OpenAPI name: start_time
  startTime?: any;
  // OpenAPI name: end_time
  endTime?: any;
  // OpenAPI name: total_epochs
  totalEpochs?: number;
  // OpenAPI name: current_epoch
  currentEpoch?: number;
  // OpenAPI name: best_metrics
  bestMetrics?: Record<string, number>;
  // OpenAPI name: metrics_history
  metricsHistory?: EpochMetricsSchema[];
  config?: Record<string, any>;
  // OpenAPI name: error_message
  errorMessage?: any;
}

/** 训练状态响应 */
export interface TrainingStatusResponse {
  // OpenAPI name: is_training
  isTraining: boolean;
  // OpenAPI name: current_session
  currentSession?: any;
  // OpenAPI name: recent_sessions
  recentSessions?: TrainingSessionSchema[];
}

/** 处置方案 */
export interface TreatmentPlanSchema {
  /** 方案名称 */
  // OpenAPI name: plan_name
  planName?: any;
  /** 处置步骤列表 */
  steps?: TreatmentStepSchema[];
  /** 所需材料 */
  materials?: any;
  /** 预估成本 */
  // OpenAPI name: estimated_cost
  estimatedCost?: any;
  /** 难度等级 easy/medium/hard */
  // OpenAPI name: difficulty_level
  difficultyLevel?: any;
  /** 所需人员 */
  // OpenAPI name: personnel_required
  personnelRequired?: any;
}

/** 处置步骤 */
export interface TreatmentStepSchema {
  /** 步骤序号 */
  // OpenAPI name: step_order
  stepOrder: number;
  /** 处置动作 */
  action: string;
  /** 详细描述 */
  description?: any;
  /** 所需工具 */
  tools?: any;
  /** 预计耗时（分钟） */
  // OpenAPI name: duration_minutes
  durationMinutes?: any;
  /** 安全注意事项 */
  // OpenAPI name: safety_notes
  safetyNotes?: any;
}

/** ValidationError */
export interface ValidationError {
  loc: any[];
  msg: string;
  type: string;
  input?: any;
  ctx?: Record<string, any>;
}

/** 预警策略配置 */
export interface WarningStrategyConfigSchema {
  /** 策略类型: 1=应报尽报, 2=精准报警 */
  // OpenAPI name: strategy_type
  strategyType: number;
  /** 策略1置信度阈值 */
  // OpenAPI name: strategy_1_confidence_threshold
  strategy1ConfidenceThreshold?: number;
  /** 策略1误报率阈值 */
  // OpenAPI name: strategy_1_false_positive_threshold
  strategy1FalsePositiveThreshold?: number;
  /** 策略2置信度阈值 */
  // OpenAPI name: strategy_2_confidence_threshold
  strategy2ConfidenceThreshold?: number;
  /** 策略2漏报率阈值 */
  // OpenAPI name: strategy_2_false_negative_threshold
  strategy2FalseNegativeThreshold?: number;
}

/** 指派工单请求 */
export interface WorkOrderAssignRequest {
  /** 处理人ID */
  // OpenAPI name: assignee_id
  assigneeId: string;
  /** 处理人姓名 */
  // OpenAPI name: assignee_name
  assigneeName: string;
  /** 指派人ID */
  // OpenAPI name: assigner_id
  assignerId?: any;
  /** 指派人姓名 */
  // OpenAPI name: assigner_name
  assignerName?: any;
}

/** 创建工单请求 */
export interface WorkOrderCreate {
  /** 工单标题 */
  title: string;
  /** 工单描述 */
  description?: any;
  /** 优先级 low/medium/high/urgent */
  priority?: string;
  /** 状态 open/assigned/in_progress/resolved/closed */
  status?: any;
  /** 节点类型 */
  // OpenAPI name: node_type
  nodeType?: any;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 告警级别 */
  // OpenAPI name: alert_level
  alertLevel?: any;
  /** 风险评分 */
  // OpenAPI name: risk_score
  riskScore?: any;
  /** 处理人ID */
  // OpenAPI name: assignee_id
  assigneeId?: any;
  /** 处理人姓名 */
  // OpenAPI name: assignee_name
  assigneeName?: any;
  /** 创建人ID */
  // OpenAPI name: creator_id
  creatorId?: any;
  /** 创建人姓名 */
  // OpenAPI name: creator_name
  creatorName?: any;
  /** 截止时间 */
  // OpenAPI name: due_time
  dueTime?: any;
  /** 推荐措施 */
  recommendations?: any;
  /** 扩展信息 */
  // OpenAPI name: extra_info
  extraInfo?: any;
  /** 多少小时后截止，due_time未设置时生效 */
  // OpenAPI name: due_hours
  dueHours?: any;
}

/** 工单列表响应 */
export interface WorkOrderListResponse {
  total: number;
  items: WorkOrderResponse[];
}

/** 解决工单请求 */
export interface WorkOrderResolveRequest {
  /** 解决备注 */
  // OpenAPI name: resolve_note
  resolveNote: string;
  /** 解决人ID */
  // OpenAPI name: resolver_id
  resolverId?: any;
  /** 解决人姓名 */
  // OpenAPI name: resolver_name
  resolverName?: any;
}

/** 工单响应 */
export interface WorkOrderResponse {
  /** 工单标题 */
  title: string;
  /** 工单描述 */
  description?: any;
  /** 优先级 low/medium/high/urgent */
  priority?: string;
  /** 状态 open/assigned/in_progress/resolved/closed */
  status?: any;
  /** 节点类型 */
  // OpenAPI name: node_type
  nodeType?: any;
  /** 节点ID */
  // OpenAPI name: node_id
  nodeId?: any;
  /** 告警级别 */
  // OpenAPI name: alert_level
  alertLevel?: any;
  /** 风险评分 */
  // OpenAPI name: risk_score
  riskScore?: any;
  /** 处理人ID */
  // OpenAPI name: assignee_id
  assigneeId?: any;
  /** 处理人姓名 */
  // OpenAPI name: assignee_name
  assigneeName?: any;
  /** 创建人ID */
  // OpenAPI name: creator_id
  creatorId?: any;
  /** 创建人姓名 */
  // OpenAPI name: creator_name
  creatorName?: any;
  /** 截止时间 */
  // OpenAPI name: due_time
  dueTime?: any;
  /** 推荐措施 */
  recommendations?: any;
  /** 扩展信息 */
  // OpenAPI name: extra_info
  extraInfo?: any;
  id: number;
  // OpenAPI name: order_no
  orderNo: string;
  // OpenAPI name: alert_id
  alertId?: any;
  // OpenAPI name: resolve_time
  resolveTime?: any;
  // OpenAPI name: resolve_note
  resolveNote?: any;
  // OpenAPI name: create_time
  createTime: Date | string;
  // OpenAPI name: update_time
  updateTime: Date | string;
}

/** 工单统计响应 */
export interface WorkOrderStatsResponse {
  /** 总工单数 */
  // OpenAPI name: total_work_orders
  totalWorkOrders?: number;
  /** 已关闭工单数 */
  // OpenAPI name: closed_work_orders
  closedWorkOrders?: number;
  /** 待处理工单数 */
  // OpenAPI name: open_work_orders
  openWorkOrders?: number;
  /** 处理中工单数 */
  // OpenAPI name: in_progress_work_orders
  inProgressWorkOrders?: number;
  /** 平均修复时间 MTTR 小时 */
  // OpenAPI name: mttr_hours
  mttrHours?: any;
  /** 平均修复时间 MTTR 分钟 */
  // OpenAPI name: mttr_minutes
  mttrMinutes?: any;
  /** 误报率 0-1 */
  // OpenAPI name: false_positive_rate
  falsePositiveRate?: any;
  /** 误报数量 */
  // OpenAPI name: false_positive_count
  falsePositiveCount?: number;
  /** 重复故障率 0-1 */
  // OpenAPI name: recurrence_rate
  recurrenceRate?: any;
  /** 重复故障数量 */
  // OpenAPI name: recurrence_count
  recurrenceCount?: number;
  /** 平均解决时间 小时 */
  // OpenAPI name: avg_resolve_hours
  avgResolveHours?: any;
  /** 按时完成率 0-1 */
  // OpenAPI name: on_time_completion_rate
  onTimeCompletionRate?: any;
  /** 优先级分布 */
  // OpenAPI name: priority_distribution
  priorityDistribution?: any;
  /** 状态分布 */
  // OpenAPI name: status_distribution
  statusDistribution?: any;
  /** 统计时间范围 */
  // OpenAPI name: time_range
  timeRange?: any;
}

/** 更新工单状态请求 */
export interface WorkOrderStatusUpdateRequest {
  /** 新状态 */
  status: string;
  /** 操作人ID */
  // OpenAPI name: operator_id
  operatorId?: any;
  /** 操作人姓名 */
  // OpenAPI name: operator_name
  operatorName?: any;
  /** 备注 */
  note?: any;
}

/** 更新工单请求 */
export interface WorkOrderUpdate {
  title?: any;
  description?: any;
  priority?: any;
  status?: any;
  // OpenAPI name: assignee_id
  assigneeId?: any;
  // OpenAPI name: assignee_name
  assigneeName?: any;
  // OpenAPI name: due_time
  dueTime?: any;
  recommendations?: any;
  // OpenAPI name: extra_info
  extraInfo?: any;
}

/** 工况信息 */
export interface WorkingConditionSchema {
  /** 环境温度 */
  temperature?: any;
  /** 系统压力 */
  pressure?: any;
  /** 环境湿度 */
  humidity?: any;
  /** 振动水平 */
  vibration?: any;
  /** 负载状况 light/medium/heavy/overload */
  // OpenAPI name: load_condition
  loadCondition?: any;
  /** 运行时长（小时） */
  // OpenAPI name: operating_hours
  operatingHours?: any;
  /** 维护周期 */
  // OpenAPI name: maintenance_cycle
  maintenanceCycle?: any;
  /** 上次维护日期 */
  // OpenAPI name: last_maintenance_date
  lastMaintenanceDate?: any;
  /** 设备使用年限 */
  // OpenAPI name: equipment_age
  equipmentAge?: any;
  /** 其他工况参数 */
  extra?: any;
}
