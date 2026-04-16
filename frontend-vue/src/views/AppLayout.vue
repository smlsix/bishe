<script setup>
import { computed, onMounted, provide, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { useApiError } from '../composables/useApiError'
import { api } from '../services/api'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const appStore = useAppStore()
const { resolveError } = useApiError()

const healthStatus = ref('checking')
const loading = ref(false)

const user = computed(() => auth.user.value)
const service = computed(() => appStore.service.value || {})
const models = computed(() => appStore.models.value)
const selectedModel = appStore.selectedModel
const confidence = appStore.confidence
const imageSize = appStore.imageSize

const navItems = [
  { name: 'overview', label: '总览' },
  { name: 'image', label: '图片检测' },
  { name: 'video', label: '视频检测' },
  { name: 'camera', label: '摄像头检测' },
  { name: 'history', label: '历史记录' },
  { name: 'performance', label: '模型性能对比' },
  { name: 'account', label: '账户设置' },
]

async function loadGlobalInfo() {
  const info = await api.info(auth.token.value)
  appStore.applyService(info.service)
  auth.setUser(info.user)
}

async function loadHealth() {
  try {
    const payload = await api.health()
    healthStatus.value = payload.status === 'ok' ? 'online' : 'offline'
  } catch {
    healthStatus.value = 'offline'
  }
}

async function refreshGlobal() {
  loading.value = true
  try {
    await Promise.all([loadGlobalInfo(), loadHealth()])
  } catch (error) {
    alert(resolveError(error))
  } finally {
    loading.value = false
  }
}

async function logout() {
  try {
    await api.logout(auth.token.value)
  } catch {
    // ignore
  } finally {
    auth.clearSession()
    router.push({ name: 'login' })
  }
}

provide('refreshGlobal', refreshGlobal)
provide('serviceInfo', service)

onMounted(async () => {
  if (!auth.token.value) {
    router.push({ name: 'login' })
    return
  }
  await refreshGlobal()
})
</script>

<template>
  <div class="app-shell">
    <aside class="side-nav">
      <div>
        <p class="side-kicker">STEEL AI</p>
        <h1 class="side-title">检测平台</h1>
      </div>

      <nav class="nav-links">
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="{ name: item.name }"
          class="nav-link"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="side-footer">
        <p>用户：{{ user?.username || '-' }}</p>
        <p>设备：{{ service.device || '-' }}</p>
      </div>
    </aside>

    <main class="content-area">
      <header class="top-bar">
        <div class="top-left">
          <span class="health-pill" :class="healthStatus === 'online' ? 'health-ok' : 'health-off'">
            {{ healthStatus === 'online' ? '服务在线' : '服务离线' }}
          </span>
          <span class="small-text">默认模型：{{ service.default_model_id || '-' }}</span>
        </div>

        <div class="top-actions">
          <button class="btn btn-ghost" :disabled="loading" @click="refreshGlobal">
            {{ loading ? '刷新中...' : '刷新全局信息' }}
          </button>
          <button class="btn btn-primary" @click="logout">退出登录</button>
        </div>
      </header>

      <section class="global-control-card">
        <h2>全局推理参数</h2>
        <div class="global-control-grid">
          <label>
            模型
            <select v-model="selectedModel" class="input">
              <option v-for="item in models" :key="item.id" :value="item.id">
                {{ item.label }}
              </option>
            </select>
          </label>
          <label>
            置信度
            <input
              v-model="confidence"
              class="input"
              type="number"
              min="0"
              max="1"
              step="0.05"
            />
          </label>
          <label>
            输入尺寸
            <input
              v-model="imageSize"
              class="input"
              type="number"
              min="32"
              step="32"
            />
          </label>
        </div>
      </section>

      <RouterView />
    </main>
  </div>
</template>
