export enum StatusCode {
  NORMAL = 0,
  ATTENTION = 1,
  CHECK = 2,
  EMERGENCY = 3,
  FAULT = 4
}

export const StatusCodeMap: Record<StatusCode, string> = {
  [StatusCode.NORMAL]: '正常',
  [StatusCode.ATTENTION]: '关注级预警',
  [StatusCode.CHECK]: '检查级预警',
  [StatusCode.EMERGENCY]: '紧急级预警',
  [StatusCode.FAULT]: '故障'
}

export const StatusColorMap: Record<StatusCode, string> = {
  [StatusCode.NORMAL]: '#22c55e',
  [StatusCode.ATTENTION]: '#eab308',
  [StatusCode.CHECK]: '#f97316',
  [StatusCode.EMERGENCY]: '#ef4444',
  [StatusCode.FAULT]: '#7f1d1d'
}

export interface Bolt {
  bolt_id: string
  collector_id: string
  splitter_num: string
  position: string
  flange_id: string
  current_preload: number
  nominal_preload: number
  status_code: StatusCode
  confidence: number
  risk_score: number
  risk_level: 'low' | 'medium' | 'high'
  diagnosis: string
  recommendations: string[]
  last_update_time: string
  health_index?: number
}

export interface Flange {
  flange_id: string
  flange_name: string
  collector_id: string
  splitter_num: string
  position: string
  bolt_count: number
  status_code: StatusCode
  confidence: number
  risk_score: number
  risk_level: 'low' | 'medium' | 'high'
  diagnosis: string
  recommendations: string[]
  attention_weights?: number[]
  last_update_time: string
  health_index?: number
  worst_bolt_id?: string
  worst_bolt_hi?: number
}

export interface Collector {
  collector_id: string
  collector_name: string
  location: string
  status: 'online' | 'offline' | 'warning'
  last_heartbeat: string
  flange_count: number
  bolt_count: number
}

export interface Position {
  position: string
  collector_id: string
  collector_name: string
  flange_count: number
  bolt_count: number
}

export interface TopologyData {
  collectors: Collector[]
  flanges: Flange[]
  bolts: Bolt[]
  positions: Position[]
  stats: Statistics
  update_time: string
}

export interface Statistics {
  total_bolts: number
  total_flanges: number
  total_collectors: number
  status_distribution: Record<StatusCode, number>
  flange_status_distribution: Record<StatusCode, number>
  risk_distribution: {
    low: number
    medium: number
    high: number
  }
  online_collectors: number
  avg_health_index: number
}

export interface FilterOptions {
  collector_id: string | null
  position: string | null
  status_codes: StatusCode[]
}

// ==================== 预警相关类型 ====================

export type AlertStatus = 'pending' | 'processing' | 'resolved' | 'ignored' | 'closed'

export type AlertLevel = 1 | 2 | 3 | 4

export type AlertStrategy = 1 | 2

export const AlertLevelMap: Record<AlertLevel, string> = {
  1: '关注级',
  2: '检查级',
  3: '紧急级',
  4: '故障级'
}

export const AlertLevelColorMap: Record<AlertLevel, string> = {
  1: '#eab308',
  2: '#f97316',
  3: '#ef4444',
  4: '#7f1d1d'
}

export const AlertStatusMap: Record<AlertStatus, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  ignored: '已忽略',
  closed: '已关闭'
}

export const AlertStatusColorMap: Record<AlertStatus, string> = {
  pending: '#ef4444',
  processing: '#f97316',
  resolved: '#22c55e',
  ignored: '#64748b',
  closed: '#64748b'
}

export const AlertStrategyMap: Record<AlertStrategy, string> = {
  1: '应报尽报',
  2: '精准报警'
}

export interface AlertEvent {
  id: number
  alert_no: string
  rule_id: number | null
  alert_level: AlertLevel
  original_level: AlertLevel | null
  node_type: 'bolt' | 'flange' | null
  node_id: string | null
  title: string | null
  content: string | null
  confidence: number | null
  risk_score: number | null
  recommendations: string[]
  status: AlertStatus
  handler_id: string | null
  handler_name: string | null
  handle_time: string | null
  handle_note: string | null
  is_upgraded: boolean
  upgrade_count: number
  last_upgrade_time: string | null
  work_order_id: number | null
  source_prediction_id: number | null
  silence_until: string | null
  create_time: string
  update_time: string
  strategy_type?: AlertStrategy
}

