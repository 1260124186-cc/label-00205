import axios from 'axios'
import type {
  WorkOrder,
  WorkOrderListResponse,
  WorkOrderFilterOptions,
  RetestRecord,
  RetestRecordCreate,
  RetestRecordListResponse,
  AlertEvent,
  AlertListResponse,
  AlertFilterOptions,
  PredictionCompare,
  OrgNodeInfo,
  UserInfo
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const apiKey = localStorage.getItem('api_key')
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_info')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export async function fetchWorkOrders(
  filters: WorkOrderFilterOptions = {},
  page = 1,
  pageSize = 20
): Promise<WorkOrderListResponse> {
  const params: Record<string, any> = {
    limit: pageSize,
    offset: (page - 1) * pageSize
  }
  if (filters.status) params.status = filters.status
  if (filters.priority) params.priority = filters.priority
  if (filters.node_type) params.node_type = filters.node_type
  if (filters.assignee_id) params.assignee_id = filters.assignee_id
  if (filters.start_time) params.start_time = filters.start_time
  if (filters.end_time) params.end_time = filters.end_time

  const res = await api.get<WorkOrderListResponse>('/work-orders', { params })
  return res.data
}

export async function fetchWorkOrderDetail(id: number): Promise<WorkOrder> {
  const res = await api.get<WorkOrder>(`/work-orders/${id}`)
  return res.data
}

export async function updateWorkOrderStatus(
  id: number,
  status: string,
  operatorId?: string,
  operatorName?: string,
  note?: string
): Promise<WorkOrder> {
  const res = await api.patch<WorkOrder>(`/work-orders/${id}/status`, {
    status,
    operator_id: operatorId,
    operator_name: operatorName,
    note
  })
  return res.data
}

export async function createRetestRecord(data: RetestRecordCreate): Promise<RetestRecord> {
  const res = await api.post<RetestRecord>('/work-orders/retests', data)
  return res.data
}

export async function fetchRetestRecords(
  workOrderId?: number,
  page = 1,
  pageSize = 20
): Promise<RetestRecordListResponse> {
  const params: Record<string, any> = {
    limit: pageSize,
    offset: (page - 1) * pageSize
  }
  if (workOrderId) params.work_order_id = workOrderId

  const res = await api.get<RetestRecordListResponse>('/work-orders/retests', { params })
  return res.data
}

export async function fetchRetestRecordDetail(id: number): Promise<RetestRecord> {
  const res = await api.get<RetestRecord>(`/work-orders/retests/${id}`)
  return res.data
}

export async function triggerRetestRepredict(id: number): Promise<PredictionCompare> {
  const res = await api.post<PredictionCompare>(`/work-orders/retests/${id}/repredict`)
  return res.data
}

export async function fetchAlerts(
  filters: AlertFilterOptions = {},
  page = 1,
  pageSize = 20
): Promise<AlertListResponse> {
  const params: Record<string, any> = {
    limit: pageSize,
    offset: (page - 1) * pageSize
  }
  if (filters.status) params.status = filters.status
  if (filters.alert_level) params.alert_level = filters.alert_level
  if (filters.node_type) params.node_type = filters.node_type
  if (filters.strategy_type) params.strategy_type = filters.strategy_type
  if (filters.start_time) params.start_time = filters.start_time
  if (filters.end_time) params.end_time = filters.end_time

  const res = await api.get<AlertListResponse>('/alert/events', { params })
  return res.data
}

export async function fetchAlertStats(): Promise<{
  total: number
  pending: number
  processing: number
  resolved: number
  byLevel: Record<number, number>
}> {
  const res = await api.get('/alert/stats')
  return res.data
}

export async function fetchOrgNodeInfo(nodeId: string): Promise<OrgNodeInfo> {
  const res = await api.get<OrgNodeInfo>(`/org/nodes/${nodeId}`)
  return res.data
}

export async function uploadFile(file: File, type: 'photo' | 'voice' = 'photo'): Promise<{ url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('type', type)

  const res = await api.post<{ url: string }>('/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return res.data
}

export async function loginWithApiKey(apiKey: string): Promise<UserInfo> {
  const res = await api.post<UserInfo>('/auth/api-key-login', { api_key: apiKey })
  return res.data
}

export async function fetchCurrentUser(): Promise<UserInfo> {
  const res = await api.get<UserInfo>('/auth/me')
  return res.data
}

export default api
