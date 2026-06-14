import axios from 'axios'
import type {
  ModelEntry,
  ModelVersion,
  TrainingSession,
  TrainingTriggerRequest,
  TrainingTriggerResponse,
  VersionCompareResult
} from '@/types'
import {
  generateMockModelEntries,
  getMockVersions,
  getMockSessions,
  mockActivateVersion,
  mockRollbackVersion,
  mockTriggerTraining,
  mockCompareVersions
} from '@/mock/data'

const USE_MOCK = true

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

export async function fetchModelList(): Promise<ModelEntry[]> {
  if (USE_MOCK) {
    return Promise.resolve(generateMockModelEntries())
  }
  try {
    const res = await api.get<ModelEntry[]>('/model/list')
    return res.data
  } catch (err) {
    console.error('获取模型列表失败:', err)
    return []
  }
}

export async function fetchModelVersions(modelId: string): Promise<ModelVersion[]> {
  if (USE_MOCK) {
    return Promise.resolve(getMockVersions(modelId))
  }
  try {
    const res = await api.get<ModelVersion[]>(`/model/versions/${modelId}`)
    return res.data
  } catch (err) {
    console.error('获取版本列表失败:', err)
    return []
  }
}

export async function fetchTrainingSessions(modelId: string): Promise<TrainingSession[]> {
  if (USE_MOCK) {
    return Promise.resolve(getMockSessions(modelId))
  }
  try {
    const res = await api.get<TrainingSession[]>(`/model/sessions/${modelId}`)
    return res.data
  } catch (err) {
    console.error('获取训练会话失败:', err)
    return []
  }
}

export async function triggerTraining(request: TrainingTriggerRequest): Promise<TrainingTriggerResponse> {
  if (USE_MOCK) {
    const session = mockTriggerTraining(request.model_type, request.model_id ?? null)
    return {
      session_id: session.session_id,
      model_type: session.model_type,
      model_id: session.model_id,
      status: session.status,
      message: '训练任务已启动'
    }
  }
  try {
    const res = await api.post<TrainingTriggerResponse>('/model/train', request)
    return res.data
  } catch (err) {
    console.error('触发训练失败:', err)
    throw err
  }
}

export async function activateVersion(modelId: string, version: string): Promise<ModelVersion | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockActivateVersion(modelId, version))
  }
  try {
    const res = await api.post<ModelVersion>(`/model/versions/${modelId}/activate`, { version })
    return res.data
  } catch (err) {
    console.error('激活版本失败:', err)
    return null
  }
}

export async function rollbackVersion(modelId: string, version: string): Promise<ModelVersion | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockRollbackVersion(modelId, version))
  }
  try {
    const res = await api.post<ModelVersion>(`/model/versions/${modelId}/rollback`, { version })
    return res.data
  } catch (err) {
    console.error('回滚版本失败:', err)
    return null
  }
}

export async function compareVersions(
  modelId: string,
  version1: string,
  version2: string
): Promise<VersionCompareResult | null> {
  if (USE_MOCK) {
    return Promise.resolve(mockCompareVersions(modelId, version1, version2))
  }
  try {
    const res = await api.get<VersionCompareResult>(`/model/versions/${modelId}/compare`, {
      params: { version1, version2 }
    })
    return res.data
  } catch (err) {
    console.error('版本比较失败:', err)
    return null
  }
}