export interface AlertListResponse {
  total: number
  items: AlertEvent[]
}

export interface AlertFilterOptions {
  status: AlertStatus | null
  alert_level: AlertLevel | null
  strategy_type: AlertStrategy | null
  node_type: 'bolt' | 'flange' | null
  start_time: string | null
  end_time: string | null
}

export interface AlertHandleRequest {
  action: 'acknowledge' | 'resolve' | 'ignore' | 'close'
  handler_id?: string
  handler_name?: string
  handle_note?: string
  silence_minutes?: number
}

export interface WorkOrder {
  id: number
  order_no: string
  alert_id: number | null
  title: string
  description: string | null
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: 'open' | 'assigned' | 'in_progress' | 'resolved' | 'closed'
  node_type: string | null
  node_id: string | null
  alert_level: number | null
  risk_score: number | null
  assignee_id: string | null
  assignee_name: string | null
  creator_id: string | null
  creator_name: string | null
  due_time: string | null
  resolve_time: string | null
  resolve_note: string | null
  recommendations: string[]
  create_time: string
  update_time: string
}

export interface WorkOrderAssignRequest {
  assignee_id: string
  assignee_name: string
  assigner_id?: string
  assigner_name?: string
}

export const WorkOrderPriorityMap: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  urgent: '紧急'
}

export const WorkOrderPriorityColorMap: Record<string, string> = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#f97316',
  urgent: '#ef4444'
}

export const WorkOrderStatusMap: Record<string, string> = {
  open: '待分配',
  assigned: '已分配',
  in_progress: '处理中',
  resolved: '已解决',
  closed: '已关闭'
}

export interface PreloadTrendPoint {
  timestamp: string
  value: number
}

export interface ProphetForecast {
  ds: string
  yhat: number
  yhat_lower: number
  yhat_upper: number
  trend: number
}

export interface StatusPrediction {
  timestamp: string
  predicted_status: StatusCode
  confidence: number
  risk_level: 'low' | 'medium' | 'high'
}

export interface TrendAnalysisData {
  bolt_id: string
  nominal_preload: number
  history: PreloadTrendPoint[]
  forecast: ProphetForecast[]
  status_predictions: StatusPrediction[]
}

// ==================== 模型管理相关类型 ====================

export type TrainingStatus = 'pending' | 'running' | 'completed' | 'failed' | 'stopped'

export const TrainingStatusMap: Record<TrainingStatus, string> = {
  pending: '等待中',
  running: '训练中',
  completed: '已完成',
  failed: '失败',
  stopped: '已停止'
}

export const TrainingStatusColorMap: Record<TrainingStatus, string> = {
  pending: '#eab308',
  running: '#3b82f6',
  completed: '#22c55e',
  failed: '#ef4444',
  stopped: '#64748b'
}

export interface EpochMetrics {
  epoch: number
  train_loss: number
  val_loss: number | null
  train_acc: number | null
  val_acc: number | null
  learning_rate: number | null
  duration_seconds: number
  timestamp: string
}

export interface TrainingSession {
  session_id: string
  model_id: string
  model_type: string
  status: TrainingStatus
  start_time: string | null
  end_time: string | null
  total_epochs: number
  current_epoch: number
  best_metrics: Record<string, number>
  metrics_history: EpochMetrics[]
  config: Record<string, unknown>
  error_message: string | null
}

export interface ModelVersion {
  version: string
  model_id: string
  model_type: string
  created_at: string
  file_path: string
  file_hash: string
  metrics: Record<string, number>
  config: Record<string, unknown>
  is_active: boolean
  description: string
}

export interface ModelEntry {
  model_id: string
  model_type: string
  display_name: string
  is_trained: boolean
  active_version: string | null
  total_versions: number
  last_training_time: string | null
  training_status: TrainingStatus | null
  best_val_acc: number | null
  description: string
}

export interface TrainingTriggerRequest {
  model_type: string
  model_id?: string | null
  force_retrain?: boolean
  epochs?: number
  learning_rate?: number
  batch_size?: number
}

export interface TrainingTriggerResponse {
  session_id: string
  model_type: string
  model_id: string | null
  status: TrainingStatus
  message: string
}

export interface VersionCompareResult {
  model_id: string
  version1: string
  version2: string
  metrics_comparison: Record<string, {
    v1: number
    v2: number
    diff: number
    improved: boolean
  }>
  config_diff: {
    v1: Record<string, unknown>
    v2: Record<string, unknown>
  }
}

