<template>
  <div class="training-chart">
    <div v-if="!session" class="chart-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
        <path d="M12 20V10"></path>
        <path d="M18 20V4"></path>
        <path d="M6 20v-4"></path>
      </svg>
      <div>选择训练会话查看曲线</div>
    </div>
    <template v-else>
      <div class="training-progress" v-if="session.status === 'running'">
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: (session.current_epoch / session.total_epochs * 100) + '%' }"
          ></div>
        </div>
        <span class="progress-text">
          Epoch {{ session.current_epoch }} / {{ session.total_epochs }}
          ({{ (session.current_epoch / session.total_epochs * 100).toFixed(0) }}%)
        </span>
      </div>
      <div ref="chartRef" class="chart-container"></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { TrainingSession } from '@/types'

interface Props {
  session: TrainingSession | null
}

const props = defineProps<Props>()

const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!chartRef.value || !props.session) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const history = props.session.metrics_history
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

  chart.setOption(option, true)
}

function handleResize() {
  chart?.resize()
}

watch(() => props.session, async () => {
  await nextTick()
  renderChart()
}, { deep: true })

onMounted(() => {
  window.addEventListener('resize', handleResize)
  if (props.session) {
    nextTick(() => renderChart())
  }
})

onBeforeUnmount(() => {
  chart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.training-chart {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 200px;
}

.chart-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
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
  min-height: 0;
}
</style>
