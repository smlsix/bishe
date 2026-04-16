<script setup>
import { ref } from 'vue'

import { useApiError } from '../composables/useApiError'
import { api } from '../services/api'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const appStore = useAppStore()
const { resolveError } = useApiError()

const file = ref(null)
const statusText = ref('等待上传视频')
const submitting = ref(false)
const videoResult = ref(null)

function withCache(url) {
  if (!url) {
    return ''
  }
  return `${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`
}

function onSelectFile(event) {
  const selected = event.target.files?.[0]
  file.value = selected || null
  statusText.value = selected ? `已选择 ${selected.name}` : '等待上传视频'
}

async function submitVideo() {
  if (!file.value) {
    statusText.value = '请先选择视频'
    return
  }

  const formData = new FormData()
  formData.append('file', file.value)
  appStore.appendCommonFields(formData)

  submitting.value = true
  statusText.value = '视频推理中，请稍等...'
  try {
    videoResult.value = await api.predictVideo(auth.token.value, formData)
    statusText.value = `处理完成：${videoResult.value.source_name}`
  } catch (error) {
    statusText.value = resolveError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="page-card">
    <div class="page-head">
      <div>
        <h2>视频检测</h2>
        <p>上传视频后自动输出检测结果视频。</p>
      </div>
      <span class="small-text">{{ statusText }}</span>
    </div>

    <label class="upload-box">
      <strong>上传视频文件</strong>
      <input type="file" accept="video/*" @change="onSelectFile" />
    </label>

    <button class="btn btn-primary" :disabled="submitting" @click="submitVideo">
      {{ submitting ? '处理中...' : '开始检测' }}
    </button>

    <div class="media-grid">
      <article class="inner-card">
        <h3>结果视频</h3>
        <video
          v-if="videoResult?.result_url"
          :src="withCache(videoResult.result_url)"
          controls
          playsinline
          class="media-preview"
        ></video>
        <p v-else class="small-text">暂无结果视频</p>
      </article>
      <article class="inner-card">
        <h3>首帧预览</h3>
        <img v-if="videoResult?.preview_url" :src="withCache(videoResult.preview_url)" alt="preview" class="media-preview" />
        <p v-else class="small-text">暂无预览</p>
      </article>
    </div>

    <div class="stat-grid">
      <article class="stat-item">
        <span>检测总数</span>
        <strong>{{ videoResult?.summary?.detection_count || 0 }}</strong>
      </article>
      <article class="stat-item">
        <span>处理帧数</span>
        <strong>{{ videoResult?.summary?.frame_count || 0 }}</strong>
      </article>
      <article class="stat-item">
        <span>耗时</span>
        <strong>{{ videoResult?.summary?.latency_seconds || 0 }} s</strong>
      </article>
      <article class="stat-item">
        <span>FPS</span>
        <strong>{{ videoResult?.summary?.fps || 0 }}</strong>
      </article>
    </div>

    <div class="inline-actions">
      <a v-if="videoResult?.source_url" :href="videoResult.source_url" target="_blank" class="link-pill">原视频</a>
      <a v-if="videoResult?.result_url" :href="videoResult.result_url" target="_blank" class="link-pill">结果视频</a>
      <a v-if="videoResult?.csv_url" :href="videoResult.csv_url" target="_blank" class="link-pill">逐帧 CSV</a>
      <a v-if="videoResult?.meta_url" :href="videoResult.meta_url" target="_blank" class="link-pill">详情 JSON</a>
    </div>
  </section>
</template>
