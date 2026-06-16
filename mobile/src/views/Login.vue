<template>
  <div class="login-page">
    <div class="login-container">
      <div class="logo-section">
        <div class="logo-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
            <path d="M2 17l10 5 10-5"></path>
            <path d="M2 12l10 5 10-5"></path>
          </svg>
        </div>
        <h1 class="app-title">螺栓预紧力巡检</h1>
        <p class="app-subtitle">Bolt Preload Inspection</p>
      </div>

      <div class="login-form">
        <div class="form-group">
          <label class="form-label">API Key</label>
          <input
            v-model="apiKey"
            type="text"
            class="form-input"
            placeholder="请输入 API Key"
            @keyup.enter="handleLogin"
          />
        </div>

        <button
          class="login-btn"
          :disabled="loading || !apiKey.trim()"
          @click="handleLogin"
        >
          <span v-if="!loading">登 录</span>
          <span v-else class="loading-text">
            <span class="spinner"></span>
            登录中...
          </span>
        </button>

        <div v-if="error" class="error-message">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          {{ error }}
        </div>

        <div class="login-tip">
          <p>现场巡检人员使用 API Key 登录</p>
        </div>
      </div>
    </div>

    <div class="version-info">
      v1.0.0 · 现场巡检版
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { loginWithApiKey } from '@/api'

const router = useRouter()
const userStore = useUserStore()

const apiKey = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  if (!apiKey.value.trim()) {
    error.value = '请输入 API Key'
    return
  }

  loading.value = true
  error.value = ''

  try {
    userStore.setApiKey(apiKey.value.trim())
    try {
      const user = await loginWithApiKey(apiKey.value.trim())
      userStore.setUserInfo(user)
    } catch (e) {
      console.warn('获取用户信息失败，使用默认信息:', e)
    }
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '登录失败，请检查 API Key'
    userStore.setApiKey('')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(ellipse at 30% 20%, rgba(59, 130, 246, 0.15) 0%, transparent 50%),
    radial-gradient(ellipse at 70% 80%, rgba(139, 92, 246, 0.1) 0%, transparent 50%),
    linear-gradient(180deg, #020617 0%, #0f172a 100%);
}

.login-container {
  width: 100%;
  max-width: 360px;
}

.logo-section {
  text-align: center;
  margin-bottom: 40px;
}

.logo-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 20px;
  border-radius: 20px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 32px rgba(59, 130, 246, 0.4);
}

.app-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 6px;
  background: linear-gradient(135deg, #e2e8f0 0%, #60a5fa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.app-subtitle {
  font-size: 12px;
  color: var(--text-tertiary);
  letter-spacing: 2px;
  text-transform: uppercase;
}

.login-form {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(12px);
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  height: 48px;
  padding: 0 16px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 15px;
  outline: none;
  transition: all 0.2s;
}

.form-input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.form-input::placeholder {
  color: var(--text-tertiary);
}

.login-btn {
  width: 100%;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-btn:active:not(:disabled) {
  transform: scale(0.98);
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.4);
}

.login-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-text {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 8px;
  color: #f87171;
  font-size: 13px;
}

.login-tip {
  margin-top: 20px;
  text-align: center;
}

.login-tip p {
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.6;
}

.version-info {
  position: absolute;
  bottom: 24px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>
