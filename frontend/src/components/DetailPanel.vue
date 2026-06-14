<template>
  <div class="detail-panel" v-if="selectedBolt || selectedFlange">
    <div class="detail-header">
      <div class="detail-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
        {{ selectedBolt ? '螺栓详情' : '法兰面详情' }}
      </div>
      <button class="close-btn" @click="$emit('close')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <template v-if="selectedBolt">
      <div class="detail-section">
        <div
          class="status-header"
          :style="{ background: StatusColorMap[selectedBolt.status_code] + '22', borderColor: StatusColorMap[selectedBolt.status_code] + '55' }"
        >
          <div class="status-dot" :style="{ background: StatusColorMap[selectedBolt.status_code] }"></div>
          <div>
            <div class="status-main">{{ StatusCodeMap[selectedBolt.status_code] }}</div>
            <div class="status-sub">置信度 {{ Math.round(selectedBolt.confidence * 100) }}%</div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">基本信息</div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">螺栓ID</span>
            <span class="info-value">{{ selectedBolt.bolt_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">采集器</span>
            <span class="info-value">{{ collectorName }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">分线器</span>
            <span class="info-value">{{ selectedBolt.splitter_num }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">安装位置</span>
            <span class="info-value">{{ selectedBolt.position }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">所属法兰面</span>
            <span class="info-value monospace">{{ selectedBolt.flange_id }}</span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">预紧力状态</div>
        <div class="preload-bar">
          <div class="preload-track">
            <div
              class="preload-fill"
              :style="{
                width: preloadPercent + '%',
                background: preloadColor
              }"
            ></div>
          </div>
          <div class="preload-values">
            <span>{{ selectedBolt.current_preload }}</span>
            <span>/ {{ selectedBolt.nominal_preload }} kN</span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">风险评估</div>
        <div class="risk-row">
          <div class="risk-score-box" :class="`risk-${selectedBolt.risk_level}`">
            <div class="score-num">{{ selectedBolt.risk_score }}</div>
            <div class="score-label">风险评分</div>
          </div>
          <div class="risk-score-box hi-box">
            <div class="score-num" :class="getHiClass(selectedBolt.health_index)">{{ selectedBolt.health_index }}</div>
            <div class="score-label">健康指数</div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">AI诊断</div>
        <div class="diagnosis-box">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          {{ selectedBolt.diagnosis }}
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">推荐措施</div>
        <ul class="recommend-list">
          <li v-for="(rec, idx) in selectedBolt.recommendations" :key="idx">
            <span class="rec-num">{{ idx + 1 }}</span>
            {{ rec }}
          </li>
        </ul>
      </div>

      <div class="detail-section">
        <div class="update-time">
          最后更新: {{ formatTime(selectedBolt.last_update_time) }}
        </div>
      </div>
    </template>

    <template v-else-if="selectedFlange">
      <div class="detail-section">
        <div
          class="status-header"
          :style="{ background: StatusColorMap[selectedFlange.status_code] + '22', borderColor: StatusColorMap[selectedFlange.status_code] + '55' }"
        >
          <div class="status-dot" :style="{ background: StatusColorMap[selectedFlange.status_code] }"></div>
          <div>
            <div class="status-main">{{ StatusCodeMap[selectedFlange.status_code] }}</div>
            <div class="status-sub">置信度 {{ Math.round(selectedFlange.confidence * 100) }}% · 共 {{ selectedFlange.bolt_count }} 个螺栓</div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">基本信息</div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">法兰面名称</span>
            <span class="info-value">{{ selectedFlange.flange_name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">法兰面ID</span>
            <span class="info-value monospace">{{ selectedFlange.flange_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">采集器</span>
            <span class="info-value">{{ flangeCollectorName }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">安装位置</span>
            <span class="info-value">{{ selectedFlange.position }}</span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">综合评估</div>
        <div class="risk-row">
          <div class="risk-score-box" :class="`risk-${selectedFlange.risk_level}`">
            <div class="score-num">{{ selectedFlange.risk_score }}</div>
            <div class="score-label">风险评分</div>
          </div>
          <div class="risk-score-box hi-box">
            <div class="score-num" :class="getHiClass(selectedFlange.health_index)">{{ selectedFlange.health_index }}</div>
            <div class="score-label">健康指数</div>
          </div>
          <div class="risk-score-box worst-box">
            <div class="score-num small" :class="getHiClass(selectedFlange.worst_bolt_hi)">
              {{ selectedFlange.worst_bolt_hi }}
            </div>
            <div class="score-label">最差螺栓</div>
            <div class="score-sub">{{ selectedFlange.worst_bolt_id }}</div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">螺栓状态分布</div>
        <div class="bolt-status-summary">
          <div
            v-for="code in statusOrder"
            :key="code"
            class="bolt-status-bar"
            :style="{ background: StatusColorMap[code] + '33', borderColor: StatusColorMap[code] + '55' }"
          >
            <div class="bs-dot" :style="{ background: StatusColorMap[code] }"></div>
            <span class="bs-label">{{ StatusCodeMap[code] }}</span>
            <span class="bs-count">{{ flangeBoltStatusCount(code) }}</span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">AI诊断</div>
        <div class="diagnosis-box">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          {{ selectedFlange.diagnosis }}
        </div>
      </div>

      <div class="detail-section">
        <div class="section-label">推荐措施</div>
        <ul class="recommend-list">
          <li v-for="(rec, idx) in selectedFlange.recommendations" :key="idx">
            <span class="rec-num">{{ idx + 1 }}</span>
            {{ rec }}
          </li>
        </ul>
      </div>

      <div class="detail-section" v-if="flangeBolts.length">
        <div class="section-label">
          螺栓列表
          <span class="bolt-count-badge">{{ flangeBolts.length }}</span>
        </div>
        <div class="bolt-mini-list">
          <div
            v-for="bolt in flangeBolts"
            :key="bolt.bolt_id"
            class="bolt-mini-item"
            :class="`bolt-status-${bolt.status_code}`"
            @click="$emit('select-bolt', bolt)"
          >
            <span class="bmi-dot" :style="{ background: StatusColorMap[bolt.status_code] }"></span>
            <span class="bmi-id">{{ bolt.bolt_id }}</span>
            <span class="bmi-value">{{ bolt.current_preload }}kN</span>
            <span class="bmi-hi" :class="getHiClass(bolt.health_index)">{{ bolt.health_index }}</span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="update-time">
          最后更新: {{ formatTime(selectedFlange.last_update_time) }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { StatusCode, StatusCodeMap, StatusColorMap } from '@/types'
import type { Bolt, Flange, Collector } from '@/types'

interface Props {
  selectedBolt: Bolt | null
  selectedFlange: Flange | null
  bolts: Bolt[]
  collectors: Collector[]
}

const props = defineProps<Props>()
defineEmits<{
  (e: 'close'): void
  (e: 'select-bolt', bolt: Bolt): void
}>()

const statusOrder: StatusCode[] = [0, 1, 2, 3, 4]

const collectorName = computed(() => {
  if (!props.selectedBolt) return '-'
  const c = props.collectors.find(x => x.collector_id === props.selectedBolt!.collector_id)
  return c ? c.collector_name : props.selectedBolt.collector_id
})

const flangeCollectorName = computed(() => {
  if (!props.selectedFlange) return '-'
  const c = props.collectors.find(x => x.collector_id === props.selectedFlange!.collector_id)
  return c ? c.collector_name : props.selectedFlange.collector_id
})

const preloadPercent = computed(() => {
  if (!props.selectedBolt) return 0
  return Math.max(0, Math.min(100, (props.selectedBolt.current_preload / props.selectedBolt.nominal_preload) * 100))
})

const preloadColor = computed(() => {
  const p = preloadPercent.value
  if (p >= 90 && p <= 110) return '#22c55e'
  if (p >= 80 && p <= 120) return '#eab308'
  return '#ef4444'
})

const flangeBolts = computed(() => {
  if (!props.selectedFlange) return []
  return props.bolts
    .filter(b => b.flange_id === props.selectedFlange!.flange_id)
    .sort((a, b) => b.status_code - a.status_code || a.bolt_id.localeCompare(b.bolt_id))
})

function flangeBoltStatusCount(code: StatusCode): number {
  return flangeBolts.value.filter(b => b.status_code === code).length
}

function getHiClass(hi?: number): string {
  if (hi === undefined) return ''
  if (hi >= 80) return 'hi-good'
  if (hi >= 60) return 'hi-fair'
  return 'hi-poor'
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<style scoped>
.detail-panel {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  flex-shrink: 0;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.close-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: rgba(71, 85, 105, 0.5);
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.detail-panel :deep(> .detail-section + .detail-section) {
  border-top: 1px solid rgba(51, 65, 85, 0.5);
}

.detail-section {
  padding: 12px 16px;
  overflow-y: auto;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.bolt-count-badge {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  font-size: 10px;
  padding: 1px 7px;
  border-radius: 8px;
  text-transform: none;
  letter-spacing: normal;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 8px;
  border: 1px solid;
}

.status-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  box-shadow: 0 0 12px currentColor;
  flex-shrink: 0;
}

.status-main {
  font-size: 16px;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.2;
}

.status-sub {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 14px;
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
  color: #e2e8f0;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.monospace {
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 11px;
  color: #60a5fa;
}

.preload-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preload-track {
  height: 10px;
  background: rgba(51, 65, 85, 0.6);
  border-radius: 5px;
  overflow: hidden;
}

.preload-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.5s ease;
  box-shadow: 0 0 10px currentColor;
}

.preload-values {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #cbd5e1;
  font-weight: 600;
}

.risk-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.risk-score-box {
  padding: 12px 8px;
  border-radius: 8px;
  text-align: center;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(51, 65, 85, 0.5);
}

.risk-score-box.risk-low { border-color: rgba(34, 197, 94, 0.4); }
.risk-score-box.risk-medium { border-color: rgba(234, 179, 8, 0.4); }
.risk-score-box.risk-high { border-color: rgba(239, 68, 68, 0.4); }

.score-num {
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  margin-bottom: 4px;
}

.risk-low .score-num { color: #22c55e; }
.risk-medium .score-num { color: #eab308; }
.risk-high .score-num { color: #ef4444; }

.score-num.small { font-size: 18px; }

.hi-good { color: #22c55e !important; }
.hi-fair { color: #eab308 !important; }
.hi-poor { color: #ef4444 !important; }

.score-label {
  font-size: 10px;
  color: #94a3b8;
}

.score-sub {
  font-size: 9px;
  color: #64748b;
  margin-top: 2px;
  font-family: 'SF Mono', Monaco, monospace;
}

.diagnosis-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  font-size: 12px;
  color: #93c5fd;
  line-height: 1.5;
}

.recommend-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recommend-list li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: #cbd5e1;
  line-height: 1.5;
  padding: 8px 10px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
}

.rec-num {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.3);
  color: #60a5fa;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.bolt-status-summary {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
}

.bolt-status-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 8px 4px;
  border-radius: 6px;
  border: 1px solid;
}

.bs-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 4px currentColor;
}

.bs-label {
  font-size: 9px;
  color: #94a3b8;
  text-align: center;
}

.bs-count {
  font-size: 16px;
  font-weight: 700;
  color: #f1f5f9;
}

.bolt-mini-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 4px;
}

.bolt-mini-list::-webkit-scrollbar {
  width: 4px;
}

.bolt-mini-list::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.5);
  border-radius: 2px;
}

.bolt-mini-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}

.bolt-mini-item:hover {
  background: rgba(51, 65, 85, 0.6);
}

.bolt-mini-item.bolt-status-2 { border-left-color: #f97316; }
.bolt-mini-item.bolt-status-3 { border-left-color: #ef4444; }
.bolt-mini-item.bolt-status-4 { border-left-color: #7f1d1d; }

.bmi-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 4px currentColor;
}

.bmi-id {
  font-family: 'SF Mono', Monaco, monospace;
  color: #e2e8f0;
  font-weight: 600;
  flex: 1;
}

.bmi-value {
  color: #94a3b8;
  font-size: 11px;
}

.bmi-hi {
  font-weight: 700;
  font-size: 12px;
  width: 28px;
  text-align: right;
}

.update-time {
  font-size: 11px;
  color: #64748b;
  text-align: right;
  padding-top: 4px;
}
</style>
