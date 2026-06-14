<template>
  <div class="trend-analysis">
    <div class="trend-header">
      <div class="trend-title">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
        </svg>
        <h2>趋势分析</h2>
      </div>
      <div class="header-controls">
        <div class="bolt-selector">
          <label class="selector-label">选择螺栓</label>
          <select v-model="selectedBoltId" @change="onBoltChange" class="bolt-select">
            <option value="">请选择螺栓</option>
            <option v-for="bolt in bolts" :key="bolt.bolt_id" :value="bolt.bolt_id">
              {{ bolt.bolt_id }} ({{ bolt.position }} · {{ bolt.current_preload }}kN)
            </option>
          </select>
        </div>
        <div class="range-selector">
          <label class="selector-label">历史范围</label>
          <div class="range-buttons">
            <button
              v-for="r in rangeOptions"
              :key="r.value"
              class="range-btn"
              :class="{ active: historyRange === r.value }"
              @click="historyRange = r.value"
            >
              {{ r.label }}
            </button>
          </div>
        </div>
        <button class="refresh-btn" @click="loadTrendData" :disabled="!selectedBoltId || loading">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <div v-if="!selectedBoltId" class="empty-state">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
      </svg>
      <div class="empty-title">选择螺栓查看趋势分析</div>
      <div class="empty-desc">从上方下拉菜单选择一个螺栓，查看预紧力历史趋势与 Prophet 预测</div>
    </div>

    <template v-else>
      <div class="trend-content">
        <div class="chart-section">
          <div class="chart-card">
            <div class="chart-title-row">
              <div class="chart-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 20V10"></path>
                  <path d="M18 20V4"></path>
                  <path d="M6 20v-4"></path>
                </svg>
                预紧力趋势曲线 + Prophet 30天预测
              </div>
              <div class="chart-legend">
                <span class="legend-item"><span class="legend-dot" style="background:#3b82f6"></span>历史值</span>
                <span class="legend-item"><span class="legend-dot" style="background:#f97316"></span>Prophet预测</span>
                <span class="legend-item"><span class="legend-band"></span>置信区间</span>
                <span class="legend-item"><span class="legend-line-dash"></span>名义预紧力</span>
              </div>
            </div>
            <div ref="preloadChartRef" class="chart-container"></div>
          </div>

          <div class="timeline-card">
            <div class="chart-title-row">
              <div class="chart-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                预测状态时间轴
              </div>
              <div class="chart-legend">
                <span v-for="code in statusOrder" :key="code" class="legend-item">
                  <span class="legend-dot" :style="{ background: StatusColorMap[code] }"></span>
                  {{ StatusCodeMap[code] }}
                </span>
              </div>
            </div>
            <div ref="timelineChartRef" class="chart-container timeline"></div>
          </div>
        </div>

        <aside class="trend-sidebar">
          <div class="sidebar-card" v-if="currentBolt">
            <div class="sidebar-title">螺栓信息</div>
            <div class="bolt-info-grid">
              <div class="info-item">
                <span class="info-label">螺栓ID</span>
                <span class="info-value monospace">{{ currentBolt.bolt_id }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">当前预紧力</span>
                <span class="info-value">{{ currentBolt.current_preload }} kN</span>
              </div>
              <div class="info-item">
                <span class="info-label">名义预紧力</span>
                <span class="info-value">{{ currentBolt.nominal_preload }} kN</span>
              </div>
              <div class="info-item">
                <span class="info-label">当前状态</span>
                <span class="info-value" :style="{ color: StatusColorMap[currentBolt.status_code] }">
                  {{ StatusCodeMap[currentBolt.status_code] }}
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">健康指数</span>
                <span class="info-value" :class="getHiClass(currentBolt.health_index)">
                  {{ currentBolt.health_index }}
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">风险评分</span>
                <span class="info-value" :style="{ color: currentBolt.risk_level === 'high' ? '#ef4444' : currentBolt.risk_level === 'medium' ? '#eab308' : '#22c55e' }">
                  {{ currentBolt.risk_score }}
                </span>
              </div>
            </div>
          </div>

          <div class="sidebar-card" v-if="trendData">
            <div class="sidebar-title">Prophet 预测摘要</div>
            <div class="forecast-summary">
              <div class="forecast-item">
                <div class="forecast-label">30天预测值</div>
                <div class="forecast-value">{{ lastForecastYhat }} kN</div>
              </div>
              <div class="forecast-item">
                <div class="forecast-label">置信区间</div>
                <div class="forecast-range">
                  {{ lastForecastLower }} ~ {{ lastForecastUpper }} kN
                </div>
              </div>
              <div class="forecast-item">
                <div class="forecast-label">预测趋势</div>
                <div class="forecast-trend" :class="trendDirection">
                  <svg v-if="trendDirection === 'down'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline>
                    <polyline points="17 18 23 18 23 12"></polyline>
                  </svg>
                  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
                    <polyline points="17 6 23 6 23 12"></polyline>
                  </svg>
                  {{ trendDirection === 'down' ? '下降趋势' : '上升趋势' }}
                </div>
              </div>
              <div class="forecast-item">
                <div class="forecast-label">30天预测状态</div>
                <div class="forecast-status" :style="{ color: lastPredictedStatusColor }">
                  {{ lastPredictedStatusLabel }}
                </div>
              </div>
              <div class="forecast-item" v-if="trendData.status_predictions.length > 0">
                <div class="forecast-label">预测置信度</div>
                <div class="confidence-bar-row">
                  <div class="confidence-bar">
                    <div class="confidence-fill" :style="{ width: lastPredictionConfidence * 100 + '%' }"></div>
                  </div>
                  <span class="confidence-value">{{ Math.round(lastPredictionConfidence * 100) }}%</span>
                </div>
              </div>
            </div>
          </div>

          <div class="sidebar-card" v-if="trendData && trendData.status_predictions.length > 0">
            <div class="sidebar-title">风险预警节点</div>
            <div class="risk-nodes">
              <div
                v-for="(pred, idx) in riskNodes"
                :key="idx"
                class="risk-node"
                :class="`risk-${pred.risk_level}`"
              >
                <div class="risk-node-dot" :style="{ background: StatusColorMap[pred.predicted_status] }"></div>
                <div class="risk-node-info">
                  <div class="risk-node-date">{{ formatShortDate(pred.timestamp) }}</div>
                  <div class="risk-node-status">{{ StatusCodeMap[pred.predicted_status] }}</div>
                </div>
                <div class="risk-node-conf">{{ Math.round(pred.confidence * 100) }}%</div>
              </div>
              <div v-if="riskNodes.length === 0" class="no-risk">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                30天内无明显风险
              </div>
            </div>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { StatusCode, StatusCodeMap, StatusColorMap } from '@/types'
import type { Bolt, TrendAnalysisData } from '@/types'
import { fetchTrendAnalysis } from '@/api/monitoring'

interface Props {
  bolts: Bolt[]
  preselectedBoltId?: string | null
}

const props = defineProps<Props>()

const selectedBoltId = ref('')
const loading = ref(false)
const trendData = ref<TrendAnalysisData | null>(null)
const historyRange = ref(60)

const preloadChartRef = ref<HTMLElement | null>(null)
const timelineChartRef = ref<HTMLElement | null>(null)
let preloadChart: echarts.ECharts | null = null
let timelineChart: echarts.ECharts | null = null

const statusOrder: StatusCode[] = [0, 1, 2, 3, 4]

const rangeOptions = [
  { label: '7天', value: 7 },
  { label: '30天', value: 30 },
  { label: '60天', value: 60 }
]

const currentBolt = computed(() => {
  if (!selectedBoltId.value) return null
  return props.bolts.find(b => b.bolt_id === selectedBoltId.value) || null
})

const lastForecastYhat = computed(() => {
  if (!trendData.value || trendData.value.forecast.length === 0) return '-'
  return trendData.value.forecast[trendData.value.forecast.length - 1].yhat.toFixed(1)
})

const lastForecastLower = computed(() => {
  if (!trendData.value || trendData.value.forecast.length === 0) return '-'
  return trendData.value.forecast[trendData.value.forecast.length - 1].yhat_lower.toFixed(1)
})

const lastForecastUpper = computed(() => {
  if (!trendData.value || trendData.value.forecast.length === 0) return '-'
  return trendData.value.forecast[trendData.value.forecast.length - 1].yhat_upper.toFixed(1)
})

const trendDirection = computed(() => {
  if (!trendData.value || trendData.value.forecast.length < 2) return 'down'
  const first = trendData.value.forecast[0].yhat
  const last = trendData.value.forecast[trendData.value.forecast.length - 1].yhat
  return last < first ? 'down' : 'up'
})

const lastPredictedStatusLabel = computed(() => {
  if (!trendData.value || trendData.value.status_predictions.length === 0) return '-'
  const last = trendData.value.status_predictions[trendData.value.status_predictions.length - 1]
  return StatusCodeMap[last.predicted_status]
})

const lastPredictedStatusColor = computed(() => {
  if (!trendData.value || trendData.value.status_predictions.length === 0) return '#94a3b8'
  const last = trendData.value.status_predictions[trendData.value.status_predictions.length - 1]
  return StatusColorMap[last.predicted_status]
})

const lastPredictionConfidence = computed(() => {
  if (!trendData.value || trendData.value.status_predictions.length === 0) return 0
  return trendData.value.status_predictions[trendData.value.status_predictions.length - 1].confidence
})

const riskNodes = computed(() => {
  if (!trendData.value) return []
  return trendData.value.status_predictions.filter(p => p.predicted_status >= 2)
})

function getHiClass(hi?: number): string {
  if (hi === undefined) return ''
  if (hi >= 80) return 'hi-good'
  if (hi >= 60) return 'hi-fair'
  return 'hi-poor'
}

function formatShortDate(iso: string): string {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

async function onBoltChange() {
  await loadTrendData()
}

async function loadTrendData() {
  if (!selectedBoltId.value || !currentBolt.value) return
  loading.value = true
  try {
    trendData.value = await fetchTrendAnalysis(
      selectedBoltId.value,
      currentBolt.value.nominal_preload
    )
    await nextTick()
    renderCharts()
  } catch (e) {
    console.error('加载趋势数据失败:', e)
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  renderPreloadChart()
  renderTimelineChart()
}

function renderPreloadChart() {
  if (!preloadChartRef.value || !trendData.value) return
  if (!preloadChart) {
    preloadChart = echarts.init(preloadChartRef.value)
  }

  const data = trendData.value
  const cutoff = historyRange.value

  const filteredHistory = data.history.slice(-cutoff)
  const historyDates = filteredHistory.map(p => {
    const d = new Date(p.timestamp)
    return `${d.getMonth() + 1}/${d.getDate()}`
  })
  const historyValues = filteredHistory.map(p => p.value)

  const forecastDates = data.forecast.map(p => {
    const d = new Date(p.ds)
    return `${d.getMonth() + 1}/${d.getDate()}`
  })
  const forecastYhat = data.forecast.map(p => p.yhat)
  const forecastLower = data.forecast.map(p => p.yhat_lower)
  const forecastUpper = data.forecast.map(p => p.yhat_upper)

  const nominalLine = [...historyDates.map(() => data.nominal_preload), ...forecastDates.map(() => data.nominal_preload)]
  const allDates = [...historyDates, ...forecastDates]

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'rgba(59, 130, 246, 0.3)',
      textStyle: { color: '#e2e8f0', fontSize: 12 },
      axisPointer: { type: 'cross', crossStyle: { color: '#475569' } }
    },
    grid: { left: 60, right: 30, top: 30, bottom: 40 },
    xAxis: {
      type: 'category',
      data: allDates,
      axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, interval: Math.floor(allDates.length / 12) },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '预紧力 (kN)',
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.1)' } }
    },
    series: [
      {
        name: '置信区间上界',
        type: 'line',
        data: [...historyValues.map(() => null), ...forecastUpper],
        lineStyle: { opacity: 0 },
        stack: 'confidence',
        symbol: 'none',
        silent: true
      },
      {
        name: '置信区间下界',
        type: 'line',
        data: [...historyValues.map(() => null), ...forecastLower.map(v => data.nominal_preload > v ? data.nominal_preload - v : -(v - data.nominal_preload))],
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(249, 115, 22, 0.12)' },
        stack: 'confidence',
        symbol: 'none',
        silent: true
      },
      {
        name: '历史预紧力',
        type: 'line',
        data: [...historyValues, ...forecastDates.map(() => null)],
        smooth: true,
        lineStyle: { color: '#3b82f6', width: 2 },
        itemStyle: { color: '#3b82f6' },
        showSymbol: false
      },
      {
        name: 'Prophet预测',
        type: 'line',
        data: [...historyDates.map(() => null), ...forecastYhat],
        smooth: true,
        lineStyle: { color: '#f97316', width: 2, type: 'dashed' },
        itemStyle: { color: '#f97316' },
        showSymbol: false
      },
      {
        name: '名义预紧力',
        type: 'line',
        data: nominalLine,
        lineStyle: { color: '#ef4444', width: 1, type: 'dotted' },
        itemStyle: { color: '#ef4444' },
        showSymbol: false,
        silent: true
      }
    ]
  }

  preloadChart.setOption(option, true)
}

