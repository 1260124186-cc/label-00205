import axios from 'axios'
import type { TopologyData } from '@/types'
import { getMockTopology, refreshMockStatus } from '@/mock/data'

const USE_MOCK = true

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

let cachedData: TopologyData | null = null

export async function fetchTopology(forceRefresh = false): Promise<TopologyData> {
  if (USE_MOCK) {
    if (!cachedData || forceRefresh) {
      cachedData = getMockTopology()
    } else {
      cachedData = refreshMockStatus(cachedData)
    }
    return Promise.resolve(JSON.parse(JSON.stringify(cachedData)))
  }

  try {
    const res = await api.get<TopologyData>('/monitoring/topology')
    cachedData = res.data
    return res.data
  } catch (err) {
    console.error('获取拓扑数据失败，使用Mock数据:', err)
    if (!cachedData) cachedData = getMockTopology()
    return cachedData
  }
}

export async function fetchCollectors(): Promise<{ collector_id: string; collector_name: string }[]> {
  if (USE_MOCK) {
    const data = cachedData || getMockTopology()
    return data.collectors.map(c => ({
      collector_id: c.collector_id,
      collector_name: c.collector_name
    }))
  }
  try {
    const res = await api.get('/monitoring/collectors')
    return res.data
  } catch (err) {
    console.error(err)
    return []
  }
}

export async function fetchPositions(collectorId?: string): Promise<{ position: string; collector_id: string }[]> {
  if (USE_MOCK) {
    const data = cachedData || getMockTopology()
    return data.positions
      .filter(p => !collectorId || p.collector_id === collectorId)
      .map(p => ({ position: p.position, collector_id: p.collector_id }))
  }
  try {
    const res = await api.get('/monitoring/positions', { params: { collector_id: collectorId } })
    return res.data
  } catch (err) {
    console.error(err)
    return []
  }
}
