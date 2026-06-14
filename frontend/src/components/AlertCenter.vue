<template>
  <div class="alert-center">
    <div class="alert-header">
      <div class="alert-title">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <h2>预警中心</h2>
      </div>
      <div class="header-actions">
        <button class="refresh-btn" @click="loadAlerts">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card stat-pending">
        <div class="stat-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.pending }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </div>
      <div class="stat-card stat-processing">
        <div class="stat-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.processing }}</div>
          <div class="stat-label">处理中</div>
        </div>
      </div>
      <div class="stat-card stat-resolved">
        <div class="stat-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.resolved }}</div>
          <div class="stat-label">已解决</div>
        </div>
      </div>
      <div class="stat-card stat-levels">
        <div class="stat-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-level-row">
            <span class="level-dot level-1"></span>
            <span class="level-count">{{ stats.byLevel[1] || 0 }}</span>
          </div>
          <div class="stat-level-row">
            <span class="level-dot level-2"></span>
            <span class="level-count">{{ stats.byLevel[2] || 0 }}</span>
          </div>
          <div class="stat-level-row">
            <span class="level-dot level-3"></span>
            <span class="level-count">{{ stats.byLevel[3] || 0 }}</span>
          </div>
          <div class="stat-level-row">
            <span class="level-dot level-4"></span>
            <span class="level-count">{{ stats.byLevel[4] || 0 }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="alert-content">
      <aside class="filter-sidebar">
        <div class="filter-section">
          <div class="filter-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
            </svg>
            筛选条件
          </div>

          <div class="filter-group">
            <label class="filter-label">预警状态</label>
            <div class="filter-options">
              <label class="filter-option">
                <input type="radio" :checked="filters.status === null" @change="setStatus(null)" />
                <span>全部</span>
              </label>
              <label class="filter-option">
                <input type="radio" :checked="filters.status === 'pending'" @change="setStatus('pending')" />
                <span class="status-badge status-pending">待处理</span>
              </label>
              <label class="filter-option">
                <input type="radio" :checked="filters.status === 'processing'" @change="setStatus('processing')" />
                <span class="status-badge status-processing">处理中</span>
              </label>
              <label class="filter-option">
                <input type="radio" :checked="filters.status === 'resolved'" @change="setStatus('resolved')" />
                <span class="status-badge status-resolved">已解决</span>
              </label>
              <label class="filter-option">
                <input type="radio" :checked="filters.status === 'closed'" @change="setStatus('closed')" />
                <span class="status-badge status-closed">已关闭</span>
              </label>
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">预警等级</label>
            <div class="filter-options">
              <label class="filter-option">
                <input type="radio" :checked="filters.alert_level === null" @change="setLevel(null)" />
                <span>全部</span>
              </label>
              <label v-for="level in [1, 2, 3, 4]" :key="level" class="filter-option">
                <input type="radio" :checked="filters.alert_level === level" @change="setLevel(level as AlertLevel)" />
                <span class="level-badge" :style="{ borderColor: AlertLevelColorMap[level as AlertLevel], color: AlertLevelColorMap[level as AlertLevel] }">
                  {{ AlertLevelMap[level as AlertLevel] }}
                </span>
              </label>
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">预警策略</label>
            <div class="filter-options">
              <label class="filter-option">
                <input type="radio" :checked="filters.strategy_type === null" @change="setStrategy(null)" />
                <span>全部</span>
              </label>
              <label class="filter-option">
                <input type="radio" :checked="filters.strategy_type === 1" @change="setStrategy(1)" />
                <span>应报尽报</span>
              </label>
              <label class="filter-option">
                <input type="radio" :checked="filters.strategy_type === 2" @change="setStrategy(2)" />
                <span>精准报警</span>
              </label>
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">时间范围</label>
            <div class="time-filter">
              <div class="time-input">
                <span class="time-label">开始</span>
                <input type="date" v-model="localStartTime" @change="onTimeChange" />
              </div>
              <div class="time-input">
                <span class="time-label">结束</span>
                <input type="date" v-model="localEndTime" @change="onTimeChange" />
              </div>
              <div class="time-quick">
                <button class="quick-btn" @click="setQuickTime(1)">近1天</button>
                <button class="quick-btn" @click="setQuickTime(7)">近7天</button>
                <button class="quick-btn" @click="setQuickTime(30)">近30天</button>
                <button class="quick-btn" @click="clearTimeFilter">清除</button>
              </div>
            </div>
          </div>

          <div class="filter-actions">
            <button class="btn btn-secondary" @click="resetFilters">重置</button>
            <button class="btn btn-primary" @click="applyFilters">应用</button>
          </div>
        </div>
      </aside>

      <section class="alert-list-section">
        <div class="list-header">
          <div class="list-title">预警列表</div>
          <div class="list-info">共 {{ total }} 条</div>
        </div>

        <div class="alert-list">
          <div v-if="loading" class="loading-state">
            <div class="loading-spinner"></div>
            <div class="loading-text">正在加载预警数据...</div>
          </div>

          <div v-else-if="alerts.length === 0" class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            <div class="empty-title">暂无预警数据</div>
            <div class="empty-desc">当前筛选条件下没有预警记录</div>
          </div>

          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="alert-card"
            :class="{ 'expanded': expandedId === alert.id }"
          >
            <div class="alert-card-header" @click="toggleExpand(alert.id)">
              <div class="alert-left">
                <div class="alert-level" :style="{ background: AlertLevelColorMap[alert.alert_level] }">
                  {{ AlertLevelMap[alert.alert_level] }}
                </div>
                <div class="alert-main">
                  <div class="alert-title-row">
                    <span class="alert-no">{{ alert.alert_no }}</span>
                    <span class="alert-title-text">{{ alert.title }}</span>
                    <span v-if="alert.is_upgraded" class="upgrade-tag">已升级</span>
                  </div>
                  <div class="alert-meta">
                    <span class="meta-item">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                      </svg>
                      {{ formatTime(alert.create_time) }}
                    </span>
                    <span class="meta-item">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                      </svg>
                      {{ alert.node_type === 'bolt' ? '螺栓' : '法兰' }}: {{ alert.node_id }}
                    </span>
                    <span class="meta-item">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                        <path d="M2 17l10 5 10-5"></path>
                        <path d="M2 12l10 5 10-5"></path>
                      </svg>
                      {{ alert.strategy_type ? AlertStrategyMap[alert.strategy_type] : '-' }}
                    </span>
                    <span class="meta-item">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 9V5a3 3 0 0 0-6 0v4"></path>
                        <rect x="5" y="9" width="14" height="11" rx="2"></rect>
                      </svg>
                      置信度: {{ roundPercent(alert.confidence) }}%
                    </span>
                  </div>
                </div>
              </div>
              <div class="alert-right">
                <span class="status-tag" :class="'status-' + alert.status">
                  {{ AlertStatusMap[alert.status] }}
                </span>
                <svg class="expand-icon" :class="{ rotated: expandedId === alert.id }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>
            </div>

            <div v-if="expandedId === alert.id" class="alert-card-detail">
              <div class="detail-section">
                <div class="detail-title">预警详情</div>
                <div class="detail-content">
                  <p>{{ alert.content }}</p>
                </div>
              </div>

              <div class="detail-section">
                <div class="detail-title">风险评分</div>
                <div class="risk-score-row">
                  <div class="risk-score-bar">
                    <div class="risk-score-fill" :style="{ width: (alert.risk_score || 0) * 10 + '%' }"></div>
                  </div>
                  <span class="risk-score-value">{{ alert.risk_score?.toFixed(1) }}</span>
                </div>
              </div>

              <div class="detail-section" v-if="alert.recommendations && alert.recommendations.length > 0">
                <div class="detail-title">推荐措施</div>
                <ul class="recommendation-list">
                  <li v-for="(rec, idx) in alert.recommendations" :key="idx">{{ rec }}</li>
                </ul>
              </div>

              <div class="detail-section" v-if="alert.handler_name">
                <div class="detail-title">处理信息</div>
                <div class="handle-info">
                  <span>处理人：{{ alert.handler_name }}</span>
                  <span v-if="alert.handle_time">处理时间：{{ formatTime(alert.handle_time) }}</span>
                  <span v-if="alert.handle_note">处理备注：{{ alert.handle_note }}</span>
                </div>
              </div>

              <div class="detail-actions" v-if="canShowActions(alert)">
                <button v-if="alert.status === 'pending'" class="action-btn action-ack" @click.stop="handleAcknowledge(alert)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  确认
                </button>
                <button v-if="alert.status === 'pending' || alert.status === 'processing'" class="action-btn action-dispatch" @click.stop="handleDispatch(alert)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                    <circle cx="8.5" cy="7" r="4"></circle>
                    <line x1="20" y1="8" x2="20" y2="14"></line>
                    <line x1="23" y1="11" x2="17" y2="11"></line>
                  </svg>
                  派工
                </button>
                <button v-if="alert.status === 'processing'" class="action-btn action-close" @click.stop="handleClose(alert)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="pagination" v-if="total > pageSize">
          <button class="page-btn" :disabled="page <= 1" @click="goToPage(page - 1)">上一页</button>
          <div class="page-info">第 {{ page }} 页 / 共 {{ totalPages }} 页</div>
          <button class="page-btn" :disabled="page >= totalPages" @click="goToPage(page + 1)">下一页</button>
        </div>
      </section>
    </div>

    <div v-if="showDispatchModal" class="modal-overlay" @click.self="showDispatchModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>派工处理</h3>
          <button class="modal-close" @click="showDispatchModal = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">指派给</label>
            <select v-model="dispatchForm.assignee_id" class="form-select">
              <option value="">请选择处理人</option>
              <option value="user1">张三</option>
              <option value="user2">李四</option>
              <option value="user3">王五</option>
              <option value="user4">赵六</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">处理人姓名</label>
            <input v-model="dispatchForm.assignee_name" type="text" class="form-input" placeholder="请输入处理人姓名" />
          </div>
          <div class="form-group">
            <label class="form-label">备注</label>
            <textarea v-model="dispatchForm.handle_note" class="form-textarea" rows="3" placeholder="请输入派工备注"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showDispatchModal = false">取消</button>
          <button class="btn btn-primary" @click="confirmDispatch" :disabled="dispatching">
            {{ dispatching ? '处理中...' : '确认派工' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showCloseModal" class="modal-overlay" @click.self="showCloseModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>关闭预警</h3>
          <button class="modal-close" @click="showCloseModal = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">关闭原因</label>
            <textarea v-model="closeForm.handle_note" class="form-textarea" rows="3" placeholder="请输入关闭原因"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showCloseModal = false">取消</button>
          <button class="btn btn-primary" @click="confirmClose" :disabled="closing">
            {{ closing ? '处理中...' : '确认关闭' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  AlertLevelMap,
  AlertLevelColorMap,
  AlertStatusMap,
  AlertStrategyMap
} from '@/types'
import type { AlertEvent, AlertFilterOptions, AlertLevel, AlertStatus, AlertStrategy } from '@/types'
import { fetchAlertList, handleAlert, createWorkOrderFromAlert, fetchAlertStats } from '@/api/alert'
import { useAuth } from '@/composables/useAuth'

const { canWrite } = useAuth()

const alerts = ref<AlertEvent[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const expandedId = ref<number | null>(null)

const stats = ref({
  total: 0,
  pending: 0,
  processing: 0,
  resolved: 0,
  byLevel: {} as Record<number, number>
})

const filters = ref<AlertFilterOptions>({
  status: 'pending',
  alert_level: null,
  strategy_type: null,
  node_type: null,
  start_time: null,
  end_time: null
})

const localStartTime = ref('')
const localEndTime = ref('')

const showDispatchModal = ref(false)
const showCloseModal = ref(false)
const dispatching = ref(false)
const closing = ref(false)
const currentAlert = ref<AlertEvent | null>(null)

const dispatchForm = ref({
  assignee_id: '',
  assignee_name: '',
  handle_note: ''
})

const closeForm = ref({
  handle_note: ''
})

const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)

async function loadAlerts() {
  loading.value = true
  try {
    const result = await fetchAlertList(filters.value, page.value, pageSize.value)
    alerts.value = result.items
    total.value = result.total
  } catch (e) {
    console.error('加载预警列表失败:', e)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await fetchAlertStats()
  } catch (e) {
    console.error('加载统计数据失败:', e)
  }
}

function setStatus(status: AlertStatus | null) {
  filters.value.status = status
  page.value = 1
  loadAlerts()
}

function setLevel(level: AlertLevel | null) {
  filters.value.alert_level = level
  page.value = 1
  loadAlerts()
}

function setStrategy(strategy: AlertStrategy | null) {
  filters.value.strategy_type = strategy
  page.value = 1
  loadAlerts()
}

function setQuickTime(days: number) {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - days)

  localStartTime.value = formatDate(start)
  localEndTime.value = formatDate(end)
  onTimeChange()
}

function clearTimeFilter() {
  localStartTime.value = ''
  localEndTime.value = ''
  filters.value.start_time = null
  filters.value.end_time = null
  page.value = 1
  loadAlerts()
}

function onTimeChange() {
  filters.value.start_time = localStartTime.value ? new Date(localStartTime.value).toISOString() : null
  filters.value.end_time = localEndTime.value ? new Date(localEndTime.value + ' 23:59:59').toISOString() : null
  page.value = 1
  loadAlerts()
}

function formatDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function resetFilters() {
  filters.value = {
    status: null,
    alert_level: null,
    strategy_type: null,
    node_type: null,
    start_time: null,
    end_time: null
  }
  localStartTime.value = ''
  localEndTime.value = ''
  page.value = 1
  loadAlerts()
}

function applyFilters() {
  page.value = 1
  loadAlerts()
}

function toggleExpand(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

function formatTime(isoString: string | null): string {
  if (!isoString) return '-'
  const d = new Date(isoString)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function roundPercent(value: number | null | undefined): number {
  if (value == null) return 0
  return Math.round(value * 100)
}

function canShowActions(alert: AlertEvent): boolean {
  if (!canWrite.value) return false
  return alert.status === 'pending' || alert.status === 'processing'
}

async function handleAcknowledge(alert: AlertEvent) {
  try {
    const result = await handleAlert(alert.id, {
      action: 'acknowledge',
      handler_name: '当前用户',
      handle_note: '已确认预警'
    })
    if (result) {
      const idx = alerts.value.findIndex(a => a.id === alert.id)
      if (idx >= 0) {
        alerts.value[idx] = result
      }
      loadStats()
    }
  } catch (e) {
    console.error('确认预警失败:', e)
  }
}

function handleDispatch(alert: AlertEvent) {
  currentAlert.value = alert
  dispatchForm.value = {
    assignee_id: '',
    assignee_name: '',
    handle_note: ''
  }
  showDispatchModal.value = true
}

async function confirmDispatch() {
  if (!currentAlert.value || !dispatchForm.value.assignee_id) return

  dispatching.value = true
  try {
    const workOrder = await createWorkOrderFromAlert(currentAlert.value.id, {
      assignee_id: dispatchForm.value.assignee_id,
      assignee_name: dispatchForm.value.assignee_name || dispatchForm.value.assignee_id
    })

    if (workOrder) {
      showDispatchModal.value = false
      loadAlerts()
      loadStats()
    }
  } catch (e) {
    console.error('派工失败:', e)
  } finally {
    dispatching.value = false
  }
}

function handleClose(alert: AlertEvent) {
  currentAlert.value = alert
  closeForm.value.handle_note = ''
  showCloseModal.value = true
}

async function confirmClose() {
  if (!currentAlert.value) return

  closing.value = true
  try {
    const result = await handleAlert(currentAlert.value.id, {
      action: 'close',
      handler_name: '当前用户',
      handle_note: closeForm.value.handle_note
    })
    if (result) {
      showCloseModal.value = false
      loadAlerts()
      loadStats()
    }
  } catch (e) {
    console.error('关闭预警失败:', e)
  } finally {
    closing.value = false
  }
}

function goToPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  loadAlerts()
}

onMounted(() => {
  loadAlerts()
  loadStats()
})
</script>

<style scoped>
.alert-center {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.alert-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(15, 23, 42, 0.85);
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}

.alert-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e2e8f0;
}

.alert-title svg {
  color: #f97316;
}

.alert-title h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
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

.refresh-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 16px 20px;
  flex-shrink: 0;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  backdrop-filter: blur(8px);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-pending .stat-icon {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.stat-processing .stat-icon {
  background: rgba(249, 115, 22, 0.15);
  color: #f97316;
}

.stat-resolved .stat-icon {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.stat-levels .stat-icon {
  background: rgba(139, 92, 246, 0.15);
  color: #8b5cf6;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #f8fafc;
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}

.stat-level-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 2px;
}

.level-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.level-1 { background: #eab308; }
.level-2 { background: #f97316; }
.level-3 { background: #ef4444; }
.level-4 { background: #7f1d1d; }

.level-count {
  font-weight: 600;
  color: #cbd5e1;
}

.alert-content {
  flex: 1;
  display: flex;
  gap: 16px;
  padding: 0 20px 20px;
  min-height: 0;
  overflow: hidden;
}

.filter-sidebar {
  width: 260px;
  flex-shrink: 0;
  overflow-y: auto;
}

.filter-section {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  padding: 16px;
  backdrop-filter: blur(8px);
}

.filter-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
}

.filter-group {
  margin-bottom: 20px;
}

.filter-label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 10px;
  font-weight: 500;
}

.filter-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-option {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #cbd5e1;
  cursor: pointer;
}

.filter-option input {
  width: 14px;
  height: 14px;
  accent-color: #3b82f6;
  cursor: pointer;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.status-pending {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.status-processing {
  background: rgba(249, 115, 22, 0.15);
  color: #fb923c;
}

.status-resolved {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.status-closed {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
}

.level-badge {
  padding: 2px 8px;
  border: 1px solid;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.time-filter {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.time-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-label {
  font-size: 12px;
  color: #64748b;
  width: 32px;
  flex-shrink: 0;
}

.time-input input {
  flex: 1;
  padding: 6px 10px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 12px;
  outline: none;
  transition: border-color 0.2s;
}

.time-input input:hover,
.time-input input:focus {
  border-color: rgba(59, 130, 246, 0.7);
}

.time-quick {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-btn {
  padding: 4px 8px;
  background: rgba(71, 85, 105, 0.5);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 4px;
  color: #94a3b8;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-btn:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  color: #60a5fa;
}

.filter-actions {
  display: flex;
  gap: 8px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(59, 130, 246, 0.2);
}

.btn {
  flex: 1;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: rgba(71, 85, 105, 0.6);
  color: #cbd5e1;
  border: 1px solid rgba(100, 116, 139, 0.4);
}

.btn-secondary:hover {
  background: rgba(71, 85, 105, 0.9);
}

.alert-list-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px 8px 0 0;
  border-bottom: none;
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}

.list-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.list-info {
  font-size: 12px;
  color: #64748b;
}

.alert-list {
  flex: 1;
  overflow-y: auto;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-top: none;
  border-radius: 0 0 8px 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-list::-webkit-scrollbar {
  width: 6px;
}

.alert-list::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.alert-card {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.alert-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
}

.alert-card.expanded {
  border-color: rgba(59, 130, 246, 0.5);
}

.alert-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  cursor: pointer;
}

.alert-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.alert-level {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.alert-main {
  flex: 1;
  min-width: 0;
}

.alert-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.alert-no {
  font-size: 12px;
  color: #64748b;
  font-family: monospace;
}

.alert-title-text {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upgrade-tag {
  padding: 2px 6px;
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  font-size: 10px;
  border-radius: 3px;
  font-weight: 500;
}

.alert-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #64748b;
}

.meta-item svg {
  flex-shrink: 0;
}

.alert-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.status-tag {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.status-tag.status-pending {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.status-tag.status-processing {
  background: rgba(249, 115, 22, 0.15);
  color: #fb923c;
}

.status-tag.status-resolved {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.status-tag.status-ignored,
.status-tag.status-closed {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
}

.expand-icon {
  color: #64748b;
  transition: transform 0.2s;
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

.alert-card-detail {
  padding: 0 16px 16px;
  border-top: 1px solid rgba(59, 130, 246, 0.1);
  background: rgba(15, 23, 42, 0.4);
}

.detail-section {
  margin-top: 14px;
}

.detail-title {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  margin-bottom: 8px;
}

.detail-content {
  font-size: 13px;
  color: #cbd5e1;
  line-height: 1.6;
}

.risk-score-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.risk-score-bar {
  flex: 1;
  height: 8px;
  background: rgba(71, 85, 105, 0.5);
  border-radius: 4px;
  overflow: hidden;
}

.risk-score-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #eab308, #ef4444);
  border-radius: 4px;
  transition: width 0.3s;
}

.risk-score-value {
  font-size: 14px;
  font-weight: 600;
  color: #f8fafc;
  min-width: 40px;
  text-align: right;
}

.recommendation-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.recommendation-list li {
  position: relative;
  padding-left: 20px;
  font-size: 13px;
  color: #cbd5e1;
  line-height: 1.8;
}

.recommendation-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 9px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
}

.handle-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #94a3b8;
}

.detail-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(59, 130, 246, 0.15);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.action-ack {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.action-ack:hover {
  background: rgba(34, 197, 94, 0.25);
  border-color: rgba(34, 197, 94, 0.5);
}

.action-dispatch {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.action-dispatch:hover {
  background: rgba(59, 130, 246, 0.25);
  border-color: rgba(59, 130, 246, 0.5);
}

.action-close {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.action-close:hover {
  background: rgba(100, 116, 139, 0.3);
  border-color: rgba(100, 116, 139, 0.5);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #475569;
  gap: 12px;
}

.empty-title {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
}

.empty-desc {
  font-size: 12px;
  color: #475569;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px 0 0;
  flex-shrink: 0;
}

.page-btn {
  padding: 6px 14px;
  background: rgba(71, 85, 105, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.4);
  border-radius: 6px;
  color: #cbd5e1;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  color: #60a5fa;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 12px;
  color: #64748b;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  width: 420px;
  max-width: 90vw;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.modal-close:hover {
  color: #e2e8f0;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 6px;
  font-weight: 500;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
  font-family: inherit;
}

.form-input:hover,
.form-select:hover,
.form-textarea:hover,
.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: rgba(59, 130, 246, 0.7);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.2);
}

.modal-footer .btn {
  flex: none;
  padding: 8px 20px;
}

.filter-sidebar::-webkit-scrollbar {
  width: 6px;
}

.filter-sidebar::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}
</style>
