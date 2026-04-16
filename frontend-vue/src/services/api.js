async function request(path, options = {}) {
  const response = await fetch(path, options)
  const contentType = response.headers.get('content-type') || ''

  let data
  if (contentType.includes('application/json')) {
    data = await response.json()
  } else {
    data = { detail: await response.text() }
  }

  if (!response.ok) {
    throw new Error(data.detail || 'Request failed')
  }
  return data
}

function authHeaders(token) {
  if (!token) {
    return {}
  }
  return { Authorization: `Bearer ${token}` }
}

async function exportWithToken(url, token, fallbackName) {
  const response = await fetch(url, {
    headers: authHeaders(token),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: 'Export failed' }))
    throw new Error(payload.detail || 'Export failed')
  }

  const blob = await response.blob()
  const contentDisposition = response.headers.get('content-disposition') || ''
  const matched = contentDisposition.match(/filename="?([^"]+)"?/)
  const fileName = matched?.[1] || fallbackName

  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

export const api = {
  health() {
    return request('/api/health')
  },
  bootstrapStatus() {
    return request('/api/auth/bootstrap-status')
  },
  register(payload) {
    return request('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },
  login(payload) {
    return request('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },
  me(token) {
    return request('/api/auth/me', {
      headers: authHeaders(token),
    })
  },
  logout(token) {
    return request('/api/auth/logout', {
      method: 'POST',
      headers: authHeaders(token),
    })
  },
  changePassword(token, payload) {
    return request('/api/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(token),
      },
      body: JSON.stringify(payload),
    })
  },
  activity(token, limit = 50) {
    return request(`/api/auth/activity?limit=${limit}`, {
      headers: authHeaders(token),
    })
  },
  modelPerformance(token, limit = 500) {
    return request(`/api/auth/model-performance?limit=${limit}`, {
      headers: authHeaders(token),
    })
  },
  info(token) {
    return request('/api/info', {
      headers: authHeaders(token),
    })
  },
  history(token, limit = 60) {
    return request(`/api/history?limit=${limit}`, {
      headers: authHeaders(token),
    })
  },
  exportHistory(format, token) {
    return exportWithToken(`/api/history/export?format=${format}`, token, `history.${format}`)
  },
  predictImage(token, formData) {
    return request('/api/predict/image', {
      method: 'POST',
      headers: authHeaders(token),
      body: formData,
    })
  },
  predictImagesBatch(token, formData) {
    return request('/api/predict/images-batch', {
      method: 'POST',
      headers: authHeaders(token),
      body: formData,
    })
  },
  predictVideo(token, formData) {
    return request('/api/predict/video', {
      method: 'POST',
      headers: authHeaders(token),
      body: formData,
    })
  },
  predictCameraFrame(token, formData) {
    return request('/api/predict/camera-frame', {
      method: 'POST',
      headers: authHeaders(token),
      body: formData,
    })
  },
}
