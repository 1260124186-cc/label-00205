import axios from 'axios'
import type {
  CarbonMonthlyRankingRequest,
  CarbonMonthlyRankingResponse,
  CarbonRiskItem,
  HICarbonDualViewRequest,
  HICarbonDualViewResponse,
  HICarbonDualItem,
  ESGReportExportRequest,
  ESGReportFragmentResponse,
  CarbonModelConfigResponse,
  CarbonModelConfigUpdateRequest,
  CarbonRiskLevel,
  HILevel,
  DegradationTrend,
  CarbonTrend,
} from '@/types'
import {
  CarbonRiskLevelMap,
  HILevelMap,
} from '@/types'

const USE_MOCK = true

const api = axios.create({
  baseURL: '/api',
  timeout: 15000
})

const nodeNames = [
  '反应釜R-101', '换热器E-102', '压缩机C-103', '泵P-104', '塔T-105',
  '冷凝器E-201', '分离器V-202', '储罐TK-203', '再沸器E-301', '回流罐V-302',
  '高压法兰F-A01', '高压法兰F-A02', '中压法兰F-B01', '低压法兰F-C01',
  '关键螺栓组B-101', '关键螺栓组B-102',
]

function generateMockNodes(count: number): CarbonRiskItem[] {
  const items: CarbonRiskItem[] = []
  const riskLevels: CarbonRiskLevel[] = ['low', 'low', 'medium', 'medium', 'high', 'critical']
  const hiLevels: HILevel[] = ['excellent', 'good', 'good', 'fair', 'fair', 'poor', 'critical']
  const trends: DegradationTrend[] = ['stable', 'stable', 'gradual_decline', 'accelerating_decline', 'recovering']

  for (let i = 0; i < count; i++) {
    const hi_score = Math.max(30, Math.min(98, 85 - i * 3 + Math.random() * 8))
    const carbon_risk_score = Math.max(5, Math.min(95, 10 + i * 5 + Math.random() * 10))
    const risk_idx = Math.min(Math.floor(i / (count / 6)), 5)
    const hi_idx = Math.min(Math.floor(i / (count / 7)), 6)

    items.push({
      rank: i + 1,
      node_id: `DEV-${String(i + 1).padStart(3, '0')}`,
      node_type: i < 10 ? 'device' : i < 14 ? 'flange' : 'bolt',
      node_name: nodeNames[i % nodeNames.length],
      hi_score: Math.round(hi_score * 10) / 10,
      hi_level: hiLevels[hi_idx],
      carbon_risk_score: Math.round(carbon_risk_score * 10) / 10,
      carbon_risk_level: riskLevels[risk_idx],
      monthly_leakage_volume_m3: Math.round((0.001 + i * 0.005 + Math.random() * 0.003) * 10000) / 10000,
      monthly_carbon_increment_kg: Math.round((0.01 + i * 0.15 + Math.random() * 0.05) * 100) / 100,
      priority_score: Math.round((carbon_risk_score + (100 - hi_score) * 0.5) * 10) / 10,
      trend: trends[Math.floor(Math.random() * trends.length)],
      recommendations: generateMockRecommendations(carbon_risk_score, hi_score),
    })
  }
  return items.sort((a, b) => b.priority_score - a.priority_score).map((it, idx) => ({ ...it, rank: idx + 1 }))
}

function generateMockRecommendations(carbonScore: number, hiScore: number): string[] {
  const recs: string[] = []
  if (carbonScore >= 75) {
    recs.push('立即安排紧固或更换密封件，降低泄漏')
    recs.push('纳入本月ESG重点整改清单')
  } else if (carbonScore >= 50) {
    recs.push('近期安排检修，评估密封性能')
    recs.push('列入月度碳排减排计划')
  } else if (carbonScore >= 25) {
    recs.push('提高监测频率，关注劣化趋势')
    recs.push('纳入预防性维护计划')
  } else {
    recs.push('保持常规监测，暂无显著碳排风险')
  }
  if (hiScore < 50) {
    recs.push('健康指数偏低，建议综合检修')
  }
  return recs
}

