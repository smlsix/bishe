<script setup>
import { onBeforeUnmount, ref } from 'vue'

import { useApiError } from '../composables/useApiError'
import { api } from '../services/api'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const appStore = useAppStore()
const { resolveError } = useApiError()

const liveVideoRef = ref(null)
const resultImageUrl = ref('')
const statusText = ref('摄像头未打开')
const loopStatus = ref('空闲')
const detectionCount = ref(0)
const latency = ref(0)
const fps = ref(0)

const streamRef = ref(null)
const detecting = ref(false)
const cameraReady = ref(false)
const canvas = document.createElement('canvas')

function withCache(url) {
  if (!url) {
    return ''
  }
  return `${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function ensureVideoReady() {
  const video = liveVideoRef.value
  if (!video) {
    return
  }

  if (video.readyState < 2) {
    await new Promise((resolve) => {
      const handler = () => {
        video.removeEventListener('loadeddata', handler)
        resolve()
      }
      video.addEventListener('loadeddata', handler)
    })
  }

  try {
    await video.play()
  } catch {
    // ignore autoplay rejections
  }
  await sleep(200)
}

async function openCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    statusText.value = '当前浏览器不支持摄像头访问'
    return
  }

  if (streamRef.value) {
    await ensureVideoReady()
    cameraReady.value = true
    statusText.value = '摄像头已打开'
    return
  }

  try {
    streamRef.value = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false,
    })
    const video = liveVideoRef.value
    if (!video) {
      statusText.value = '视频组件未准备好'
      return
    }
    video.srcObject = streamRef.value
    await ensureVideoReady()
    cameraReady.value = true
    statusText.value = '摄像头已打开'
  } catch (error) {
    statusText.value = resolveError(error)
  }
}

function closeCamera() {
  detecting.value = false
  loopStatus.value = '已停止'

  if (streamRef.value) {
    streamRef.value.getTracks().forEach((track) => track.stop())
    streamRef.value = null
  }

  const video = liveVideoRef.value
  if (video) {
    video.pause()
    video.srcObject = null
  }
  cameraReady.value = false
  statusText.value = '摄像头已关闭'
}

async function captureBlob() {
  const video = liveVideoRef.value
  if (!video || !video.videoWidth || !video.videoHeight) {
    throw new Error('摄像头画面尚未准备好')
  }

  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const context = canvas.getContext('2d')
  context.drawImage(video, 0, 0, canvas.width, canvas.height)

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('无法抓取摄像头帧'))
        return
      }
      resolve(blob)
    }, 'image/jpeg', 0.9)
  })
}

async function detectLoop() {
  while (detecting.value) {
    try {
      const blob = await captureBlob()
      const formData = new FormData()
      formData.append('file', blob, `camera_${Date.now()}.jpg`)
      appStore.appendCommonFields(formData)
      const payload = await api.predictCameraFrame(auth.token.value, formData)

      resultImageUrl.value = payload.result_url || ''
      detectionCount.value = payload.summary?.detection_count || 0
      latency.value = payload.summary?.latency_seconds || 0
      fps.value = payload.summary?.fps || 0
      loopStatus.value = payload.summary?.class_counts
        ? Object.entries(payload.summary.class_counts)
            .map(([name, count]) => `${name} x ${count}`)
            .join(' / ')
        : '未检测到目标'
      statusText.value = `最近一次推理：${payload.created_at || '-'}`
    } catch (error) {
      statusText.value = resolveError(error)
    }
    await sleep(700)
  }
}

async function startDetection() {
  await openCamera()
  if (!cameraReady.value || detecting.value) {
    return
  }
  detecting.value = true
  statusText.value = '实时检测中...'
  loopStatus.value = '运行中'
  detectLoop()
}

function stopDetection() {
  detecting.value = false
  statusText.value = cameraReady.value ? '检测已停止，摄像头仍开启' : '检测已停止'
  loopStatus.value = '已停止'
}

onBeforeUnmount(() => {
  closeCamera()
})
</script>

<template>
  <section class="page-card">
    <div class="page-head">
      <div>
        <h2>摄像头实时检测</h2>
        <p>这个页面专门做实时帧推理，不再和其他功能混在一起。</p>
      </div>
      <span class="small-text">{{ statusText }}</span>
    </div>

    <div class="inline-actions">
      <button class="btn btn-ghost" @click="openCamera">打开摄像头</button>
      <button class="btn btn-primary" @click="startDetection">开始检测</button>
      <button class="btn btn-ghost" @click="stopDetection">停止检测</button>
      <button class="btn btn-ghost" @click="closeCamera">关闭摄像头</button>
    </div>

    <div class="media-grid">
      <article class="inner-card">
        <h3>实时画面</h3>
        <video
          ref="liveVideoRef"
          autoplay
          playsinline
          muted
          class="media-preview"
        ></video>
      </article>
      <article class="inner-card">
        <h3>推理结果</h3>
        <img v-if="resultImageUrl" :src="withCache(resultImageUrl)" alt="camera result" class="media-preview" />
        <p v-else class="small-text">暂无推理结果</p>
      </article>
    </div>

    <div class="stat-grid">
      <article class="stat-item">
        <span>当前检测数</span>
        <strong>{{ detectionCount }}</strong>
      </article>
      <article class="stat-item">
        <span>推理耗时</span>
        <strong>{{ latency }} s</strong>
      </article>
      <article class="stat-item">
        <span>FPS</span>
        <strong>{{ fps }}</strong>
      </article>
      <article class="stat-item">
        <span>循环状态</span>
        <strong>{{ loopStatus }}</strong>
      </article>
    </div>
  </section>
</template>