function renderTimelineChart() {
  if (!timelineChartRef.value || !trendData.value) return
  if (!timelineChart) {
    timelineChart = echarts.init(timelineChartRef.value)
  }

  const predictions = trendData.value.status_predictions
  const dates = predictions.map(p => {
    const d = new Date(p.timestamp)
    return `${d.getMonth() + 1}/${d.getDate()}`
  })

  const statusValues = predictions.map(p => p.predicted_status)
  const confidenceValues = predictions.map(p => Math.round(p.confidence * 100))

  const pieces = statusOrder.map(code => ({
    min: code - 0.4,
    max: code + 0.4,
    color: StatusColorMap[code],
    label: StatusCodeMap[code]
  }))

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'rgba(59, 130, 246, 0.3)',
      textStyle: { color: '#e2e8f0', fontSize: 12 },
      formatter(params: any) {
        const p = Array.isArray(params) ? params[0] : params
        const idx = p.dataIndex
        const pred = predictions[idx]
        if (!pred) return ''
        return `<div style="font-weight:600;margin-bottom:4px">${p.name}</div>
                <div>预测状态: <span style="color:${StatusColorMap[pred.predicted_status]}">${StatusCodeMap[pred.predicted_status]}</span></div>
                <div>置信度: ${Math.round(pred.confidence * 100)}%</div>
                <div>风险等级: ${pred.risk_level === 'high' ? '高' : pred.risk_level === 'medium' ? '中' : '低'}</div>`
      }
    },
    grid: { left: 60, right: 60, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      splitLine: { show: false }
    },
    yAxis: [
      {
        type: 'category',
        data: statusOrder.map(c => StatusCodeMap[c]),
        axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.08)' } }
      },
      {
        type: 'value',
        name: '置信度%',
        nameTextStyle: { color: '#94a3b8', fontSize: 10 },
        min: 40,
        max: 100,
        axisLine: { show: false },
        axisLabel: { color: '#94a3b8', fontSize: 9 },
        splitLine: { show: false }
      }
    ],
    visualMap: {
      show: false,
      pieces,
      seriesIndex: 0
    },
    series: [
      {
        name: '预测状态',
        type: 'line',
        step: 'middle',
        data: statusValues,
        lineStyle: { width: 3 },
        itemStyle: { borderWidth: 2, borderColor: '#0f172a' },
        showSymbol: true,
        symbolSize: 10
      },
      {
        name: '置信度',
        type: 'bar',
        yAxisIndex: 1,
        data: confidenceValues,
        barWidth: '40%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.4)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
          ]),
          borderRadius: [2, 2, 0, 0]
        },
        z: -1
      }
    ]
  }

  timelineChart.setOption(option, true)
}

