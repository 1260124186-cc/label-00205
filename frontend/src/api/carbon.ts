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

function deterministicHash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

const POSITION_ENERGY_MAP: Record<string, string> = {
  'A面': 'electricity',
  'B面': 'electricity',
  'C面': 'steam',
  'D面': 'natural_gas',
  'E面': 'electricity',
  '地锚': 'electricity',
  '法兰盘': 'steam',
  '弯头': 'natural_gas',
}

const LOCATION_TEMP_RANGE: Record<string, [number, number]> = {
  '主厂房东区': [28, 42],
  '主厂房西区': [35, 55],
}

function resolveAvgTemperature(collectorId: string, location: string): number {
  const range = LOCATION_TEMP_RANGE[location] || [25, 40]
  const hash = deterministicHash(collectorId + '_temp')
  return range[0] + (hash % 1000) / 1000 * (range[1] - range[0])
}

function resolveOperatingPressure(nominalPreload: number, boltId: string): number {
  const basePressure = Math.max(0.5, Math.min(5.0, nominalPreload / 200))
  const offset = (deterministicHash(boltId + '_press') % 100) / 100
  return Math.round((basePressure + offset * 0.5) * 100) / 100
}

function resolveServiceAge(
  nominalPreload: number,
  currentPreload: number,
  preloadHistory: number[]
): number {
  if (preloadHistory.length >= 3) {
    const recent = preloadHistory.slice(-3)
    const dropPerStep = (recent[0] - recent[recent.length - 1]) / recent.length
    if (dropPerStep > 0 && nominalPreload > 0) {
      const monthsFromRate = Math.round((1 - currentPreload / nominalPreload) / (dropPerStep / nominalPreload))
      return Math.max(1, Math.min(360, monthsFromRate))
    }
  }
  const totalDrop = nominalPreload - currentPreload
  if (totalDrop > 0 && nominalPreload > 0) {
    const dropRatio = totalDrop / nominalPreload
    return Math.max(1, Math.round(dropRatio / 0.005))
  }
  return 6
}

function resolveSealAge(serviceAgeMonths: number): number {
  return Math.round(serviceAgeMonths / 24 * 10) / 10
}

function resolveEnergySource(position: string): string {
  return POSITION_ENERGY_MAP[position] || 'electricity'
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
let cachedLocationMap: Map<string, string> | null = null

async function buildLocationMap(topology: TopologyData): Promise<Map<string, string>> {
  if (cachedLocationMap) return cachedLocationMap
  const map = new Map<string, string>()
  for (const collector of topology.collectors) {
    map.set(collector.collector_id, collector.location)
  }
  cachedLocationMap = map
  return map
}

export async function buildCarbonNodesFromTopology(
  forceRefresh = false
): Promise<CarbonNodeInput[]> {
  if (cachedNodes && !forceRefresh) {
    return cachedNodes
  }

  const topology: TopologyData = await fetchTopology(forceRefresh)
  const locationMap = await buildLocationMap(topology)
  const nodes: CarbonNodeInput[] = []

  const flangeMap = new Map<string, Flange>()
  for (const f of topology.flanges) {
    flangeMap.set(f.flange_id, f)
  }

  const boltNodePromises = topology.bolts.map(async (bolt: Bolt) => {
    let preloadHistory: number[] = []
    let timestamps: string[] | undefined

    try {
      const trendData = await fetchTrendAnalysis(bolt.bolt_id, bolt.nominal_preload)
      preloadHistory = trendData.history.map(p => p.value)
      timestamps = trendData.history.map(p => p.timestamp)
    } catch {
      preloadHistory = [bolt.nominal_preload, bolt.current_preload]
    }

    const flange = flangeMap.get(bolt.flange_id)
    const flangeName = flange?.flange_name || bolt.flange_id
    const hiScore = bolt.health_index ?? 70
    const location = locationMap.get(bolt.collector_id) || '主厂房东区'

    const serviceAge = resolveServiceAge(bolt.nominal_preload, bolt.current_preload, preloadHistory)
    const avgTemp = resolveAvgTemperature(bolt.collector_id, location)
    const pressure = resolveOperatingPressure(bolt.nominal_preload, bolt.bolt_id)

    const node: CarbonNodeInput = {
      node_id: bolt.bolt_id,
      node_type: 'bolt',
      node_name: `${flangeName}-${bolt.bolt_id}`,
      hi_score: Math.round(hiScore * 10) / 10,
      hi_level: hiScoreToLevel(hiScore),
      preload_history: preloadHistory.length >= 2
        ? preloadHistory
        : [bolt.nominal_preload, bolt.current_preload],
      timestamps: timestamps && timestamps.length >= 2 ? timestamps : undefined,
      service_age_months: serviceAge,
      avg_temperature: avgTemp,
      seal_age_years: resolveSealAge(serviceAge),
      operating_pressure_mpa: pressure,
      energy_source: resolveEnergySource(bolt.position),
    }
    return node
  })

  const flangeNodePromises = topology.flanges.map(async (flange: Flange) => {
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
    const location = locationMap.get(flange.collector_id) || '主厂房东区'

    const nominalRef = representativeBolt?.nominal_preload ?? 400
    const currentRef = representativeBolt?.current_preload ?? 380
    const serviceAge = resolveServiceAge(nominalRef, currentRef, preloadHistory)
    const avgTemp = resolveAvgTemperature(flange.collector_id, location)
    const pressure = resolveOperatingPressure(nominalRef, flange.flange_id)

    const node: CarbonNodeInput = {
      node_id: flange.flange_id,
      node_type: 'flange',
      node_name: flange.flange_name || flange.flange_id,
      hi_score: Math.round(hiScore * 10) / 10,
      hi_level: hiScoreToLevel(hiScore),
      preload_history: preloadHistory.length >= 2
        ? preloadHistory
        : [nominalRef, currentRef],
      timestamps: timestamps && timestamps.length >= 2 ? timestamps : undefined,
      service_age_months: serviceAge,
      avg_temperature: avgTemp,
      seal_age_years: resolveSealAge(serviceAge),
      operating_pressure_mpa: pressure,
      energy_source: resolveEnergySource(flange.position),
    }
    return node
  })

  const boltNodes = await Promise.all(boltNodePromises)
  const flangeNodes = await Promise.all(flangeNodePromises)

  nodes.push(...boltNodes)
  nodes.push(...flangeNodes)

  cachedNodes = nodes
  return nodes
}

export function invalidateCarbonNodesCache() {
  cachedNodes = null
  cachedLocationMap = null
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
