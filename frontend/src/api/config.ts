import axios from 'axios'
import type {
  AlertRule,
  AlertRuleCreateRequest,
  AlertRuleUpdateRequest,
  ThresholdPreset,
  ThresholdPresetCreateRequest,
  ThresholdPresetUpdateRequest,
  CronTask,
  CronTaskCreateRequest,
  CronTaskUpdateRequest,
  WarningStrategyConfig,
  ThresholdConfig,
  ScheduledJob,
  SchedulerJobUpdateRequest,
  ConfigCenterResponse
} from '@/types'
import {
  getMockAlertRules,
  mockCreateAlertRule,
  mockUpdateAlertRule,
  mockDeleteAlertRule,
  mockToggleAlertRule,
  getMockThresholdPresets,
  mockCreateThresholdPreset,
  mockUpdateThresholdPreset,
  mockDeleteThresholdPreset,
  mockSetDefaultPreset,
  getMockCronTasks,
  mockCreateCronTask,
  mockUpdateCronTask,
  mockDeleteCronTask,
  mockToggleCronTask,
  mockRunCronTaskNow
} from '@/mock/data'

const USE_MOCK = true

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000
})

export async function fetchAlertRules(): Promise<AlertRule[]> {
  if (USE_MOCK) {
    return Promise.resolve(getMockAlertRules())
  }
  try {
    const res = await api.get<AlertRule[]>('/config/alert-rules')
    return res.data
  } catch (err) {
    console.error('获取预警规则失败:', err)
    return []
  }
}

export async function createAlertRule(data: AlertRuleCreateRequest): Promise<AlertRule | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockCreateAlertRule(data))
  }
  try {
    const res = await api.post<AlertRule>('/config/alert-rules', data)
    return res.data
  } catch (err) {
    console.error('创建预警规则失败:', err)
    return null
  }
}

export async function updateAlertRule(id: number, data: AlertRuleUpdateRequest): Promise<AlertRule | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockUpdateAlertRule(id, data))
  }
  try {
    const res = await api.put<AlertRule>(`/config/alert-rules/${id}`, data)
    return res.data
  } catch (err) {
    console.error('更新预警规则失败:', err)
    return null
  }
}

export async function deleteAlertRule(id: number): Promise<boolean> {
  if (USE_MOCK) {
    return Promise.resolve(mockDeleteAlertRule(id))
  }
  try {
    await api.delete(`/config/alert-rules/${id}`)
    return true
  } catch (err) {
    console.error('删除预警规则失败:', err)
    return false
  }
}

export async function toggleAlertRule(id: number): Promise<AlertRule | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockToggleAlertRule(id))
  }
  try {
    const res = await api.post<AlertRule>(`/config/alert-rules/${id}/toggle`)
    return res.data
  } catch (err) {
    console.error('切换预警规则状态失败:', err)
    return null
  }
}

export async function fetchThresholdPresets(): Promise<ThresholdPreset[]> {
  if (USE_MOCK) {
    return Promise.resolve(getMockThresholdPresets())
  }
  try {
    const res = await api.get<ThresholdPreset[]>('/config/threshold-presets')
    return res.data
  } catch (err) {
    console.error('获取阈值预设失败:', err)
    return []
  }
}

export async function createThresholdPreset(data: ThresholdPresetCreateRequest): Promise<ThresholdPreset | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockCreateThresholdPreset(data))
  }
  try {
    const res = await api.post<ThresholdPreset>('/config/threshold-presets', data)
    return res.data
  } catch (err) {
    console.error('创建阈值预设失败:', err)
    return null
  }
}

export async function updateThresholdPreset(id: number, data: ThresholdPresetUpdateRequest): Promise<ThresholdPreset | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockUpdateThresholdPreset(id, data))
  }
  try {
    const res = await api.put<ThresholdPreset>(`/config/threshold-presets/${id}`, data)
    return res.data
  } catch (err) {
    console.error('更新阈值预设失败:', err)
    return null
  }
}

export async function deleteThresholdPreset(id: number): Promise<boolean> {
  if (USE_MOCK) {
    return Promise.resolve(mockDeleteThresholdPreset(id))
  }
  try {
    await api.delete(`/config/threshold-presets/${id}`)
    return true
  } catch (err) {
    console.error('删除阈值预设失败:', err)
    return false
  }
}

export async function setDefaultPreset(id: number): Promise<ThresholdPreset | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockSetDefaultPreset(id))
  }
  try {
    const res = await api.post<ThresholdPreset>(`/config/threshold-presets/${id}/set-default`)
    return res.data
  } catch (err) {
    console.error('设置默认阈值方案失败:', err)
    return null
  }
}

export async function fetchCronTasks(): Promise<CronTask[]> {
  if (USE_MOCK) {
    return Promise.resolve(getMockCronTasks())
  }
  try {
    const res = await api.get<CronTask[]>('/config/cron-tasks')
    return res.data
  } catch (err) {
    console.error('获取Cron任务失败:', err)
    return []
  }
}

export async function createCronTask(data: CronTaskCreateRequest): Promise<CronTask | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockCreateCronTask(data))
  }
  try {
    const res = await api.post<CronTask>('/config/cron-tasks', data)
    return res.data
  } catch (err) {
    console.error('创建Cron任务失败:', err)
    return null
  }
}

export async function updateCronTask(id: number, data: CronTaskUpdateRequest): Promise<CronTask | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockUpdateCronTask(id, data))
  }
  try {
    const res = await api.put<CronTask>(`/config/cron-tasks/${id}`, data)
    return res.data
  } catch (err) {
    console.error('更新Cron任务失败:', err)
    return null
  }
}

