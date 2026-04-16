import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

export function useApiError() {
  const router = useRouter()
  const auth = useAuthStore()

  function resolveError(error) {
    const message = error?.message || '请求失败'
    if (message.includes('Token is invalid') || message.includes('Authorization header')) {
      auth.clearSession()
      router.push({ name: 'login' })
    }
    return message
  }

  return {
    resolveError,
  }
}
