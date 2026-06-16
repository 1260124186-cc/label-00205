<template>
  <div class="compliance-inspection">
    <div class="ci-header">
      <div class="ci-title">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 11l3 3L22 4"></path>
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
        </svg>
        <h2>合规与检验标准检查</h2>
        <span class="ci-subtitle">Compliance & Inspection Standards</span>
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

    <div class="ci-tabs">
      <button
        v-for="tab in tabOptions"
        :key="tab.value"
        class="ci-tab"
        :class="{ active: activeTab === tab.value }"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="ci-content">
      <template v-if="activeTab === 'templates'">
        <div class="templates-view">
          <div class="section-toolbar">
            <div class="toolbar-left">
              <select v-model="templateCategory" class="filter-select" @change="loadTemplates">
                <option value="">全部类别</option>
                <option value="储罐">储罐</option>
                <option value="法兰">法兰</option>
                <option value="压力容器">压力容器</option>
                <option value="管道">管道</option>
              </select>
            </div>
            <button class="action-btn primary" @click="showCreateTemplate = true">
              + 新建模板
            </button>
          </div>

          <div class="template-grid">
            <div
              v-for="tpl in templates"
              :key="tpl.code"
              class="template-card"
              @click="selectTemplate(tpl)"
            >
              <div class="tpl-header">
                <span class="tpl-code">{{ tpl.code }}</span>
                <span class="tpl-category" v-if="tpl.category">{{ tpl.category }}</span>
              </div>
              <div class="tpl-name">{{ tpl.name }}</div>
              <div class="tpl-desc" v-if="tpl.description">{{ tpl.description }}</div>
              <div class="tpl-meta">
                <span class="tpl-version" v-if="tpl.version">v{{ tpl.version }}</span>
                <span class="tpl-items">{{ tpl.checklist_items?.length || 0 }} 项</span>
                <span class="tpl-mandatory">
                  {{ tpl.checklist_items?.filter(i => i.is_mandatory).length || 0 }} 必检
                </span>
              </div>
            </div>
          </div>

          <div v-if="selectedTemplate" class="template-detail">
            <div class="detail-header">
              <h3>{{ selectedTemplate.name }} ({{ selectedTemplate.code }})</h3>
              <button class="close-btn" @click="selectedTemplate = null">✕</button>
            </div>
            <table class="checklist-table">
              <thead>
                <tr>
                  <th>编码</th>
                  <th>检查内容</th>
                  <th>必检</th>
                  <th>严重度</th>
                  <th>检查方法</th>
                  <th>验收标准</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in selectedTemplate.checklist_items" :key="item.item_code">
                  <td class="code-cell">{{ item.item_code }}</td>
                  <td>{{ item.content }}</td>
                  <td>
                    <span class="badge" :class="item.is_mandatory ? 'badge-red' : 'badge-gray'">
                      {{ item.is_mandatory ? '必检' : '选检' }}
                    </span>
                  </td>
                  <td>
                    <span class="severity-dot" :style="{ background: SeverityColorMap[item.severity] }"></span>
                    {{ SeverityMap[item.severity] }}
                  </td>
                  <td>{{ item.inspection_method || '--' }}</td>
                  <td>{{ item.acceptance_criteria || '--' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <template v-if="activeTab === 'tasks'">
        <div class="tasks-view">
          <div class="section-toolbar">
            <div class="toolbar-left">
              <select v-model="taskStatusFilter" class="filter-select" @change="loadTasks">
                <option value="">全部状态</option>
                <option value="pending">待检</option>
                <option value="in_progress">进行中</option>
                <option value="completed">已完成</option>
              </select>
              <select v-model="taskEquipFilter" class="filter-select" @change="loadTasks">
                <option value="">全部装置</option>
                <option value="storage_tank">储罐</option>
                <option value="flange">法兰</option>
                <option value="pressure_vessel">压力容器</option>
                <option value="pipeline">管道</option>
              </select>
            </div>
            <button class="action-btn primary" @click="showCreateTask = true">
              + 创建检验任务
            </button>
          </div>

          <div class="task-list">
            <div
              v-for="task in tasks"
              :key="task.id"
              class="task-card"
              :class="{ 'task-completed': task.status === 'completed' }"
              @click="selectTask(task)"
            >
              <div class="task-top">
                <span class="task-no">{{ task.task_no }}</span>
                <span class="task-status" :class="`status-${task.status}`">
                  {{ statusMap[task.status] }}
                </span>
              </div>
              <div class="task-info">
                <span v-if="task.equipment_type">装置: {{ equipMap[task.equipment_type] || task.equipment_type }}</span>
                <span v-if="task.work_order_id">工单: #{{ task.work_order_id }}</span>
              </div>
              <div class="task-standards">
                <span v-for="code in task.standard_codes" :key="code" class="std-tag">{{ code }}</span>
              </div>
              <div class="task-score-bar">
                <div class="score-track">
                  <div
                    class="score-fill"
                    :style="{
                      width: task.completion_score + '%',
                      background: scoreColor(task.completion_score)
                    }"
                  ></div>
                </div>
                <span class="score-text" :style="{ color: scoreColor(task.completion_score) }">
                  {{ task.completion_score.toFixed(1) }}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-if="activeTab === 'checklist' && selectedTask">
        <div class="checklist-view">
          <div class="cl-header">
            <div class="cl-title-row">
              <h3>{{ selectedTask.task_no }} 检验清单</h3>
              <div class="cl-actions">
                <button class="action-btn" @click="loadScore">
                  刷新评分
                </button>
                <button class="action-btn primary" @click="exportPdf">
                  导出 PDF 报告
                </button>
              </div>
            </div>
            <div class="cl-stats">
              <div class="cl-stat">
                <span class="stat-label">完成度</span>
                <span class="stat-value" :style="{ color: scoreColor(selectedTask.completion_score) }">
                  {{ selectedTask.completion_score.toFixed(1) }}%
                </span>
              </div>
              <div class="cl-stat">
                <span class="stat-label">已检/总数</span>
                <span class="stat-value">
                  {{ checkedCount }}/{{ selectedTask.checklist_items?.length || 0 }}
                </span>
              </div>
              <div class="cl-stat">
                <span class="stat-label">必检完成</span>
                <span class="stat-value">
                  {{ mandatoryCheckedCount }}/{{ mandatoryTotal }}
                </span>
              </div>
              <div class="cl-stat" v-if="selectedTask.alert_level">
                <span class="stat-label">告警级别</span>
                <span class="stat-value alert-level-{{ selectedTask.alert_level }}">
                  L{{ selectedTask.alert_level }}
                </span>
              </div>
            </div>
          </div>

          <div class="cl-items">
            <div
              v-for="item in selectedTask.checklist_items"
              :key="item.item_code"
              class="cl-item"
              :class="{
                'item-checked': item.checked,
                'item-mandatory': item.is_mandatory,
                'item-auto': item.auto_checked,
                'item-fail': item.result === 'fail'
              }"
            >
              <div class="item-left">
                <label class="item-check">
                  <input
                    type="checkbox"
                    :checked="item.checked"
                    :disabled="item.auto_checked"
                    @change="toggleItem(item)"
                  />
                  <span class="checkmark"></span>
                </label>
              </div>
              <div class="item-body">
                <div class="item-header-row">
                  <span class="item-code">{{ item.item_code }}</span>
                  <span class="badge" :class="item.is_mandatory ? 'badge-red' : 'badge-gray'">
                    {{ item.is_mandatory ? '必检' : '选检' }}
                  </span>
                  <span class="severity-tag" :style="{ color: SeverityColorMap[item.severity], borderColor: SeverityColorMap[item.severity] }">
                    {{ SeverityMap[item.severity] }}
                  </span>
                  <span v-if="item.auto_checked" class="auto-badge">自动勾选</span>
                  <span v-if="item.result" class="result-tag" :style="{ color: InspectionResultColorMap[item.result] }">
                    {{ InspectionResultMap[item.result] || item.result }}
                  </span>
                </div>
                <div class="item-content">{{ item.content }}</div>
                <div class="item-detail" v-if="item.inspection_method || item.acceptance_criteria">
                  <span v-if="item.inspection_method">方法: {{ item.inspection_method }}</span>
                  <span v-if="item.acceptance_criteria">标准: {{ item.acceptance_criteria }}</span>
                </div>
                <div class="item-evidence" v-if="item.evidence">
                  <span class="evidence-label">预测证据:</span>
                  <span v-for="(val, key) in item.evidence" :key="key" class="evidence-item">
                    {{ key }}: {{ typeof val === 'object' ? JSON.stringify(val) : val }}
                  </span>
                </div>
                <div class="item-inspector" v-if="item.inspector_name">
                  检验人: {{ item.inspector_name }}
                  <span v-if="item.inspect_time"> | {{ item.inspect_time }}</span>
                </div>
              </div>
              <div class="item-actions" v-if="!item.checked || item.result === 'fail'">
                <select
                  v-if="item.checked"
                  class="result-select"
                  :value="item.result"
                  @change="updateItemResult(item, ($event.target as HTMLSelectElement).value)"
                >
                  <option value="pass">合格</option>
                  <option value="fail">不合格</option>
                  <option value="na">不适用</option>
                </select>
              </div>
            </div>
          </div>

          <div class="cl-footer">
            <div class="close-check" v-if="selectedTask.work_order_id">
              <button class="action-btn" @click="checkClose">
                检查工单关闭条件
              </button>
              <div v-if="closeCheckResult" class="close-result" :class="{ 'can-close': closeCheckResult.can_close }">
                <div v-if="closeCheckResult.can_close" class="close-ok">
                  ✓ 工单可关闭，完成度 {{ closeCheckResult.completion_score.toFixed(1) }}%
                </div>
                <div v-else class="close-blocked">
                  ✕ 工单无法关闭: {{ closeCheckResult.reason }}
                  <div class="unchecked-list" v-if="closeCheckResult.mandatory_unchecked?.length">
                    <div v-for="u in closeCheckResult.mandatory_unchecked" :key="u.item_code" class="unchecked-item">
                      {{ u.item_code }} - {{ u.content }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-if="activeTab === 'checklist' && !selectedTask">
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M9 11l3 3L22 4"></path>
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
          </svg>
          <p>请在「检验任务」选项卡中选择一个任务查看检查清单</p>
        </div>
      </template>
    </div>

    <div v-if="showCreateTask" class="modal-overlay" @click.self="showCreateTask = false">
      <div class="modal">
        <div class="modal-header">
          <h3>创建检验任务</h3>
          <button class="close-btn" @click="showCreateTask = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>工单 ID</label>
            <input v-model.number="newTask.work_order_id" type="number" placeholder="关联工单ID" />
          </div>
          <div class="form-group">
            <label>装置类型</label>
            <select v-model="newTask.equipment_type">
              <option value="storage_tank">储罐</option>
              <option value="flange">法兰</option>
              <option value="pressure_vessel">压力容器</option>
              <option value="pipeline">管道</option>
            </select>
          </div>
          <div class="form-group">
            <label>适用标准</label>
            <div class="checkbox-group">
              <label v-for="tpl in templates" :key="tpl.code" class="checkbox-label">
                <input type="checkbox" :value="tpl.code" v-model="newTask.standard_codes" />
                {{ tpl.name }}
              </label>
            </div>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="newTask.auto_check_mandatory" />
              紧急预警自动勾选必检项
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="action-btn" @click="showCreateTask = false">取消</button>
          <button class="action-btn primary" @click="createTask">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  fetchStandardTemplates,
  fetchInspectionTasks,
  fetchInspectionTask,
  checkInspectionItem,
  checkWorkOrderClose,
  exportInspectionPdf,
  fetchCompletionScore,
  createInspectionTask,
} from '@/api/compliance'
import {
  SeverityMap,
  SeverityColorMap,
  InspectionResultMap,
  InspectionResultColorMap,
} from '@/types'
import type {
  StandardTemplate,
  InspectionTask,
  WorkOrderCloseCheck,
} from '@/types'

