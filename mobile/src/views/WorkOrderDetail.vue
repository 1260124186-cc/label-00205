<template>
  <div class="workorder-detail-page">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="workOrder" class="detail-content">
      <div class="detail-header">
        <div class="header-top">
          <span class="order-no">{{ workOrder.order_no }}</span>
          <span :class="['priority-badge', `priority-${workOrder.priority}`]">
            {{ priorityText(workOrder.priority) }}
          </span>
        </div>
        <h2 class="detail-title">{{ workOrder.title }}</h2>
        <div class="header-meta">
          <span :class="['status-badge', `status-${workOrder.status}`]">
            {{ statusText(workOrder.status) }}
          </span>
          <span class="create-time">{{ formatDateTime(workOrder.create_time) }}</span>
        </div>
      </div>

      <div class="info-section">
        <h3 class="section-title">基本信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">节点类型</span>
            <span class="info-value">{{ workOrder.node_type || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">节点ID</span>
            <span class="info-value mono">{{ workOrder.node_id || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">告警级别</span>
            <span :class="['info-value', `level-${workOrder.alert_level}`]">
              {{ workOrder.alert_level ? `Lv.${workOrder.alert_level}` : '-' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">风险评分</span>
            <span :class="['info-value', getRiskClass(workOrder.risk_score)]">
              {{ workOrder.risk_score?.toFixed(1) || '-' }}
            </span>
          </div>
          <div class="info-item full-width">
            <span class="info-label">处理人</span>
            <span class="info-value">{{ workOrder.assignee_name || '未指派' }}</span>
          </div>
          <div class="info-item full-width">
            <span class="info-label">截止时间</span>
            <span class="info-value">{{ workOrder.due_time ? formatDateTime(workOrder.due_time) : '-' }}</span>
          </div>
        </div>
      </div>

      <div v-if="workOrder.description" class="info-section">
        <h3 class="section-title">工单描述</h3>
        <p class="desc-text">{{ workOrder.description }}</p>
      </div>

      <div v-if="workOrder.recommendations && workOrder.recommendations.length > 0" class="info-section">
        <h3 class="section-title">推荐措施</h3>
        <ul class="recommendation-list">
          <li v-for="(rec, index) in workOrder.recommendations" :key="index" class="rec-item">
            <span class="rec-number">{{ index + 1 }}</span>
            <span class="rec-text">{{ rec }}</span>
          </li>
        </ul>
      </div>

      <div class="info-section">
        <h3 class="section-title">复测记录</h3>
        <div v-if="retestRecords.length === 0" class="empty-retest">
          <p>暂无复测记录</p>
        </div>
        <div v-else class="retest-list">
          <div v-for="record in retestRecords" :key="record.id" class="retest-item">
            <div class="retest-header">
              <span :class="['retest-result', `result-${record.retest_result}`]">
                {{ retestResultText(record.retest_result) }}
              </span>
              <span class="retest-time">{{ formatDateTime(record.retest_time || record.create_time) }}</span>
            </div>
            <div class="retest-info">
              <div class="info-row">
                <span class="info-label">复测人</span>
                <span class="info-value">{{ record.retester_name || '-' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">测量值</span>
                <span class="info-value">{{ record.measured_value != null ? record.measured_value : '-' }}</span>
              </div>
              <div v-if="record.retest_notes" class="info-row">
                <span class="info-label">备注</span>
                <span class="info-value">{{ record.retest_notes }}</span>
              </div>
            </div>
            <div v-if="record.photos && record.photos.length > 0" class="retest-photos">
              <img
                v-for="(photo, idx) in record.photos"
                :key="idx"
                :src="photo"
                class="photo-thumb"
                @click="previewPhoto(photo)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="bottom-actions">
      <button class="action-btn secondary" @click="goToScan">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 7V5a2 2 0 0 1 2-2h2"></path>
          <path d="M17 3h2a2 2 0 0 1 2 2v2"></path>
          <path d="M21 17v2a2 2 0 0 1-2 2h-2"></path>
          <path d="M7 21H5a2 2 0 0 1-2-2v-2"></path>
          <line x1="7" y1="12" x2="17" y2="12"></line>
        </svg>
        扫码巡检
      </button>
      <button class="action-btn primary" @click="goToRetest">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
        一键复测
      </button>
    </div>

    <div v-if="showPhotoPreview" class="photo-preview" @click="closePhotoPreview">
      <img :src="previewUrl" class="preview-image" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchWorkOrderDetail, fetchRetestRecords } from '@/api'
import { useOfflineStore } from '@/stores/offline'
import type { WorkOrder, RetestRecord } from '@/types'

const route = useRoute()
const router = useRouter()
const offlineStore = useOfflineStore()

const workOrder = ref<WorkOrder | null>(null)
const retestRecords = ref<RetestRecord[]>([])
const loading = ref(true)
const showPhotoPreview = ref(false)
const previewUrl = ref('')

const workOrderId = computed(() => Number(route.params.id))

import { computed } from 'vue'

async function loadDetail() {
  loading.value = true
  try {
    workOrder.value = await fetchWorkOrderDetail(workOrderId.value)
    await loadRetestRecords()
  } catch (e) {
    console.error('加载工单详情失败:', e)
  } finally {
    loading.value = false
  }
}

async function loadRetestRecords() {
  try {
    const response = await fetchRetestRecords(workOrderId.value, 1, 20)
    retestRecords.value = response.items || []
    offlineStore.cacheRetestRecords(workOrderId.value, retestRecords.value)
  } catch (e) {
    console.error('加载复测记录失败:', e)
    const cached = offlineStore.getCachedRetestRecords(workOrderId.value)
    if (cached) {
      retestRecords.value = cached
    }
  }
}

function goToRetest() {
  router.push(`/workorders/${workOrderId.value}/retest`)
}

function goToScan() {
  router.push('/scan')
}

function previewPhoto(url: string) {
  previewUrl.value = url
  showPhotoPreview.value = true
}

function closePhotoPreview() {
  showPhotoPreview.value = false
}

function priorityText(priority: string): string {
  const map: Record<string, string> = {
    low: '低优先级',
    medium: '中优先级',
    high: '高优先级',
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

function retestResultText(result: string): string {
  const map: Record<string, string> = {
    pass: '通过',
    fail: '不通过',
    pending: '待确认'
  }
  return map[result] || result
}

function getRiskClass(riskScore?: number): string {
  if (!riskScore) return 'risk-normal'
  if (riskScore >= 70) return 'risk-critical'
  if (riskScore >= 40) return 'risk-warning'
  return 'risk-normal'
}

function formatDateTime(timeStr: string): string {
  const date = new Date(timeStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

onMounted(() => {
  loadDetail()
})
</script>

<style scoped>
.workorder-detail-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding-bottom: 80px;
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

.detail-header {
  padding: 16px;
  background: rgba(30, 41, 59, 0.6);
  border-bottom: 1px solid var(--border-light);
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.order-no {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: monospace;
}

.priority-badge {
  padding: 3px 10px;
  border-radius: 12px;
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

.detail-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
  margin-bottom: 10px;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
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

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item.full-width {
  grid-column: span 2;
}

.info-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.info-value {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.info-value.mono {
  font-family: monospace;
}

.level-1 { color: #4ade80; }
.level-2 { color: #fbbf24; }
.level-3 { color: #f97316; }
.level-4 { color: #ef4444; }

.risk-normal { color: #4ade80; }
.risk-warning { color: #fbbf24; }
.risk-critical { color: #ef4444; }

.desc-text {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.recommendation-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rec-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
}

.rec-number {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-color);
  color: white;
  font-size: 11px;
  font-weight: 600;
  border-radius: 50%;
}

.rec-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.empty-retest {
  text-align: center;
  padding: 20px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.retest-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.retest-item {
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid var(--border-light);
  border-radius: 10px;
}

.retest-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.retest-result {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.result-pass {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.result-fail {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.result-pending {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.retest-time {
  font-size: 11px;
  color: var(--text-tertiary);
}

.retest-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-row .info-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.info-row .info-value {
  font-size: 13px;
  color: var(--text-secondary);
}

.retest-photos {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.photo-thumb {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid var(--border-light);
}

.bottom-actions {
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
  gap: 6px;
  height: 48px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  transition: all 0.2s;
}

.action-btn:active {
  transform: scale(0.97);
}

.action-btn.secondary {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.action-btn.primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
}

.photo-preview {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
</style>
