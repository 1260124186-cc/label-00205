<template>
  <div class="topology-container" ref="containerRef">
    <div class="topology-header">
      <div class="topology-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="5" r="3"></circle>
          <circle cx="5" cy="19" r="3"></circle>
          <circle cx="19" cy="19" r="3"></circle>
          <line x1="12" y1="8" x2="12" y2="16"></line>
          <line x1="5" y1="16" x2="12" y2="11"></line>
          <line x1="19" y1="16" x2="12" y2="11"></line>
        </svg>
        法兰面 / 螺栓拓扑图
        <span v-if="filterActive" class="filter-badge">已筛选</span>
      </div>
      <div class="topology-legend">
        <div class="legend-title">状态图例</div>
        <div class="legend-items">
          <div v-for="code in statusOrder" :key="code" class="legend-item">
            <span class="legend-dot" :style="{ background: StatusColorMap[code] }"></span>
            <span class="legend-text">{{ StatusCodeMap[code] }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="topology-scroll" ref="scrollRef">
      <div class="topology-canvas" :style="canvasStyle">
        <div v-if="filteredFlanges.length === 0" class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <div class="empty-text">暂无匹配的数据</div>
          <div class="empty-hint">请调整筛选条件或重置</div>
        </div>

        <TransitionGroup name="flange-list" tag="div" class="flanges-grid">
          <div
            v-for="flange in filteredFlanges"
            :key="flange.flange_id"
            class="flange-node"
            :class="`flange-status-${flange.status_code}`"
            :style="getFlangeStyle(flange)"
            @click="selectFlange(flange)"
          >
            <div class="flange-header">
              <div class="flange-name" :title="flange.flange_id">
                <span class="flange-icon">⬡</span>
                {{ flange.flange_name }}
              </div>
              <div
                class="flange-status-badge"
                :style="{ background: StatusColorMap[flange.status_code] }"
              >
                {{ StatusCodeMap[flange.status_code] }}
              </div>
            </div>

            <div class="flange-meta">
              <div class="meta-item">
                <span class="meta-label">采集器</span>
                <span class="meta-value">{{ getCollectorName(flange.collector_id) }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">位置</span>
                <span class="meta-value">{{ flange.position }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">螺栓数</span>
                <span class="meta-value">{{ flange.bolt_count }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">健康度</span>
                <span
                  class="meta-value hi-value"
                  :class="getHiClass(flange.health_index)"
                >
                  {{ flange.health_index }}
                </span>
              </div>
            </div>

            <div class="bolts-ring">
              <div
                v-for="(bolt, idx) in getBoltsByFlange(flange.flange_id)"
                :key="bolt.bolt_id"
                class="bolt-node"
                :class="`bolt-status-${bolt.status_code} bolt-pos-${getBoltPositionClass(idx, flange.bolt_count)}`"
                :style="getBoltStyle(idx, flange.bolt_count, bolt)"
                @click.stop="selectBolt(bolt)"
                :title="getBoltTooltip(bolt)"
              >
                <div class="bolt-inner">
                  {{ bolt.bolt_id.slice(-3) }}
                </div>
                <div
                  v-if="bolt.status_code >= 2"
                  class="bolt-pulse"
                  :style="{ background: StatusColorMap[bolt.status_code] }"
                ></div>
              </div>

              <div class="flange-center">
                <div class="center-risk">
                  <span class="risk-label">风险</span>
                  <span
                    class="risk-score"
                    :class="getRiskClass(flange.risk_level)"
                  >
                    {{ flange.risk_score }}
                  </span>
                </div>
                <div class="center-confidence">
                  {{ Math.round(flange.confidence * 100) }}%
                </div>
              </div>
            </div>

            <div v-if="flange.status_code >= 2" class="flange-warning">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
              {{ flange.diagnosis }}
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { StatusCode, StatusCodeMap, StatusColorMap } from '@/types'
import type { Flange, Bolt, Collector, FilterOptions } from '@/types'

interface Props {
  flanges: Flange[]
  bolts: Bolt[]
  collectors: Collector[]
  filters: FilterOptions
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'select-flange', flange: Flange): void
  (e: 'select-bolt', bolt: Bolt): void
}>()

const containerRef = ref<HTMLElement | null>(null)
const scrollRef = ref<HTMLElement | null>(null)

const statusOrder: StatusCode[] = [0, 1, 2, 3, 4]

const filterActive = computed(() => {
  return (
    props.filters.collector_id !== null ||
    props.filters.position !== null ||
    props.filters.status_codes.length < 5
  )
})

const filteredFlanges = computed(() => {
  return props.flanges.filter(f => {
    if (props.filters.collector_id && f.collector_id !== props.filters.collector_id) return false
    if (props.filters.position && f.position !== props.filters.position) return false
    if (!props.filters.status_codes.includes(f.status_code)) {
      const hasMatchingBolt = props.bolts
        .filter(b => b.flange_id === f.flange_id)
        .some(b => props.filters.status_codes.includes(b.status_code))
      if (!hasMatchingBolt) return false
    }
    return true
  }).sort((a, b) => b.status_code - a.status_code)
})

const canvasStyle = computed(() => {
  const count = filteredFlanges.value.length
  const cols = count <= 1 ? 1 : count <= 2 ? 2 : count <= 4 ? 2 : count <= 6 ? 3 : count <= 9 ? 3 : 4
  return {
    '--grid-cols': String(cols)
  } as Record<string, string>
})

function getCollectorName(id: string): string {
  const c = props.collectors.find(x => x.collector_id === id)
  return c ? c.collector_name : id
}

function getBoltsByFlange(flangeId: string): Bolt[] {
  return props.bolts
    .filter(b => b.flange_id === flangeId)
    .sort((a, b) => a.bolt_id.localeCompare(b.bolt_id))
}

function getFlangeStyle(flange: Flange): Record<string, string> {
  const color = StatusColorMap[flange.status_code]
  return {
    '--flange-border-color': color,
    '--flange-glow': `${color}33`
  }
}

function getBoltPositionClass(idx: number, total: number): number {
  return total
}

function getBoltStyle(idx: number, total: number, bolt: Bolt): Record<string, string> {
  const angle = (idx / Math.max(total, 1)) * Math.PI * 2 - Math.PI / 2
  const radius = 58
  const x = 50 + Math.cos(angle) * radius / 2
  const y = 50 + Math.sin(angle) * radius / 2
  const color = StatusColorMap[bolt.status_code]
  const hasFilter = props.filters.status_codes.length < 5
  const dimmed = hasFilter && !props.filters.status_codes.includes(bolt.status_code)

  return {
    left: `${x}%`,
    top: `${y}%`,
    '--bolt-color': color,
    '--bolt-glow': `${color}66`,
    opacity: dimmed ? '0.25' : '1'
  }
}

function getBoltTooltip(bolt: Bolt): string {
  return [
    `螺栓: ${bolt.bolt_id}`,
    `状态: ${StatusCodeMap[bolt.status_code]}`,
    `预紧力: ${bolt.current_preload} / ${bolt.nominal_preload}`,
    `置信度: ${Math.round(bolt.confidence * 100)}%`,
    `风险评分: ${bolt.risk_score} (${bolt.risk_level})`,
    `诊断: ${bolt.diagnosis}`
  ].join('\n')
}

function getHiClass(hi?: number): string {
  if (hi === undefined) return ''
  if (hi >= 80) return 'hi-good'
  if (hi >= 60) return 'hi-fair'
  return 'hi-poor'
}

function getRiskClass(level: string): string {
  return `risk-${level}`
}

function selectFlange(flange: Flange) {
  emit('select-flange', flange)
}

function selectBolt(bolt: Bolt) {
  emit('select-bolt', bolt)
}
</script>

<style scoped>
.topology-container {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  backdrop-filter: blur(8px);
}

.topology-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  flex-shrink: 0;
  gap: 16px;
  flex-wrap: wrap;
}

.topology-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.filter-badge {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid rgba(59, 130, 246, 0.4);
  font-weight: 500;
}

.topology-legend {
  display: flex;
  align-items: center;
  gap: 14px;
}

.legend-title {
  font-size: 11px;
  color: #94a3b8;
}

.legend-items {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #cbd5e1;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  box-shadow: 0 0 6px currentColor;
}

.topology-scroll {
  flex: 1;
  overflow: auto;
  padding: 20px;
}

.topology-scroll::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.topology-scroll::-webkit-scrollbar-track {
  background: rgba(30, 41, 59, 0.5);
  border-radius: 4px;
}

.topology-scroll::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.5);
  border-radius: 4px;
}