const activeTab = ref<'templates' | 'tasks' | 'checklist'>('templates')
const tabOptions: Array<{ value: 'templates' | 'tasks' | 'checklist'; label: string }> = [
  { value: 'templates', label: '标准模板库' },
  { value: 'tasks', label: '检验任务' },
  { value: 'checklist', label: '检查清单' },
]

const templates = ref<StandardTemplate[]>([])
const templateCategory = ref('')
const selectedTemplate = ref<StandardTemplate | null>(null)
const showCreateTemplate = ref(false)

const tasks = ref<InspectionTask[]>([])
const taskStatusFilter = ref('')
const taskEquipFilter = ref('')
const selectedTask = ref<InspectionTask | null>(null)
const showCreateTask = ref(false)
const closeCheckResult = ref<WorkOrderCloseCheck | null>(null)

const newTask = ref<{
  work_order_id: number
  equipment_type: string
  standard_codes: string[]
  auto_check_mandatory: boolean
}>({
  work_order_id: 0,
  equipment_type: 'flange',
  standard_codes: [],
  auto_check_mandatory: true,
})

const statusMap: Record<string, string> = {
  pending: '待检',
  in_progress: '进行中',
  completed: '已完成',
}

const equipMap: Record<string, string> = {
  storage_tank: '储罐',
  flange: '法兰',
  pressure_vessel: '压力容器',
  pipeline: '管道',
}

