<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

async function handleRegister() {
  errorMessage.value = ''
  successMessage.value = ''
  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致。'
    return
  }

  loading.value = true
  try {
    const response = await api.register({
      username: username.value,
      password: password.value,
    })
    auth.setSession(response)
    successMessage.value = '注册成功，正在进入系统...'
    setTimeout(() => {
      router.push({ name: 'overview' })
    }, 350)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-shell">
    <section class="auth-box auth-intro">
      <p class="auth-kicker">CREATE ACCOUNT</p>
      <h1>创建检测账号</h1>
      <p>
        注册完成后自动登录。系统会记录每次推理的模型与性能数据，
        供后续对比分析。
      </p>
      <p class="auth-hint">用户名支持字母、数字、下划线，长度 3-32。</p>
    </section>

    <section class="auth-box auth-form-box">
      <h2>注册</h2>
      <form class="auth-form" @submit.prevent="handleRegister">
        <label>
          用户名
          <input
            v-model.trim="username"
            type="text"
            class="input"
            minlength="3"
            maxlength="32"
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
            required
          />
        </label>
        <label>
          确认密码
          <input
            v-model="confirmPassword"
            type="password"
            class="input"
            minlength="6"
            maxlength="128"
            required
          />
        </label>
        <button class="btn btn-primary" type="submit" :disabled="loading">
          {{ loading ? '注册中...' : '创建账号' }}
        </button>
        <RouterLink class="btn btn-ghost auth-link-btn" to="/login">返回登录</RouterLink>
      </form>
      <p class="text-error">{{ errorMessage }}</p>
      <p class="text-ok">{{ successMessage }}</p>
    </section>
  </div>
</template>
