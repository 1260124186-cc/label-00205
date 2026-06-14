<template>
  <div class="app-root">
    <header class="app-header">
      <div class="header-left">
        <div class="logo">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
            <path d="M2 17l10 5 10-5"></path>
            <path d="M2 12l10 5 10-5"></path>
          </svg>
        </div>
        <div class="header-title-group">
          <h1 class="app-title">螺栓预紧力监控与运维控制台</h1>
          <p class="app-subtitle">Bolt Preload Monitoring & Operations Center</p>
        </div>
      </div>

      <div class="header-center">
        <nav class="nav-tabs">
          <button
            class="nav-tab"
            :class="{ active: currentView === 'monitoring' }"
            @click="currentView = 'monitoring'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polygon points="10 8 16 12 10 16 10 8"></polygon>
            </svg>
            监控视图
          </button>
          <button
            class="nav-tab"
            :class="{ active: currentView === 'alert' }"
            @click="currentView = 'alert'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            预警中心
            <span v-if="alertStats.pending > 0" class="alert-badge">{{ alertStats.pending }}</span>
          </button>
          <button
            class="nav-tab"
            :class="{ active: currentView === 'trend' }"
            @click="currentView = 'trend'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            趋势分析
          </button>
          <button
            class="nav-tab"
            :class="{ active: currentView === 'model' }"
            @click="currentView = 'model'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
              <path d="M2 17l10 5 10-5"></path>
              <path d="M2 12l10 5 10-5"></path>
            </svg>
            模型管理
          </button>
        </nav>
        <div class="realtime-status" :class="{ active: autoRefresh }" v-if="currentView === 'monitoring'">
          <span class="status-dot"></span>
          {{ autoRefresh ? '实时监控中' : '已暂停' }}
        </div>
        <div class="update-info" v-if="topologyData && currentView === 'monitoring'">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          更新时间: {{ formatUpdateTime() }}
        </div>
      </div>

      <div class="header-right">
        <div class="refresh-controls" v-if="currentView === 'monitoring'">
          <select v-model.number="refreshInterval" class="interval-select" :disabled="!autoRefresh">
            <option :value="3000">3秒</option>
            <option :value="5000">5秒</option>
            <option :value="10000">10秒</option>
            <option :value="30000">30秒</option>
            <option :value="60000">60秒</option>
          </select>
          <button
            class="toggle-btn"
            :class="{ active: autoRefresh }"
            @click="toggleAutoRefresh"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            {{ autoRefresh ? '暂停' : '自动刷新' }}
          </button>
          <button class="refresh-btn" @click="loadData(true)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="1 4 1 10 7 10"></polyline>
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
            </svg>
            刷新
          </button>
        </div>
      </div>
    </header>

    <main class="app-main" :class="{ 'app-main-full': currentView === 'alert' || currentView === 'trend' || currentView === 'model' }">
      <template v-if="currentView === 'monitoring'">
        <aside class="sidebar-left">
          <FilterPanel
            v-model="filters"
            :collector-options="collectorOptions"
            :position-options="positionOptions"
            @collector-change="onCollectorChange"
          />
          <div class="sidebar-spacer"></div>
          <StatsPanel v-if="topologyData" :stats="topologyData.stats" />
        </aside>

        <section class="main-content">
          <FlangeTopology
            v-if="topologyData"
            :flanges="topologyData.flanges"
            :bolts="topologyData.bolts"
            :collectors="topologyData.collectors"
            :filters="filters"
            @select-flange="onSelectFlange"
            @select-bolt="onSelectBolt"
          />
          <div v-else class="loading-state">
            <div class="loading-spinner"></div>
            <div class="loading-text">正在加载监控数据...</div>
          </div>
        </section>

        <aside class="sidebar-right">
          <DetailPanel
            v-if="selectedBolt || selectedFlange"
            :selected-bolt="selectedBolt"
            :selected-flange="selectedFlange"
            :bolts="topologyData?.bolts || []"
            :collectors="topologyData?.collectors || []"
            @close="clearSelection"
            @select-bolt="onSelectBoltFromDetail"
          />
          <div v-else class="empty-detail">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <div class="empty-title">选择节点查看详情</div>
            <div class="empty-desc">点击拓扑图中的法兰面或螺栓查看详细信息</div>
          </div>
        </aside>
      </template>

      <AlertCenter v-else-if="currentView === 'alert'" />

      <TrendAnalysis
        v-else-if="currentView === 'trend'"
        :bolts="topologyData?.bolts || []"
        :preselected-bolt-id="selectedBolt?.bolt_id || null"
      />

      <ModelManagement v-else-if="currentView === 'model'" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import FilterPanel from '@/components/FilterPanel.vue'
import StatsPanel from '@/components/StatsPanel.vue'
import FlangeTopology from '@/components/FlangeTopology.vue'
import DetailPanel from '@/components/DetailPanel.vue'
import AlertCenter from '@/components/AlertCenter.vue'
import TrendAnalysis from '@/components/TrendAnalysis.vue'
import ModelManagement from '@/components/ModelManagement.vue'
import { fetchTopology, fetchCollectors, fetchPositions } from '@/api/monitoring'
import { fetchAlertStats } from '@/api/alert'
import type { TopologyData, FilterOptions, Flange, Bolt } from '@/types'

const currentView = ref<'monitoring' | 'alert' | 'trend' | 'model'>('monitoring')

const topologyData = ref<TopologyData | null>(null)
const autoRefresh = ref(true)
const refreshInterval = ref(5000)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const alertStats = ref({
  total: 0,
  pending: 0,
  processing: 0,
  resolved: 0,
  byLevel: {} as Record<number, number>
})