function generateMockDualViews(count: number): HICarbonDualItem[] {
  const items: HICarbonDualItem[] = []
  const hiLevels: HILevel[] = ['excellent', 'good', 'fair', 'poor']
  const carbonLevels: CarbonRiskLevel[] = ['low', 'medium', 'high']
  const carbonTrends: CarbonTrend[] = ['stable', 'increasing', 'decreasing']
  const hiTrends = ['improving', 'stable', 'declining']

  for (let i = 0; i < count; i++) {
    const hi_score = Math.max(35, Math.min(95, 80 - i * 2.5 + Math.random() * 6))
    const carbon_kg = Math.round((0.005 + i * 0.08 + Math.random() * 0.03) * 100) / 100
    items.push({
      node_id: `DEV-${String(i + 1).padStart(3, '0')}`,
      node_type: i < 8 ? 'device' : 'flange',
      node_name: nodeNames[i % nodeNames.length],
      hi_score: Math.round(hi_score * 10) / 10,
      hi_level: hiLevels[Math.min(Math.floor(i / 4), 3)],
      hi_trend: hiTrends[Math.floor(Math.random() * hiTrends.length)],
      degradation_rate_per_month: Math.round((0.005 + i * 0.003 + Math.random() * 0.002) * 10000) / 10000,
      estimated_leakage_rate_m3_hour: Math.round((0.00001 + i * 0.00005 + Math.random() * 0.00002) * 100000) / 100000,
      monthly_carbon_increment_kg: carbon_kg,
      carbon_risk_level: carbonLevels[Math.min(Math.floor(i / 5), 2)],
      carbon_trend: carbonTrends[Math.floor(Math.random() * carbonTrends.length)],
    })
  }
  return items.sort((a, b) => b.monthly_carbon_increment_kg - a.monthly_carbon_increment_kg)
}

let cachedRanking: CarbonMonthlyRankingResponse | null = null
let cachedDualView: HICarbonDualViewResponse | null = null
let cachedConfig: CarbonModelConfigResponse | null = null

export async function fetchCarbonMonthlyRanking(
  request: CarbonMonthlyRankingRequest
): Promise<CarbonMonthlyRankingResponse> {
  if (USE_MOCK) {
    if (!cachedRanking) {
      const items = generateMockNodes(request.top_n || 12)
      const totalCarbon = items.reduce((s, i) => s + i.monthly_carbon_increment_kg, 0)
      const totalLeakage = items.reduce((s, i) => s + i.monthly_leakage_volume_m3, 0)
      const dist: Record<CarbonRiskLevel, number> = { low: 0, medium: 0, high: 0, critical: 0 }
      items.forEach(i => { dist[i.carbon_risk_level]++ })

      cachedRanking = {
        report_month: new Date().toISOString().slice(0, 7),
        total_nodes: items.length,
        total_monthly_carbon_increment_kg: Math.round(totalCarbon * 100) / 100,
        total_monthly_leakage_volume_m3: Math.round(totalLeakage * 10000) / 10000,
        risk_distribution: dist,
        ranked_items: items,
        generated_at: new Date().toISOString(),
      }
    }
    return Promise.resolve(JSON.parse(JSON.stringify(cachedRanking)))
  }

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
  if (USE_MOCK) {
    if (!cachedDualView) {
      const items = generateMockDualViews(10)
      cachedDualView = {
        report_month: new Date().toISOString().slice(0, 7),
        total_nodes: items.length,
        items,
        generated_at: new Date().toISOString(),
      }
    }
    return Promise.resolve(JSON.parse(JSON.stringify(cachedDualView)))
  }

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
  if (USE_MOCK) {
    const ranking = await fetchCarbonMonthlyRanking({ nodes: [], top_n: request.top_n || 10 })
    const totalCarbon = ranking.total_monthly_carbon_increment_kg
    const top5 = ranking.ranked_items.slice(0, 5)
    const top5Carbon = top5.reduce((s, i) => s + i.monthly_carbon_increment_kg, 0)
    const severity: '高' | '中' | '低' = totalCarbon > 3 ? '高' : totalCarbon > 1 ? '中' : '低'
    const declining = ranking.ranked_items.filter(i => i.trend === 'accelerating_decline' || i.trend === 'gradual_decline').length
    const improving = ranking.ranked_items.filter(i => i.trend === 'recovering').length
    const ratio = declining / ranking.total_nodes
    const observation = ratio > 0.5
      ? `${(ratio * 100).toFixed(0)}% 的装置呈劣化趋势，建议集中治理`
      : ratio > 0.2
      ? `${(ratio * 100).toFixed(0)}% 的装置呈劣化趋势，建议加强巡检`
      : '整体状况稳定，维持常规监测节奏'

    const recs: string[] = []
    if (ranking.risk_distribution.critical > 0) recs.push(`优先处理 ${ranking.risk_distribution.critical} 个碳排高风险装置`)
    if (ranking.risk_distribution.high > 0) recs.push(`对 ${ranking.risk_distribution.high} 个高风险装置安排月度检修`)
    if (top5Carbon / totalCarbon > 0.6) recs.push(`前5名贡献 ${(top5Carbon / totalCarbon * 100).toFixed(0)}% 碳排增量，建议重点治理`)
    recs.push('建立密封件全生命周期碳排台账')
    recs.push('将碳排风险纳入预防性维护决策指标')

    const methodology = (
      '本报告片段采用简化关联模型进行估算，不用于精确计量和合规申报。' +
      '方法: (1) 基于预紧力时序与工况因子估算压紧力劣化速率; ' +
      '(2) 通过有效压紧比、密封老化、介质压力估算泄漏率趋势; ' +
      '(3) 将泄漏量折算为压缩机补充能耗并通过排放因子(电力0.5839kgCO₂e/kWh等)换算碳排增量。' +
      '所有系数可配置，建议用于趋势分析与优先级排序。'
    )

    let csvContent: string | undefined
    if (request.format === 'csv') {
      csvContent = generateMockCSV(ranking.report_month, top5, observation, recs, methodology)
    }

    return Promise.resolve({
      report_period: ranking.report_month,
      generated_at: new Date().toISOString(),
      summary: {
        reporting_period: ranking.report_month,
        total_devices_analyzed: ranking.total_nodes,
        estimated_monthly_carbon_increment_kg: Math.round(totalCarbon * 100) / 100,
        estimated_monthly_carbon_increment_tons: Math.round(totalCarbon / 1000 * 10000) / 10000,
        estimated_monthly_leakage_m3: ranking.total_monthly_leakage_volume_m3,
        average_carbon_per_device_kg: Math.round(totalCarbon / ranking.total_nodes * 100) / 100,
        carbon_risk_severity: severity,
        top5_contribution_ratio: Math.round(top5Carbon / totalCarbon * 10000) / 10000,
        risk_distribution: ranking.risk_distribution,
      },
      top_risk_items: top5,
      trend_analysis: {
        overall_trend: ratio > 0.5 ? 'deteriorating' : improving / ranking.total_nodes > 0.3 ? 'improving' : 'stable',
        improving_count: improving,
        stable_count: ranking.ranked_items.filter(i => i.trend === 'stable').length,
        declining_count: declining,
        key_observation: observation,
      },
      recommendations: recs,
      methodology_note: request.include_methodology !== false ? methodology : undefined,
      csv_content: csvContent,
    })
  }

  try {
    const res = await api.post<ESGReportFragmentResponse>('/carbon/esg/export', request)
    return res.data
  } catch (err) {
    console.error('获取ESG报表片段失败:', err)
    throw err
  }
}

