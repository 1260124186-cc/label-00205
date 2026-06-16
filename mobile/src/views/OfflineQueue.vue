<template>
  <div class="offline-queue-page">
    <div class="page-header">
      <h2 class="page-title">离线队列</h2>
      <p class="page-desc">
        <span class="status-dot" :class="{ online: offlineStore.isOnline }"></span>
        {{ offlineStore.isOnline ? '在线 - 自动同步中' : '离线 - 数据暂存本地' }}
      </p>
    </div>

    <div v-if="offlineStore.queue.length === 0" class="empty-state">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
      <p class="empty-title">暂无待同步数据</p>
      <p class="empty-desc">所有数据都已同步到服务器</p>
    </div>

    <div v-else class="queue-list">
      <div class="list-header">
        <span class="list-title">待同步 ({{ offlineStore.pendingCount }})</span>
        <button
          v-if="offlineStore.isOnline && offlineStore.pendingCount > 0"
          class="sync-btn"
          :disabled="offlineStore.syncing"
          @click="syncAll"
        >
          <svg v-if="!offlineStore.syncing" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          <svg v-else class="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
          </svg>
          {{ offlineStore.syncing ? '同步中...' : '立即同步' }}
        </button>
      </div>

      <div
        v-for="item in offlineStore.queue"
        :key="item.id"
        class="queue-item"
        :class="`status-${item.status}`"
      >
        <div class="item-icon" :class="`icon-${item.type}`">
          <svg v-if="item.type === 'retest'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          <svg v-else-if="item.type === 'photo'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21 15 16 10 5 21"></polyline>
          </svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
          </svg>
        </div>

        <div class="item-info">
          <h4 class="item-title">{{ typeText(item.type) }}</h4>
          <p class="item-desc">{{ item.data.work_order_id ? `工单 #${item.data.work_order_id}` : item.data.title || '数据记录' }}</p>
          <p class="item-time">{{ formatTime(item.createdAt) }}</p>
        </div>

        <div class="item-status">
          <span v-if="item.status === 'pending'" class="status-pending">待同步</span>
          <span v-else-if="item.status === 'uploading'" class="status-uploading">
            <span class="mini-spinner"></span>
            上传中
          </span>
          <span v-else class="status-failed">失败</span>
        </div>

        <button v-if="item.status === 'failed'" class="retry-btn" @click="retryItem(item)">
          重试
        </button>

        <button class="remove-btn" @click="removeItem(item.id)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>

    <div v-if="offlineStore.failedCount > 0" class="failed-section">
      <div class="failed-header">
        <span class="failed-title">同步失败 ({{ offlineStore.failedCount }})</span>
        <button class="retry-all-btn" @click="retryAll">全部重试</button>
      </div>
      <p class="failed-tip">点击重试按钮或网络恢复后自动同步</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useOfflineStore } from '@/stores/offline'
import type { OfflineQueueItem } from '@/types'

const offlineStore = useOfflineStore()

function typeText(type: string): string {
  const map: Record<string, string> = {
    retest: '复测记录',
    photo: '现场照片',
    voice: '语音备注'
  }
  return map[type] || type
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / (1000 * 60))

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`

  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function syncAll() {
  offlineStore.syncQueue()
}

function retryItem(item: OfflineQueueItem) {
  offlineStore.updateQueueItem(item.id, { status: 'pending', retryCount: 0, error: undefined })
  if (offlineStore.isOnline) {
    offlineStore.syncQueue()
  }
}

function retryAll() {
  offlineStore.queue.forEach(item => {
    if (item.status === 'failed') {
      offlineStore.updateQueueItem(item.id, { status: 'pending', retryCount: 0, error: undefined })
    }
  })
  if (offlineStore.isOnline) {
    offlineStore.syncQueue()
  }
}

function removeItem(id: string) {
  offlineStore.removeFromQueue(id)
}
</script>

<style scoped>
.offline-queue-page {
  min-height: 100%;
  padding-bottom: 20px;
}

.page-header {
  padding: 20px 16px;
  background: rgba(30, 41, 59, 0.6);
  border-bottom: 1px solid var(--border-light);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.page-desc {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.status-dot.online {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  gap: 12px;
  color: var(--text-tertiary);
  text-align: center;
}

.empty-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-secondary);
}

.empty-desc {
  font-size: 13px;
  color: var(--text-tertiary);
}

.queue-list {
  padding: 12px 16px;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.list-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.sync-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  color: var(--primary-light);
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
}

.sync-btn:disabled {
  opacity: 0.6;
}

.sync-btn .spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  margin-bottom: 10px;
  position: relative;
}

.queue-item.status-failed {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.05);
}

.queue-item.status-uploading {
  border-color: rgba(59, 130, 246, 0.3);
}

.item-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  flex-shrink: 0;
}

.icon-retest {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.icon-photo {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.icon-voice {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.item-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-time {
  font-size: 11px;
  color: var(--text-tertiary);
}

.item-status {
  flex-shrink: 0;
}

.status-pending {
  padding: 4px 10px;
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  font-size: 11px;
  font-weight: 500;
  border-radius: 12px;
}

.status-uploading {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  font-size: 11px;
  font-weight: 500;
  border-radius: 12px;
}

.mini-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(96, 165, 250, 0.3);
  border-top-color: #60a5fa;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.status-failed {
  padding: 4px 10px;
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  font-size: 11px;
  font-weight: 500;
  border-radius: 12px;
}

.retry-btn {
  padding: 6px 12px;
  background: var(--primary-color);
  color: white;
  font-size: 12px;
  font-weight: 500;
  border-radius: 6px;
  flex-shrink: 0;
}

.remove-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  opacity: 0.6;
  transition: opacity 0.2s;
}

.remove-btn:active {
  opacity: 1;
}

.failed-section {
  margin: 16px;
  padding: 16px;
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 12px;
}

.failed-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.failed-title {
  font-size: 14px;
  font-weight: 600;
  color: #f87171;
}

.retry-all-btn {
  padding: 6px 12px;
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  color: #f87171;
  font-size: 12px;
  font-weight: 500;
}

.failed-tip {
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>