let alertStatsTimer: ReturnType<typeof setInterval> | null = null

const filters = ref<FilterOptions>({
  collector_id: null,
  position: null,
  status_codes: [0, 1, 2, 3, 4]
})

const collectorOptions = ref<{ collector_id: string; collector_name: string }[]>([])
const positionOptions = ref<{ position: string; collector_id: string }[]>([])

const selectedBolt = ref<Bolt | null>(null)
const selectedFlange = ref<Flange | null>(null)

async function loadData(force = false) {
  try {
    topologyData.value = await fetchTopology(force)
    if (collectorOptions.value.length === 0 || force) {
      collectorOptions.value = await fetchCollectors()
    }
    await updatePositionOptions()
  } catch (e) {
    console.error('加载数据失败:', e)
  }
}

async function updatePositionOptions(collectorId?: string | null) {
  const cid = (collectorId !== undefined ? collectorId : filters.value.collector_id) || undefined
  positionOptions.value = await fetchPositions(cid)
}

function onCollectorChange(id: string | null) {
  updatePositionOptions(id)
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  setupTimer()
}

function setupTimer() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (autoRefresh.value) {
    refreshTimer = setInterval(() => {
      loadData(false)
    }, refreshInterval.value)
  }
}

function formatUpdateTime(): string {
  if (!topologyData.value) return '--'
  const d = new Date(topologyData.value.update_time)
  return d.toLocaleString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function onSelectFlange(flange: Flange) {
  selectedFlange.value = flange
  selectedBolt.value = null
}

function onSelectBolt(bolt: Bolt) {
  selectedBolt.value = bolt
  selectedFlange.value = null
}

function onSelectBoltFromDetail(bolt: Bolt) {
  selectedBolt.value = bolt
  selectedFlange.value = null
}

function clearSelection() {
  selectedBolt.value = null
  selectedFlange.value = null
}

async function loadAlertStats() {
  try {
    alertStats.value = await fetchAlertStats()
  } catch (e) {
    console.error('加载预警统计失败:', e)
  }
}

function setupAlertStatsTimer() {
  if (alertStatsTimer) {
    clearInterval(alertStatsTimer)
    alertStatsTimer = null
  }
  alertStatsTimer = setInterval(() => {
    loadAlertStats()
  }, 30000)
}

watch(refreshInterval, () => {
  setupTimer()
})

onMounted(() => {
  loadData(true)
  setupTimer()
  loadAlertStats()
  setupAlertStatsTimer()
})

onBeforeUnmount(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  if (alertStatsTimer) {
    clearInterval(alertStatsTimer)
  }
})
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body, #app {
  height: 100%;
  width: 100%;
  overflow: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: #020617;
  color: #e2e8f0;
  font-size: 14px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>

<style scoped>
.app-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background:
    radial-gradient(ellipse at 20% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
    linear-gradient(180deg, #020617 0%, #0f172a 100%);
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: rgba(15, 23, 42, 0.85);
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  backdrop-filter: blur(10px);
  gap: 24px;
  flex-shrink: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.logo {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
}

.header-title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.app-title {
  font-size: 18px;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: 0.5px;
  background: linear-gradient(135deg, #e2e8f0 0%, #60a5fa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.app-subtitle {
  font-size: 10px;
  color: #64748b;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 20px;
}

.nav-tabs {
  display: flex;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  padding: 4px;
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.nav-tab:hover {
  color: #cbd5e1;
  background: rgba(71, 85, 105, 0.4);
}

.nav-tab.active {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
}

.alert-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: #ef4444;
  color: white;
  font-size: 10px;
  font-weight: 600;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translate(50%, -30%);
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
}

.realtime-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  color: #86efac;
}

.realtime-status:not(.active) {
  background: rgba(100, 116, 139, 0.15);
  border-color: rgba(100, 116, 139, 0.3);
  color: #94a3b8;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}

.realtime-status:not(.active) .status-dot {
  background: #64748b;
  box-shadow: none;
}

.realtime-status.active .status-dot {
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.2); }
}

.update-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.header-right {
  display: flex;
  align-items: center;
}

.refresh-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.interval-select {
  padding: 6px 10px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 12px;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.interval-select:hover:not(:disabled),
.interval-select:focus {
  border-color: rgba(59, 130, 246, 0.6);
}

.toggle-btn,
.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid rgba(71, 85, 105, 0.5);
  background: rgba(30, 41, 59, 0.8);
  color: #cbd5e1;
  transition: all 0.2s;
}

.toggle-btn:hover,
.refresh-btn:hover {
  border-color: rgba(59, 130, 246, 0.5);
  color: #e2e8f0;
}

.toggle-btn.active {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  color: #60a5fa;
}

.refresh-btn {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border-color: transparent;
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
}

.refresh-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
}

.app-main {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
  min-height: 0;
}

.app-main-full {
  grid-template-columns: 1fr;
  padding: 0;
}

.sidebar-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: auto;
}

.sidebar-left::-webkit-scrollbar {
  width: 6px;
}

.sidebar-left::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.sidebar-spacer {
  flex: 1;
  min-height: 0;
}

.main-content {
  min-height: 0;
  min-width: 0;
}

.sidebar-right {
  min-height: 0;
  min-width: 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 14px;
  color: #94a3b8;
}

.empty-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px 24px;
  gap: 12px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  color: #475569;
  text-align: center;
  backdrop-filter: blur(8px);
}

.empty-title {
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  margin-top: 4px;
}

.empty-desc {
  font-size: 12px;
  color: #475569;
  max-width: 220px;
  line-height: 1.6;
}
</style>