export interface ModelVersionListResponse {
  model_id: string
  model_type: string
  versions: ModelVersion[]
}

export interface ModelVersionActivateRequest {
  version: string
}

export interface ModelVersionCompareRequest {
  version1: string
  version2: string
}

export interface ModelVersionCompareResponse extends VersionCompareResult {}

export interface TrainingSessionListResponse {
  total: number
  items: TrainingSession[]
}

export interface TrainingStatusResponse {
  is_training: boolean
  current_session: TrainingSession | null
  recent_sessions: TrainingSession[]
}

export interface ModelItem {
  model_id: string
  model_type: string
  version_count: number
  active_version: string | null
  latest_version: string
  latest_metrics: Record<string, number>
  last_updated: string
}

export interface ModelListResponse {
  total: number
  models: ModelItem[]
}

// ==================== 配置中心相关类型 ====================

export type AlertRuleStatus = 'active' | 'inactive' | 'draft'

export const AlertRuleStatusMap: Record<AlertRuleStatus, string> = {
  active: '已启用',
  inactive: '已停用',
  draft: '草稿'
}

export const AlertRuleStatusColorMap: Record<AlertRuleStatus, string> = {
  active: '#22c55e',
  inactive: '#64748b',
  draft: '#eab308'
}

export interface AlertRuleCondition {
  field: string
  operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'neq' | 'between'
  value: number | string
  value2?: number
}

export const ConditionOperatorMap: Record<string, string> = {
  gt: '大于',
  gte: '大于等于',
  lt: '小于',
  lte: '小于等于',
  eq: '等于',
  neq: '不等于',
  between: '介于'
}

export const ConditionFieldMap: Record<string, string> = {
  current_preload: '当前预紧力',
  nominal_preload: '标称预紧力',
  preload_ratio: '预紧力比率',
  risk_score: '风险评分',
  confidence: '置信度',
  health_index: '健康指数',
  status_code: '状态码'
}

export interface AlertRule {
  id: number
  name: string
  description: string
  strategy_type: AlertStrategy
  alert_level: AlertLevel
  conditions: AlertRuleCondition[]
  logic_operator: 'and' | 'or'
  node_type: 'bolt' | 'flange' | 'both'
  silence_minutes: number
  upgrade_enabled: boolean
  upgrade_interval_minutes: number
  status: AlertRuleStatus
  trigger_count: number
  last_trigger_time: string | null
  create_time: string
  update_time: string
}

export interface AlertRuleCreateRequest {
  name: string
  description?: string
  strategy_type: AlertStrategy
  alert_level: AlertLevel
  conditions: AlertRuleCondition[]
  logic_operator?: 'and' | 'or'
  node_type?: 'bolt' | 'flange' | 'both'
  silence_minutes?: number
  upgrade_enabled?: boolean
  upgrade_interval_minutes?: number
  status?: AlertRuleStatus
}

export interface AlertRuleUpdateRequest extends Partial<AlertRuleCreateRequest> {}

export interface ThresholdPreset {
  id: number
  name: string
  description: string
  is_default: boolean
  thresholds: ThresholdItem[]
  create_time: string
  update_time: string
}

export interface ThresholdItem {
  level: AlertLevel
  field: string
  operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq'
  value: number
  color: string
}

export interface ThresholdPresetCreateRequest {
  name: string
  description?: string
  is_default?: boolean
  thresholds: ThresholdItem[]
}

export interface ThresholdPresetUpdateRequest extends Partial<ThresholdPresetCreateRequest> {}

export type CronTaskStatus = 'running' | 'stopped' | 'error'

export const CronTaskStatusMap: Record<CronTaskStatus, string> = {
  running: '运行中',
  stopped: '已停止',
  error: '异常'
}

export const CronTaskStatusColorMap: Record<CronTaskStatus, string> = {
  running: '#22c55e',
  stopped: '#64748b',
  error: '#ef4444'
}

export interface CronTask {
  id: number
  name: string
  description: string
  task_type: 'data_collect' | 'model_train' | 'alert_check' | 'report_generate' | 'data_cleanup'
  cron_expression: string
  cron_human: string
  status: CronTaskStatus
  last_run_time: string | null
  next_run_time: string | null
  last_run_duration_ms: number | null
  run_count: number
  error_count: number
  last_error: string | null
  config: Record<string, unknown>
  create_time: string
  update_time: string
}