const checkedCount = computed(() => selectedTask.value?.checklist_items?.filter(i => i.checked).length || 0)
const mandatoryTotal = computed(() => selectedTask.value?.checklist_items?.filter(i => i.is_mandatory).length || 0)
const mandatoryCheckedCount = computed(() => selectedTask.value?.checklist_items?.filter(i => i.is_mandatory && i.checked).length || 0)

function scoreColor(score: number): string {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#eab308'
  if (score >= 40) return '#f97316'
  return '#ef4444'
}

async function loadTemplates() {
  try {
    const resp = await fetchStandardTemplates(templateCategory.value || undefined)
    templates.value = resp.items || []
  } catch (e) {
    console.error('加载标准模板失败:', e)
  }
}

function selectTemplate(tpl: StandardTemplate) {
  selectedTemplate.value = selectedTemplate.value?.code === tpl.code ? null : tpl
}

async function loadTasks() {
  try {
    const resp = await fetchInspectionTasks({
      status: taskStatusFilter.value || undefined,
      equipment_type: taskEquipFilter.value || undefined,
    })
    tasks.value = resp.items || []
  } catch (e) {
    console.error('加载检验任务失败:', e)
  }
}

async function selectTask(task: InspectionTask) {
  try {
    const detail = await fetchInspectionTask(task.id)
    selectedTask.value = detail
    closeCheckResult.value = null
    activeTab.value = 'checklist'
  } catch (e) {
    console.error('加载检验任务详情失败:', e)
  }
}

