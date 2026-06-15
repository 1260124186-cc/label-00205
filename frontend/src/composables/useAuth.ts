import { ref, computed, onMounted } from 'vue'
import type {
  CurrentUser,
  UserRole,
  Permission,
  LoginRequest
} from '@/types'
import { RoleViewPermissions, RolePermissionMap } from '@/types'
import {
  login as apiLogin,
  loginWithAPIKey as apiLoginWithAPIKey,
  fetchCurrentUser,
  logout as apiLogout,
  storeAuthData,
  getStoredToken,
  getStoredAPIKey,
  getStoredUser,
  hasPermission as checkPermission
} from '@/api/auth'

const currentUser = ref<CurrentUser | null>(null)
const isAuthenticated = ref(false)
const isLoading = ref(false)
const authError = ref<string | null>(null)

export function useAuth() {
  const userRole = computed<UserRole>(() => currentUser.value?.role || 'anonymous')
  const permissions = computed<Permission[]>(() => currentUser.value?.permissions || [])
  const displayName = computed<string>(() => currentUser.value?.display_name || '未登录')
  const authMethod = computed(() => currentUser.value?.auth_method || 'none')

  const availableViews = computed<Array<'monitoring' | 'alert' | 'trend' | 'model' | 'config' | 'federated' | 'carbon'>>(() => {
    const role = userRole.value
    return RoleViewPermissions[role] || []
  })

  const canViewMonitoring = computed(() => availableViews.value.includes('monitoring'))
  const canViewAlert = computed(() => availableViews.value.includes('alert'))
  const canViewTrend = computed(() => availableViews.value.includes('trend'))
  const canViewModel = computed(() => availableViews.value.includes('model'))
  const canViewConfig = computed(() => availableViews.value.includes('config'))
  const canViewFederated = computed(() => availableViews.value.includes('federated'))
  const canViewCarbon = computed(() => availableViews.value.includes('carbon'))

  const canWrite = computed(() => {
    const perms = permissions.value
    return perms.includes('write') || perms.includes('admin') || perms.includes('tenant_admin')
  })

  const isAdmin = computed(() => {
    const role = userRole.value
    return role === 'admin' || role === 'tenant_admin'
  })

  const isOperator = computed(() => {
    const role = userRole.value
    return role === 'operator' || role === 'admin' || role === 'tenant_admin'
  })

  const isViewer = computed(() => userRole.value === 'viewer')

  function hasPermission(required: Permission | Permission[]): boolean {
    return checkPermission(permissions.value, required)
  }

  function hasRole(roles: UserRole | UserRole[]): boolean {
    const roleList = Array.isArray(roles) ? roles : [roles]
    return roleList.includes(userRole.value)
  }

  async function initAuth() {
    isLoading.value = true
    authError.value = null
    try {
      const token = getStoredToken()
      const apiKey = getStoredAPIKey()
      const storedUser = getStoredUser()

      if (!token && !apiKey) {
        isAuthenticated.value = false
        currentUser.value = null
        return false
      }

      if (storedUser) {
        currentUser.value = storedUser
        isAuthenticated.value = true
        return true
      }

      const user = await fetchCurrentUser()
      if (user) {
        currentUser.value = user
        isAuthenticated.value = true
        return true
      } else {
        isAuthenticated.value = false
        currentUser.value = null
        return false
      }
    } catch (e) {
      console.error('初始化认证失败:', e)
      isAuthenticated.value = false
      currentUser.value = null
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function login(request: LoginRequest): Promise<boolean> {
    isLoading.value = true
    authError.value = null
    try {
      const result = await apiLogin(request)
      if (result) {
        const user: CurrentUser = {
          tenant_id: result.tenant_id,
          tenant_code: request.tenant_code,
          tenant_name: null,
          user_id: result.user_id,
          username: result.username,
          display_name: result.username,
          role: result.role,
          permissions: RolePermissionMap[result.role] || [],
          auth_method: 'token',
          email: null,
          phone: null,
          org_node_id: null,
          status: 'active',
          last_login_time: new Date().toISOString()
        }
        storeAuthData(result.token, user)
        currentUser.value = user
        isAuthenticated.value = true

        const freshUser = await fetchCurrentUser()
        if (freshUser) {
          currentUser.value = freshUser
          storeAuthData(result.token, freshUser)
        }
        return true
      } else {
        authError.value = '租户编码、用户名或密码错误'
        return false
      }
    } catch (e) {
      console.error('登录失败:', e)
      authError.value = '登录失败，请稍后重试'
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function loginWithAPIKey(apiKey: string): Promise<boolean> {
    isLoading.value = true
    authError.value = null
    try {
      const success = await apiLoginWithAPIKey(apiKey)
      if (success) {
        const user = getStoredUser()
        if (user) {
          currentUser.value = user
          isAuthenticated.value = true
        }
        return success
      } else {
        authError.value = '无效的 API Key'
        return false
      }
    } catch (e) {
      console.error('API Key 登录失败:', e)
      authError.value = 'API Key 验证失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    isLoading.value = true
    try {
      await apiLogout()
    } finally {
      currentUser.value = null
      isAuthenticated.value = false
      isLoading.value = false
    }
  }

  function clearError() {
    authError.value = null
  }

  return {
    currentUser,
    isAuthenticated,
    isLoading,
    authError,
    userRole,
    permissions,
    displayName,
    authMethod,
    availableViews,
    canViewMonitoring,
    canViewAlert,
    canViewTrend,
    canViewModel,
    canViewConfig,
    canViewFederated,
    canViewCarbon,
    canWrite,
    isAdmin,
    isOperator,
    isViewer,
    hasPermission,
    hasRole,
    initAuth,
    login,
    loginWithAPIKey,
    logout,
    clearError
  }
}
