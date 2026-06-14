<template>
  <LoginView v-if="!isAuthenticated" @login-success="onLoginSuccess" />

  <div v-else class="app-root">
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
            v-if="canViewMonitoring"
            class="nav-tab"
            :class="{ active: currentView === 'monitoring' }"
            @click="switchView('monitoring')"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polygon points="10 8 16 12 10 16 10 8"></polygon>
            </svg>
            监控视图
          </button>
          <button
            v-if="canViewAlert"
            class="nav-tab"
            :class="{ active: currentView === 'alert' }"
            @click="switchView('alert')"
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
            v-if="canViewTrend"
            class="nav-tab"
            :class="{ active: currentView === 'trend' }"
            @click="switchView('trend')"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            趋势分析
          </button>
          <button
            v-if="canViewModel"
            class="nav-tab"
            :class="{ active: currentView === 'model' }"
            @click="switchView('model')"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
              <path d="M2 17l10 5 10-5"></path>
              <path d="M2 12l10 5 10-5"></path>
            </svg>
            模型管理
          </button>
          <button
            v-if="canViewConfig"
            class="nav-tab"
            :class="{ active: currentView === 'config' }"
            @click="switchView('config')"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 15a1.65 1.65 0 0 0-1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            配置中心
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
          <select v-model.number="refreshInterval" class="interval-select" :disabled="!autoRefresh || !canWrite">
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
            :disabled="!canWrite"
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

        <div class="user-section">
          <div class="user-info" @click="showUserMenu = !showUserMenu">
            <div class="user-avatar" :style="{ background: avatarGradient }">
              {{ avatarInitial }}
            </div>
            <div class="user-details">
              <div class="user-name">{{ displayName }}</div>
              <div class="user-role" :style="{ color: roleColor }">
                {{ roleText }}
                <span v-if="authMethod === 'api_key'" class="auth-method-tag">API Key</span>
              </div>
            </div>
            <svg class="user-dropdown-icon" :class="{ rotated: showUserMenu }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>

          <transition name="dropdown">
            <div v-if="showUserMenu" class="user-menu" @click.self="showUserMenu = false">
              <div class="user-menu-header">
                <div class="user-menu-avatar" :style="{ background: avatarGradient }">
                  {{ avatarInitial }}
                </div>
                <div class="user-menu-info">
                  <div class="user-menu-name">{{ displayName }}</div>
                  <div class="user-menu-username" v-if="currentUser?.username">
                    @{{ currentUser.username }}
                  </div>
                  <div class="user-menu-tenant" v-if="currentUser?.tenant_name">
                    {{ currentUser.tenant_name }}
                  </div>
                </div>
              </div>
              <div class="user-menu-divider"></div>
              <div class="user-menu-permissions">
                <div class="permissions-title">权限信息</div>
                <div class="permissions-list">
                  <span v-for="p in displayPermissions" :key="p" class="permission-chip">
                    {{ permissionText(p) }}
                  </span>
                </div>
              </div>
              <div class="user-menu-divider"></div>
              <button class="user-menu-item menu-logout" @click="handleLogout">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                退出登录
              </button>
            </div>
          </transition>
        </div>
      </div>
    </header>

    <main class="app-main" :class="{ 'app-main-full': currentView === 'alert' || currentView === 'trend' || currentView === 'model' || currentView === 'config' }">
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

      <ConfigurationCenter v-else-if="currentView === 'config'" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, computed, nextTick } from 'vue'
import FilterPanel from '@/components/FilterPanel.vue'
import StatsPanel from '@/components/StatsPanel.vue'
import FlangeTopology from '@/components/FlangeTopology.vue'
import DetailPanel from '@/components/DetailPanel.vue'
import AlertCenter from '@/components/AlertCenter.vue'
import TrendAnalysis from '@/components/TrendAnalysis.vue'
import ModelManagement from '@/components/ModelManagement.vue'
import ConfigCenter from '@/components/ConfigCenter.vue'
import LoginView from '@/components/LoginView.vue'
import { fetchTopology, fetchCollectors, fetchPositions } from '@/api/monitoring'
import { fetchAlertStats } from '@/api/alert'
import { useAuth } from '@/composables/useAuth'
import { UserRoleMap, UserRoleColorMap } from '@/types'
import type { TopologyData, FilterOptions, Flange, Bolt, Permission, UserRole } from '@/types'

const {
  initAuth,
  isAuthenticated,
  isLoading,
  currentUser,
  displayName,
  userRole,
  authMethod,
  permissions,
  canViewMonitoring,
  canViewAlert,
  canViewTrend,
  canViewModel,
  canViewConfig,
  canWrite,
  hasPermission,
  logout
} = useAuth()

type ViewName = 'monitoring' | 'alert' | 'trend' | 'model' | 'config'

const currentView = ref<ViewName>('monitoring')
const showUserMenu = ref(false)

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

const avatarInitial = computed(() => {
  const name = displayName.value || 'U'
  return name.charAt(0).toUpperCase()
})

const avatarGradient = computed(() => {
  const role = userRole.value
  const gradients: Record<UserRole, string> = {
    tenant_admin: 'linear-gradient(135deg, #ef4444, #dc2626)',
    admin: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
    operator: 'linear-gradient(135deg, #3b82f6, #2563eb)',
    viewer: 'linear-gradient(135deg, #64748b, #475569)',
    anonymous: 'linear-gradient(135deg, #94a3b8, #64748b)',
    api_key: 'linear-gradient(135deg, #f97316, #ea580c)'
  }
  return gradients[role] || gradients.anonymous
})

