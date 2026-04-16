<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useApiError } from '../composables/useApiError'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const { resolveError } = useApiError()

const user = computed(() => auth.user.value)

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

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

async function changePassword() {
  errorMessage.value = ''
  successMessage.value = ''

  if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
    errorMessage.value = '请完整填写密码信息。'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的新密码不一致。'
    return
  }

  submitting.value = true
  try {
    await api.changePassword(auth.token.value, {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    successMessage.value = '密码修改成功，请重新登录。'
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    setTimeout(logout, 700)
  } catch (error) {
    errorMessage.value = resolveError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="page-card">
    <div class="page-head">
      <div>
        <h2>账户设置</h2>
        <p>修改密码后会自动退出登录。</p>
      </div>
    </div>

    <section class="inner-card">
      <h3>账户信息</h3>
      <div class="stat-grid">
        <article class="stat-item">
          <span>用户ID</span>
          <strong>{{ user?.id || '-' }}</strong>
        </article>
        <article class="stat-item">
          <span>用户名</span>
          <strong>{{ user?.username || '-' }}</strong>
        </article>
        <article class="stat-item">
          <span>创建时间</span>
          <strong>{{ user?.created_at || '-' }}</strong>
        </article>
        <article class="stat-item">
          <span>最近登录</span>
          <strong>{{ user?.last_login_at || '-' }}</strong>
        </article>
      </div>
    </section>

    <section class="inner-card">
      <h3>修改密码</h3>
      <div class="global-control-grid">
        <label>
          旧密码
          <input v-model="oldPassword" type="password" class="input" minlength="6" maxlength="128" />
        </label>
        <label>
          新密码
          <input v-model="newPassword" type="password" class="input" minlength="6" maxlength="128" />
        </label>
        <label>
          确认新密码
          <input v-model="confirmPassword" type="password" class="input" minlength="6" maxlength="128" />
        </label>
      </div>
      <div class="inline-actions">
        <button class="btn btn-ghost" :disabled="submitting" @click="changePassword">
          {{ submitting ? '提交中...' : '确认修改' }}
        </button>
      </div>
      <p class="text-error">{{ errorMessage }}</p>
      <p class="text-ok">{{ successMessage }}</p>
    </section>
  </section>
</template>
