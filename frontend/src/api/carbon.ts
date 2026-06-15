import axios from 'axios'
import type {
  CarbonMonthlyRankingRequest,
  CarbonMonthlyRankingResponse,
  HICarbonDualViewRequest,
  HICarbonDualViewResponse,
  ESGReportExportRequest,
  ESGReportFragmentResponse,
  CarbonModelConfigResponse,
  CarbonModelConfigUpdateRequest,
  Bolt,
  Flange,
  TopologyData,
  HILevel,
} from '@/types'
import { fetchTopology, fetchTrendAnalysis } from '@/api/monitoring'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000
})

function hiScoreToLevel(hi: number): HILevel {
  if (hi >= 85) return 'excellent'
  if (hi >= 70) return 'good'
  if (hi >= 50) return 'fair'
  if (hi >= 30) return 'poor'
  return 'critical'
}

export interface CarbonNodeInput {
  node_id: string
  node_type: string
  node_name: string
  hi_score: number
  hi_level: string
  preload_history: number[]
  timestamps?: string[]
  service_age_months?: number
  avg_temperature?: number
  seal_age_years?: number
  operating_pressure_mpa?: number
  energy_source?: string
}

let cachedNodes: CarbonNodeInput[] | null = null

export async function buildCarbonNodesFromTopology(
  forceRefresh = false
): Promise<CarbonNodeInput[]> {
  if (cachedNodes && !forceRefresh) {
    return cachedNodes
  }

  const topology: TopologyData = await fetchTopology(forceRefresh)
  const nodes: CarbonNodeInput[] = []

  const flangeMap = new Map<string, Flange>()
  for (const f of topology.flanges) {
    flangeMap.set(f.flange_id, f)
  }

  const boltNodePromises = topology.bolts.map(async (bolt: Bolt) => {
    try {
      const trendData = await fetchTrendAnalysis(bolt.bolt_id, bolt.nominal_preload)
      const preloadHistory = trendData.history.map(p => p.value)
      const timestamps = trendData.history.map(p => p.timestamp)

      const flange = flangeMap.get(bolt.flange_id)
      const flangeName = flange?.flange_name || bolt.flange_id

      const hiScore = bolt.health_index ?? 70
      const node: CarbonNodeInput = {
        node_id: bolt.bolt_id,
        node_type: 'bolt',
        node_name: `${flangeName}-${bolt.bolt_id}`,
        hi_score: Math.round(hiScore * 10) / 10,
        hi_level: hiScoreToLevel(hiScore),
        preload_history: preloadHistory.length >= 2
          ? preloadHistory
          : [bolt.nominal_preload, bolt.current_preload],
        timestamps: timestamps.length >= 2 ? timestamps : undefined,
        service_age_months: Math.max(0, Math.round((100 - hiScore) * 0.5)),
        avg_temperature: 25 + Math.random() * 15,
        seal_age_years: Math.max(0, (100 - hiScore) * 0.02),
        operating_pressure_mpa: 0.5 + Math.random() * 2.5,
        energy_source: 'electricity',
      }
      return node
    } catch (e) {
      console.warn(`构建螺栓 ${bolt.bolt_id} 碳排节点数据失败:`, e)
      const flange = flangeMap.get(bolt.flange_id)
      const flangeName = flange?.flange_name || bolt.flange_id
      const hiScore = bolt.health_index ?? 70
      const node: CarbonNodeInput = {
        node_id: bolt.bolt_id,
        node_type: 'bolt',
        node_name: `${flangeName}-${bolt.bolt_id}`,
        hi_score: Math.round(hiScore * 10) / 10,
        hi_level: hiScoreToLevel(hiScore),
        preload_history: [bolt.nominal_preload, bolt.current_preload],
        service_age_months: Math.max(0, Math.round((100 - hiScore) * 0.5)),
        avg_temperature: 30,
        seal_age_years: Math.max(0, (100 - hiScore) * 0.02),
        operating_pressure_mpa: 1.5,
        energy_source: 'electricity',
      }
      return node
    }
  })

  const flangeNodePromises = topology.flanges.map(async (flange: Flange) => {
    try {
      const representativeBolt = topology.bolts.find(b => b.flange_id === flange.flange_id)
      let preloadHistory: number[] = []
      let timestamps: string[] | undefined

      if (representativeBolt) {
        try {
          const trendData = await fetchTrendAnalysis(representativeBolt.bolt_id, representativeBolt.nominal_preload)
          preloadHistory = trendData.history.map(p => p.value)
          timestamps = trendData.history.map(p => p.timestamp)
        } catch {
          preloadHistory = [representativeBolt.nominal_preload, representativeBolt.current_preload]
        }
      }

      const hiScore = flange.health_index ?? 70
      const node: CarbonNodeInput = {
        node_id: flange.flange_id,
        node_type: 'flange',
        node_name: flange.flange_name || flange.flange_id,
        hi_score: Math.round(hiScore * 10) / 10,
        hi_level: hiScoreToLevel(hiScore),
        preload_history: preloadHistory.length >= 2
          ? preloadHistory
          : [400, 380],
        timestamps: timestamps?.length && timestamps.length >= 2 ? timestamps : undefined,
        service_age_months: Math.max(0, Math.round((100 - hiScore) * 0.6)),
        avg_temperature: 30 + Math.random() * 20,
        seal_age_years: Math.max(0, (100 - hiScore) * 0.03),
        operating_pressure_mpa: 1.0 + Math.random() * 3.0,
        energy_source: 'electricity',
      }
      return node
    } catch (e) {
      console.warn(`构建法兰 ${flange.flange_id} 碳排节点数据失败:`, e)
      const hiScore = flange.health_index ?? 70
      const node: CarbonNodeInput = {
        node_id: flange.flange_id,
        node_type: 'flange',
        node_name: flange.flange_name || flange.flange_id,
        hi_score: Math.round(hiScore * 10) / 10,
        hi_level: hiScoreToLevel(hiScore),
        preload_history: [400, 380],
        service_age_months: Math.max(0, Math.round((100 - hiScore) * 0.6)),
        avg_temperature: 35,
        seal_age_years: Math.max(0, (100 - hiScore) * 0.03),
        operating_pressure_mpa: 2.0,
        energy_source: 'electricity',
      }
      return node
    }
  })

  const boltNodes = await Promise.all(boltNodePromises)
  const flangeNodes = await Promise.all(flangeNodePromises)

  nodes.push(...boltNodes.filter((n): n is CarbonNodeInput => n !== null))
  nodes.push(...flangeNodes.filter((n): n is CarbonNodeInput => n !== null))

  cachedNodes = nodes
  return nodes
}