export const CronTaskTypeMap: Record<string, string> = {
  data_collect: '数据采集',
  model_train: '模型训练',
  alert_check: '预警检测',
  report_generate: '报告生成',
  data_cleanup: '数据清理'
}

export const CronTaskTypeColorMap: Record<string, string> = {
  data_collect: '#3b82f6',
  model_train: '#8b5cf6',
  alert_check: '#f97316',
  report_generate: '#22c55e',
  data_cleanup: '#64748b'
}

export interface CronTaskCreateRequest {
  name: string
  description?: string
  task_type: CronTask['task_type']
  cron_expression: string
  config?: Record<string, unknown>
}

export interface CronTaskUpdateRequest extends Partial<CronTaskCreateRequest> {}

export interface WarningStrategyConfig {
  strategy_type: AlertStrategy
  strategy_1_confidence_threshold: number
  strategy_1_false_positive_threshold: number
  strategy_2_confidence_threshold: number
  strategy_2_false_negative_threshold: number
}

export interface ThresholdConfig {
  high_risk_threshold: number
  medium_risk_threshold: number
  min_normal_preload: number
  max_normal_preload: number
  warning_deviation: number
  critical_deviation: number
  auto_create_work_order_level: AlertLevel
  default_upgrade_minutes: number
}

export interface ScheduledJob {
  id: string
  name: string
  enabled: boolean
  cron: string
  next_run: string | null
  description?: string
}

export interface SchedulerJobUpdateRequest {
  enabled?: boolean
  cron?: string
}

export interface ConfigCenterResponse {
  warning_strategy: WarningStrategyConfig
  thresholds: ThresholdConfig
  scheduled_jobs: ScheduledJob[]
  updated_at: string
}

// ==================== 权限与认证相关类型 ====================

export type UserRole = 'tenant_admin' | 'admin' | 'operator' | 'viewer' | 'anonymous' | 'api_key'

export type AuthMethod = 'token' | 'api_key' | 'none'

export const UserRoleMap: Record<UserRole, string> = {
  tenant_admin: '租户管理员',
  admin: '管理员',
  operator: '运维人员',
  viewer: '只读用户',
  anonymous: '匿名用户',
  api_key: 'API Key'
}

export const UserRoleColorMap: Record<UserRole, string> = {
  tenant_admin: '#ef4444',
  admin: '#8b5cf6',
  operator: '#3b82f6',
  viewer: '#64748b',
  anonymous: '#94a3b8',
  api_key: '#f97316'
}

export type Permission =
  | 'monitoring:read'
  | 'alert:read'
  | 'alert:write'
  | 'alert:handle'
  | 'trend:read'
  | 'model:read'
  | 'model:write'
  | 'model:train'
  | 'config:read'
  | 'config:write'
  | 'workorder:read'
  | 'workorder:write'
  | 'tenant:admin'
  | 'read'
  | 'write'
  | 'admin'
  | 'tenant_admin'

export interface CurrentUser {
  tenant_id: number | null
  tenant_code: string | null
  tenant_name: string | null
  user_id: number | null
  username: string | null
  display_name: string
  role: UserRole
  permissions: Permission[]
  auth_method: AuthMethod
  email: string | null
  phone: string | null
  org_node_id: number | null
  status: string | null
  last_login_time: string | null
}

export interface LoginRequest {
  tenant_code: string
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  tenant_id: number
  user_id: number
  username: string
  role: UserRole
  expires_at: string
}

export interface APIKeyLoginRequest {
  api_key: string
}

// 角色到视图的映射（哪些角色可以看到哪些导航页面）
export const RoleViewPermissions: Record<UserRole, Array<'monitoring' | 'alert' | 'trend' | 'model' | 'config'>> = {
  tenant_admin: ['monitoring', 'alert', 'trend', 'model', 'config'],
  admin: ['monitoring', 'alert', 'trend', 'model', 'config'],
  operator: ['monitoring', 'alert', 'trend', 'model'],
  viewer: ['monitoring', 'alert', 'trend'],
  anonymous: [],
  api_key: ['monitoring', 'alert', 'trend', 'model', 'config']
}

// 角色到权限的映射
export const RolePermissionMap: Record<UserRole, Permission[]> = {
  tenant_admin: ['read', 'write', 'admin', 'tenant_admin'],
  admin: ['read', 'write', 'admin'],
  operator: ['read', 'write'],
  viewer: ['read'],
  anonymous: [],
  api_key: ['read']
}
