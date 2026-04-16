import { createRouter, createWebHashHistory } from 'vue-router'

import AppLayout from '../views/AppLayout.vue'
import AccountView from '../views/AccountView.vue'
import CameraView from '../views/CameraView.vue'
import HistoryView from '../views/HistoryView.vue'
import ImageView from '../views/ImageView.vue'
import LoginView from '../views/LoginView.vue'
import OverviewView from '../views/OverviewView.vue'
import PerformanceView from '../views/PerformanceView.vue'
import RegisterView from '../views/RegisterView.vue'
import VideoView from '../views/VideoView.vue'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: {
      publicOnly: true,
    },
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
    meta: {
      publicOnly: true,
    },
  },
  {
    path: '/app',
    component: AppLayout,
    meta: {
      requiresAuth: true,
    },
    children: [
      {
        path: '',
        redirect: '/app/overview',
      },
      {
        path: 'overview',
        name: 'overview',
        component: OverviewView,
      },
      {
        path: 'image',
        name: 'image',
        component: ImageView,
      },
      {
        path: 'video',
        name: 'video',
        component: VideoView,
      },
      {
        path: 'camera',
        name: 'camera',
        component: CameraView,
      },
      {
        path: 'history',
        name: 'history',
        component: HistoryView,
      },
      {
        path: 'performance',
        name: 'performance',
        component: PerformanceView,
      },
      {
        path: 'account',
        name: 'account',
        component: AccountView,
      },
    ],
  },
  {
    path: '/dashboard',
    redirect: '/app/overview',
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login',
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const publicOnly = to.matched.some((record) => record.meta.publicOnly)

  if (requiresAuth && !auth.isAuthenticated.value) {
    return { name: 'login' }
  }

  if (publicOnly && auth.isAuthenticated.value) {
    return { name: 'overview' }
  }

  return true
})

export default router