async function toggleItem(item: any) {
  if (!selectedTask.value || item.auto_checked) return
  const result = item.checked ? 'na' : 'pass'
  try {
    const updated = await checkInspectionItem(
      selectedTask.value.id,
      item.item_code,
      result,
    )
    selectedTask.value = updated
  } catch (e) {
    console.error('勾选检验项失败:', e)
  }
}

async function updateItemResult(item: any, result: string) {
  if (!selectedTask.value) return
  try {
    const updated = await checkInspectionItem(
      selectedTask.value.id,
      item.item_code,
      result,
    )
    selectedTask.value = updated
  } catch (e) {
    console.error('更新检验结果失败:', e)
  }
}

async function loadScore() {
  if (!selectedTask.value) return
  try {
    const resp = await fetchCompletionScore(selectedTask.value.id)
    selectedTask.value = { ...selectedTask.value, completion_score: resp.completion_score }
  } catch (e) {
    console.error('刷新评分失败:', e)
  }
}

async function checkClose() {
  if (!selectedTask.value?.work_order_id) return
  try {
    closeCheckResult.value = await checkWorkOrderClose(selectedTask.value.work_order_id)
  } catch (e) {
    console.error('检查关闭条件失败:', e)
  }
}

async function exportPdf() {
  if (!selectedTask.value) return
  try {
    const resp = await exportInspectionPdf(selectedTask.value.id)
    const blob = new Blob([resp.html_content], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const win = window.open(url, '_blank')
    if (win) {
      win.onload = () => {
        win.print()
      }
    }
  } catch (e) {
    console.error('导出PDF失败:', e)
  }
}

async function createTask() {
  try {
    const task = await createInspectionTask({
      work_order_id: newTask.value.work_order_id,
      equipment_type: newTask.value.equipment_type,
      standard_codes: newTask.value.standard_codes,
      auto_check_mandatory: newTask.value.auto_check_mandatory,
    })
    showCreateTask.value = false
    await loadTasks()
    selectedTask.value = task
    activeTab.value = 'checklist'
  } catch (e) {
    console.error('创建检验任务失败:', e)
  }
}

function refreshAll() {
  loadTemplates()
  loadTasks()
  if (selectedTask.value) {
    fetchInspectionTask(selectedTask.value.id).then(t => { selectedTask.value = t }).catch(() => {})
  }
}

onMounted(() => {
  loadTemplates()
  loadTasks()
})
</script>

<style scoped>
.compliance-inspection {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0a0e1a;
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  overflow: hidden;
}

.ci-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
}

