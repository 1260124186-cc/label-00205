<template>
  <div class="model-management">
    <div class="mm-header">
      <div class="mm-title">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
          <path d="M2 17l10 5 10-5"></path>
          <path d="M2 12l10 5 10-5"></path>
        </svg>
        <h2>模型管理</h2>
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

    <div class="mm-content">
      <aside class="mm-sidebar">
        <div class="sidebar-section">
          <div class="sidebar-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            训练触发
          </div>
          <div class="train-form">
            <div class="form-group">
              <label class="form-label">模型类型</label>
              <select v-model="trainForm.model_type" class="form-select">
                <option value="bolt">螺栓模型</option>
                <option value="flange">法兰模型</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">目标模型</label>
              <select v-model="trainForm.model_id" class="form-select">
                <option :value="null">全部{{ trainForm.model_type === 'bolt' ? '螺栓' : '法兰' }}模型</option>
                <option v-for="m in filteredModels" :key="m.model_id" :value="m.model_id">
                  {{ m.display_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">训练轮次</label>
              <input v-model.number="trainForm.epochs" type="number" class="form-input" min="10" max="200" />
            </div>
            <div class="form-group">
              <label class="form-label">学习率</label>
              <input v-model.number="trainForm.learning_rate" type="number" class="form-input" step="0.0001" min="0.00001" max="0.1" />
            </div>
            <div class="form-group">
              <label class="form-group-inline">
                <input type="checkbox" v-model="trainForm.force_retrain" />
                <span>强制重训练</span>
              </label>
            </div>
            <button class="btn btn-train" @click="handleTrain" :disabled="training">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
              {{ training ? '训练启动中...' : '开始训练' }}
            </button>
          </div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
            模型列表
          </div>
          <div class="model-list">
            <div
              v-for="model in models"
              :key="model.model_id"
              class="model-card"
              :class="{ active: selectedModelId === model.model_id }"
              @click="selectModel(model.model_id)"
            >
              <div class="model-card-header">
                <div class="model-type-badge" :class="model.model_type">
                  {{ model.model_type === 'bolt' ? '螺栓' : '法兰' }}
                </div>
                <div class="model-card-name">{{ model.display_name }}</div>
              </div>
              <div class="model-card-meta">
                <span v-if="model.active_version" class="meta-item">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                  </svg>
                  {{ model.active_version }}
                </span>
                <span class="meta-item">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 20V10"></path>
                    <path d="M18 20V4"></path>
                    <path d="M6 20v-4"></path>
                  </svg>
                  {{ model.total_versions }}个版本
                </span>
                <span
                  v-if="model.training_status"
                  class="training-status-dot"
                  :class="model.training_status"
                ></span>
              </div>
              <div class="model-card-metrics" v-if="model.best_val_acc">
                <span class="metric-mini">
                  <span class="metric-label">最佳精度</span>
                  <span class="metric-val">{{ (model.best_val_acc * 100).toFixed(1) }}%</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <section class="mm-main">
        <div v-if="!selectedModelId" class="empty-state">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
            <path d="M2 17l10 5 10-5"></path>
            <path d="M2 12l10 5 10-5"></path>
          </svg>
          <div class="empty-title">选择模型查看详情</div>
          <div class="empty-desc">从左侧模型列表选择一个模型，查看版本信息、训练曲线与指标对比</div>
        </div>

        <template v-else>
          <div class="main-top">
            <div class="model-info-bar">
              <div class="info-bar-left">
                <div class="info-type-badge" :class="currentModel?.model_type">
                  {{ currentModel?.model_type === 'bolt' ? '螺栓模型' : '法兰模型' }}
                </div>
                <div class="info-bar-name">{{ currentModel?.display_name }}</div>
                <span v-if="currentModel?.active_version" class="info-version">活动版本: {{ currentModel.active_version }}</span>
              </div>
              <div class="info-bar-right">
                <span
                  v-if="currentModel?.training_status"
                  class="status-tag"
                  :class="'status-' + currentModel.training_status"
                >
                  {{ TrainingStatusMap[currentModel.training_status] }}
                </span>
                <span v-if="currentModel?.best_val_acc" class="info-acc">
                  最佳精度 {{ (currentModel.best_val_acc * 100).toFixed(1) }}%
                </span>
              </div>
            </div>
          </div>

          <div class="main-body">
            <div class="body-left">
              <div class="panel version-panel">
                <div class="panel-header">
                  <div class="panel-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    </svg>
                    版本列表
                  </div>
                  <div class="panel-actions" v-if="selectedVersions.length === 2">
                    <button class="btn btn-compare" @click="handleCompare">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="20" x2="18" y2="10"></line>
                        <line x1="12" y1="20" x2="12" y2="4"></line>
                        <line x1="6" y1="20" x2="6" y2="14"></line>
                      </svg>
                      对比选中版本
                    </button>
                  </div>
                </div>
                <div class="version-list">
                  <div
                    v-for="ver in versions"
                    :key="ver.version"
                    class="version-item"
                    :class="{ active: ver.is_active, selected: selectedVersions.includes(ver.version) }"
                  >
                    <div class="version-left">
                      <label class="version-checkbox" @click.stop>
                        <input
                          type="checkbox"
                          :checked="selectedVersions.includes(ver.version)"
                          @change="toggleVersionSelect(ver.version)"
                          :disabled="!selectedVersions.includes(ver.version) && selectedVersions.length >= 2"
                        />
                      </label>
                      <div class="version-info">
                        <div class="version-name-row">
                          <span class="version-name">{{ ver.version }}</span>
                          <span v-if="ver.is_active" class="active-badge">活动</span>
                        </div>
                        <div class="version-meta">
                          {{ formatTime(ver.created_at) }} · {{ Object.keys(ver.metrics).length }}项指标
                        </div>
                      </div>
                    </div>
                    <div class="version-metrics-mini">
                      <span v-for="(val, key) in ver.metrics" :key="key" class="vmm-item">
                        <span class="vmm-key">{{ formatMetricKey(key as string) }}</span>
                        <span class="vmm-val">{{ (typeof val === 'number' && val < 1 ? (val * 100).toFixed(1) + '%' : val) }}</span>
                      </span>
                    </div>
                    <div class="version-actions">
                      <button
                        v-if="!ver.is_active"
                        class="action-btn action-activate"
                        @click.stop="handleActivate(ver.version)"
                        title="激活此版本"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                          <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                      </button>
                      <button
                        v-if="!ver.is_active"
                        class="action-btn action-rollback"
                        @click.stop="handleRollback(ver.version)"
                        title="回滚到此版本"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <polyline points="1 4 1 10 7 10"></polyline>
                          <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="body-right">
              <div class="panel curve-panel">
                <div class="panel-header">
                  <div class="panel-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 20V10"></path>
                      <path d="M18 20V4"></path>
                      <path d="M6 20v-4"></path>
                    </svg>
                    训练曲线
                  </div>
                  <div class="panel-actions">
                    <select v-model="selectedSessionId" class="session-select">
                      <option value="">选择训练会话</option>
                      <option v-for="s in sessions" :key="s.session_id" :value="s.session_id">
                        {{ formatTime(s.start_time) }} ({{ s.status === 'running' ? `${s.current_epoch}/${s.total_epochs}` : s.status }})
                      </option>
                    </select>
                  </div>
                </div>
                <div class="curve-chart-area">
                  <div v-if="!selectedSessionId || !currentSession" class="chart-empty">
                    选择训练会话查看曲线
                  </div>
                  <template v-else>
                    <div class="training-progress" v-if="currentSession.status === 'running'">
                      <div class="progress-bar">
                        <div
                          class="progress-fill"
                          :style="{ width: (currentSession.current_epoch / currentSession.total_epochs * 100) + '%' }"
                        ></div>
                      </div>
                      <span class="progress-text">
                        Epoch {{ currentSession.current_epoch }} / {{ currentSession.total_epochs }}
                        ({{ (currentSession.current_epoch / currentSession.total_epochs * 100).toFixed(0) }}%)
                      </span>
                    </div>
                    <div ref="curveChartRef" class="chart-container"></div>
                  </template>
                </div>
              </div>

              <div class="panel compare-panel" v-if="compareResult">
                <div class="panel-header">
                  <div class="panel-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="18" y1="20" x2="18" y2="10"></line>
                      <line x1="12" y1="20" x2="12" y2="4"></line>
                      <line x1="6" y1="20" x2="6" y2="14"></line>
                    </svg>
                    指标对比: {{ compareResult.version1 }} vs {{ compareResult.version2 }}
                  </div>
                  <div class="panel-actions">
                    <button class="btn btn-close-compare" @click="compareResult = null">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                      关闭
                    </button>
                  </div>
                </div>
                <div ref="compareChartRef" class="chart-container compare-chart"></div>
                <div class="compare-table">
                  <table>
                    <thead>
                      <tr>
                        <th>指标</th>
                        <th>{{ compareResult.version1 }}</th>
                        <th>{{ compareResult.version2 }}</th>
                        <th>差异</th>
                        <th>趋势</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(comp, key) in compareResult.metrics_comparison" :key="key">
                        <td class="metric-name">{{ formatMetricKey(key) }}</td>
                        <td>{{ formatMetricValue(comp.v1, key) }}</td>
                        <td>{{ formatMetricValue(comp.v2, key) }}</td>
                        <td :class="comp.improved ? 'diff-improved' : 'diff-degraded'">
                          {{ comp.diff > 0 ? '+' : '' }}{{ formatMetricValue(comp.diff, key) }}
                        </td>
                        <td>
                          <svg v-if="comp.improved" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2">
                            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
                          </svg>
                          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2">
                            <polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline>
                          </svg>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </template>
      </section>
    </div>

    <div v-if="showTrainModal" class="modal-overlay" @click.self="showTrainModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>确认启动训练</h3>
          <button class="modal-close" @click="showTrainModal = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="confirm-info">
            <div class="confirm-row">
              <span class="confirm-label">模型类型</span>
              <span class="confirm-value">{{ trainForm.model_type === 'bolt' ? '螺栓模型' : '法兰模型' }}</span>
            </div>
            <div class="confirm-row">
              <span class="confirm-label">目标模型</span>
              <span class="confirm-value">{{ trainForm.model_id ? getModelDisplayName(trainForm.model_id) : '全部模型' }}</span>
            </div>
            <div class="confirm-row">
              <span class="confirm-label">训练轮次</span>
              <span class="confirm-value">{{ trainForm.epochs }}</span>
            </div>
            <div class="confirm-row">
              <span class="confirm-label">学习率</span>
              <span class="confirm-value">{{ trainForm.learning_rate }}</span>
            </div>
            <div class="confirm-row" v-if="trainForm.force_retrain">
              <span class="confirm-label">强制重训练</span>
              <span class="confirm-value warn">是</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showTrainModal = false">取消</button>
          <button class="btn btn-primary" @click="confirmTrain" :disabled="training">
            {{ training ? '启动中...' : '确认训练' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { TrainingStatusMap, TrainingStatusColorMap } from '@/types'
import type { ModelEntry, ModelVersion, TrainingSession, VersionCompareResult } from '@/types'
import {
  fetchModelList,
  fetchModelVersions,
  fetchTrainingSessions,
  triggerTraining,
  activateVersion,
  rollbackVersion,
  compareVersions
} from '@/api/model'

const models = ref<ModelEntry[]>([])
const selectedModelId = ref<string | null>(null)
const versions = ref<ModelVersion[]>([])
const sessions = ref<TrainingSession[]>([])
const selectedSessionId = ref('')
const selectedVersions = ref<string[]>([])
const compareResult = ref<VersionCompareResult | null>(null)
const training = ref(false)
const showTrainModal = ref(false)

const trainForm = ref({
  model_type: 'bolt' as 'bolt' | 'flange',
  model_id: null as string | null,
  epochs: 50,
  learning_rate: 0.001,
  force_retrain: false
})

const curveChartRef = ref<HTMLElement | null>(null)
const compareChartRef = ref<HTMLElement | null>(null)
let curveChart: echarts.ECharts | null = null
let compareChart: echarts.ECharts | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

const currentModel = computed(() => {
  if (!selectedModelId.value) return null
  return models.value.find(m => m.model_id === selectedModelId.value) || null
})

const filteredModels = computed(() => {
  return models.value.filter(m => m.model_type === trainForm.value.model_type)
})

const currentSession = computed(() => {
  if (!selectedSessionId.value) return null
  return sessions.value.find(s => s.session_id === selectedSessionId.value) || null
})

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatMetricKey(key: string): string {
  const map: Record<string, string> = {
    val_acc: '验证精度',
    train_acc: '训练精度',
    val_loss: '验证损失',
    train_loss: '训练损失',
    f1_score: 'F1分数',
    precision: '精确率',
    recall: '召回率',
    best_val_acc: '最佳验证精度',
    best_val_loss: '最佳验证损失',
    best_epoch: '最佳轮次'
  }
  return map[key] || key
}

function formatMetricValue(val: number, key: string): string {
  if (key.includes('epoch')) return String(Math.round(val))
  if (val > 0 && val < 1) return (val * 100).toFixed(2) + '%'
  return val.toFixed(4)
}

function getModelDisplayName(modelId: string): string {
  const m = models.value.find(e => e.model_id === modelId)
  return m?.display_name || modelId
}

async function loadModels() {
  models.value = await fetchModelList()
}

async function selectModel(modelId: string) {
  selectedModelId.value = modelId
  selectedVersions.value = []
  compareResult.value = null
  selectedSessionId.value = ''

  const [vers, sess] = await Promise.all([
    fetchModelVersions(modelId),
    fetchTrainingSessions(modelId)
  ])
  versions.value = vers
  sessions.value = sess

  if (sess.length > 0) {
    selectedSessionId.value = sess[0].session_id
  }
}

async function refreshAll() {
  await loadModels()
  if (selectedModelId.value) {
    await selectModel(selectedModelId.value)
  }
}

function toggleVersionSelect(version: string) {
  const idx = selectedVersions.value.indexOf(version)
  if (idx >= 0) {
    selectedVersions.value.splice(idx, 1)
  } else if (selectedVersions.value.length < 2) {
    selectedVersions.value.push(version)
  }
}

async function handleActivate(version: string) {
  if (!selectedModelId.value) return
  const result = await activateVersion(selectedModelId.value, version)
  if (result) {
    await selectModel(selectedModelId.value)
    await loadModels()
  }
}

async function handleRollback(version: string) {
  if (!selectedModelId.value) return
  const result = await rollbackVersion(selectedModelId.value, version)
  if (result) {
    await selectModel(selectedModelId.value)
    await loadModels()
  }
}

async function handleCompare() {
  if (!selectedModelId.value || selectedVersions.value.length !== 2) return
  const result = await compareVersions(
    selectedModelId.value,
    selectedVersions.value[0],
    selectedVersions.value[1]
  )
  if (result) {
    compareResult.value = result
    await nextTick()
    renderCompareChart()
  }
}

function handleTrain() {
  showTrainModal.value = true
}

async function confirmTrain() {
  training.value = true
  try {
    await triggerTraining({
      model_type: trainForm.value.model_type,
      model_id: trainForm.value.model_id,
      force_retrain: trainForm.value.force_retrain,
      epochs: trainForm.value.epochs,
      learning_rate: trainForm.value.learning_rate
    })
    showTrainModal.value = false
    await refreshAll()
  } catch (e) {
    console.error('启动训练失败:', e)
  } finally {
    training.value = false
  }
}

function renderCurveChart() {
  if (!curveChartRef.value || !currentSession.value) return
  if (!curveChart) {
    curveChart = echarts.init(curveChartRef.value)
  }

  const session = currentSession.value
  const history = session.metrics_history
  if (history.length === 0) return

  const epochs = history.map(m => m.epoch)
  const trainLoss = history.map(m => m.train_loss)
  const valLoss = history.map(m => m.val_loss ?? null)
  const trainAcc = history.map(m => m.train_acc != null ? m.train_acc * 100 : null)
  const valAcc = history.map(m => m.val_acc != null ? m.val_acc * 100 : null)

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'rgba(59, 130, 246, 0.3)',
      textStyle: { color: '#e2e8f0', fontSize: 12 }
    },
    legend: {
      data: ['训练损失', '验证损失', '训练精度', '验证精度'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      top: 0,
      right: 10
    },
    grid: { left: 55, right: 55, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: epochs,
      name: 'Epoch',
      nameTextStyle: { color: '#94a3b8', fontSize: 10 },
      axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, interval: Math.max(0, Math.floor(epochs.length / 10) - 1) },
      splitLine: { show: false }
    },
    yAxis: [
      {
        type: 'value',
        name: 'Loss',
        nameTextStyle: { color: '#94a3b8', fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.08)' } }
      },
      {
        type: 'value',
        name: 'Accuracy %',
        nameTextStyle: { color: '#94a3b8', fontSize: 10 },
        axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { show: false },
        min: 0,
        max: 100
      }
    ],
    series: [
      {
        name: '训练损失',
        type: 'line',
        data: trainLoss,
        smooth: true,
        lineStyle: { color: '#3b82f6', width: 2 },
        itemStyle: { color: '#3b82f6' },
        showSymbol: false
      },
      {
        name: '验证损失',
        type: 'line',
        data: valLoss,
        smooth: true,
        lineStyle: { color: '#f97316', width: 2 },
        itemStyle: { color: '#f97316' },
        showSymbol: false
      },
      {
        name: '训练精度',
        type: 'line',
        yAxisIndex: 1,
        data: trainAcc,
        smooth: true,
        lineStyle: { color: '#22c55e', width: 2, type: 'dashed' },
        itemStyle: { color: '#22c55e' },
        showSymbol: false
      },
      {
        name: '验证精度',
        type: 'line',
        yAxisIndex: 1,
        data: valAcc,
        smooth: true,
        lineStyle: { color: '#eab308', width: 2, type: 'dashed' },
        itemStyle: { color: '#eab308' },
        showSymbol: false
      }
    ]
  }

  curveChart.setOption(option, true)
}

function renderCompareChart() {
  if (!compareChartRef.value || !compareResult.value) return
  if (!compareChart) {
    compareChart = echarts.init(compareChartRef.value)
  }

  const result = compareResult.value
  const keys = Object.keys(result.metrics_comparison)
  const v1Data = keys.map(k => {
    const v = result.metrics_comparison[k].v1
    return (v > 0 && v < 1) ? v * 100 : v
  })
  const v2Data = keys.map(k => {
    const v = result.metrics_comparison[k].v2
    return (v > 0 && v < 1) ? v * 100 : v
  })
  const labels = keys.map(k => formatMetricKey(k))

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'rgba(59, 130, 246, 0.3)',
      textStyle: { color: '#e2e8f0', fontSize: 12 }
    },
    legend: {
      data: [result.version1, result.version2],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      top: 0
    },
    grid: { left: 80, right: 30, top: 40, bottom: 30 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, rotate: 20 },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '值 (%)',
      nameTextStyle: { color: '#94a3b8', fontSize: 10 },
      axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.08)' } }
    },
    series: [
      {
        name: result.version1,
        type: 'bar',
        data: v1Data,
        barWidth: '30%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#3b82f6' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.3)' }
          ]),
          borderRadius: [3, 3, 0, 0]
        }
      },
      {
        name: result.version2,
        type: 'bar',
        data: v2Data,
        barWidth: '30%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#8b5cf6' },
            { offset: 1, color: 'rgba(139, 92, 246, 0.3)' }
          ]),
          borderRadius: [3, 3, 0, 0]
        }
      }
    ]
  }

  compareChart.setOption(option, true)
}