.topology-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.8);
}

.topology-canvas {
  min-height: 100%;
}

.flanges-grid {
  display: grid;
  grid-template-columns: repeat(var(--grid-cols, 3), minmax(280px, 1fr));
  gap: 18px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #64748b;
  gap: 10px;
  grid-column: 1 / -1;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  color: #94a3b8;
}

.empty-hint {
  font-size: 13px;
  color: #64748b;
}

.flange-node {
  background: rgba(30, 41, 59, 0.7);
  border: 1.5px solid var(--flange-border-color, rgba(59, 130, 246, 0.3));
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 0 0 var(--flange-glow);
  position: relative;
}

.flange-node::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 12px;
  padding: 1.5px;
  background: linear-gradient(
    135deg,
    var(--flange-border-color) 0%,
    transparent 40%,
    transparent 60%,
    var(--flange-border-color) 100%
  );
  opacity: 0.4;
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
  pointer-events: none;
}

.flange-node:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px var(--flange-glow), 0 0 20px var(--flange-glow);
}

.flange-status-3,
.flange-status-4 {
  animation: flange-warn-pulse 2s ease-in-out infinite;
}

@keyframes flange-warn-pulse {
  0%, 100% { box-shadow: 0 0 0 var(--flange-glow); }
  50% { box-shadow: 0 0 24px var(--flange-glow), 0 0 48px var(--flange-glow); }
}

