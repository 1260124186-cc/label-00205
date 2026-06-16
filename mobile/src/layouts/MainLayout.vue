<template>
  <div class="main-layout">
    <header class="app-header">
      <div class="header-left">
        <button v-if="showBack" class="back-btn" @click="goBack">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <h1 class="page-title">{{ pageTitle }}</h1>
      </div>
      <div class="header-right">
        <div v-if="!offlineStore.isOnline" class="offline-indicator" title="离线模式">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 1l22 22"></path>
            <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"></path>
            <path d="M25 12.55a21 21 0 0 0-3.17-2.06"></path>
          </svg>
        </div>
        <button v-if="offlineStore.pendingCount > 0" class="offline-badge" @click="goToOffline">
          <span class="badge-count">{{ offlineStore.pendingCount }}</span>
          <span class="badge-text">待同步</span>
        </button>
      </div>
    </header>

    <main class="content-area">
      <router-view v-slot="{ Component }">
        <transition name="page-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <nav class="bottom-nav">
      <button
        v-for="tab in tabs"
        :key="tab.name"
        class="nav-item"
        :class="{ active: currentRoute === tab.path }"
        @click="navigateTo(tab.path)"
      >
        <div class="nav-icon">
          <svg v-if="tab.icon === 'list'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="8" y1="6" x2="21" y2="6"></line>
            <line x1="8" y1="12" x2="21" y2="12"></line>
            <line x1="8" y1="18" x2="21" y2="18"></line>
            <line x1="3" y1="6" x2="3.01" y2="6"></line>
            <line x1="3" y1="12" x2="3.01" y2="12"></line>
            <line x1="3" y1="18" x2="3.01" y2="18"></line>
          </svg>
          <svg v-else-if="tab.icon === 'alert'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          <svg v-else-if="tab.icon === 'scan'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 7V5a2 2 0 0 1 2-2h2"></path>
            <path d="M17 3h2a2 2 0 0 1 2 2v2"></path>
            <path d="M21 17v2a2 2 0 0 1-2 2h-2"></path>
            <path d="M7 21H5a2 2 0 0 1-2-2v-2"></path>
            <line x1="7" y1="12" x2="17" y2="12"></line>
          </svg>
          <svg v-else-if="tab.icon === 'user'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <span v-if="tab.icon === 'alert' && alertCount > 0" class="nav-badge">{{ alertCount > 99 ? '99+' : alertCount }}</span>
        </div>
        <span class="nav-label">{{ tab.label }}</span>
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOfflineStore } from '@/stores/offline'
import { fetchAlertStats } from '@/api'

const route = useRoute()
const router = useRouter()
const offlineStore = useOfflineStore()

const tabs = [
  { path: '/workorders', name: 'WorkOrders', label: '工单', icon: 'list' },
  { path: '/alerts', name: 'Alerts', label: '预警', icon: 'alert' },
  { path: '/scan', name: 'Scan', label: '扫码', icon: 'scan' },
  { path: '/profile', name: 'Profile', label: '我的', icon: 'user' }
]

const currentRoute = computed(() => route.path)
const showBack = computed(() => !tabs.some(t => t.path === route.path))
const pageTitle = computed(() => {
  const tab = tabs.find(t => t.path === route.path)
  if (tab) return tab.label
  return (route.meta.title as string) || '现场巡检'
})

const alertCount = ref(0)

function goBack() {
  router.back()
}

function navigateTo(path: string) {
  if (currentRoute.value !== path) {
    router.push(path)
  }
}

function goToOffline() {
  router.push('/offline')
}

async function loadAlertStats() {
  try {
    const stats = await fetchAlertStats()
    alertCount.value = stats.pending + stats.processing
  } catch (e) {
    console.error('加载预警统计失败:', e)
  }
}

watch(() => route.path, () => {
  if (route.path === '/alerts') {
    loadAlertStats()
  }
})

onMounted(() => {
  loadAlertStats()
  setInterval(loadAlertStats, 30000)
})
</script>

<style scoped>
.main-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background:
    radial-gradient(ellipse at 20% 0%, rgba(59, 130, 246, 0.06) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(139, 92, 246, 0.06) 0%, transparent 50%),
    linear-gradient(180deg, #020617 0%, #0f172a 100%);
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  padding-top: calc(12px + var(--safe-area-top));
  background: rgba(15, 23, 42, 0.9);
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(10px);
  flex-shrink: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.back-btn:active {
  background: rgba(59, 130, 246, 0.1);
  color: var(--primary-light);
}

.page-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.offline-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: var(--warning-color);
  background: rgba(245, 158, 11, 0.1);
}

.offline-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(249, 115, 22, 0.15);
  border: 1px solid rgba(249, 115, 22, 0.3);
  border-radius: 20px;
  color: #fb923c;
  font-size: 11px;
  font-weight: 500;
}

.badge-count {
  font-weight: 600;
}

.content-area {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.bottom-nav {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 8px 0;
  padding-bottom: calc(8px + var(--safe-area-bottom));
  background: rgba(15, 23, 42, 0.95);
  border-top: 1px solid var(--border-color);
  backdrop-filter: blur(10px);
  flex-shrink: 0;
  z-index: 10;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 6px 16px;
  color: var(--text-tertiary);
  transition: all 0.2s;
  position: relative;
}

.nav-item.active {
  color: var(--primary-light);
}

.nav-icon {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-badge {
  position: absolute;
  top: -4px;
  right: -8px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: var(--danger-color);
  color: white;
  font-size: 10px;
  font-weight: 600;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
}

.nav-label {
  font-size: 11px;
  font-weight: 500;
}

.page-slide-enter-active,
.page-slide-leave-active {
  transition: transform 0.25s ease-out, opacity 0.25s ease-out;
}

.page-slide-enter-from {
  transform: translateX(16px);
  opacity: 0;
}

.page-slide-leave-to {
  transform: translateX(-16px);
  opacity: 0;
}
</style>