const roleText = computed(() => UserRoleMap[userRole.value] || '未知角色')
const roleColor = computed(() => UserRoleColorMap[userRole.value] || '#94a3b8')

const displayPermissions = computed(() => {
  const perms = permissions.value
  if (perms.includes('tenant_admin')) return ['tenant_admin']
  if (perms.includes('admin')) return ['admin']
  if (perms.includes('write')) return ['read', 'write']
  if (perms.includes('read')) return ['read']
  return perms.slice(0, 4)
})

function permissionText(p: Permission | string): string {
  const map: Record<string, string> = {
    read: '读取',
    write: '写入',
    admin: '管理',
    tenant_admin: '租户管理',
    'monitoring:read': '监控读取',
    'alert:read': '预警读取',
    'alert:handle': '预警处理',
    'model:read': '模型读取',
    'model:train': '模型训练',
    'config:read': '配置读取',
    'config:write': '配置写入'
  }
  return map[p] || p
}

function switchView(view: ViewName) {
  const allowed: Record<ViewName, boolean> = {
    monitoring: canViewMonitoring.value,
    alert: canViewAlert.value,
    trend: canViewTrend.value,
    model: canViewModel.value,
    config: canViewConfig.value
  }
  if (!allowed[view]) return
  currentView.value = view
  showUserMenu.value = false
}

function ensureValidView() {
  const allowed: Record<ViewName, boolean> = {
    monitoring: canViewMonitoring.value,
    alert: canViewAlert.value,
    trend: canViewTrend.value,
    model: canViewModel.value,
    config: canViewConfig.value
  }
  if (!allowed[currentView.value]) {
    const firstAllowed = (Object.keys(allowed) as ViewName[]).find(v => allowed[v])
    if (firstAllowed) {
      currentView.value = firstAllowed
    }
  }
}

async function onLoginSuccess() {
  await nextTick()
  ensureValidView()
  loadData(true)
  setupTimer()
  loadAlertStats()
  setupAlertStatsTimer()
}

async function handleLogout() {
  await logout()
  showUserMenu.value = false
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (alertStatsTimer) {
    clearInterval(alertStatsTimer)
    alertStatsTimer = null
  }
  topologyData.value = null
  selectedBolt.value = null
  selectedFlange.value = null
}

async function loadData(force = false) {
  if (!isAuthenticated.value) return
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
  if (!canWrite.value) return
  autoRefresh.value = !autoRefresh.value
  setupTimer()
}

function setupTimer() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (autoRefresh.value && isAuthenticated.value) {
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
  if (!isAuthenticated.value) return
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
  if (isAuthenticated.value) {
    alertStatsTimer = setInterval(() => {
      loadAlertStats()
    }, 30000)
  }
}

watch(refreshInterval, () => {
  setupTimer()
})

watch(isAuthenticated, (val) => {
  if (val) {
    ensureValidView()
    loadData(true)
    setupTimer()
    loadAlertStats()
    setupAlertStatsTimer()
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
    if (alertStatsTimer) {
      clearInterval(alertStatsTimer)
      alertStatsTimer = null
    }
  }
})

document.addEventListener('click', (e) => {
  const target = e.target as HTMLElement
  if (!target.closest('.user-section')) {
    showUserMenu.value = false
  }
})

onMounted(async () => {
  await initAuth()
  if (isAuthenticated.value) {
    ensureValidView()
    loadData(true)
    setupTimer()
    loadAlertStats()
    setupAlertStatsTimer()
  }
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

.user-section {
  margin-left: 16px;
  padding-left: 16px;
  border-left: 1px solid rgba(59, 130, 246, 0.15);
  position: relative;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.user-info:hover {
  background: rgba(30, 41, 59, 0.8);
}

.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.user-role {
  font-size: 11px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.auth-method-tag {
  padding: 1px 5px;
  background: rgba(249, 115, 22, 0.15);
  border: 1px solid rgba(249, 115, 22, 0.3);
  border-radius: 4px;
  font-size: 9px;
  color: #fb923c;
}

.user-dropdown-icon {
  color: #64748b;
  transition: transform 0.2s;
  flex-shrink: 0;
}

.user-dropdown-icon.rotated {
  transform: rotate(180deg);
}

.user-menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 280px;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  z-index: 100;
  backdrop-filter: blur(12px);
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.user-menu-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(30, 41, 59, 0.6);
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
}

.user-menu-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.user-menu-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.user-menu-name {
  font-size: 15px;
  font-weight: 600;
  color: #f1f5f9;
}

.user-menu-username {
  font-size: 12px;
  color: #64748b;
}

.user-menu-tenant {
  font-size: 11px;
  color: #3b82f6;
  margin-top: 2px;
}

.user-menu-divider {
  height: 1px;
  background: rgba(59, 130, 246, 0.1);
  margin: 0 16px;
}

.user-menu-permissions {
  padding: 12px 16px;
}

.permissions-title {
  font-size: 11px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  margin-bottom: 8px;
}

.permissions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.permission-chip {
  padding: 4px 10px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  color: #60a5fa;
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  font-size: 13px;
}

.user-menu-item:hover {
  background: rgba(30, 41, 59, 0.8);
}

.menu-logout {
  color: #f87171;
  border-top: 1px solid rgba(59, 130, 246, 0.1);
}

.menu-logout:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.header-right {
  display: flex;
  align-items: center;
}
</style>