function handleResize() {
  curveChart?.resize()
  compareChart?.resize()
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    const hasRunning = sessions.value.some(s => s.status === 'running')
    if (hasRunning && selectedModelId.value) {
      sessions.value = await fetchTrainingSessions(selectedModelId.value)
      await loadModels()
      if (currentSession.value && currentSession.value.status === 'running') {
        await nextTick()
        renderCurveChart()
      }
    }
  }, 2000)
}

watch(selectedSessionId, () => {
  nextTick(() => {
    renderCurveChart()
  })
})

watch(trainForm, (newVal) => {
  const matchingModels = models.value.filter(m => m.model_type === newVal.model_type)
  if (newVal.model_id && !matchingModels.find(m => m.model_id === newVal.model_id)) {
    trainForm.value.model_id = null
  }
}, { deep: true })

onMounted(async () => {
  await loadModels()
  startPolling()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  curveChart?.dispose()
  compareChart?.dispose()
  if (pollTimer) clearInterval(pollTimer)
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.model-management {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.mm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(15, 23, 42, 0.85);
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}

.mm-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e2e8f0;
}

.mm-title svg {
  color: #8b5cf6;
}

.mm-title h2 {
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

.mm-content {
  flex: 1;
  display: flex;
  gap: 0;
  min-height: 0;
  overflow: hidden;
}

.mm-sidebar {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
  background: rgba(15, 23, 42, 0.5);
  border-right: 1px solid rgba(59, 130, 246, 0.15);
}

.mm-sidebar::-webkit-scrollbar {
  width: 5px;
}

.mm-sidebar::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.sidebar-section {
  padding: 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
}

.sidebar-section:last-child {
  border-bottom: none;
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
}

.train-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.form-group-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #cbd5e1;
  cursor: pointer;
}

.form-group-inline input[type="checkbox"] {
  width: 14px;
  height: 14px;
  accent-color: #3b82f6;
}

.form-input,
.form-select {
  width: 100%;
  padding: 7px 10px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 12px;
  outline: none;
  transition: border-color 0.2s;
}

.form-input:hover,
.form-select:hover,
.form-input:focus,
.form-select:focus {
  border-color: rgba(59, 130, 246, 0.7);
}

.btn-train {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 12px;
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.4);
  margin-top: 4px;
}

