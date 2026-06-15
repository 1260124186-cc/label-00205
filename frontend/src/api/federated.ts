import axios from 'axios'
import type {
  FederatedServerStatus,
  FederatedClientStatus,
  FederatedModelHistory,
  FederatedRoundStartRequest,
  FederatedRoundStartResponse,
  FederatedRoundAggregateRequest,
  FederatedRoundAggregateResponse,
  FederatedLocalTrainRequest,
  FederatedLocalTrainResponse,
  FederatedClient
} from '@/types'

const USE_MOCK = true

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

export async function fetchServerStatus(): Promise<FederatedServerStatus | null> {
  if (USE_MOCK) {
    return mockServerStatus()
  }
  try {
    const res = await api.get<FederatedServerStatus>('/federated/server/status')
    return res.data
  } catch (err) {
    console.error('获取服务器状态失败:', err)
    return null
  }
}

export async function registerClient(
  clientId: string,
  factoryName?: string,
  location?: string,
  clientInfo?: Record<string, any>
): Promise<boolean> {
  if (USE_MOCK) {
    return true
  }
  try {
    await api.post('/federated/client/register', {
      client_id: clientId,
      factory_name: factoryName,
      location,
      client_info: clientInfo
    })
    return true
  } catch (err) {
    console.error('注册客户端失败:', err)
    return false
  }
}

export async function fetchClientStatus(clientId: string): Promise<FederatedClientStatus | null> {
  if (USE_MOCK) {
    return mockClientStatus(clientId)
  }
  try {
    const res = await api.get<FederatedClientStatus>(`/federated/client/status/${clientId}`)
    return res.data
  } catch (err) {
    console.error('获取客户端状态失败:', err)
    return null
  }
}

export async function fetchModelHistory(
  modelType: string,
  nodeId: string
): Promise<FederatedModelHistory | null> {
  if (USE_MOCK) {
    return mockModelHistory(modelType, nodeId)
  }
  try {
    const res = await api.get<FederatedModelHistory>(
      `/federated/model/history/${modelType}/${nodeId}`
    )
    return res.data
  } catch (err) {
    console.error('获取模型历史失败:', err)
    return null
  }
}

export async function startRound(
  request: FederatedRoundStartRequest
): Promise<FederatedRoundStartResponse | null> {
  if (USE_MOCK) {
    return mockStartRound(request)
  }
  try {
    const res = await api.post<FederatedRoundStartResponse>(
      '/federated/round/start',
      request
    )
    return res.data
  } catch (err) {
    console.error('开始轮次失败:', err)
    return null
  }
}

export async function aggregateUpdates(
  request: FederatedRoundAggregateRequest
): Promise<FederatedRoundAggregateResponse | null> {
  if (USE_MOCK) {
    return mockAggregateUpdates(request)
  }
  try {
    const res = await api.post<FederatedRoundAggregateResponse>(
      '/federated/round/aggregate',
      request
    )
    return res.data
  } catch (err) {
    console.error('聚合并更新失败:', err)
    return null
  }
}

export async function localTrain(
  request: FederatedLocalTrainRequest
): Promise<FederatedLocalTrainResponse | null> {
  if (USE_MOCK) {
    return mockLocalTrain(request)
  }
  try {
    const res = await api.post<FederatedLocalTrainResponse>(
      '/federated/client/train/local',
      request
    )
    return res.data
  } catch (err) {
    console.error('本地训练失败:', err)
    return null
  }
}

function mockServerStatus(): FederatedServerStatus {
  return {
    registered_clients: 5,
    active_clients: 4,
    total_rounds: 12,
    completed_rounds: 10,
    failed_rounds: 1,
    aggregation_strategy: 'weighted_avg',
    managed_models: ['bolt_B001', 'bolt_B002', 'flange_F001'],
    current_round: {
      round_id: 13,
      model_type: 'bolt',
      node_id: 'B001',
      status: 'waiting',
      start_time: new Date(Date.now() - 300000).toISOString(),
      expected_clients: ['factory_001', 'factory_002', 'factory_003', 'factory_004', 'factory_005'],
      received_updates: 3
    }
  }
}

function mockClientStatus(clientId: string): FederatedClientStatus {
  return {
    client_id: clientId,
    factory_id: clientId,
    model_type: 'bolt',
    node_id: 'B001',
    current_round: 12,
    has_global_model: true,
    has_local_model: true,
    training_count: 8,
    privacy_mechanism: 'none',
    update_type: 'difference',
    two_level_arch_enabled: true,
    last_update_time: new Date(Date.now() - 600000).toISOString()
  }
}

function mockModelHistory(modelType: string, nodeId: string): FederatedModelHistory {
  const history = []
  for (let i = 10; i >= 1; i--) {
    history.push({
      version: i,
      round_id: i,
      model_type: modelType,
      node_id: nodeId,
      created_at: new Date(Date.now() - i * 86400000).toISOString(),
      metrics: {
        avg_val_acc: 0.85 + Math.random() * 0.1,
        total_samples: 5000 + Math.floor(Math.random() * 2000),
        num_clients: 3 + Math.floor(Math.random() * 3)
      },
      num_clients: 3 + Math.floor(Math.random() * 3)
    })
  }
  return {
    model_type: modelType,
    node_id: nodeId,
    history
  }
}

function mockStartRound(
  request: FederatedRoundStartRequest
): FederatedRoundStartResponse {
  return {
    round_id: 14,
    model_type: request.model_type,
    node_id: request.node_id,
    status: 'waiting',
    expected_clients: request.expected_clients || ['factory_001', 'factory_002', 'factory_003'],
    started_at: new Date().toISOString()
  }
}

function mockAggregateUpdates(
  request: FederatedRoundAggregateRequest
): FederatedRoundAggregateResponse {
  return {
    round_id: 13,
    model_type: request.model_type,
    node_id: request.node_id,
    status: 'success',
    message: '聚合成功',
    num_clients_aggregated: 4,
    version: 11,
    metrics: {
      avg_val_acc: 0.92,
      total_samples: 8500
    },
    aggregated_at: new Date().toISOString()
  }
}

function mockLocalTrain(
  request: FederatedLocalTrainRequest
): FederatedLocalTrainResponse {
  return {
    client_id: request.client_id,
    model_type: request.model_type,
    node_id: request.node_id,
    status: 'success',
    message: '本地训练完成',
    num_samples: 1200,
    training_time: 45.5,
    metrics: {
      final_train_loss: 0.12,
      final_train_acc: 0.96,
      final_val_loss: 0.18,
      final_val_acc: 0.91
    }
  }
}
