import { computed, ref } from 'vue'

const TOKEN_KEY = 'steel_web_token'
const USER_KEY = 'steel_web_user'
const EXPIRES_AT_KEY = 'steel_web_expires_at'

const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const expiresAt = ref(localStorage.getItem(EXPIRES_AT_KEY) || '')
const user = ref(null)

const cachedUser = localStorage.getItem(USER_KEY)
if (cachedUser) {
  try {
    user.value = JSON.parse(cachedUser)
  } catch {
    user.value = null
  }
}

const isAuthenticated = computed(() => Boolean(token.value))

function persist() {
  if (token.value) {
    localStorage.setItem(TOKEN_KEY, token.value)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }

  if (expiresAt.value) {
    localStorage.setItem(EXPIRES_AT_KEY, expiresAt.value)
  } else {
    localStorage.removeItem(EXPIRES_AT_KEY)
  }

  if (user.value) {
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  } else {
    localStorage.removeItem(USER_KEY)
  }
}

function setSession(payload) {
  token.value = payload.token || ''
  expiresAt.value = payload.expires_at || ''
  user.value = payload.user || null
  persist()
}

function setUser(nextUser) {
  user.value = nextUser || null
  persist()
}

function clearSession() {
  token.value = ''
  expiresAt.value = ''
  user.value = null
  persist()
}

export function useAuthStore() {
  return {
    token,
    user,
    expiresAt,
    isAuthenticated,
    setSession,
    setUser,
    clearSession,
  }
}