.btn-train:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.5);
}

.btn-train:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-card {
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.model-card:hover {
  border-color: rgba(59, 130, 246, 0.3);
  background: rgba(30, 41, 59, 0.7);
}

.model-card.active {
  border-color: rgba(139, 92, 246, 0.5);
  background: rgba(139, 92, 246, 0.1);
}

.model-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.model-type-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.model-type-badge.bolt {
  background: rgba(59, 130, 246, 0.7);
}

.model-type-badge.flange {
  background: rgba(139, 92, 246, 0.7);
}

.model-card-name {
  font-size: 13px;
  font-weight: 500;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-card-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #94a3b8;
}

.training-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.training-status-dot.running {
  background: #3b82f6;
  box-shadow: 0 0 8px #3b82f6;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

.training-status-dot.completed {
  background: #22c55e;
}

.training-status-dot.failed {
  background: #ef4444;
}

.training-status-dot.pending {
  background: #eab308;
}

.training-status-dot.stopped {
  background: #64748b;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.3); }
}

.model-card-metrics {
  margin-top: 6px;
}

.metric-mini {
  display: flex;
  align-items: center;
  gap: 6px;
}

.metric-label {
  font-size: 10px;
  color: #64748b;
}

.metric-val {
  font-size: 12px;
  font-weight: 600;
  color: #22c55e;
}

.mm-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
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

.main-top {
  flex-shrink: 0;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
}

.model-info-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  padding: 10px 16px;
  backdrop-filter: blur(8px);
}

.info-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-type-badge {
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: white;
}

.info-type-badge.bolt {
  background: rgba(59, 130, 246, 0.7);
}

.info-type-badge.flange {
  background: rgba(139, 92, 246, 0.7);
}

.info-bar-name {
  font-size: 15px;
  font-weight: 600;
  color: #f8fafc;
}

.info-version {
  font-size: 12px;
  color: #94a3b8;
  padding: 2px 8px;
  background: rgba(139, 92, 246, 0.15);
  border-radius: 4px;
}

.info-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-tag {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.status-tag.status-running {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.status-tag.status-completed {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.status-tag.status-failed {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.status-tag.status-pending {
  background: rgba(234, 179, 8, 0.15);
  color: #facc15;
}

.status-tag.status-stopped {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
}

.info-acc {
  font-size: 13px;
  font-weight: 600;
  color: #22c55e;
}

.main-body {
  flex: 1;
  display: flex;
  gap: 16px;
  padding: 16px 20px;
  min-height: 0;
  overflow: hidden;
}

.body-left {
  width: 340px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.body-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow-y: auto;
}

.body-right::-webkit-scrollbar {
  width: 5px;
}

.body-right::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.panel {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.version-panel {
  flex: 1;
  min-height: 0;
}

.curve-panel {
  flex: 1;
  min-height: 260px;
}

.compare-panel {
  flex-shrink: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-select {
  padding: 5px 10px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 11px;
  outline: none;
  cursor: pointer;
  max-width: 240px;
}

.session-select:hover,
.session-select:focus {
  border-color: rgba(59, 130, 246, 0.6);
}

.btn-compare {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.4);
  border-radius: 4px;
  color: #a78bfa;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-compare:hover {
  background: rgba(139, 92, 246, 0.3);
  border-color: rgba(139, 92, 246, 0.6);
}

.btn-close-compare {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: rgba(100, 116, 139, 0.2);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 4px;
  color: #94a3b8;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-close-compare:hover {
  background: rgba(100, 116, 139, 0.3);
}

.version-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.version-list::-webkit-scrollbar {
  width: 5px;
}

.version-list::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.version-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 8px;
  transition: all 0.2s;
}

.version-item:hover {
  border-color: rgba(59, 130, 246, 0.3);
}

.version-item.active {
  border-color: rgba(139, 92, 246, 0.4);
  background: rgba(139, 92, 246, 0.08);
}

.version-item.selected {
  border-color: rgba(59, 130, 246, 0.5);
  background: rgba(59, 130, 246, 0.08);
}

.version-left {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.version-checkbox input {
  width: 14px;
  height: 14px;
  accent-color: #8b5cf6;
  cursor: pointer;
  margin-top: 2px;
}

.version-info {
  flex: 1;
  min-width: 0;
}

.version-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.version-name {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  font-family: 'SF Mono', Monaco, monospace;
}

.active-badge {
  padding: 1px 6px;
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
  font-size: 10px;
  border-radius: 3px;
  font-weight: 600;
}

.version-meta {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.version-metrics-mini {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-left: 24px;
}

.vmm-item {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
}

.vmm-key {
  color: #64748b;
}

.vmm-val {
  color: #cbd5e1;
  font-weight: 500;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 10px;
}

.version-actions {
  display: flex;
  gap: 6px;
  padding-left: 24px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  border: 1px solid;
  transition: all 0.2s;
  background: transparent;
}

.action-activate {
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.3);
}

.action-activate:hover {
  background: rgba(34, 197, 94, 0.15);
  border-color: rgba(34, 197, 94, 0.5);
}

.action-rollback {
  color: #f97316;
  border-color: rgba(249, 115, 22, 0.3);
}

.action-rollback:hover {
  background: rgba(249, 115, 22, 0.15);
  border-color: rgba(249, 115, 22, 0.5);
}

.curve-chart-area {
  flex: 1;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #475569;
  font-size: 13px;
}

.training-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(59, 130, 246, 0.08);
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
  flex-shrink: 0;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: rgba(71, 85, 105, 0.5);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-text {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
  min-width: 160px;
}

.chart-container {
  flex: 1;
  min-height: 200px;
}

.compare-chart {
  height: 220px;
  flex: none;
}

.compare-table {
  padding: 12px 16px;
  border-top: 1px solid rgba(59, 130, 246, 0.15);
  overflow-x: auto;
}

.compare-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.compare-table th {
  text-align: left;
  padding: 8px 10px;
  color: #94a3b8;
  font-weight: 600;
  font-size: 11px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
}

.compare-table td {
  padding: 7px 10px;
  color: #cbd5e1;
  border-bottom: 1px solid rgba(59, 130, 246, 0.06);
}

.compare-table .metric-name {
  color: #e2e8f0;
  font-weight: 500;
}

.diff-improved {
  color: #4ade80 !important;
  font-weight: 600;
}

.diff-degraded {
  color: #f87171 !important;
  font-weight: 600;
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
  width: 440px;
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
  transition: color 0.2s;
}

.modal-close:hover {
  color: #e2e8f0;
}

.modal-body {
  padding: 20px;
}

.confirm-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.confirm-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.confirm-label {
  font-size: 13px;
  color: #94a3b8;
}

.confirm-value {
  font-size: 13px;
  font-weight: 500;
  color: #e2e8f0;
}

.confirm-value.warn {
  color: #f97316;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.2);
}

.btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
  color: white;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.4);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.5);
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
</style>
