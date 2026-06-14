<template>
  <div class="version-list">
    <div class="panel-header">
      <div class="panel-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        版本列表
      </div>
      <div class="panel-actions" v-if="selectedVersions.length === 2">
        <button class="btn btn-compare" @click="$emit('compare')">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
          对比选中版本
        </button>
      </div>
    </div>
    <div class="version-list-content">
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
              @change="toggleSelect(ver.version)"
              :disabled="!selectedVersions.includes(ver.version) && selectedVersions.length >= 2"
            />
          </label>
          <div class="version-info">
            <div class="version-name-row">
              <span class="version-name">{{ ver.version }}</span>
              <span v-if="ver.is_active" class="active-badge">活动</span>
              <span v-if="ver.description" class="version-desc">{{ ver.description }}</span>
            </div>
            <div class="version-meta">
              {{ formatTime(ver.created_at) }} · {{ Object.keys(ver.metrics).length }}项指标
            </div>
          </div>
        </div>
        <div class="version-metrics-mini">
          <span v-for="(val, key) in ver.metrics" :key="key" class="vmm-item">
            <span class="vmm-key">{{ formatMetricKey(key as string) }}</span>
            <span class="vmm-val">{{ formatMetricValue(val as number, key as string) }}</span>
          </span>
        </div>
        <div class="version-actions">
          <button
            v-if="!ver.is_active"
            class="action-btn action-activate"
            @click.stop="$emit('activate', ver.version)"
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
            @click.stop="$emit('rollback', ver.version)"
            title="回滚到此版本"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="1 4 1 10 7 10"></polyline>
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
            </svg>
          </button>
          <button
            v-if="!ver.is_active"
            class="action-btn action-delete"
            @click.stop="$emit('delete', ver.version)"
            title="删除此版本"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
      <div v-if="versions.length === 0" class="empty-state">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        <div>暂无版本记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ModelVersion } from '@/types'

interface Props {
  versions: ModelVersion[]
  selectedVersions: string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:selectedVersions', value: string[]): void
  (e: 'activate', version: string): void
  (e: 'rollback', version: string): void
  (e: 'delete', version: string): void
  (e: 'compare'): void
}>()

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
  if (val > 0 && val < 1) return (val * 100).toFixed(1) + '%'
  return val.toFixed(4)
}

function toggleSelect(version: string) {
  const idx = props.selectedVersions.indexOf(version)
  const newSelected = [...props.selectedVersions]
  if (idx >= 0) {
    newSelected.splice(idx, 1)
  } else if (newSelected.length < 2) {
    newSelected.push(version)
  }
  emit('update:selectedVersions', newSelected)
}
</script>

<style scoped>
.version-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  backdrop-filter: blur(8px);
  overflow: hidden;
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

.version-list-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.version-list-content::-webkit-scrollbar {
  width: 5px;
}

.version-list-content::-webkit-scrollbar-thumb {
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
  flex-wrap: wrap;
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

.version-desc {
  font-size: 11px;
  color: #94a3b8;
  padding: 2px 6px;
  background: rgba(71, 85, 105, 0.3);
  border-radius: 3px;
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

.action-delete {
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.3);
}

.action-delete:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.5);
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #475569;
  font-size: 12px;
  padding: 40px 20px;
}
</style>
