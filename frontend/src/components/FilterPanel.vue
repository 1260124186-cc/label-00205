<template>
  <div class="filter-panel">
    <div class="filter-title">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
      </svg>
      筛选条件
    </div>

    <div class="filter-group">
      <label class="filter-label">采集器</label>
      <select v-model="localCollectorId" @change="onCollectorChange" class="filter-select">
        <option :value="null">全部采集器</option>
        <option v-for="c in collectorOptions" :key="c.collector_id" :value="c.collector_id">
          {{ c.collector_name }} ({{ c.collector_id }})
        </option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label">安装位置</label>
      <select v-model="localPosition" @change="onPositionChange" class="filter-select" :disabled="!positionOptions.length">
        <option :value="null">全部位置</option>
        <option v-for="p in positionOptions" :key="p.position + p.collector_id" :value="p.position">
          {{ p.position }}
        </option>
      </select>
    </div>

    <div class="filter-group">
      <label class="filter-label">状态等级</label>
      <div class="status-checkboxes">
        <label v-for="code in allStatusCodes" :key="code" class="status-checkbox">
          <input
            type="checkbox"
            :checked="localStatusCodes.includes(code)"
            @change="toggleStatusCode(code)"
          />
          <span class="status-indicator" :style="{ background: StatusColorMap[code] }"></span>
          <span class="status-text">{{ StatusCodeMap[code] }}</span>
        </label>
      </div>
    </div>

    <div class="filter-actions">
      <button @click="resetFilters" class="btn btn-secondary">重置</button>
      <button @click="applyFilters" class="btn btn-primary">应用</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { StatusCode, StatusCodeMap, StatusColorMap } from '@/types'
import type { FilterOptions } from '@/types'

interface Props {
  modelValue: FilterOptions
  collectorOptions: { collector_id: string; collector_name: string }[]
  positionOptions: { position: string; collector_id: string }[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: FilterOptions): void
  (e: 'collector-change', collectorId: string | null): void
}>()

const allStatusCodes: StatusCode[] = [0, 1, 2, 3, 4]

const localCollectorId = ref<string | null>(props.modelValue.collector_id)
const localPosition = ref<string | null>(props.modelValue.position)
const localStatusCodes = ref<StatusCode[]>([...props.modelValue.status_codes])

watch(
  () => props.modelValue,
  val => {
    localCollectorId.value = val.collector_id
    localPosition.value = val.position
    localStatusCodes.value = [...val.status_codes]
  }
)

function onCollectorChange() {
  localPosition.value = null
  emit('collector-change', localCollectorId.value)
}

function onPositionChange() {}

function toggleStatusCode(code: StatusCode) {
  const idx = localStatusCodes.value.indexOf(code)
  if (idx >= 0) {
    localStatusCodes.value.splice(idx, 1)
  } else {
    localStatusCodes.value.push(code)
  }
}

function resetFilters() {
  localCollectorId.value = null
  localPosition.value = null
  localStatusCodes.value = [0, 1, 2, 3, 4]
  emit('collector-change', null)
  applyFilters()
}

function applyFilters() {
  emit('update:modelValue', {
    collector_id: localCollectorId.value,
    position: localPosition.value,
    status_codes: [...localStatusCodes.value]
  })
}
</script>

<style scoped>
.filter-panel {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  padding: 16px;
  backdrop-filter: blur(8px);
}

.filter-title {
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

.filter-group {
  margin-bottom: 16px;
}

.filter-label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.filter-select {
  width: 100%;
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.filter-select:hover:not(:disabled),
.filter-select:focus {
  border-color: rgba(59, 130, 246, 0.7);
  outline: none;
}

.filter-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #cbd5e1;
}

.status-checkbox input {
  width: 14px;
  height: 14px;
  accent-color: #3b82f6;
  cursor: pointer;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  box-shadow: 0 0 8px currentColor;
}

.status-text {
  flex: 1;
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

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
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
