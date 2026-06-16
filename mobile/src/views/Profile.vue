<template>
  <div class="profile-page">
    <div class="profile-header">
      <div class="avatar">
        {{ avatarText }}
      </div>
      <div class="user-info">
        <h2 class="user-name">{{ userStore.userInfo?.name || '巡检员' }}</h2>
        <p class="user-role">{{ roleText }}</p>
        <p v-if="userStore.userInfo?.tenant_name" class="user-tenant">
          {{ userStore.userInfo.tenant_name }}
        </p>
      </div>
    </div>

    <div class="stats-section">
      <div class="stat-item">
        <span class="stat-value">{{ stats.pending }}</span>
        <span class="stat-label">待处理工单</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="stat-value">{{ stats.today }}</span>
        <span class="stat-label">今日处理</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="stat-value">{{ stats.total }}</span>
        <span class="stat-label">累计处理</span>
      </div>
    </div>

    <div class="menu-section">
      <div class="menu-title">功能</div>

      <button class="menu-item" @click="goToOfflineQueue">
        <div class="menu-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
        </div>
        <span class="menu-label">离线队列</span>
        <span v-if="offlineStore.pendingCount > 0" class="menu-badge">
          {{ offlineStore.pendingCount }}
        </span>
        <svg class="menu-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>

      <button class="menu-item" @click="goToScan">
        <div class="menu-icon scan">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 7V5a2 2 0 0 1 2-2h2"></path>
            <path d="M17 3h2a2 2 0 0 1 2 2v2"></path>
            <path d="M21 17v2a2 2 0 0 1-2 2h-2"></path>
            <path d="M7 21H5a2 2 0 0 1-2-2v-2"></path>
            <line x1="7" y1="12" x2="17" y2="12"></line>
          </svg>
        </div>
        <span class="menu-label">扫码巡检</span>
        <svg class="menu-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
    </div>

    <div class="menu-section">
      <div class="menu-title">设置</div>

      <div class="menu-item">
        <div class="menu-icon settings">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </div>
        <span class="menu-label">系统设置</span>
        <svg class="menu-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </div>

      <div class="menu-item">
        <div class="menu-icon info">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
        </div>
        <span class="menu-label">关于</span>
        <span class="menu-value">v1.0.0</span>
        <svg class="menu-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </div>
    </div>

    <div class="logout-section">
      <button class="logout-btn" @click="handleLogout">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
          <polyline points="16 17 21 12 16 7"></polyline>
          <line x1="21" y1="12" x2="9" y2="12"></line>
        </svg>
        退出登录
      </button>
    </div>

    <div class="network-status">
      <span class="status-dot" :class="{ online: offlineStore.isOnline }"></span>
      <span class="status-text">{{ offlineStore.isOnline ? '在线' : '离线' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useOfflineStore } from '@/stores/offline'
import { fetchWorkOrders } from '@/api'

const router = useRouter()
const userStore = useUserStore()
const offlineStore = useOfflineStore()

const stats = ref({
  pending: 0,
  today: 0,
  total: 0
})

const avatarText = computed(() => {
  const name = userStore.userInfo?.name || 'U'
  return name.charAt(0).toUpperCase()
})

const roleText = computed(() => {
  const role = userStore.userInfo?.role || 'operator'
  const map: Record<string, string> = {
    tenant_admin: '租户管理员',
    admin: '管理员',
    operator: '巡检员',
    viewer: '查看员'
  }
  return map[role] || role
})

function goToOfflineQueue() {
  router.push('/offline')
}

function goToScan() {
  router.push('/scan')
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

async function loadStats() {
  try {
    const [pendingRes, allRes] = await Promise.all([
      fetchWorkOrders({ status: 'open' }, 1, 1),
      fetchWorkOrders({}, 1, 100)
    ])
    stats.value.pending = pendingRes.total

    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayItems = allRes.items.filter(item => {
      const createTime = new Date(item.create_time)
      return createTime >= today && item.status !== 'open' && item.status !== 'assigned'
    })
    stats.value.today = todayItems.length
    stats.value.total = allRes.total
  } catch (e) {
    console.error('加载统计数据失败:', e)
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.profile-page {
  min-height: 100%;
  padding-bottom: 20px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 20px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.15));
  border-bottom: 1px solid var(--border-color);
}

.avatar {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  font-size: 24px;
  font-weight: 600;
  border-radius: 50%;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.user-role {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 2px;
}

.user-tenant {
  font-size: 12px;
  color: var(--primary-light);
}

.stats-section {
  display: flex;
  align-items: center;
  padding: 20px;
  background: rgba(30, 41, 59, 0.6);
  margin: 12px 16px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: var(--border-light);
}

.menu-section {
  margin: 16px;
}

.menu-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-tertiary);
  margin-bottom: 8px;
  padding-left: 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--border-light);
  margin-bottom: 8px;
  border-radius: 10px;
  transition: all 0.2s;
  cursor: pointer;
}

.menu-item:active {
  background: rgba(30, 41, 59, 0.9);
  transform: scale(0.98);
}

.menu-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59, 130, 246, 0.15);
  color: var(--primary-light);
  border-radius: 8px;
  flex-shrink: 0;
}

.menu-icon.scan {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.menu-icon.settings {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.menu-icon.info {
  background: rgba(6, 182, 212, 0.15);
  color: #22d3ee;
}

.menu-label {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.menu-badge {
  padding: 2px 8px;
  background: var(--danger-color);
  color: white;
  font-size: 11px;
  font-weight: 600;
  border-radius: 10px;
}

.menu-value {
  font-size: 13px;
  color: var(--text-tertiary);
}

.menu-arrow {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.logout-section {
  padding: 0 16px;
  margin-top: 24px;
}

.logout-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 48px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 10px;
  color: #f87171;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.2s;
}

.logout-btn:active {
  background: rgba(239, 68, 68, 0.2);
  transform: scale(0.98);
}

.network-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 20px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.status-dot.online {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
}

.status-text {
  font-size: 12px;
}
</style>
