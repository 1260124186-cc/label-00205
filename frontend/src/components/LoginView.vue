<template>
  <div class="login-page">
    <div class="login-background">
      <div class="bg-grid"></div>
      <div class="bg-glow bg-glow-1"></div>
      <div class="bg-glow bg-glow-2"></div>
    </div>

    <div class="login-container">
      <div class="login-brand">
        <div class="brand-logo">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
            <path d="M2 17l10 5 10-5"></path>
            <path d="M2 12l10 5 10-5"></path>
          </svg>
        </div>
        <h1 class="brand-title">螺栓预紧力监控与运维控制台</h1>
        <p class="brand-subtitle">Bolt Preload Monitoring & Operations Center</p>
      </div>

      <div class="login-card">
        <div class="login-tabs">
          <button
            class="login-tab"
            :class="{ active: loginMode === 'password' }"
            @click="loginMode = 'password'; clearError()"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
            账号登录
          </button>
          <button
            class="login-tab"
            :class="{ active: loginMode === 'apikey' }"
            @click="loginMode = 'apikey'; clearError()"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path>
            </svg>
            API Key
          </button>
        </div>

        <form v-if="loginMode === 'password'" class="login-form" @submit.prevent="handlePasswordLogin">
          <div class="form-group">
            <label class="form-label">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
              </svg>
              租户编码
            </label>
            <input
              v-model="passwordForm.tenant_code"
              type="text"
              class="form-input"
              placeholder="请输入租户编码（默认：default）"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label class="form-label">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              用户名
            </label>
            <input
              v-model="passwordForm.username"
              type="text"
              class="form-input"
              placeholder="请输入用户名"
              :disabled="isLoading"
              autocomplete="username"
            />
          </div>

          <div class="form-group">
            <label class="form-label">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
              密码
            </label>
            <input
              v-model="passwordForm.password"
              :type="showPassword ? 'text' : 'password'"
              class="form-input"
              placeholder="请输入密码"
              :disabled="isLoading"
              autocomplete="current-password"
            />
            <button type="button" class="password-toggle" @click="showPassword = !showPassword">
              <svg v-if="!showPassword" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
              </svg>
            </button>
          </div>

          <div v-if="authError" class="error-message">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            {{ authError }}
          </div>

          <button type="submit" class="submit-btn" :disabled="isLoading || !canSubmitPassword">
            <span v-if="isLoading" class="loading-spinner-sm"></span>
            {{ isLoading ? '登录中...' : '登录' }}
          </button>
        </form>

        <form v-else class="login-form" @submit.prevent="handleAPIKeyLogin">
          <div class="form-group">
            <label class="form-label">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path>
              </svg>
              API Key
            </label>
            <input
              v-model="apiKeyForm.api_key"
              type="text"
              class="form-input"
              placeholder="请输入 API Key（格式：tp_xxxxxx）"
              :disabled="isLoading"
            />
          </div>

          <div class="api-key-hint">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            API Key 具有只读权限，可用于查看监控数据和预警信息
          </div>

          <div v-if="authError" class="error-message">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            {{ authError }}
          </div>

          <button type="submit" class="submit-btn" :disabled="isLoading || !canSubmitAPIKey">
            <span v-if="isLoading" class="loading-spinner-sm"></span>
            {{ isLoading ? '验证中...' : '验证并登录' }}
          </button>
        </form>

        <div class="demo-accounts">
          <div class="demo-title">演示账号（测试环境）</div>
          <div class="demo-list">
            <div class="demo-item" @click="fillDemo('admin')">
              <span class="demo-role" style="color: #8b5cf6">管理员</span>
              <span class="demo-creds">admin / admin123</span>
            </div>
            <div class="demo-item" @click="fillDemo('operator')">
              <span class="demo-role" style="color: #3b82f6">运维</span>
              <span class="demo-creds">operator / oper123</span>
            </div>
            <div class="demo-item" @click="fillDemo('viewer')">
              <span class="demo-role" style="color: #64748b">只读</span>
              <span class="demo-creds">viewer / view123</span>
            </div>
          </div>
        </div>
      </div>

      <div class="login-footer">
        <p>© 2025 螺栓预紧力监控系统 · RBAC 权限管理</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAuth } from '@/composables/useAuth'