.ci-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ci-title h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.ci-subtitle {
  font-size: 12px;
  color: #64748b;
  margin-left: 4px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  color: #94a3b8;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: rgba(255,255,255,0.1);
  color: #e2e8f0;
}

.ci-tabs {
  display: flex;
  padding: 0 24px;
  gap: 4px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  background: rgba(15, 23, 42, 0.3);
}

.ci-tab {
  padding: 10px 20px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: #64748b;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.ci-tab:hover {
  color: #94a3b8;
}

.ci-tab.active {
  color: #60a5fa;
  border-bottom-color: #3b82f6;
}

.ci-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.section-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.toolbar-left {
  display: flex;
  gap: 10px;
}

.filter-select {
  padding: 6px 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
}

.filter-select option {
  background: #1e293b;
}

.action-btn {
  padding: 7px 16px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(255,255,255,0.12);
}

.action-btn.primary {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.4);
  color: #93bbfc;
}

.action-btn.primary:hover {
  background: rgba(59, 130, 246, 0.3);
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.template-card {
  padding: 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.template-card:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(59, 130, 246, 0.3);
}

.tpl-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.tpl-code {
  font-size: 12px;
  color: #60a5fa;
  font-weight: 600;
  font-family: monospace;
}

.tpl-category {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(139, 92, 246, 0.15);
  border-radius: 10px;
  color: #a78bfa;
}

.tpl-name {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
}

.tpl-desc {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
  line-height: 1.5;
}

.tpl-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #94a3b8;
}

.tpl-mandatory {
  color: #f87171;
}

.template-detail {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 20px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.detail-header h3 {
  margin: 0;
  font-size: 16px;
}

.close-btn {
  background: none;
  border: none;
  color: #64748b;
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
}

.close-btn:hover {
  color: #e2e8f0;
}

.checklist-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.checklist-table th {
  text-align: left;
  padding: 10px 12px;
  background: rgba(255,255,255,0.04);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  color: #94a3b8;
  font-weight: 600;
  font-size: 12px;
}

.checklist-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  vertical-align: top;
}

