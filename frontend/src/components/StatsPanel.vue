<template>
  <div class="stats-panel">
    <div class="stats-title">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="20" x2="18" y2="10"></line>
        <line x1="12" y1="20" x2="12" y2="4"></line>
        <line x1="6" y1="20" x2="6" y2="14"></line>
      </svg>
      运行概览
    </div>

    <div class="stats-grid">
      <div class="stat-card stat-total">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.total_bolts }}</div>
          <div class="stat-label">螺栓总数</div>
        </div>
      </div>

      <div class="stat-card stat-flange">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2"></rect>
            <line x1="3" y1="9" x2="21" y2="9"></line>
            <line x1="9" y1="21" x2="9" y2="9"></line>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.total_flanges }}</div>
          <div class="stat-label">法兰面数</div>
        </div>
      </div>

      <div class="stat-card stat-collector" :class="stats.online_collectors < stats.total_collectors ? 'warning' : ''">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="2" width="20" height="8" rx="2"></rect>
            <rect x="2" y="14" width="20" height="8" rx="2"></rect>
            <line x1="6" y1="6" x2="6.01" y2="6"></line>
            <line x1="6" y1="18" x2="6.01" y2="18"></line>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.online_collectors }}/{{ stats.total_collectors }}</div>
          <div class="stat-label">在线采集器</div>
        </div>
      </div>

      <div class="stat-card stat-health">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value" :class="healthClass">{{ stats.avg_health_index }}</div>
          <div class="stat-label">平均健康指数</div>
        </div>
      </div>
    </div>

    <div class="status-distribution">
      <div class="dist-title">螺栓状态分布</div>
      <div class="dist-bars">
        <div
          v-for="code in statusOrder"
          :key="code"
          class="dist-bar-item"
        >
          <div class="dist-bar-label">
            <span class="dist-dot" :style="{ background: StatusColorMap[code] }"></span>
            {{ StatusCodeMap[code] }}
          </div>
          <div class="dist-bar-track">
            <div
              class="dist-bar-fill"
              :style="{
                width: getBarWidth(code) + '%',
                background: StatusColorMap[code],
                boxShadow: `0 0 10px ${StatusColorMap[code]}66`
              }"
            ></div>
          </div>
          <div class="dist-bar-value">{{ statusCount(code) }}</div>
        </div>
      </div>
    </div>

    <div class="risk-distribution">
      <div class="dist-title">风险等级分布</div>
      <div class="risk-cards">
        <div class="risk-card risk-low">
          <div class="risk-count">{{ stats.risk_distribution.low }}</div>
          <div class="risk-label">低风险</div>
        </div>
        <div class="risk-card risk-medium">
          <div class="risk-count">{{ stats.risk_distribution.medium }}</div>
          <div class="risk-label">中风险</div>
        </div>
        <div class="risk-card risk-high">
          <div class="risk-count">{{ stats.risk_distribution.high }}</div>
          <div class="risk-label">高风险</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { StatusCode, StatusCodeMap, StatusColorMap } from '@/types'
import type { Statistics } from '@/types'

interface Props {
  stats: Statistics
}

const props = defineProps<Props>()

const statusOrder: StatusCode[] = [0, 1, 2, 3, 4]

const healthClass = computed(() => {
  const hi = props.stats.avg_health_index
  if (hi >= 80) return 'good'
  if (hi >= 60) return 'fair'
  return 'poor'
})

function statusCount(code: StatusCode): number {
  return props.stats.status_distribution[code] || 0
}

function getBarWidth(code: StatusCode): number {
  const total = Math.max(1, props.stats.total_bolts)
  return (statusCount(code) / total) * 100
}
</script>

<style scoped>
.stats-panel {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  padding: 16px;
  backdrop-filter: blur(8px);
}

.stats-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(51, 65, 85, 0.5);
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: rgba(59, 130, 246, 0.4);
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-total .stat-icon { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
.stat-flange .stat-icon { background: rgba(139, 92, 246, 0.2); color: #a78bfa; }
.stat-collector .stat-icon { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.stat-collector.warning .stat-icon { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
.stat-health .stat-icon { background: rgba(236, 72, 153, 0.2); color: #f472b6; }

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.2;
}

.stat-value.good { color: #22c55e; }
.stat-value.fair { color: #eab308; }
.stat-value.poor { color: #ef4444; }

.stat-label {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.dist-title {
  font-size: 13px;
  font-weight: 600;
  color: #cbd5e1;
  margin-bottom: 12px;
}

.status-distribution {
  margin-bottom: 20px;
  padding: 14px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 8px;
}

.dist-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dist-bar-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dist-bar-label {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 80px;
  font-size: 11px;
  color: #94a3b8;
  flex-shrink: 0;
}

.dist-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.dist-bar-track {
  flex: 1;
  height: 8px;
  background: rgba(51, 65, 85, 0.6);
  border-radius: 4px;
  overflow: hidden;
}

.dist-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.dist-bar-value {
  width: 36px;
  text-align: right;
  font-size: 12px;
  font-weight: 600;
  color: #e2e8f0;
  flex-shrink: 0;
}

.risk-distribution {
  padding: 14px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 8px;
}

.risk-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.risk-card {
  padding: 10px 6px;
  border-radius: 6px;
  text-align: center;
  transition: transform 0.2s;
}

.risk-card:hover {
  transform: scale(1.03);
}

.risk-low { background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); }
.risk-medium { background: rgba(234, 179, 8, 0.15); border: 1px solid rgba(234, 179, 8, 0.3); }
.risk-high { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); }

.risk-low .risk-count { color: #22c55e; }
.risk-medium .risk-count { color: #eab308; }
.risk-high .risk-count { color: #ef4444; }

.risk-count {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.2;
}

.risk-label {
  font-size: 10px;
  color: #94a3b8;
  margin-top: 2px;
}
</style>
