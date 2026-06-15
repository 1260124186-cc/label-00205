<template>
  <div class="carbon-analysis">
    <div class="ca-header">
      <div class="ca-title">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2v4"></path>
          <path d="M5 10l-1.9 6.7A2 2 0 005 19h14a2 2 0 001.9-2.3L19 10"></path>
          <path d="M8 10V7a4 4 0 018 0v3"></path>
          <path d="M12 14v3"></path>
        </svg>
        <h2>碳排与能效关联分析</h2>
        <span class="ca-subtitle">Carbon Emission &amp; Energy Efficiency Analysis</span>
      </div>
      <div class="header-actions">
        <button class="refresh-btn" @click="refreshAll">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <div class="ca-tabs">
      <button
        v-for="tab in tabOptions"
        :key="tab.value"
        class="ca-tab"
        :class="{ active: activeTab === tab.value }"
        @click="activeTab = tab.value"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <component :is="tab.icon" />
        </svg>
        {{ tab.label }}
      </button>
    </div>

    <div class="ca-content">
      <template v-if="activeTab === 'ranking'">
        <div class="ranking-view">
          <div class="summary-cards">
            <div class="summary-card">
              <div class="summary-icon"></div>
              <div class="summary-label">报告期</div>
              <div class="summary-value">{{ rankingReport.report_month || '--' }}</div>
            </div>
            <div class="summary-card accent-blue">
              <div class="summary-label">月度碳排增量</div>
              <div class="summary-value">
                <span class="summary-big">{{ rankingCarbonKg }}</span>
                <span class="summary-unit">kgCO₂e</span>
              </div>
              <div class="summary-sub">估算值，不用于精确计量</div>
            </div>
            <div class="summary-card accent-orange">
              <div class="summary-label">月度泄漏量</div>
              <div class="summary-value">
                <span class="summary-big">{{ rankingLeakageM3 }}</span>
                <span class="summary-unit">m³</span>
              </div>
              <div class="summary-sub">基于预紧力劣化估算</div>
            </div>
            <div class="summary-card accent-purple">
              <div class="summary-label">分析装置</div>
              <div class="summary-value">
                <span class="summary-big">{{ rankingReport.total_nodes || 0 }}</span>
                <span class="summary-unit">台</span>
              </div>
              <div class="summary-sub">装置总数</div>
            </div>
            <div class="summary-card risk-summary">
              <div class="summary-label">风险分布</div>
              <div class="risk-donut">
                <div
                  v-for="(count, level) in rankingReport.risk_distribution"
                  :key="level"
                  class="risk-legend"
                  :style="{ color: CarbonRiskLevelColorMap[level as CarbonRiskLevel] }"
                >
                  <span class="legend-dot" :style="{ background: CarbonRiskLevelColorMap[level as CarbonRiskLevel] }"></span>
                  <span class="legend-name">{{ CarbonRiskLevelMap[level as CarbonRiskLevel] }}</span>
                  <span class="legend-count">{{ count || 0 }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="ranking-table-card">
            <div class="card-header">
              <div class="card-title">装置级月度碳排风险贡献排行</div>
              <div class="card-desc">按优先级评分 (HI 40% + 泄漏 40% + 趋势 ±15%) 加权排序</div>
            </div>
            <div class="table-wrapper">
              <table class="ranking-table">
                <thead>
                  <tr>
                    <th style="width:50px">排名</th>
                    <th>装置</th>
                    <th style="width:80px">类型</th>
                    <th style="width:100px">HI</th>
                    <th style="width:100px">碳排风险分</th>
                    <th style="width:100px">趋势</th>
                    <th style="width:120px">月度泄漏(m³)</th>
                    <th style="width:140px">月度碳排增量</th>
                    <th style="width:90px">优先级</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in rankingReport.ranked_items" :key="item.node_id" class="rank-row">
                    <td>
                      <span class="rank-badge" :class="'rank-' + Math.min(item.rank || 99, 3)">
                        {{ item.rank }}
                      </span>
                    </td>
                    <td>
                      <div class="node-name">{{ item.node_name }}</div>
                      <div class="node-id">{{ item.node_id }}</div>
                    </td>
                    <td>
                      <span class="node-type">{{ nodeTypeLabel(item.node_type) }}</span>
                    </td>
                    <td>
                      <div class="hi-cell">
                        <div class="score-bar">
                          <div
                            class="score-fill"
                            :style="{ width: item.hi_score + '%', background: HILevelColorMap[item.hi_level] }"
                          ></div>
                        </div>
                        <div class="score-text">
                          <span :style="{ color: HILevelColorMap[item.hi_level] }" class="score-num">{{ item.hi_score }}</span>
                          <span class="score-level">{{ HILevelMap[item.hi_level] }}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div class="risk-cell">
                        <span
                          class="risk-level"
                          :style="{
                            background: CarbonRiskLevelBgColorMap[item.carbon_risk_level],
                            color: CarbonRiskLevelColorMap[item.carbon_risk_level]
                          }"
                        >
                          {{ CarbonRiskLevelMap[item.carbon_risk_level] }}
                        </span>
                        <span class="risk-score">{{ item.carbon_risk_score }}</span>
                      </div>
                    </td>
                    <td>
                      <span
                        class="trend-chip"
                        :style="{ color: DegradationTrendColorMap[item.trend] }"
                      >
                        {{ DegradationTrendMap[item.trend] }}
                      </span>
                    </td>
                    <td class="num-cell">{{ item.monthly_leakage_volume_m3.toFixed(4) }}</td>
                    <td>
                      <span class="carbon-num">{{ item.monthly_carbon_increment_kg.toFixed(3) }}</span>
                      <span class="carbon-unit">kgCO₂e</span>
                    </td>
                    <td>
                      <span class="priority-score">{{ item.priority_score.toFixed(1) }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'dual_view'">
        <div class="dual-view">
          <div class="dual-intro">
            <div class="dual-intro-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
            </div>
            <div>
              <h3>健康指数 (HI) 与碳排风险并列视图</h3>
              <p>对比每台装置的机械健康与潜在碳排增量对比，识别"高健康但高碳排"优先处理优先级</p>
            </div>
          </div>

          <div class="dual-grid">
            <div
              v-for="item in dualView.items"
              :key="item.node_id"
              class="dual-card"
            >
              <div class="dual-card-header">
                <div class="dual-title">{{ item.node_name }}</div>
                <span class="dual-sub">{{ item.node_id }} · {{ nodeTypeLabel(item.node_type) }}</span>
              </div>

              <div class="dual-columns">
                <div class="dual-col hi-col">
                  <div class="col-label">HI 健康指数</div>
                  <div class="hi-bar">
                    <div
                      class="hi-bar-fill"
                      :style="{ width: item.hi_score + '%', background: HILevelColorMap[item.hi_level] }"
                    ></div>
                  </div>
                  <div class="col-value">
                    <span class="big" :style="{ color: HILevelColorMap[item.hi_level] }">{{ item.hi_score }}</span>
                    <span class="level">{{ HILevelMap[item.hi_level] }}</span>
                  </div>
                  <div class="col-trend">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                    </svg>
                    <span>{{ item.hi_trend }}</span>
                  </div>
                </div>

                <div class="dual-divider"></div>

                <div class="dual-col carbon-col">
                  <div class="col-label">月度碳排增量</div>
                  <div class="carbon-bar">
                    <div
                      class="carbon-bar-fill"
                      :style="{
                        width: Math.min(100, item.monthly_carbon_increment_kg * 50) + '%',
                        background: CarbonRiskLevelColorMap[item.carbon_risk_level]
                      }"
                    ></div>
                  </div>
                  <div class="col-value">
                    <span class="big" :style="{ color: CarbonRiskLevelColorMap[item.carbon_risk_level] }">
                      {{ item.monthly_carbon_increment_kg.toFixed(3) }}
                    </span>
                    <span class="level">kgCO₂e</span>
                  </div>
                  <div class="col-trend">
                    <span :style="{ color: CarbonTrendColorMap[item.carbon_trend] }">
                      {{ CarbonTrendMap[item.carbon_trend] }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="dual-metrics">
                <div class="metric-item">
                  <div class="metric-label">劣化速率</div>
                  <div class="metric-value">{{ (item.degradation_rate_per_month * 100).toFixed(2) }}%/月</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">泄漏率</div>
                  <div class="metric-value">{{ item.estimated_leakage_rate_m3_hour.toFixed(5) }} m³/h</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'esg'">
        <div class="esg-view">
          <div class="esg-header-row">
            <div class="esg-summary-grid">
              <div class="esg-sum-card main">
                <div class="esg-sum-label">月度碳排增量估算</div>
                <div class="esg-sum-value">
                  <span class="big">{{ esgCarbonKg }}</span>
                  <span class="unit">kgCO₂e</span>
                </div>
                <div class="esg-sum-sub">
                  ≈ {{ esgCarbonTons }} 吨
                </div>
              </div>
              <div class="esg-sum-card">
                <div class="esg-sum-label">装置平均碳排</div>
                <div class="esg-sum-value">
                  <span class="big">{{ esgAvgPerDevice }}</span>
                  <span class="unit">kg/台</span>
                </div>
              </div>
              <div class="esg-sum-card">
                <div class="esg-sum-label">TOP5 贡献占比</div>
                <div class="esg-sum-value">
                  <span class="big">{{ esgTop5Pct }}</span>
                  <span class="unit">%</span>
                </div>
                <div class="esg-sum-sub">
                  风险严重度：
                  <span
                    class="severity-tag"
                    :class="esgSeverityClass"
                  >{{ esgSeverity }}</span>
                </div>
              </div>
              <div class="esg-sum-card">
                <div class="esg-sum-label">趋势</div>
                <div class="esg-sum-value trend">
                  <span :class="esgOverallTrend">
                    {{ esgOverallTrendLabel }}
                  </span>
                </div>
                <div class="esg-sum-sub">
                  改善 {{ esgImprovingCount }}
                  · 稳定 {{ esgStableCount }}
                  · 劣化 {{ esgDecliningCount }}
                </div>
              </div>
            </div>

            <div class="esg-actions">
              <button
                class="btn-export"
                @click="exportJSON"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                导出 JSON
              </button>
              <button
                class="btn-export csv"
                @click="exportCSV"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                导出 CSV
              </button>
            </div>
          </div>

          <div class="esg-observation">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <span>{{ esgKeyObservation }}</span>
          </div>

          <div class="esg-section">
            <h4>TOP 碳排风险装置</h4>
            <div class="esg-risk-list">
              <div
                v-for="(item, idx) in esgReport.top_risk_items"
                :key="item.node_id"
                class="esg-risk-item"
              >
                <div class="esg-rank">{{ idx + 1 }}</div>
                <div class="esg-risk-info">
                  <div class="esg-risk-name">{{ item.node_name }} <span class="esg-id">{{ item.node_id }}</span></div>
                  <div class="esg-risk-meta">
                    HI {{ item.hi_score }} · {{ HILevelMap[item.hi_level] }}
                    · 泄漏 {{ item.monthly_leakage_volume_m3.toFixed(4) }} m³
                  </div>
                </div>
                <div class="esg-risk-carbon">
                  <span class="esg-carbon-num">{{ item.monthly_carbon_increment_kg.toFixed(2) }}</span>
                  <span class="esg-carbon-unit">kgCO₂e/月</span>
                </div>
                <div
                  class="esg-risk-level"
                  :style="{
                    background: CarbonRiskLevelBgColorMap[item.carbon_risk_level],
                    color: CarbonRiskLevelColorMap[item.carbon_risk_level]
                  }"
                >
                  {{ CarbonRiskLevelMap[item.carbon_risk_level] }}
                </div>
              </div>
            </div>
          </div>

          <div class="esg-section">
            <h4>建议措施</h4>
            <ul class="esg-rec-list">
              <li v-for="(rec, i) in esgReport.recommendations" :key="i">{{ rec }}</li>
            </ul>
          </div>

          <div v-if="esgReport.methodology_note" class="esg-section methodology">
            <h4>方法学说明</h4>
            <p>{{ esgReport.methodology_note }}</p>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'config'">
        <div class="config-view">
          <div class="config-intro">
            <h3>模型系数配置</h3>
            <p>所有模型系数可配置，修改后立即生效并持久化。系数用于趋势与优先级估算。</p>
          </div>

          <div class="config-sections">
            <div class="config-section">
              <h4>预紧力劣化模型</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>名义预紧力 (kN)</label>
                  <input type="number" v-model.number="configForm.degradation.nominal_preload" step="10" />
                </div>
                <div class="config-item">
                  <label>最小有效压紧比</label>
                  <input type="number" v-model.number="configForm.degradation.min_effective_preload_ratio" step="0.01" />
                </div>
                <div class="config-item">
                  <label>松弛速率 (/月)</label>
                  <input type="number" v-model.number="configForm.degradation.relaxation_rate_per_month" step="0.001" />
                </div>
                <div class="config-item">
                  <label>温度加速因子</label>
                  <input type="number" v-model.number="configForm.degradation.temperature_acceleration_factor" step="0.001" />
                </div>
                <div class="config-item">
                  <label>振动加速因子</label>
                  <input type="number" v-model.number="configForm.degradation.vibration_acceleration_factor" step="0.001" />
                </div>
                <div class="config-item">
                  <label>压力循环加速因子</label>
                  <input type="number" v-model.number="configForm.degradation.cycle_acceleration_factor" step="0.00001" />
                </div>
              </div>
            </div>

            <div class="config-section">
              <h4>泄漏率估算模型</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>基础泄漏率 (m³/h)</label>
                  <input type="number" v-model.number="configForm.leakage.base_leakage_rate_m3_per_hour" step="0.00001" />
                </div>
                <div class="config-item">
                  <label>临界泄漏阈值</label>
                  <input type="number" v-model.number="configForm.leakage.critical_leakage_threshold" step="0.01" />
                </div>
                <div class="config-item">
                  <label>预紧力泄漏敏感度</label>
                  <input type="number" v-model.number="configForm.leakage.preload_leakage_sensitivity" step="0.1" />
                </div>
                <div class="config-item">
                  <label>密封老化因子 (/年)</label>
                  <input type="number" v-model.number="configForm.leakage.seal_aging_factor_per_year" step="0.01" />
                </div>
                <div class="config-item">
                  <label>压力敏感度</label>
                  <input type="number" v-model.number="configForm.leakage.pressure_sensitivity" step="0.1" />
                </div>
              </div>
            </div>

            <div class="config-section">
              <h4>能耗/碳排换算模型</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>单位泄漏能耗 (kWh/m³)</label>
                  <input type="number" v-model.number="configForm.energy_carbon.energy_per_leakage_unit" step="0.1" />
                </div>
                <div class="config-item">
                  <label>电力排放因子 (kgCO₂e/kWh)</label>
                  <input type="number" v-model.number="configForm.energy_carbon.carbon_factor_electricity" step="0.0001" />
                </div>
                <div class="config-item">
                  <label>天然气排放因子</label>
                  <input type="number" v-model.number="configForm.energy_carbon.carbon_factor_natural_gas" step="0.0001" />
                </div>
                <div class="config-item">
                  <label>蒸汽排放因子</label>
                  <input type="number" v-model.number="configForm.energy_carbon.carbon_factor_steam" step="0.001" />
                </div>
                <div class="config-item">
                  <label>压缩机效率</label>
                  <input type="number" v-model.number="configForm.energy_carbon.compressor_efficiency" step="0.01" />
                </div>
                <div class="config-item">
                  <label>回收率</label>
                  <input type="number" v-model.number="configForm.energy_carbon.recovery_rate" step="0.01" />
                </div>
                <div class="config-item">
                  <label>基础月度能耗 (kWh)</label>
                  <input type="number" v-model.number="configForm.energy_carbon.base_monthly_energy_kwh" step="100" />
                </div>
                <div class="config-item">
                  <label>基础月度碳排 (kg)</label>
                  <input type="number" v-model.number="configForm.energy_carbon.base_monthly_carbon_kg" step="10" />
                </div>
              </div>
            </div>
          </div>

          <div class="config-actions">
            <button class="btn-reset" @click="resetConfig">重置默认</button>
            <button class="btn-save" @click="saveConfig">保存配置</button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, h } from 'vue'
