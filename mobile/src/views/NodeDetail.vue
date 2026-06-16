<template>
  <div class="node-detail-page">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else class="detail-content">
      <div class="node-header">
        <div class="node-icon" :class="`icon-${nodeType}`">
          <svg v-if="nodeType === 'bolt'" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M8 12h8"></path>
            <path d="M12 8v8"></path>
          </svg>
          <svg v-else width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <ellipse cx="12" cy="12" rx="10" ry="6"></ellipse>
            <path d="M12 6v12"></path>
            <path d="M2 12h4"></path>
            <path d="M18 12h4"></path>
          </svg>
        </div>
        <div class="node-info">
          <h2 class="node-name">{{ nodeInfo?.node_name || orgNodeId }}</h2>
          <p class="node-id">{{ orgNodeId }}</p>
          <span :class="['node-type', `type-${nodeType}`]">{{ nodeTypeText }}</span>
        </div>
      </div>

      <div class="info-section">
        <h3 class="section-title">位置信息</h3>
        <div class="info-row">
          <span class="info-label">所在位置</span>
          <span class="info-value">{{ nodeInfo?.location || '-' }}</span>
        </div>
      </div>

      <div class="info-section">
        <h3 class="section-title">相关工单</h3>
        <div v-if="workOrders.length === 0" class="empty-orders">
          <p>暂无相关工单</p>
        </div>
        <div v-else class="order-list">
          <div
            v-for="wo in workOrders"
            :key="wo.id"
            class="order-item"
            @click="goToWorkOrder(wo.id)"
          >
            <div class="order-info">
              <span class="order-no">{{ wo.order_no }}</span>
              <span :class="['priority-badge', `priority-${wo.priority}`]">
                {{ priorityText(wo.priority) }}
              </span>
            </div>
            <p class="order-title">{{ wo.title }}</p>
            <div class="order-footer">
              <span :class="['status-badge', `status-${wo.status}`]">
                {{ statusText(wo.status) }}
              </span>
              <span class="order-time">{{ formatTime(wo.create_time) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="action-section">
        <button class="action-btn primary" @click="startInspection">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          开始巡检
        </button>
        <button class="action-btn secondary" @click="goBack">
          返回
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchOrgNodeInfo, fetchWorkOrders } from '@/api'
import type { OrgNodeInfo, WorkOrder } from '@/types'

const route = useRoute()
const router = useRouter()

const orgNodeId = computed(() => {
  const id = route.params.orgNodeId as string
  return decodeURIComponent(id)
})

const nodeInfo = ref<OrgNodeInfo | null>(null)
const workOrders = ref<WorkOrder[]>([])
const loading = ref(true)

const nodeType = computed(() => nodeInfo.value?.node_type || 'bolt')
const nodeTypeText = computed(() => {
  const map: Record<string, string> = {
    bolt: '螺栓',
    flange: '法兰面',
    production_line: '生产线'
  }
  return map[nodeType.value] || nodeType.value
})

async function loadNodeInfo() {
  loading.value = true
  try {
    try {
      nodeInfo.value = await fetchOrgNodeInfo(orgNodeId.value)
    } catch (e) {
      console.warn('获取节点信息失败，使用默认值:', e)
      nodeInfo.value = {
        node_id: orgNodeId.value,
        node_type: orgNodeId.value.includes('flange') ? 'flange' : 'bolt'
      }
    }

    await loadWorkOrders()
  } finally {
    loading.value = false
  }
}

async function loadWorkOrders() {
  try {
    const response = await fetchWorkOrders({ status: 'pending' }, 1, 10)
    workOrders.value = response.items || []
  } catch (e) {
    console.error('加载工单失败:', e)
  }
}

function goToWorkOrder(id: number) {
  router.push(`/workorders/${id}`)
}

function startInspection() {
  router.push('/workorders?node_id=' + encodeURIComponent(orgNodeId.value))
}

function goBack() {
  router.back()
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
    closed: '已关闭'
  }
  return map[status] || status
}

function formatTime(timeStr: string): string {
  const date = new Date(timeStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

onMounted(() => {
  loadNodeInfo()
})
</script>

<style scoped>
.node-detail-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding-bottom: 100px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
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

@keyframes spin {
  to { transform: rotate(360deg); }
}

.detail-content {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 16px;
  background: rgba(30, 41, 59, 0.6);
  border-bottom: 1px solid var(--border-light);
}

.node-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  flex-shrink: 0;
}

.node-icon.icon-bolt {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.node-icon.icon-flange {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-id {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: monospace;
  margin-bottom: 8px;
}

.node-type {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.node-type.type-bolt {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.node-type.type-flange {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
}

.node-type.type-production_line {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.info-section {
  padding: 16px;
  border-bottom: 1px solid var(--border-light);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.info-label {
  font-size: 13px;
  color: var(--text-tertiary);
}

.info-value {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.empty-orders {
  text-align: center;
  padding: 20px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.order-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.order-item {
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.order-item:active {
  transform: scale(0.98);
  background: rgba(30, 41, 59, 0.8);
}

.order-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.order-no {
  font-size: 12px;
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
}

.priority-high {
  background: rgba(249, 115, 22, 0.15);
  color: #fb923c;
}

.priority-medium {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.priority-low {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.order-title {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.order-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 10px;
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

.order-time {
  font-size: 12px;
  color: var(--text-tertiary);
}

.action-section {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  padding-bottom: calc(12px + var(--safe-area-bottom));
  background: rgba(15, 23, 42, 0.95);
  border-top: 1px solid var(--border-color);
  backdrop-filter: blur(10px);
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 48px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  transition: all 0.2s;
}

.action-btn.primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
}

.action-btn.secondary {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.action-btn:active {
  transform: scale(0.97);
}
</style>