export function invalidateCarbonNodesCache() {
  cachedNodes = null
}

let cachedConfig: CarbonModelConfigResponse | null = null

export async function fetchCarbonMonthlyRanking(
  request: CarbonMonthlyRankingRequest
): Promise<CarbonMonthlyRankingResponse> {
  try {
    const res = await api.post<CarbonMonthlyRankingResponse>('/carbon/ranking/monthly', request)
    return res.data
  } catch (err) {
    console.error('获取碳排月度排行失败:', err)
    throw err
  }
}

export async function fetchHICarbonDualView(
  request: HICarbonDualViewRequest
): Promise<HICarbonDualViewResponse> {
  try {
    const res = await api.post<HICarbonDualViewResponse>('/carbon/hi-dual-view', request)
    return res.data
  } catch (err) {
    console.error('获取HI碳排并列视图失败:', err)
    throw err
  }
}

export async function fetchESGReport(
  request: ESGReportExportRequest
): Promise<ESGReportFragmentResponse> {
  try {
    const res = await api.post<ESGReportFragmentResponse>('/carbon/esg/export', request)
    return res.data
  } catch (err) {
    console.error('获取ESG报表片段失败:', err)
    throw err
  }
}

export async function fetchCarbonModelConfig(): Promise<CarbonModelConfigResponse> {
  if (cachedConfig) {
    return cachedConfig
  }
  try {
    const res = await api.get<CarbonModelConfigResponse>('/carbon/config')
    cachedConfig = res.data
    return res.data
  } catch (err) {
    console.error('获取碳排模型配置失败:', err)
    throw err
  }
}

export async function updateCarbonModelConfig(
  request: CarbonModelConfigUpdateRequest
): Promise<CarbonModelConfigResponse> {
  try {
    const res = await api.post<CarbonModelConfigResponse>('/carbon/config', request)
    cachedConfig = res.data
    return res.data
  } catch (err) {
    console.error('更新碳排模型配置失败:', err)
    throw err
  }
}

export function downloadCSV(csvContent: string, filename: string) {
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
