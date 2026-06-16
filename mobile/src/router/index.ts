import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/workorders'
      },
      {
        path: 'workorders',
        name: 'WorkOrders',
        component: () => import('@/views/WorkOrderList.vue'),
        meta: { title: '待办工单', icon: 'list' }
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/AlertList.vue'),
        meta: { title: '预警推送', icon: 'alert' }
      },
      {
        path: 'scan',
        name: 'Scan',
        component: () => import('@/views/Scan.vue'),
        meta: { title: '扫码识别', icon: 'scan' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
        meta: { title: '我的', icon: 'user' }
      }
    ]
  },
  {
    path: '/workorders/:id',
    name: 'WorkOrderDetail',
    component: () => import('@/views/WorkOrderDetail.vue'),
    meta: { requiresAuth: true, title: '工单详情' }
  },
  {
    path: '/workorders/:id/retest',
    name: 'RetestForm',
    component: () => import('@/views/RetestForm.vue'),
    meta: { requiresAuth: true, title: '复测录入' }
  },
  {
    path: '/node/:orgNodeId',
    name: 'NodeDetail',
    component: () => import('@/views/NodeDetail.vue'),
    meta: { requiresAuth: true, title: '节点详情' }
  },
  {
    path: '/offline',
    name: 'OfflineQueue',
    component: () => import('@/views/OfflineQueue.vue'),
    meta: { requiresAuth: true, title: '离线队列' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token')
  const apiKey = localStorage.getItem('api_key')
  const isLoggedIn = !!token || !!apiKey

  if (to.meta.requiresAuth && !isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
