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
