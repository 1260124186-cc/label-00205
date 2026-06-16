<template>
  <div class="alert-list-page">
    <div class="filter-bar">
      <div class="filter-tabs">
        <button
          v-for="tab in levelTabs"
          :key="tab.value"
          class="filter-tab"
          :class="{ active: currentLevel === tab.value }"
          @click="switchLevel(tab.value)"
        >
          <span class="level-dot" :class="`dot-${tab.value}`"></span>
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="list-container" ref="listContainer" @scroll="onScroll">
      <div v-if="loading && alerts.length === 0" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="alerts.length === 0" class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <p class="empty-title">暂无预警</p>
        <p class="empty-desc">当前筛选条件下没有预警记录</p>
      </div>

      <div v-else class="alert-list">
        <div
          v-for="alert in alerts"
          :key="alert.id"
          class="alert-card"
          :class="`level-${alert.alert_level}`"
          @click="goToAlertDetail(alert.id)"
        >
          <div class="card-header">
            <div class="alert-level">
              <span class="level-badge" :class="`badge-${alert.alert_level}`">
                Lv.{{ alert.alert_level }}
              </span>
            </div>
            <span :class="['status-badge', `status-${alert.status}`]">
              {{ statusText(alert.status) }}
            </span>
          </div>

          <h3 class="card-title">{{ alert.title || '预警通知' }}</h3>

          <p v-if="alert.content" class="card-content">
            {{ alert.content }}
          </p>

          <div class="card-info">
            <div class="info-item">
              <span class="info-label">节点</span>
              <span class="info-value">{{ alert.node_id || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">风险</span>
              <span class="info-value risk">{{ alert.risk_score?.toFixed(1) || '-' }}</span>
            </div>
          </div>

          <div class="card-footer">
            <span class="create-time">{{ formatTime(alert.create_time) }}</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="arrow">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </div>
        </div>

        <div v-if="loadingMore" class="loading-more">
          <div class="spinner small"></div>
          <span>加载更多...</span>
        </div>

        <div v-if="!hasMore && alerts.length > 0" class="no-more">
          — 没有更多了 —
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchAlerts } from '@/api'
import { useOfflineStore } from '@/stores/offline'
import type { AlertEvent } from '@/types'

const router = useRouter()
const offlineStore = useOfflineStore()

const alerts = ref<AlertEvent[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const currentPage = ref(1)
const hasMore = ref(true)
const listContainer = ref<HTMLElement | null>(null)

const levelTabs = ref([
  { label: '全部', value: 'all' },
  { label: '紧急', value: 4 },
  { label: '高', value: 3 },
  { label: '中', value: 2 },
  { label: '低', value: 1 }
])

const currentLevel = ref<string | number>('all')

async function loadAlerts(refresh = false) {
  if (refresh) {
    currentPage.value = 1
    hasMore.value = true
    alerts.value = []
  }

  if (!hasMore.value) return

  if (refresh) {
    loading.value = true
  } else {
    loadingMore.value = true
  }

  try {
    const filters: any = {}
    if (currentLevel.value !== 'all') {
      filters.alert_level = currentLevel.value
    }

    const response = await fetchAlerts(filters, currentPage.value, 20)
    const items = response.items || []

    if (refresh) {
      alerts.value = items
      offlineStore.cacheAlerts(items)
    } else {
      alerts.value = [...alerts.value, ...items]
    }

    hasMore.value = items.length === 20
    if (hasMore.value) {
      currentPage.value++
    }
  } catch (e) {
    console.error('加载预警失败:', e)
    if (refresh) {
      const cached = offlineStore.getCachedAlerts()
      if (cached && cached.length > 0) {
        alerts.value = cached
      }
    }
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

function onScroll(e: Event) {
  const target = e.target as HTMLElement
  const scrollBottom = target.scrollTop + target.clientHeight
  const scrollHeight = target.scrollHeight

  if (scrollBottom >= scrollHeight - 100 && !loadingMore.value && hasMore.value) {
    loadAlerts(false)
  }
}

function switchLevel(level: string | number) {
  currentLevel.value = level
  loadAlerts(true)
}

function goToAlertDetail(id: number) {
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    resolved: '已解决',
    ignored: '已忽略',
    closed: '已关闭'
  }
  return map[status] || status
}

function formatTime(timeStr: string): string {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60))
    if (hours === 0) {
      const minutes = Math.floor(diff / (1000 * 60))
      return `${minutes}分钟前`
    }
    return `${hours}小时前`
  } else if (days === 1) {
    return '昨天'
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return `${date.getMonth() + 1}/${date.getDate()}`
  }
}

onMounted(() => {
  loadAlerts(true)
})
</script>

<style scoped>
.alert-list-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.filter-bar {
  padding: 12px 16px;
  background: rgba(15, 23, 42, 0.9);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.filter-tabs {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(30, 41, 59, 0.6);
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.2s;
}

.filter-tab.active {
  background: var(--primary-color);
  color: white;
}

.level-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.dot-all { background: #94a3b8; }
.dot-4 { background: #ef4444; }
.dot-3 { background: #f97316; }
.dot-2 { background: #f59e0b; }
.dot-1 { background: #22c55e; }

.list-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  -webkit-overflow-scrolling: touch;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  gap: 12px;
  color: var(--text-tertiary);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner.small {
  width: 18px;
  height: 18px;
  border-width: 2px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  gap: 12px;
  color: var(--text-tertiary);
  text-align: center;
}

.empty-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-secondary);
}

.empty-desc {
  font-size: 13px;
  color: var(--text-tertiary);
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-card {
  position: relative;
  padding: 14px 16px;
  background: rgba(30, 41, 59, 0.7);
  border-left: 4px solid;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  overflow: hidden;
}

.alert-card:active {
  transform: scale(0.98);
  background: rgba(30, 41, 59, 0.9);
}

.alert-card.level-1 { border-left-color: #22c55e; }
.alert-card.level-2 { border-left-color: #f59e0b; }
.alert-card.level-3 { border-left-color: #f97316; }
.alert-card.level-4 { border-left-color: #ef4444; }

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.level-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.badge-1 {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.badge-2 {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.badge-3 {
  background: rgba(249, 115, 22, 0.15);
  color: #fb923c;
}

.badge-4 {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.status-pending {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.status-processing {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.status-resolved {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.status-ignored {
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
}

.status-closed {
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
  line-height: 1.4;
}

.card-content {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-info {
  display: flex;
  gap: 20px;
  margin-bottom: 10px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.info-value {
  font-size: 13px;
  color: var(--text-secondary);
  font-family: monospace;
}

.info-value.risk {
  font-weight: 600;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.create-time {
  font-size: 12px;
  color: var(--text-tertiary);
}

.arrow {
  color: var(--text-tertiary);
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.no-more {
  text-align: center;
  padding: 16px;
  color: var(--text-tertiary);
  font-size: 12px;
}
</style>