function generateMockCSV(
  period: string,
  top5: CarbonRiskItem[],
  observation: string,
  recs: string[],
  methodology: string
): string {
  const lines: string[] = []
  lines.push('# ESG 碳排风险报表片段')
  lines.push(`# 报告期,${period}`)
  lines.push(`# 生成时间,${new Date().toISOString()}`)
  lines.push('')
  lines.push('=== 汇总数据 ===')
  lines.push(`关键观察,${observation}`)
  lines.push('')
  lines.push('=== 碳排风险 TOP5 装置 ===')
  lines.push('排名,节点ID,节点名称,HI分数,HI等级,碳排风险分数,碳排风险等级,月度泄漏量(m3),月度碳排增量(kgCO2e)')
  top5.forEach((it, idx) => {
    lines.push([
      idx + 1,
      it.node_id,
      it.node_name,
      it.hi_score,
      HILevelMap[it.hi_level],
      it.carbon_risk_score,
      CarbonRiskLevelMap[it.carbon_risk_level],
      it.monthly_leakage_volume_m3.toFixed(4),
      it.monthly_carbon_increment_kg.toFixed(2),
    ].join(','))
  })
  lines.push('')
  lines.push('=== 建议措施 ===')
  recs.forEach(r => lines.push(r))
  lines.push('')
  lines.push('=== 方法学说明 ===')
  lines.push(methodology)
  return lines.join('\n')
}

export async function fetchCarbonModelConfig(): Promise<CarbonModelConfigResponse> {
  if (USE_MOCK) {
    if (!cachedConfig) {
      cachedConfig = {
        degradation: {
          nominal_preload: 600.0,
          min_effective_preload_ratio: 0.6,
          relaxation_rate_per_month: 0.015,
          temperature_acceleration_factor: 0.002,
          vibration_acceleration_factor: 0.003,
          cycle_acceleration_factor: 0.0001,
        },
        leakage: {
          base_leakage_rate_m3_per_hour: 0.0,
          critical_leakage_threshold: 0.05,
          preload_leakage_sensitivity: 2.5,
          seal_aging_factor_per_year: 0.08,
          pressure_sensitivity: 1.2,
        },
        energy_carbon: {
          energy_per_leakage_unit: 8.5,
          carbon_factor_electricity: 0.5839,
          carbon_factor_natural_gas: 2.1622,
          carbon_factor_steam: 0.11,
          compressor_efficiency: 0.75,
          recovery_rate: 0.0,
          base_monthly_energy_kwh: 10000.0,
          base_monthly_carbon_kg: 5839.0,
        },
      }
    }
    return Promise.resolve(JSON.parse(JSON.stringify(cachedConfig)))
  }

  try {
    const res = await api.get<CarbonModelConfigResponse>('/carbon/config')
    return res.data
  } catch (err) {
    console.error('获取碳排模型配置失败:', err)
    throw err
  }
}

export async function updateCarbonModelConfig(
  request: CarbonModelConfigUpdateRequest
): Promise<CarbonModelConfigResponse> {
  if (USE_MOCK) {
    cachedConfig = null
    return fetchCarbonModelConfig()
  }

  try {
    const res = await api.post<CarbonModelConfigResponse>('/carbon/config', request)
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