function handleResize() {
  preloadChart?.resize()
  timelineChart?.resize()
}

watch(historyRange, () => {
  if (trendData.value) {
    renderPreloadChart()
  }
})

onMounted(() => {
  if (props.preselectedBoltId) {
    selectedBoltId.value = props.preselectedBoltId
    loadTrendData()
  }
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  preloadChart?.dispose()
  timelineChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.trend-analysis {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.trend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(15, 23, 42, 0.85);
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}

.trend-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e2e8f0;
}

.trend-title svg {
  color: #3b82f6;
}

.trend-title h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 20px;
}

.bolt-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-label {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.bolt-select {
  padding: 7px 12px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 12px;
  outline: none;
  min-width: 220px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.bolt-select:hover,
.bolt-select:focus {
  border-color: rgba(59, 130, 246, 0.6);
}

.range-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.range-buttons {
  display: flex;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 6px;
  overflow: hidden;
}

.range-btn {
  padding: 6px 14px;
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.range-btn:hover {
  color: #cbd5e1;
  background: rgba(59, 130, 246, 0.1);
}

.range-btn.active {
  background: rgba(59, 130, 246, 0.25);
  color: #60a5fa;
  font-weight: 600;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
}

.refresh-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.trend-content {
  flex: 1;
  display: flex;
  gap: 16px;
  padding: 16px 20px;
  min-height: 0;
  overflow: hidden;
}

.chart-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.chart-card,
.timeline-card {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chart-card {
  flex: 3;
}

.timeline-card {
  flex: 2;
}

.chart-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
  flex-shrink: 0;
}

.chart-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
}

.chart-legend {
  display: flex;
  align-items: center;
  gap: 14px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #94a3b8;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-band {
  width: 16px;
  height: 8px;
  border-radius: 2px;
  background: rgba(249, 115, 22, 0.25);
  border: 1px dashed rgba(249, 115, 22, 0.5);
  flex-shrink: 0;
}

.legend-line-dash {
  width: 16px;
  height: 0;
  border-top: 1px dotted #ef4444;
  flex-shrink: 0;
}

.chart-container {
  flex: 1;
  min-height: 0;
}

.chart-container.timeline {
  min-height: 140px;
}

.trend-sidebar {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.trend-sidebar::-webkit-scrollbar {
  width: 5px;
}

.trend-sidebar::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.sidebar-card {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  padding: 14px 16px;
  backdrop-filter: blur(8px);
}

.sidebar-title {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
}

.bolt-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-label {
  font-size: 10px;
  color: #64748b;
}

.info-value {
  font-size: 13px;
  font-weight: 500;
  color: #e2e8f0;
}

.info-value.monospace {
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 12px;
  color: #60a5fa;
}

.hi-good { color: #22c55e !important; }
.hi-fair { color: #eab308 !important; }
.hi-poor { color: #ef4444 !important; }

.forecast-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.forecast-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.forecast-label {
  font-size: 10px;
  color: #64748b;
}

.forecast-value {
  font-size: 16px;
  font-weight: 700;
  color: #f8fafc;
}

.forecast-range {
  font-size: 12px;
  color: #94a3b8;
  font-family: 'SF Mono', Monaco, monospace;
}

.forecast-trend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}

.forecast-trend.down {
  color: #ef4444;
}

.forecast-trend.up {
  color: #22c55e;
}

.forecast-status {
  font-size: 14px;
  font-weight: 600;
}

.confidence-bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.confidence-bar {
  flex: 1;
  height: 6px;
  background: rgba(71, 85, 105, 0.5);
  border-radius: 3px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  border-radius: 3px;
  transition: width 0.3s;
}

.confidence-value {
  font-size: 12px;
  font-weight: 600;
  color: #cbd5e1;
  min-width: 36px;
  text-align: right;
}

.risk-nodes {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.risk-node {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 6px;
  border-left: 3px solid transparent;
}

.risk-node.risk-low { border-left-color: #eab308; }
.risk-node.risk-medium { border-left-color: #f97316; }
.risk-node.risk-high { border-left-color: #ef4444; }

.risk-node-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 6px currentColor;
}

.risk-node-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.risk-node-date {
  font-size: 12px;
  font-weight: 500;
  color: #e2e8f0;
}

.risk-node-status {
  font-size: 10px;
  color: #94a3b8;
}

.risk-node-conf {
  font-size: 11px;
  font-weight: 600;
  color: #cbd5e1;
}

.no-risk {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  font-size: 12px;
  color: #22c55e;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 12px;
  color: #475569;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #64748b;
}

.empty-desc {
  font-size: 13px;
  color: #475569;
  max-width: 360px;
  text-align: center;
  line-height: 1.6;
}
</style>