import {
  buildCarbonNodesFromTopology,
  invalidateCarbonNodesCache,
  fetchCarbonMonthlyRanking,
  fetchHICarbonDualView,
  fetchESGReport,
  fetchCarbonModelConfig,
  updateCarbonModelConfig,
  downloadCSV,
} from '@/api/carbon'
import type { CarbonNodeInput } from '@/api/carbon'
import {
  CarbonRiskLevelMap,
  CarbonRiskLevelColorMap,
  CarbonRiskLevelBgColorMap,
  DegradationTrendMap,
  DegradationTrendColorMap,
  CarbonTrendMap,
  CarbonTrendColorMap,
  HILevelMap,
  HILevelColorMap,
  ESGTrendMap,
  CarbonViewModeMap,
} from '@/types'
import type {
  CarbonRiskLevel,
  CarbonMonthlyRankingResponse,
  HICarbonDualViewResponse,
  ESGReportFragmentResponse,
  CarbonModelConfigResponse,
} from '@/types'

type TabValue = 'ranking' | 'dual_view' | 'esg' | 'config'

const tabOptions: Array<{ value: TabValue; label: string; icon: any }> = [
  {
    value: 'ranking',
    label: CarbonViewModeMap['ranking'],
    icon: () => h('path', { d: 'M3 3v18h18' }),
  },
  {
    value: 'dual_view',
    label: CarbonViewModeMap['dual_view'],
    icon: () => h('rect', { x: 3, y: 3, width: 7, height: 7 }),
  },
  {
    value: 'esg',
    label: CarbonViewModeMap['esg'],
    icon: () => h('path', { d: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z' }),
  },
  {
    value: 'config',
    label: CarbonViewModeMap['config'],
    icon: () => h('circle', { cx: 12, cy: 12, r: 3 }),
  },
]

const activeTab = ref<TabValue>('ranking')
const loading = ref(false)
const nodesReady = ref(false)
const carbonNodes = ref<CarbonNodeInput[]>([])

const rankingReport = reactive<Partial<CarbonMonthlyRankingResponse>>({
  report_month: '',
  total_nodes: 0,
  total_monthly_carbon_increment_kg: 0,
  total_monthly_leakage_volume_m3: 0,
  risk_distribution: { low: 0, medium: 0, high: 0, critical: 0 } as any,
  ranked_items: [],
  generated_at: '',
})

const dualView = reactive<Partial<HICarbonDualViewResponse>>({
  report_month: '',
  total_nodes: 0,
  items: [],
  generated_at: '',
})

const esgReport = reactive<Partial<ESGReportFragmentResponse>>({
  report_period: '',
  generated_at: '',
  summary: undefined,
  top_risk_items: [],
  trend_analysis: undefined,
  recommendations: [],
  methodology_note: '',
  csv_content: undefined,
})

const defaultConfig: CarbonModelConfigResponse = {
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

const configForm = reactive<CarbonModelConfigResponse>(JSON.parse(JSON.stringify(defaultConfig)))

function nodeTypeLabel(t: string): string {
  const map: Record<string, string> = { device: '装置', flange: '法兰', bolt: '螺栓' }
  return map[t] || t
}

function fmt2(v: number | undefined | null): string {
  return v !== undefined && v !== null && !isNaN(v) ? v.toFixed(2) : '0.00'
}
function fmt3(v: number | undefined | null): string {
  return v !== undefined && v !== null && !isNaN(v) ? v.toFixed(3) : '0.000'
}
function fmt4(v: number | undefined | null): string {
  return v !== undefined && v !== null && !isNaN(v) ? v.toFixed(4) : '0.0000'
}
function fmt5(v: number | undefined | null): string {
  return v !== undefined && v !== null && !isNaN(v) ? v.toFixed(5) : '0.00000'
}

const rankingCarbonKg = computed(() => fmt2(rankingReport.total_monthly_carbon_increment_kg))
const rankingLeakageM3 = computed(() => fmt4(rankingReport.total_monthly_leakage_volume_m3))

const esgCarbonKg = computed(() => fmt2(esgReport.summary?.estimated_monthly_carbon_increment_kg))
const esgCarbonTons = computed(() => fmt4(esgReport.summary?.estimated_monthly_carbon_increment_tons))
const esgAvgPerDevice = computed(() => fmt3(esgReport.summary?.average_carbon_per_device_kg))
const esgTop5Pct = computed(() => {
  const r = esgReport.summary?.top5_contribution_ratio ?? 0
  return (r * 100).toFixed(1)
})
const esgSeverity = computed(() => esgReport.summary?.carbon_risk_severity || '-')
const esgSeverityClass = computed(() => {
  const s = esgReport.summary?.carbon_risk_severity
  if (s === '高') return 'severity-high'
  if (s === '中') return 'severity-medium'
  if (s === '低') return 'severity-low'
  return ''
})
const esgOverallTrend = computed(() => esgReport.trend_analysis?.overall_trend || 'stable')
const esgOverallTrendLabel = computed(() => ESGTrendMap[esgOverallTrend.value] || '稳定')
const esgImprovingCount = computed(() => esgReport.trend_analysis?.improving_count || 0)
const esgStableCount = computed(() => esgReport.trend_analysis?.stable_count || 0)
const esgDecliningCount = computed(() => esgReport.trend_analysis?.declining_count || 0)
const esgKeyObservation = computed(() => esgReport.trend_analysis?.key_observation || '正在分析...')

async function ensureNodes(forceRefresh = false): Promise<CarbonNodeInput[]> {
  if (nodesReady.value && carbonNodes.value.length > 0 && !forceRefresh) {
    return carbonNodes.value
  }
  try {
    const nodes = await buildCarbonNodesFromTopology(forceRefresh)
    carbonNodes.value = nodes
    nodesReady.value = true
    return nodes
  } catch (e) {
    console.error('构建碳排节点数据失败:', e)
    return []
  }
}

async function loadRanking(forceRefresh = false) {
  try {
    const nodes = await ensureNodes(forceRefresh)
    const data = await fetchCarbonMonthlyRanking({ nodes, top_n: 15 })
    Object.assign(rankingReport, data)
  } catch (e) {
    console.error('加载月度排行失败:', e)
  }
}

async function loadDualView(forceRefresh = false) {
  try {
    const nodes = await ensureNodes(forceRefresh)
    const data = await fetchHICarbonDualView({ nodes })
    Object.assign(dualView, data)
  } catch (e) {
    console.error('加载HI并列视图失败:', e)
  }
}

async function loadESGReport(forceRefresh = false) {
  try {
    const nodes = await ensureNodes(forceRefresh)
    const data = await fetchESGReport({ nodes, format: 'json', include_methodology: true, top_n: 5 })
    Object.assign(esgReport, data)
  } catch (e) {
    console.error('加载ESG报表失败:', e)
  }
}

async function loadConfig() {
  try {
    const data = await fetchCarbonModelConfig()
    Object.assign(configForm, data)
  } catch (e) {
    console.error('加载模型配置失败:', e)
  }
}

async function refreshAll() {
  loading.value = true
  invalidateCarbonNodesCache()
  nodesReady.value = false
  carbonNodes.value = []
  try {
    await ensureNodes(true)
    await Promise.all([loadRanking(), loadDualView(), loadESGReport()])
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  try {
    await updateCarbonModelConfig({
      degradation: configForm.degradation,
      leakage: configForm.leakage,
      energy_carbon: configForm.energy_carbon,
      operator_name: 'current',
      description: '前端保存碳排模型配置',
    })
    alert('配置保存成功')
    refreshAll()
  } catch (e) {
    console.error('保存配置失败:', e)
    alert('保存失败，请稍后重试')
  }
}

function resetConfig() {
  Object.assign(configForm, JSON.parse(JSON.stringify(defaultConfig)))
}

function exportJSON() {
  const json = JSON.stringify(esgReport, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `esg-carbon-report-${esgReport.report_period || 'latest'}.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function exportCSV() {
  try {
    const nodes = await ensureNodes()
    const data = await fetchESGReport({ nodes, format: 'csv', include_methodology: true, top_n: 10 })
    const csv = data.csv_content || ''
    downloadCSV(csv, `esg-carbon-report-${data.report_period || 'latest'}.csv`)
  } catch (e) {
    console.error('导出CSV失败:', e)
  }
}

onMounted(async () => {
  await refreshAll()
  await loadConfig()
})
</script>

<style scoped>
.carbon-analysis {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background:
    radial-gradient(ellipse at 20% 0%, rgba(34, 197, 94, 0.04) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(59, 130, 246, 0.05) 0%, transparent 50%),
    linear-gradient(180deg, #020617 0%, #0f172a 100%);
}

.ca-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ca-title {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #e2e8f0;
}

.ca-title h2 {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #22c55e 0%, #3b82f6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.ca-subtitle {
  font-size: 11px;
  color: #64748b;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
  transition: all 0.2s;
}

.refresh-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.45);
}

.ca-tabs {
  display: flex;
  gap: 8px;
  background: rgba(30, 41, 59, 0.7);
  padding: 6px;
  border-radius: 10px;
  width: fit-content;
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.ca-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: transparent;
  border: none;
  border-radius: 7px;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.ca-tab:hover {
  color: #cbd5e1;
  background: rgba(71, 85, 105, 0.4);
}

.ca-tab.active {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: white;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.35);
}

.ca-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.summary-card {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  padding: 18px 20px;
  backdrop-filter: blur(8px);
}

.summary-card.accent-blue {
  border-left: 3px solid #3b82f6;
}

.summary-card.accent-orange {
  border-left: 3px solid #f97316;
}

.summary-card.accent-purple {
  border-left: 3px solid #8b5cf6;
}

.summary-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}

.summary-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.summary-big {
  font-size: 22px;
  font-weight: 700;
  color: #f1f5f9;
}

.summary-unit {
  font-size: 12px;
  color: #94a3b8;
}

.summary-sub {
  font-size: 11px;
  color: #475569;
  margin-top: 6px;
}

.risk-donut {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.risk-legend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-name {
  flex: 1;
  color: #94a3b8;
}

.legend-count {
  font-weight: 600;
}

.ranking-table-card,
.config-section,
.esg-section {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  overflow: hidden;
  backdrop-filter: blur(8px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #f1f5f9;
}

.card-desc {
  font-size: 12px;
  color: #64748b;
}

.table-wrapper {
  overflow: auto;
}

.ranking-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.ranking-table th {
  text-align: left;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.6);
  color: #94a3b8;
  font-weight: 500;
  font-size: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  position: sticky;
  top: 0;
  z-index: 1;
}

.rank-row {
  border-bottom: 1px solid rgba(148, 163, 184, 0.05);
  transition: background 0.15s;
}

.rank-row:hover {
  background: rgba(59, 130, 246, 0.04);
}

.ranking-table td {
  padding: 12px 16px;
  color: #cbd5e1;
  vertical-align: middle;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}

.rank-badge.rank-1 {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: #fff;
  box-shadow: 0 2px 6px rgba(245, 158, 11, 0.4);
}

.rank-badge.rank-2 {
  background: linear-gradient(135deg, #94a3b8, #64748b);
  color: #fff;
}

.rank-badge.rank-3 {
  background: linear-gradient(135deg, #b45309, #92400e);
  color: #fff;
}

.node-name {
  font-weight: 600;
  color: #f1f5f9;
  font-size: 13px;
}

.node-id {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.node-type {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  background: rgba(59, 130, 246, 0.1);
  color: #60a5fa;
  border-radius: 4px;
}

.hi-cell {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 90px;
}

.score-bar {
  height: 6px;
  background: rgba(148, 163, 184, 0.15);
  border-radius: 3px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}

.score-text {
  display: flex;
  align-items: center;
  gap: 6px;
}

.score-num {
  font-weight: 600;
  font-size: 13px;
}

.score-level {
  font-size: 11px;
  color: #94a3b8;
}

.risk-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.risk-level {
  padding: 3px 8px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 600;
}

.risk-score {
  color: #94a3b8;
  font-size: 12px;
}

.trend-chip {
  font-size: 12px;
  font-weight: 500;
}

.num-cell {
  font-family: 'SF Mono', Menlo, monospace;
  color: #e2e8f0;
}

.carbon-num {
  font-family: 'SF Mono', Menlo, monospace;
  font-weight: 600;
  color: #f8fafc;
}

.carbon-unit {
  font-size: 11px;
  color: #64748b;
  margin-left: 4px;
}

.priority-score {
  font-family: 'SF Mono', Menlo, monospace;
  font-weight: 700;
  color: #f1f5f9;
  font-size: 14px;
}

.dual-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.dual-intro {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  color: #e2e8f0;
}

.dual-intro-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.15));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #22c55e;
  flex-shrink: 0;
}

.dual-intro h3 {
  font-size: 15px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 4px;
}

.dual-intro p {
  font-size: 12px;
  color: #94a3b8;
}

.dual-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
}

.dual-card {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  padding: 16px;
  backdrop-filter: blur(8px);
}

.dual-card-header {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}

.dual-title {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
}

.dual-sub {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.dual-columns {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 12px;
  align-items: stretch;
  margin-bottom: 12px;
}

.dual-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dual-divider {
  width: 1px;
  background: rgba(148, 163, 184, 0.15);
}

.col-label {
  font-size: 11px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.hi-bar,
.carbon-bar {
  height: 8px;
  background: rgba(148, 163, 184, 0.15);
  border-radius: 4px;
  overflow: hidden;
}

.hi-bar-fill,
.carbon-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.col-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.col-value .big {
  font-size: 18px;
  font-weight: 700;
}

.col-value .level {
  font-size: 11px;
  color: #94a3b8;
}

.col-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #64748b;
}

.dual-metrics {
  display: flex;
  gap: 12px;
  padding-top: 10px;
  border-top: 1px dashed rgba(148, 163, 184, 0.08);
}

.metric-item {
  flex: 1;
}

.metric-label {
  font-size: 10px;
  color: #64748b;
  margin-bottom: 2px;
}

.metric-value {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 12px;
  color: #cbd5e1;
  font-weight: 500;
}

.esg-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.esg-header-row {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.esg-summary-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.esg-sum-card {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  padding: 16px 18px;
  backdrop-filter: blur(8px);
}

.esg-sum-card.main {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.08),
    rgba(59, 130, 246, 0.06));
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.esg-sum-label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.esg-sum-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.esg-sum-value .big {
  font-size: 24px;
  font-weight: 700;
  color: #f1f5f9;
}

.esg-sum-value .unit {
  font-size: 12px;
  color: #94a3b8;
}

.esg-sum-value.trend {
  font-size: 18px;
  font-weight: 600;
}

.esg-sum-value.trend .deteriorating {
  color: #ef4444;
}

.esg-sum-value.trend .stable {
  color: #eab308;
}

.esg-sum-value.trend .improving {
  color: #22c55e;
}

.esg-sum-sub {
  font-size: 11px;
  color: #64748b;
  margin-top: 6px;
}

.severity-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.severity-tag.high {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.severity-tag.medium {
  background: rgba(234, 179, 8, 0.15);
  color: #facc15;
}

.severity-tag.low {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.esg-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.btn-export {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  color: #60a5fa;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-export:hover {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.5);
}

.btn-export.csv {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border-color: transparent;
  color: white;
}

.btn-export.csv:hover {
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.4);
}

.esg-observation {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  color: #93c5fd;
  font-size: 13px;
}

.esg-section {
  padding: 18px 20px;
}

.esg-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 14px;
}

.esg-risk-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.esg-risk-item {
  display: grid;
  grid-template-columns: 36px 1fr auto auto;
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.08);
}

.esg-rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
}

.esg-risk-name {
  font-weight: 600;
  color: #f1f5f9;
  font-size: 13px;
}

.esg-id {
  color: #64748b;
  font-size: 11px;
  font-weight: 400;
}

.esg-risk-meta {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 3px;
}

.esg-risk-carbon {
  text-align: right;
}

.esg-carbon-num {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 16px;
  font-weight: 700;
  color: #f1f5f9;
}

.esg-carbon-unit {
  font-size: 11px;
  color: #64748b;
  display: block;
}

.esg-risk-level {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.esg-rec-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.esg-rec-list li {
  padding: 10px 14px;
  background: rgba(30, 41, 59, 0.5);
  border-left: 3px solid #22c55e;
  border-radius: 6px;
  color: #cbd5e1;
  font-size: 13px;
}

.methodology {
  background: rgba(15, 23, 42, 0.6);
  border: 1px dashed rgba(148, 163, 184, 0.1);
}

.methodology p {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.7;
}

.config-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.config-intro {
  padding: 16px 20px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 12px;
}

.config-intro h3 {
  font-size: 16px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 6px;
}

.config-intro p {
  font-size: 12px;
  color: #94a3b8;
}

.config-sections {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.config-section {
  padding: 18px 20px;
}

.config-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 14px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.config-item label {
  font-size: 12px;
  color: #94a3b8;
}

.config-item input {
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 13px;
  font-family: 'SF Mono', Menlo, monospace;
  outline: none;
  transition: border-color 0.2s;
}

.config-item input:focus {
  border-color: rgba(139, 92, 246, 0.5);
}

.config-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-reset {
  padding: 10px 22px;
  background: rgba(100, 116, 139, 0.15);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 8px;
  color: #cbd5e1;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-reset:hover {
  background: rgba(100, 116, 139, 0.3);
}

.btn-save {
  padding: 10px 24px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.35);
  transition: all 0.2s;
}

.btn-save:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.5);
}
</style>
