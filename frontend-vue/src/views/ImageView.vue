<script setup>
import { computed, ref } from 'vue'

import { useApiError } from '../composables/useApiError'
import { api } from '../services/api'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const appStore = useAppStore()
const { resolveError } = useApiError()

const imageFiles = ref([])
const submitting = ref(false)
const statusText = ref('等待上传图片')
const imageResult = ref(null)
const activeIndex = ref(0)

const imageItems = computed(() => imageResult.value?.items || [])
const activeItem = computed(() => imageItems.value[activeIndex.value] || null)
const detections = computed(() => activeItem.value?.detections || [])

function withCache(url) {
  if (!url) {
    return ''
  }
  return `${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`
}

function formatClassCounts(classCounts = {}) {
  const entries = Object.entries(classCounts)
  if (!entries.length) {
    return '未检测到目标'
  }
  return entries.map(([name, count]) => `${name} x ${count}`).join(' / ')
}

function normalizeImageResult(payload) {
  if (payload.items) {
    return payload
  }
  return {
    ...payload,
    summary: {
      ...(payload.summary || {}),
      image_count: 1,
    },
    items: [
      {
        source_name: payload.source_name,
        summary: payload.summary || {},
        detections: payload.detections || [],
        source_url: payload.source_url,
        result_url: payload.result_url,
      },
    ],
  }
}

function onSelectFiles(event) {
  imageFiles.value = Array.from(event.target.files || [])
  if (!imageFiles.value.length) {
    statusText.value = '等待上传图片'
    return
  }
  if (imageFiles.value.length === 1) {
    statusText.value = `已选择 ${imageFiles.value[0].name}`
    return
  }
  statusText.value = `已选择 ${imageFiles.value.length} 张图片`
}

function setActive(index) {
  if (index < 0 || index >= imageItems.value.length) {
    return
  }
  activeIndex.value = index
}

async function submitImages() {
  if (!imageFiles.value.length) {
    statusText.value = '请先选择图片'
    return
  }

  const formData = new FormData()
  const isBatch = imageFiles.value.length > 1
  if (isBatch) {
    imageFiles.value.forEach((file) => formData.append('files', file))
  } else {
    formData.append('file', imageFiles.value[0])
  }
  appStore.appendCommonFields(formData)

  submitting.value = true
  statusText.value = isBatch ? '批量推理中...' : '图片推理中...'
  try {
    const payload = isBatch
      ? await api.predictImagesBatch(auth.token.value, formData)
      : await api.predictImage(auth.token.value, formData)
    imageResult.value = normalizeImageResult(payload)
    activeIndex.value = 0
    statusText.value = isBatch ? '批量处理完成' : '处理完成'
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
        <h2>图片检测</h2>
        <p>单图和批量都在本页完成。</p>
      </div>
      <span class="small-text">{{ statusText }}</span>
    </div>

    <label class="upload-box">
      <strong>上传图片（支持多选）</strong>
      <input type="file" accept="image/*" multiple @change="onSelectFiles" />
    </label>

    <button class="btn btn-primary" :disabled="submitting" @click="submitImages">
      {{ submitting ? '处理中...' : '开始检测' }}
    </button>

    <div class="media-grid">
      <article class="inner-card">
        <h3>原图预览</h3>
        <img v-if="activeItem?.source_url" :src="withCache(activeItem.source_url)" alt="source" class="media-preview" />
        <p v-else class="small-text">暂无图片</p>
      </article>
      <article class="inner-card">
        <h3>结果预览</h3>
        <img v-if="activeItem?.result_url" :src="withCache(activeItem.result_url)" alt="result" class="media-preview" />
        <p v-else class="small-text">暂无结果</p>
      </article>
    </div>

    <div class="stat-grid">
      <article class="stat-item">
        <span>图片数</span>
        <strong>{{ imageResult?.summary?.image_count || imageItems.length || 0 }}</strong>
      </article>
      <article class="stat-item">
        <span>检测总数</span>
        <strong>{{ imageResult?.summary?.detection_count || 0 }}</strong>
      </article>
      <article class="stat-item">
        <span>耗时</span>
        <strong>{{ imageResult?.summary?.latency_seconds || 0 }} s</strong>
      </article>
      <article class="stat-item">
        <span>类别统计</span>
        <strong>{{ formatClassCounts(imageResult?.summary?.class_counts || {}) }}</strong>
      </article>
    </div>

    <div class="inline-actions">
      <button class="btn btn-ghost" :disabled="activeIndex <= 0" @click="setActive(activeIndex - 1)">上一张</button>
      <span class="small-text">
        {{ imageItems.length ? `第 ${activeIndex + 1} / ${imageItems.length} 张` : '暂无批量结果' }}
      </span>
      <button class="btn btn-ghost" :disabled="activeIndex >= imageItems.length - 1" @click="setActive(activeIndex + 1)">
        下一张
      </button>
      <a v-if="imageResult?.csv_url" :href="imageResult.csv_url" target="_blank" class="link-pill">下载 CSV</a>
      <a v-if="imageResult?.meta_url" :href="imageResult.meta_url" target="_blank" class="link-pill">详情 JSON</a>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>图片</th>
            <th>检测数</th>
            <th>类别统计</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!imageItems.length">
            <td colspan="4">暂无检测结果</td>
          </tr>
          <tr v-for="(item, index) in imageItems" :key="`${item.source_name || 'item'}_${index}`" @click="setActive(index)">
            <td>{{ index + 1 }}</td>
            <td>{{ item.source_name || '-' }}</td>
            <td>{{ item.summary?.detection_count || 0 }}</td>
            <td>{{ formatClassCounts(item.summary?.class_counts || {}) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>类别</th>
            <th>置信度</th>
            <th>框坐标</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!detections.length">
            <td colspan="4">当前图片没有检测框</td>
          </tr>
          <tr v-for="(det, index) in detections" :key="index">
            <td>{{ index + 1 }}</td>
            <td>{{ det.display_name }}</td>
            <td>{{ det.confidence }}</td>
            <td>[{{ det.bbox.x1 }}, {{ det.bbox.y1 }}, {{ det.bbox.x2 }}, {{ det.bbox.y2 }}]</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
