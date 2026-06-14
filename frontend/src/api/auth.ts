import axios from 'axios'
import type {
  LoginRequest,
  LoginResponse,
  CurrentUser,
  UserRole,
  Permission
} from '@/types'
import { RolePermissionMap } from '@/types'

const USE_MOCK = true

const TOKEN_STORAGE_KEY = 'bolt_preload_token'
const API_KEY_STORAGE_KEY = 'bolt_preload_api_key'
const USER_STORAGE_KEY = 'bolt_preload_user'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  const apiKey = localStorage.getItem(API_KEY_STORAGE_KEY)
  if (token) {
    config.headers['X-Tenant-Token'] = token
  }
  if (apiKey) {
    config.headers['X-Tenant-API-Key'] = apiKey
  }
  return config
})

function generateMockCurrentUser(role: UserRole = 'admin'): CurrentUser {
  return {
    tenant_id: 1,
    tenant_code: 'default',
    tenant_name: '默认租户',
    user_id: role === 'admin' ? 1 : role === 'operator' ? 2 : 3,
    username: role === 'admin' ? 'admin' : role === 'operator' ? 'operator01' : 'viewer01',
    display_name: role === 'admin' ? '系统管理员' : role === 'operator' ? '运维工程师' : '只读用户',
    role,
    permissions: RolePermissionMap[role],
    auth_method: 'token',
    email: role === 'admin' ? 'admin@example.com' : null,
    phone: null,
    org_node_id: null,
    status: 'active',
    last_login_time: new Date().toISOString()
  }
}

const mockUsers: Record<string, { password: string; role: UserRole }> = {
  admin: { password: 'admin123', role: 'admin' },
  operator: { password: 'oper123', role: 'operator' },
  viewer: { password: 'view123', role: 'viewer' }
}

export async function login(request: LoginRequest): Promise<LoginResponse | null> {
  if (USE_MOCK) {
    const user = mockUsers[request.username]
    if (user && user.password === request.password) {
      const token = 'mock_token_' + Math.random().toString(36).substring(2)
      return Promise.resolve({
        token,
        tenant_id: 1,
        user_id: request.username === 'admin' ? 1 : request.username === 'operator' ? 2 : 3,
        username: request.username,
        role: user.role,
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      })
    }
    return Promise.resolve(null)
  }

  try {
    const res = await api.post<LoginResponse>('/tenant/login', request)
    return res.data
  } catch (err) {
    console.error('登录失败:', err)
    return null
  }
}

export async function loginWithAPIKey(apiKey: string): Promise<boolean> {
  if (USE_MOCK) {
    if (apiKey.startsWith('tp_')) {
      localStorage.setItem(API_KEY_STORAGE_KEY, apiKey)
      const mockUser = generateMockCurrentUser('api_key')
      mockUser.permissions = ['read']
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(mockUser))
      return Promise.resolve(true)
    }
    return Promise.resolve(false)
  }

  try {
    localStorage.setItem(API_KEY_STORAGE_KEY, apiKey)
    const user = await fetchCurrentUser()
    if (user) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
      return true
    }
    localStorage.removeItem(API_KEY_STORAGE_KEY)
    return false
  } catch (err) {
    console.error('API Key 登录失败:', err)
    localStorage.removeItem(API_KEY_STORAGE_KEY)
    return false
  }
}

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  if (USE_MOCK) {
    const stored = localStorage.getItem(USER_STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
    const token = localStorage.getItem(TOKEN_STORAGE_KEY)
    const apiKey = localStorage.getItem(API_KEY_STORAGE_KEY)
    if (!token && !apiKey) return null

    for (const [username, info] of Object.entries(mockUsers)) {
      if (token && token.includes(username)) {
        return generateMockCurrentUser(info.role)
      }
    }
    if (apiKey && apiKey.startsWith('tp_')) {
      return generateMockCurrentUser('api_key')
    }
    return null
  }

  try {
    const res = await api.get<CurrentUser>('/tenant/me')
    return res.data
  } catch (err) {
    console.error('获取当前用户信息失败:', err)
    return null
  }
}

export async function logout(): Promise<boolean> {
  if (!USE_MOCK) {
    try {
      await api.post('/tenant/logout')
    } catch (err) {
      console.error('登出请求失败:', err)
    }
  }
  localStorage.removeItem(TOKEN_STORAGE_KEY)
  localStorage.removeItem(API_KEY_STORAGE_KEY)
  localStorage.removeItem(USER_STORAGE_KEY)
  return true
}

export function storeAuthData(token: string, user: CurrentUser) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function getStoredAPIKey(): string | null {
  return localStorage.getItem(API_KEY_STORAGE_KEY)
}

export function getStoredUser(): CurrentUser | null {
  const stored = localStorage.getItem(USER_STORAGE_KEY)
  if (stored) {
    try {
      return JSON.parse(stored)
    } catch {
      return null
    }
  }
  return null
}

export function hasPermission(userPermissions: Permission[], required: Permission | Permission[]): boolean {
  const requiredList = Array.isArray(required) ? required : [required]
  if (userPermissions.includes('admin') || userPermissions.includes('tenant_admin')) {
    return true
  }
  if (userPermissions.includes('write')) {
    const hasWriteOnly = requiredList.every(p => !p.toString().startsWith('config') && !p.toString().startsWith('tenant'))
    if (hasWriteOnly) return true
  }
  if (userPermissions.includes('read')) {
    const allRead = requiredList.every(p => p.toString().endsWith(':read') || p === 'read')
    if (allRead) return true
  }
  return requiredList.every(p => userPermissions.includes(p))
}

export { api as authApi }
