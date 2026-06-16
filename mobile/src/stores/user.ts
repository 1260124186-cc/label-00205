import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo, OfflineQueueItem } from '@/types'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<UserInfo | null>(null)
  const token = ref<string>('')
  const apiKey = ref<string>('')

  const isLoggedIn = computed(() => !!token.value || !!apiKey.value)

  function setUserInfo(user: UserInfo) {
    userInfo.value = user
    localStorage.setItem('user_info', JSON.stringify(user))
  }

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('auth_token', newToken)
  }

  function setApiKey(key: string) {
    apiKey.value = key
    localStorage.setItem('api_key', key)
  }

  function logout() {
    userInfo.value = null
    token.value = ''
    apiKey.value = ''
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_info')
    localStorage.removeItem('api_key')
  }

  function initFromStorage() {
    const storedUser = localStorage.getItem('user_info')
    const storedToken = localStorage.getItem('auth_token')
    const storedApiKey = localStorage.getItem('api_key')

    if (storedUser) {
      try {
        userInfo.value = JSON.parse(storedUser)
      } catch (e) {
        console.error('解析用户信息失败:', e)
      }
    }
    if (storedToken) {
      token.value = storedToken
    }
    if (storedApiKey) {
      apiKey.value = storedApiKey
    }
  }

  return {
    userInfo,
    token,
    apiKey,
    isLoggedIn,
    setUserInfo,
    setToken,
    setApiKey,
    logout,
    initFromStorage
  }
})