.flange-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
  gap: 8px;
}

.flange-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  line-height: 1.3;
}

.flange-icon {
  color: #60a5fa;
  font-size: 16px;
}

.flange-status-badge {
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  color: white;
  white-space: nowrap;
  flex-shrink: 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.flange-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 10px;
  margin-bottom: 12px;
  padding: 8px 10px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 6px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

.meta-label {
  color: #64748b;
  flex-shrink: 0;
}

.meta-value {
  color: #cbd5e1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hi-value { font-weight: 700; }
.hi-good { color: #22c55e; }
.hi-fair { color: #eab308; }
.hi-poor { color: #ef4444; }

.bolts-ring {
  position: relative;
  width: 100%;
  padding-top: 100%;
  margin-bottom: 10px;
  background:
    radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 65%),
    repeating-radial-gradient(
      circle at 50% 50%,
      transparent 0,
      transparent 28%,
      rgba(59, 130, 246, 0.1) 28.5%,
      transparent 29%
    );
  border-radius: 50%;
}

.flange-center {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 52%;
  height: 52%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(15, 23, 42, 0.95) 60%, rgba(15, 23, 42, 0.7) 100%);
  border: 1px solid rgba(59, 130, 246, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.4);
}

.center-risk {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1;
}

.risk-label {
  font-size: 9px;
  color: #64748b;
  margin-bottom: 3px;
}

.risk-score {
  font-size: 20px;
  font-weight: 800;
  line-height: 1;
}

.risk-low { color: #22c55e; }
.risk-medium { color: #eab308; }
.risk-high { color: #ef4444; }

.center-confidence {
  font-size: 10px;
  color: #94a3b8;
  margin-top: 2px;
}

.bolt-node {
  position: absolute;
  width: 30px;
  height: 30px;
  transform: translate(-50%, -50%);
  cursor: pointer;
  z-index: 2;
}

.bolt-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--bolt-color);
  color: white;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 0 10px var(--bolt-glow),
    inset 0 1px 2px rgba(255, 255, 255, 0.3),
    0 2px 4px rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 255, 255, 0.2);
  transition: all 0.2s ease;
}

.bolt-node:hover .bolt-inner {
  transform: scale(1.25);
  box-shadow:
    0 0 20px var(--bolt-glow),
    0 0 30px var(--bolt-glow);
  border-color: rgba(255, 255, 255, 0.5);
}

.bolt-pulse {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  opacity: 0.4;
  animation: bolt-pulse 1.5s ease-out infinite;
  z-index: -1;
}

@keyframes bolt-pulse {
  0% {
    transform: scale(0.9);
    opacity: 0.6;
  }
  100% {
    transform: scale(1.8);
    opacity: 0;
  }
}

.flange-warning {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 10px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 6px;
  font-size: 11px;
  color: #fbbf24;
  line-height: 1.4;
}

.flange-status-3 .flange-warning,
.flange-status-4 .flange-warning {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.flange-list-enter-active,
.flange-list-leave-active {
  transition: all 0.4s ease;
}

.flange-list-enter-from,
.flange-list-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(10px);
}

.flange-list-move {
  transition: transform 0.4s ease;
}
</style>