export async function deleteCronTask(id: number): Promise<boolean> {
  if (USE_MOCK) {
    return Promise.resolve(mockDeleteCronTask(id))
  }
  try {
    await api.delete(`/config/cron-tasks/${id}`)
    return true
  } catch (err) {
    console.error('删除Cron任务失败:', err)
    return false
  }
}

export async function toggleCronTask(id: number): Promise<CronTask | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockToggleCronTask(id))
  }
  try {
    const res = await api.post<CronTask>(`/config/cron-tasks/${id}/toggle`)
    return res.data
  } catch (err) {
    console.error('切换Cron任务状态失败:', err)
    return null
  }
}

export async function runCronTaskNow(id: number): Promise<CronTask | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockRunCronTaskNow(id))
  }
  try {
    const res = await api.post<CronTask>(`/config/cron-tasks/${id}/run`)
    return res.data
  } catch (err) {
    console.error('立即执行Cron任务失败:', err)
    return null
  }
}

// ==================== 配置中心 Mock 数据 ====================

function getMockConfigCenter(): ConfigCenterResponse {
  return {
    warning_strategy: {
      strategy_type: 1,
      strategy_1_confidence_threshold: 0.7,
      strategy_1_false_positive_threshold: 0.05,
      strategy_2_confidence_threshold: 0.95,
      strategy_2_false_negative_threshold: 0.10
    },
    thresholds: {
      high_risk_threshold: 3,
      medium_risk_threshold: 7,
      min_normal_preload: 400,
      max_normal_preload: 800,
      warning_deviation: 0.1,
      critical_deviation: 0.2,
      auto_create_work_order_level: 3,
      default_upgrade_minutes: 30
    },
    scheduled_jobs: [
      {
        id: 'training_job',
        name: '模型训练任务',
        enabled: true,
        cron: '0 2 * * 0',
        next_run: new Date(Date.now() + 86400000).toISOString(),
        description: '每周日凌晨2点自动执行模型训练'
      },
      {
        id: 'prediction_job',
        name: '实时预测任务',
        enabled: true,
        cron: '*/5 * * * *',
        next_run: new Date(Date.now() + 300000).toISOString(),
        description: '每5分钟执行一次实时状态预测'
      },
      {
        id: 'monthly_prediction_job',
        name: '月度趋势预测',
        enabled: true,
        cron: '0 3 1 * *',
        next_run: new Date(Date.now() + 2592000000).toISOString(),
        description: '每月1日凌晨3点生成月度趋势预测报告'
      },
      {
        id: 'alert_upgrade_job',
        name: '告警升级检查',
        enabled: true,
        cron: '*/10 * * * *',
        next_run: new Date(Date.now() + 600000).toISOString(),
        description: '每10分钟检查超时未处理告警并自动升级'
      },
      {
        id: 'audit_cleanup_job',
        name: '审计日志清理',
        enabled: false,
        cron: '0 4 * * *',
        next_run: null,
        description: '每日凌晨4点清理超过90天的审计日志'
      }
    ],
    updated_at: new Date().toISOString()
  }
}

// ==================== 配置中心 API ====================

export async function fetchConfigCenter(): Promise<ConfigCenterResponse> {
  if (USE_MOCK) {
    return Promise.resolve(getMockConfigCenter())
  }
  try {
    const res = await api.get<ConfigCenterResponse>('/config/center')
    return res.data
  } catch (err) {
    console.error('获取配置中心数据失败:', err)
    return getMockConfigCenter()
  }
}

export async function updateWarningStrategy(data: WarningStrategyConfig): Promise<WarningStrategyConfig | null> {
  if (USE_MOCK) {
    return Promise.resolve({ ...data })
  }
  try {
    const res = await api.put<WarningStrategyConfig>('/config/warning-strategy', data)
    return res.data
  } catch (err) {
    console.error('更新预警策略配置失败:', err)
    return null
  }
}

export async function updateThresholds(data: ThresholdConfig): Promise<ThresholdConfig | null> {
  if (USE_MOCK) {
    return Promise.resolve({ ...data })
  }
  try {
    const res = await api.put<ThresholdConfig>('/config/thresholds', data)
    return res.data
  } catch (err) {
    console.error('更新阈值配置失败:', err)
    return null
  }
}

export async function fetchScheduledJobs(): Promise<ScheduledJob[]> {
  if (USE_MOCK) {
    return Promise.resolve(getMockConfigCenter().scheduled_jobs)
  }
  try {
    const res = await api.get<ScheduledJob[]>('/config/scheduler/jobs')
    return res.data
  } catch (err) {
    console.error('获取调度任务列表失败:', err)
    return []
  }
}

export async function updateSchedulerJob(jobId: string, data: SchedulerJobUpdateRequest): Promise<ScheduledJob | null> {
  if (USE_MOCK) {
    const mock = getMockConfigCenter()
    const job = mock.scheduled_jobs.find(j => j.id === jobId)
    if (job) {
      return Promise.resolve({ ...job, ...data, next_run: data.enabled ? new Date(Date.now() + 300000).toISOString() : null })
    }
    return Promise.resolve(null)
  }
  try {
    const res = await api.put<ScheduledJob>(`/config/scheduler/jobs/${jobId}`, data)
    return res.data
  } catch (err) {
    console.error('更新调度任务失败:', err)
    return null
  }
}

export async function triggerSchedulerJob(jobId: string): Promise<boolean> {
  if (USE_MOCK) {
    return Promise.resolve(true)
  }
  try {
    await api.post(`/config/scheduler/jobs/${jobId}/trigger`)
    return true
  } catch (err) {
    console.error('触发调度任务失败:', err)
    return false
  }
}
