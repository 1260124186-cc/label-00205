<template>
  <div class="workorder-list-page">
    <div class="filter-bar">
      <div class="filter-tabs">
        <button
          v-for="tab in statusTabs"
          :key="tab.value"
          class="filter-tab"
          :class="{ active: currentStatus === tab.value }"
          @click="switchStatus(tab.value)"
        >
          {{ tab.label }}
          <span v-if="tab.count > 0" class="tab-count">{{ tab.count }}</span>
        </button>
      </div>
    </div>

    <div class="list-container" ref="listContainer" @scroll="onScroll">
      <div v-if="loading && workOrders.length === 0" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="workOrders.length === 0" class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="9" y1="13" x2="15" y2="13"></line>
          <line x1="9" y1="17" x2="15" y2="17"></line>
        </svg>
        <p class="empty-title">暂无工单</p>
        <p class="empty-desc">当前筛选条件下没有工单</p>
      </div>

      <div v-else class="workorder-list">
        <div
          v-for="wo in workOrders"
          :key="wo.id"
          class="workorder-card"
          @click="goToDetail(wo.id)"
        >
          <div class="card-header">
            <span class="order-no">{{ wo.order_no }}</span>
            <span :class="['priority-badge', `priority-${wo.priority}`]">
              {{ priorityText(wo.priority) }}
            </span>
          </div>

          <h3 class="card-title">{{ wo.title }}</h3>

          <div v-if="wo.description" class="card-desc">
            {{ wo.description }}
          </div>

          <div class="card-info">
            <div class="info-item">
              <span class="info-label">节点</span>
              <span class="info-value">{{ wo.node_id || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">风险</span>
              <span :class="['risk-value', getRiskClass(wo.risk_score)]">
                {{ wo.risk_score?.toFixed(1) || '-' }}
              </span>
            </div>
          </div>

          <div class="card-footer">
            <span :class="['status-badge', `status-${wo.status}`]">
              {{ statusText(wo.status) }}
            </span>
            <span class="create-time">{{ formatTime(wo.create_time) }}</span>
          </div>

          <div class="card-arrow">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </div>
        </div>

        <div v-if="loadingMore" class="loading-more">
          <div class="spinner small"></div>
          <span>加载更多...</span>
        </div>

        <div v-if="!hasMore && workOrders.length > 0" class="no-more">
          — 没有更多了 —
        </div>
      </div>
    </div>

    <button class="fab-btn" @click="goToScan">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 7V5a2 2 0 0 1 2-2h2"></path>
        <path d="M17 3h2a2 2 0 0 1 2 2v2"></path>
        <path d="M21 17v2a2 2 0 0 1-2 2h-2"></path>
        <path d="M7 21H5a2 2 0 0 1-2-2v-2"></path>
        <line x1="7" y1="12" x2="17" y2="12"></line>
      </svg>
      <span>扫码</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { fetchWorkOrders } from '@/api'
import { useOfflineStore } from '@/stores/offline'
import type { WorkOrder } from '@/types'

const router = useRouter()
const offlineStore = useOfflineStore()

const workOrders = ref<WorkOrder[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const currentPage = ref(1)
const hasMore = ref(true)
const listContainer = ref<HTMLElement | null>(null)

const statusTabs = ref([
  { label: '待处理', value: 'pending', count: 0 },
  { label: '处理中', value: 'in_progress', count: 0 },
  { label: '全部', value: 'all', count: 0 }
])

const currentStatus = ref('pending')

const statusMap: Record<string, string[]> = {
  pending: ['open', 'assigned'],
  in_progress: ['in_progress'],
  all: []
}

async function loadWorkOrders(refresh = false) {
  if (refresh) {
    currentPage.value = 1
    hasMore.value = true
    workOrders.value = []
  }

  if (!hasMore.value) return

  if (refresh) {
    loading.value = true
  } else {
    loadingMore.value = true
  }

  try {
    const statuses = statusMap[currentStatus.value] || []
    const filters: any = {}
    if (statuses.length === 1) {
      filters.status = statuses[0]
    }

    const response = await fetchWorkOrders(filters, currentPage.value, 20)
    const items = response.items || []

    if (refresh) {
      workOrders.value = items
      offlineStore.cacheWorkOrders(items)
    } else {
      workOrders.value = [...workOrders.value, ...items]
    }

    hasMore.value = items.length === 20
    if (hasMore.value) {
      currentPage.value++
    }
  } catch (e) {
    console.error('加载工单失败:', e)
    if (refresh) {
      const cached = offlineStore.getCachedWorkOrders()
      if (cached && cached.length > 0) {
        workOrders.value = cached
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
    loadWorkOrders(false)
  }
}

function switchStatus(status: string) {
  currentStatus.value = status
  loadWorkOrders(true)
}

function goToDetail(id: number) {
  router.push(`/workorders/${id}`)
}

function goToScan() {
  router.push('/scan')
}

function priorityText(priority: string): string {
  const map: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
    urgent: '紧急'
  }
  return map[priority] || priority
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    open: '待分配',
    assigned: '已指派',
    in_progress: '处理中',
    resolved: '已解决',
    closed: '已关闭',
    retested: '已复测'
  }
  return map[status] || status
}

function getRiskClass(riskScore?: number): string {
  if (!riskScore) return 'risk-normal'
  if (riskScore >= 70) return 'risk-critical'
  if (riskScore >= 40) return 'risk-warning'
  return 'risk-normal'
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
  loadWorkOrders(true)
})
</script>

<style scoped>
.workorder-list-page {
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
  gap: 8px;
  background: rgba(30, 41, 59, 0.6);
  padding: 4px;
  border-radius: 10px;
}

.filter-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-tab.active {
  background: var(--primary-color);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.tab-count {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.filter-tab:not(.active) .tab-count {
  background: rgba(148, 163, 184, 0.2);
  color: var(--text-tertiary);
}

.list-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px 80px;
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

.workorder-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.workorder-card {
  position: relative;
  padding: 16px;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  overflow: hidden;
}

.workorder-card:active {
  transform: scale(0.98);
  background: rgba(30, 41, 59, 0.9);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.order-no {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-tertiary);
  font-family: monospace;
}

.priority-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.priority-urgent {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.priority-high {
  background: rgba(249, 115, 22, 0.15);
  color: #fb923c;
  border: 1px solid rgba(249, 115, 22, 0.3);
}

.priority-medium {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.priority-low {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-info {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
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
  font-weight: 500;
  color: var(--text-secondary);
  font-family: monospace;
}

.risk-value {
  font-weight: 600;
}

.risk-normal {
  color: #4ade80;
}

.risk-warning {
  color: #fbbf24;
}

.risk-critical {
  color: #f87171;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.status-open {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.status-assigned {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
}

.status-in_progress {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.status-resolved {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.status-closed {
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
}

.status-retested {
  background: rgba(6, 182, 212, 0.15);
  color: #22d3ee;
}

.create-time {
  font-size: 12px;
  color: var(--text-tertiary);
}

.card-arrow {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
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

.fab-btn {
  position: fixed;
  right: 20px;
  bottom: calc(80px + var(--safe-area-bottom));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border-radius: 50%;
  color: white;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4);
  z-index: 100;
  transition: all 0.2s;
}

.fab-btn:active {
  transform: scale(0.92);
}

.fab-btn span {
  font-size: 10px;
  font-weight: 500;
}
</style>