.code-cell {
  font-family: monospace;
  color: #60a5fa;
  font-size: 12px;
}

.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.badge-red {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.badge-gray {
  background: rgba(148, 163, 184, 0.1);
  color: #94a3b8;
}

.severity-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.task-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}

.task-card {
  padding: 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.task-card:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(59, 130, 246, 0.3);
}

.task-card.task-completed {
  opacity: 0.7;
}

.task-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.task-no {
  font-family: monospace;
  font-size: 13px;
  color: #60a5fa;
}

.task-status {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 500;
}

.status-pending {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.status-in_progress {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.status-completed {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.task-info {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.task-standards {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.std-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(139, 92, 246, 0.12);
  border-radius: 10px;
  color: #a78bfa;
}

.task-score-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-track {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.06);
  border-radius: 3px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.score-text {
  font-size: 13px;
  font-weight: 600;
  min-width: 50px;
  text-align: right;
}

.checklist-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cl-header {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 16px 20px;
}

.cl-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.cl-title-row h3 {
  margin: 0;
  font-size: 16px;
}

.cl-actions {
  display: flex;
  gap: 8px;
}

.cl-stats {
  display: flex;
  gap: 24px;
}

.cl-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: #64748b;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
}

.cl-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cl-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  transition: all 0.2s;
}

.cl-item:hover {
  background: rgba(255,255,255,0.04);
}

.cl-item.item-checked {
  border-left: 3px solid #22c55e;
}

.cl-item.item-mandatory {
  border-left-color: #f97316;
}

.cl-item.item-mandatory.item-checked {
  border-left-color: #22c55e;
}

.cl-item.item-auto {
  background: rgba(59, 130, 246, 0.04);
}

.cl-item.item-fail {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.04);
}

.item-left {
  padding-top: 4px;
}

.item-check {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.item-check input {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #3b82f6;
}

.item-body {
  flex: 1;
  min-width: 0;
}

.item-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.item-code {
  font-family: monospace;
  font-size: 12px;
  color: #60a5fa;
}

.severity-tag {
  font-size: 11px;
  padding: 1px 6px;
  border: 1px solid;
  border-radius: 4px;
}

.auto-badge {
  font-size: 10px;
  padding: 1px 6px;
  background: rgba(59, 130, 246, 0.15);
  border-radius: 4px;
  color: #60a5fa;
}

.result-tag {
  font-size: 12px;
  font-weight: 600;
}

.item-content {
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 4px;
}

.item-detail {
  font-size: 12px;
  color: #64748b;
  display: flex;
  gap: 16px;
}

.item-evidence {
  margin-top: 6px;
  padding: 6px 10px;
  background: rgba(139, 92, 246, 0.06);
  border-radius: 6px;
  font-size: 11px;
  color: #a78bfa;
}

.evidence-label {
  font-weight: 600;
  margin-right: 6px;
}

.evidence-item {
  margin-right: 10px;
}

.item-inspector {
  margin-top: 4px;
  font-size: 11px;
  color: #475569;
}

.item-actions {
  display: flex;
  align-items: center;
}

.result-select {
  padding: 4px 8px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 4px;
  color: #e2e8f0;
  font-size: 12px;
}

.result-select option {
  background: #1e293b;
}

.cl-footer {
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.close-check {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.close-result {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
}

.close-ok {
  color: #22c55e;
  font-weight: 600;
}

.close-blocked {
  color: #f87171;
}

.unchecked-list {
  margin-top: 8px;
  padding-left: 16px;
}

.unchecked-item {
  font-size: 13px;
  color: #fca5a5;
  margin-bottom: 4px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  color: #475569;
}

.empty-state p {
  font-size: 14px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1e293b;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  width: 480px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  color: #94a3b8;
}

.form-group input,
.form-group select {
  padding: 8px 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 14px;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #3b82f6;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #e2e8f0;
  cursor: pointer;
}

.checkbox-label input {
  accent-color: #3b82f6;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
</style>
