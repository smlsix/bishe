<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')
const setupHint = ref('')

async function handleSubmit() {
  errorMessage.value = ''
  loading.value = true
  try {
    const response = await api.login({
      username: username.value,
      password: password.value,
    })
    auth.setSession(response)
    router.push({ name: 'overview' })
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const bootstrap = await api.bootstrapStatus()
    if (bootstrap.needs_setup) {
      setupHint.value = '当前系统还没有用户，请先注册。'
    }
  } catch {
    setupHint.value = ''
  }
})
</script>

<template>
  <div class="auth-shell">
    <section class="auth-box auth-intro">
      <p class="auth-kicker">STEEL DEFECT AI</p>
      <h1>钢板缺陷检测平台</h1>
      <p>
        新版界面已经拆分为多页面：图片检测、视频检测、摄像头检测、
        历史记录、模型性能对比、账户管理。
      </p>
      <p class="auth-hint">{{ setupHint || '使用账号密码登录后进入系统。' }}</p>
    </section>

    <section class="auth-box auth-form-box">
      <h2>登录</h2>
      <form class="auth-form" @submit.prevent="handleSubmit">
        <label>
          用户名
          <input
            v-model.trim="username"
            type="text"
            class="input"
            minlength="3"
            maxlength="32"
            placeholder="例如 student_01"
            required
          />
        </label>
        <label>
          密码
          <input
            v-model="password"
            type="password"
            class="input"
            minlength="6"
            maxlength="128"
            placeholder="至少 6 位"
            required
          />
        </label>
        <button class="btn btn-primary" type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登录系统' }}
        </button>
        <RouterLink class="btn btn-ghost auth-link-btn" to="/register">去注册</RouterLink>
      </form>
      <p class="text-error">{{ errorMessage }}</p>
    </section>
  </div>
</template>
