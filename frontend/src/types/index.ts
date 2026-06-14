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
