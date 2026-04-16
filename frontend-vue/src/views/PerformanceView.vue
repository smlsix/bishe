<script setup>
import { computed, onMounted, ref } from 'vue'

import { useApiError } from '../composables/useApiError'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const { resolveError } = useApiError()

const loading = ref(false)
const performance = ref({ count: 0, records: [] })

const records = computed(() => performance.value.records || [])
const hasData = computed(() => records.value.length > 0)
const isSingleModel = computed(() => records.value.length === 1)

function formatRecentTimes(times) {
  const list = Array.isArray(times) ? times : []
  if (!list.length) {
    return '-'
  }
  return list.join(' | ')
}

async function loadData() {
  loading.value = true
  try {
    performance.value = await api.modelPerformance(auth.token.value, 1000)
  } catch (error) {
    alert(resolveError(error))
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="page-card">
    <div class="page-head">
      <div>
        <h2>模型性能对比</h2>
        <p>只保留表格，并标注具体统计时间。</p>
      </div>
      <button class="btn btn-ghost" :disabled="loading" @click="loadData">
        {{ loading ? '刷新中...' : '刷新统计' }}
      </button>
    </div>

    <section v-if="!hasData" class="inner-card">
      <p>暂无可统计数据，请先执行图片/视频/摄像头推理任务。</p>
    </section>

    <section v-else class="inner-card">
      <p v-if="isSingleModel" class="small-text">
        当前仅使用了一个模型，展示该模型性能统计。
      </p>
      <p v-else class="small-text">
        当前已使用多个模型，展示对比统计表。
      </p>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>模型</th>
              <th>运行次数</th>
              <th>平均 FPS</th>
              <th>平均耗时(s)</th>
              <th>平均 Pipeline(ms)</th>
              <th>检测总数</th>
              <th>最近一次时间</th>
              <th>最早一次时间</th>
              <th>样本时间(最近5次)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in records" :key="item.model_id || item.model_label">
              <td>{{ item.model_label }}</td>
              <td>{{ item.run_count }}</td>
              <td>{{ item.avg_fps }}</td>
              <td>{{ item.avg_latency_seconds }}</td>
              <td>{{ item.avg_pipeline_ms }}</td>
              <td>{{ item.total_detections }}</td>
              <td>{{ item.last_run_at || '-' }}</td>
              <td>{{ item.first_run_at || '-' }}</td>
              <td>{{ formatRecentTimes(item.recent_run_times) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
