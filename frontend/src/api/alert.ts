import axios from 'axios'
import type {
  AlertEvent,
  AlertListResponse,
  AlertFilterOptions,
  AlertHandleRequest,
  WorkOrder,
  WorkOrderAssignRequest
} from '@/types'
import { generateMockAlerts } from '@/mock/data'

const USE_MOCK = true

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

let mockAlerts: AlertEvent[] | null = null

function getMockAlerts(): AlertEvent[] {
  if (!mockAlerts) {
    mockAlerts = generateMockAlerts()
  }
  return mockAlerts
}

export async function fetchAlertList(
  filters: AlertFilterOptions,
  page = 1,
  pageSize = 20
): Promise<AlertListResponse> {
  if (USE_MOCK) {
    let alerts = [...getMockAlerts()]

    if (filters.status) {
      alerts = alerts.filter(a => a.status === filters.status)
    }

    if (filters.alert_level) {
      alerts = alerts.filter(a => a.alert_level === filters.alert_level)
    }

    if (filters.strategy_type) {
      alerts = alerts.filter(a => a.strategy_type === filters.strategy_type)
    }

    if (filters.node_type) {
      alerts = alerts.filter(a => a.node_type === filters.node_type)
    }

    if (filters.start_time) {
      const start = new Date(filters.start_time).getTime()
      alerts = alerts.filter(a => new Date(a.create_time).getTime() >= start)
    }

    if (filters.end_time) {
      const end = new Date(filters.end_time).getTime()
      alerts = alerts.filter(a => new Date(a.create_time).getTime() <= end)
    }

    alerts.sort((a, b) => new Date(b.create_time).getTime() - new Date(a.create_time).getTime())

    const start = (page - 1) * pageSize
    const items = alerts.slice(start, start + pageSize)

    return {
      total: alerts.length,
      items: items
    }
  }

  try {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (page - 1) * pageSize
    }
    if (filters.status) params.status = filters.status
    if (filters.alert_level) params.alert_level = filters.alert_level
    if (filters.node_type) params.node_type = filters.node_type

    const res = await api.get<AlertListResponse>('/alert/events', { params })
    return res.data
  } catch (err) {
    console.error('获取预警列表失败:', err)
    return { total: 0, items: [] }
  }
}

export async function fetchAlertDetail(alertId: number): Promise<AlertEvent | null> {
  if (USE_MOCK) {
    const alerts = getMockAlerts()
    const alert = alerts.find(a => a.id === alertId)
    return alert || null
  }

  try {
    const res = await api.get<AlertEvent>(`/alert/events/${alertId}`)
    return res.data
  } catch (err) {
    console.error('获取预警详情失败:', err)
    return null
  }
}

export async function handleAlert(
  alertId: number,
  request: AlertHandleRequest
): Promise<AlertEvent | null> {
  if (USE_MOCK) {
    const alerts = getMockAlerts()
    const alert = alerts.find(a => a.id === alertId)
    if (!alert) return null

    if (request.action === 'acknowledge') {
      alert.status = 'processing'
      alert.handler_id = request.handler_id || 'current_user'
      alert.handler_name = request.handler_name || '当前用户'
      alert.handle_time = new Date().toISOString()
      alert.handle_note = request.handle_note || null
    } else if (request.action === 'resolve') {
      alert.status = 'resolved'
      alert.handler_id = request.handler_id || 'current_user'
      alert.handler_name = request.handler_name || '当前用户'
      alert.handle_time = new Date().toISOString()
      alert.handle_note = request.handle_note || null
    } else if (request.action === 'ignore') {
      alert.status = 'ignored'
      alert.handler_id = request.handler_id || 'current_user'
      alert.handler_name = request.handler_name || '当前用户'
      alert.handle_time = new Date().toISOString()
      alert.handle_note = request.handle_note || null
      if (request.silence_minutes) {
        const silenceUntil = new Date()
        silenceUntil.setMinutes(silenceUntil.getMinutes() + request.silence_minutes)
        alert.silence_until = silenceUntil.toISOString()
      }
    } else if (request.action === 'close') {
      alert.status = 'closed'
      alert.handle_time = new Date().toISOString()
      alert.handle_note = request.handle_note || null
    }

    alert.update_time = new Date().toISOString()
    return { ...alert }
  }

  try {
    const res = await api.post<AlertEvent>(`/alert/events/${alertId}/handle`, request)
    return res.data
  } catch (err) {
    console.error('处理预警失败:', err)
    return null
  }
}

export async function createWorkOrderFromAlert(
  alertId: number,
  assignee?: WorkOrderAssignRequest
): Promise<WorkOrder | null> {
  if (USE_MOCK) {
    const alerts = getMockAlerts()
    const alert = alerts.find(a => a.id === alertId)
    if (!alert) return null

    const workOrder: WorkOrder = {
      id: Date.now(),
      order_no: `WO${Date.now()}`,
      alert_id: alertId,
      title: alert.title || '预警工单',
      description: alert.content || '',
      priority: alert.alert_level >= 3 ? 'urgent' : alert.alert_level >= 2 ? 'high' : 'medium',
      status: assignee ? 'assigned' : 'open',
      node_type: alert.node_type,
      node_id: alert.node_id,
      alert_level: alert.alert_level,
      risk_score: alert.risk_score,
      assignee_id: assignee?.assignee_id || null,
      assignee_name: assignee?.assignee_name || null,
      creator_id: 'system',
      creator_name: '系统自动生成',
      due_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      resolve_time: null,
      resolve_note: null,
      recommendations: alert.recommendations,
      create_time: new Date().toISOString(),
      update_time: new Date().toISOString()
    }

    alert.work_order_id = workOrder.id
    alert.status = 'processing'
    alert.update_time = new Date().toISOString()

    return workOrder
  }

  try {
    const res = await api.post<WorkOrder>(`/alert/events/${alertId}/work-order`, assignee || {})
    return res.data
  } catch (err) {
    console.error('创建工单失败:', err)
    return null
  }
}

export async function fetchAlertStats(): Promise<{
  total: number
  pending: number
  processing: number
  resolved: number
  byLevel: Record<number, number>
}> {
  if (USE_MOCK) {
    const alerts = getMockAlerts()
    const pending = alerts.filter(a => a.status === 'pending').length
    const processing = alerts.filter(a => a.status === 'processing').length
    const resolved = alerts.filter(a => a.status === 'resolved' || a.status === 'closed').length

    const byLevel: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0 }
    for (const a of alerts) {
      if (a.status === 'pending' || a.status === 'processing') {
        byLevel[a.alert_level] = (byLevel[a.alert_level] || 0) + 1
      }
    }

    return {
      total: alerts.length,
      pending,
      processing,
      resolved,
      byLevel
    }
  }

  try {
    const res = await api.get('/alert/stats')
    return res.data
  } catch (err) {
    console.error('获取预警统计失败:', err)
    return { total: 0, pending: 0, processing: 0, resolved: 0, byLevel: {} }
  }
}