const emit = defineEmits<{
  (e: 'login-success'): void
}>()

const { login, loginWithAPIKey, isLoading, authError, clearError } = useAuth()

const loginMode = ref<'password' | 'apikey'>('password')
const showPassword = ref(false)

const passwordForm = ref({
  tenant_code: 'default',
  username: '',
  password: ''
})

const apiKeyForm = ref({
  api_key: ''
})

const canSubmitPassword = computed(() => {
  return passwordForm.value.tenant_code.trim() !== '' &&
    passwordForm.value.username.trim() !== '' &&
    passwordForm.value.password.trim() !== ''
})

const canSubmitAPIKey = computed(() => {
  return apiKeyForm.value.api_key.trim() !== ''
})

async function handlePasswordLogin() {
  const success = await login({
    tenant_code: passwordForm.value.tenant_code,
    username: passwordForm.value.username,
    password: passwordForm.value.password
  })
  if (success) {
    emit('login-success')
  }
}

async function handleAPIKeyLogin() {
  const success = await loginWithAPIKey(apiKeyForm.value.api_key.trim())
  if (success) {
    emit('login-success')
  }
}

function fillDemo(role: 'admin' | 'operator' | 'viewer') {
  loginMode.value = 'password'
  clearError()
  passwordForm.value.tenant_code = 'default'
  passwordForm.value.username = role
  passwordForm.value.password = role === 'admin' ? 'admin123' : role === 'operator' ? 'oper123' : 'view123'
}

watch(loginMode, () => {
  clearError()
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: #020617;
}

.login-background {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(59, 130, 246, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.06) 1px, transparent 1px);
  background-size: 50px 50px;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.4;
}

.bg-glow-1 {
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  top: -150px;
  left: -100px;
}

.bg-glow-2 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #06b6d4, #3b82f6);
  bottom: -200px;
  right: -150px;
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 460px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.login-brand {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.brand-logo {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 32px rgba(59, 130, 246, 0.4);
}

.brand-title {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #e2e8f0 0%, #60a5fa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.5px;
  margin: 0;
}

.brand-subtitle {
  font-size: 11px;
  color: #64748b;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  margin: 0;
}

.login-card {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 16px;
  padding: 28px;
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.login-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 4px;
  background: rgba(30, 41, 59, 0.6);
  border-radius: 10px;
  margin-bottom: 24px;
}

.login-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 14px;
  background: transparent;
  border: none;
  border-radius: 7px;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.login-tab:hover {
  color: #cbd5e1;
}

.login-tab.active {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-group {
  position: relative;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: 11px 14px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 14px;
  outline: none;
  transition: all 0.2s;
  padding-right: 44px;
}

.form-input::placeholder {
  color: #475569;
}

.form-input:hover:not(:disabled) {
  border-color: rgba(59, 130, 246, 0.5);
}

.form-input:focus {
  border-color: rgba(59, 130, 246, 0.8);
  background: rgba(30, 41, 59, 1);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.form-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.password-toggle {
  position: absolute;
  right: 12px;
  top: 38px;
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.password-toggle:hover {
  color: #94a3b8;
}

.api-key-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 10px 12px;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  font-size: 12px;
  color: #60a5fa;
  line-height: 1.5;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 8px;
  font-size: 13px;
  color: #f87171;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 4px;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.5);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.demo-accounts {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.15);
}

.demo-title {
  font-size: 11px;
  color: #64748b;
  text-align: center;
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}

.demo-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.demo-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(71, 85, 105, 0.3);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.demo-item:hover {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
}

.demo-role {
  font-size: 12px;
  font-weight: 600;
}

.demo-creds {
  font-size: 12px;
  color: #94a3b8;
  font-family: monospace;
}

.login-footer {
  text-align: center;
  color: #475569;
  font-size: 12px;
}

.login-footer p {
  margin: 0;
}
</style>
