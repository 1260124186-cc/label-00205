export interface WorkOrder {
  id: number
  order_no: string
  alert_id?: number
  title: string
  description?: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: 'open' | 'assigned' | 'in_progress' | 'resolved' | 'closed' | 'retested'
  node_type?: string
  node_id?: string
  alert_level?: number
  risk_score?: number
  assignee_id?: string
  assignee_name?: string
  creator_id?: string
  creator_name?: string
  due_time?: string
  resolve_time?: string
  resolve_note?: string
  recommendations?: string[]
  extra_info?: Record<string, any>
  create_time: string
  update_time: string
}

export interface WorkOrderListResponse {
  total: number
  items: WorkOrder[]
}

export interface WorkOrderFilterOptions {
  status?: string
  priority?: string
  node_type?: string
  assignee_id?: string
  start_time?: string
  end_time?: string
}

export interface RetestRecord {
  id: number
  work_order_id: number
  retest_time?: string
  retester_id?: string
  retester_name?: string
  retest_result: 'pass' | 'fail' | 'pending'
  measured_value?: number
  data_points?: any[][]
  before_risk_score?: number
  after_risk_score?: number
  status_after_retest?: 'normal' | 'warning' | 'critical'
  confidence?: number
  retest_notes?: string
  photos?: string[]
  voice_note?: string
  extra_info?: Record<string, any>
  create_time: string
}

export interface RetestRecordCreate {
  work_order_id: number
  retest_time?: string
  retester_id?: string
  retester_name?: string
  retest_result?: 'pass' | 'fail' | 'pending'
  measured_value?: number
  data_points?: any[][]
  before_risk_score?: number
  after_risk_score?: number
  status_after_retest?: string
  confidence?: number
  retest_notes?: string
  photos?: string[]
  extra_info?: Record<string, any>
  auto_repredict?: boolean
}

export interface RetestRecordListResponse {
  total: number
  items: RetestRecord[]
}

export interface AlertEvent {
  id: number
  title?: string
  content?: string
  alert_level: number
  status: 'pending' | 'processing' | 'resolved' | 'ignored' | 'closed'
  node_type?: string
  node_id?: string
  risk_score?: number
  strategy_type?: string
  handler_id?: string
  handler_name?: string
  handle_time?: string
  handle_note?: string
  work_order_id?: number
  silence_until?: string
  extra_info?: Record<string, any>
  create_time: string
  update_time: string
}

export interface AlertListResponse {
  total: number
  items: AlertEvent[]
}

export interface AlertFilterOptions {
  status?: string
  alert_level?: number
  node_type?: string
  strategy_type?: string
  start_time?: string
  end_time?: string
}

export interface OrgNodeInfo {
  node_id: string
  node_type: 'bolt' | 'flange' | 'production_line'
  node_name?: string
  parent_id?: string
  description?: string
  location?: string
  extra_info?: Record<string, any>
}

export interface PredictionCompare {
  id: number
  work_order_id: number
  retest_id?: number
  original_status?: string
  retest_status?: string
  original_risk_score?: number
  retest_risk_score?: number
  risk_change?: 'improved' | 'stable' | 'worsened'
  risk_delta?: number
  status_match?: boolean
  is_false_positive?: boolean
  is_recurring?: boolean
  comparison_detail?: Record<string, any>
  create_time: string
}

export interface UserInfo {
  id: string
  username: string
  name: string
  role: string
  tenant_id?: string
  tenant_name?: string
  permissions?: string[]
}

export interface OfflineQueueItem {
  id: string
  type: 'retest' | 'disposal' | 'photo' | 'voice'
  data: any
  status: 'pending' | 'uploading' | 'failed'
  retryCount: number
  createdAt: number
  error?: string
}

export interface ScanResult {
  org_node_id: string
  node_type: 'bolt' | 'flange'
  node_name?: string
  location?: string
}
