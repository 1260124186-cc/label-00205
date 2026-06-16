import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WorkOrder, AlertEvent, OfflineQueueItem, RetestRecord } from '@/types'

const OFFLINE_QUEUE_KEY = 'offline_queue'
const CACHED_WORKORDERS_KEY = 'cached_workorders'
const CACHED_ALERTS_KEY = 'cached_alerts'
const CACHED_RETESTS_KEY = 'cached_retests'

export const useOfflineStore = defineStore('offline', () => {
  const queue = ref<OfflineQueueItem[]>([])
  const isOnline = ref(navigator.onLine)
  const syncing = ref(false)

  const pendingCount = computed(() =>
    queue.value.filter(item => item.status === 'pending').length
  )

  const failedCount = computed(() =>
    queue.value.filter(item => item.status === 'failed').length
  )

  function init() {
    loadQueue()
    setupNetworkListener()
  }

  function loadQueue() {
    try {
      const stored = localStorage.getItem(OFFLINE_QUEUE_KEY)
      if (stored) {
        queue.value = JSON.parse(stored)
      }
    } catch (e) {
      console.error('加载离线队列失败:', e)
    }
  }

  function saveQueue() {
    try {
      localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue.value))
    } catch (e) {
      console.error('保存离线队列失败:', e)
    }
  }

  function setupNetworkListener() {
    window.addEventListener('online', () => {
      isOnline.value = true
      syncQueue()
    })
    window.addEventListener('offline', () => {
      isOnline.value = false
    })
  }

  function addToQueue(type: OfflineQueueItem['type'], data: any): string {
    const item: OfflineQueueItem = {
      id: `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      data,
      status: 'pending',
      retryCount: 0,
      createdAt: Date.now()
    }
    queue.value.unshift(item)
    saveQueue()

    if (isOnline.value) {
      syncQueue()
    }

    return item.id
  }

  function updateQueueItem(id: string, updates: Partial<OfflineQueueItem>) {
    const index = queue.value.findIndex(item => item.id === id)
    if (index !== -1) {
      queue.value[index] = { ...queue.value[index], ...updates }
      saveQueue()
    }
  }

  function removeFromQueue(id: string) {
    queue.value = queue.value.filter(item => item.id !== id)
    saveQueue()
  }

  async function syncQueue() {
    if (syncing.value || !isOnline.value) return

    syncing.value = true
    const pendingItems = queue.value.filter(item => item.status === 'pending' || item.status === 'failed')

    for (const item of pendingItems) {
      try {
        updateQueueItem(item.id, { status: 'uploading' })
        await processQueueItem(item)
        removeFromQueue(item.id)
      } catch (e: any) {
        const retryCount = item.retryCount + 1
        updateQueueItem(item.id, {
          status: retryCount >= 3 ? 'failed' : 'pending',
          retryCount,
          error: e.message
        })
      }
    }

    syncing.value = false
  }

  async function processQueueItem(item: OfflineQueueItem) {
    const { createRetestRecord, uploadFile } = await import('@/api')

    switch (item.type) {
      case 'retest':
        await createRetestRecord(item.data)
        break
      case 'photo':
        if (item.data.file) {
          await uploadFile(item.data.file, 'photo')
        }
        break
      case 'voice':
        if (item.data.file) {
          await uploadFile(item.data.file, 'voice')
        }
        break
      default:
        throw new Error(`未知的队列类型: ${item.type}`)
    }
  }

  function cacheWorkOrders(workOrders: WorkOrder[]) {
    try {
      localStorage.setItem(CACHED_WORKORDERS_KEY, JSON.stringify({
        data: workOrders,
        timestamp: Date.now()
      }))
    } catch (e) {
      console.error('缓存工单失败:', e)
    }
  }

  function getCachedWorkOrders(): WorkOrder[] | null {
    try {
      const stored = localStorage.getItem(CACHED_WORKORDERS_KEY)
      if (stored) {
        const { data } = JSON.parse(stored)
        return data
      }
    } catch (e) {
      console.error('读取缓存工单失败:', e)
    }
    return null
  }

  function cacheAlerts(alerts: AlertEvent[]) {
    try {
      localStorage.setItem(CACHED_ALERTS_KEY, JSON.stringify({
        data: alerts,
        timestamp: Date.now()
      }))
    } catch (e) {
      console.error('缓存预警失败:', e)
    }
  }

  function getCachedAlerts(): AlertEvent[] | null {
    try {
      const stored = localStorage.getItem(CACHED_ALERTS_KEY)
      if (stored) {
        const { data } = JSON.parse(stored)
        return data
      }
    } catch (e) {
      console.error('读取缓存预警失败:', e)
    }
    return null
  }

  function cacheRetestRecords(workOrderId: number, records: RetestRecord[]) {
    try {
      const key = `${CACHED_RETESTS_KEY}_${workOrderId}`
      localStorage.setItem(key, JSON.stringify({
        data: records,
        timestamp: Date.now()
      }))
    } catch (e) {
      console.error('缓存复测记录失败:', e)
    }
  }

  function getCachedRetestRecords(workOrderId: number): RetestRecord[] | null {
    try {
      const key = `${CACHED_RETESTS_KEY}_${workOrderId}`
      const stored = localStorage.getItem(key)
      if (stored) {
        const { data } = JSON.parse(stored)
        return data
      }
    } catch (e) {
      console.error('读取缓存复测记录失败:', e)
    }
    return null
  }

  function clearCache() {
    localStorage.removeItem(CACHED_WORKORDERS_KEY)
    localStorage.removeItem(CACHED_ALERTS_KEY)
    const keys = Object.keys(localStorage)
    keys.forEach(key => {
      if (key.startsWith(CACHED_RETESTS_KEY)) {
        localStorage.removeItem(key)
      }
    })
  }

  return {
    queue,
    isOnline,
    syncing,
    pendingCount,
    failedCount,
    init,
    addToQueue,
    updateQueueItem,
    removeFromQueue,
    syncQueue,
    cacheWorkOrders,
    getCachedWorkOrders,
    cacheAlerts,
    getCachedAlerts,
    cacheRetestRecords,
    getCachedRetestRecords,
    clearCache
  }
})
