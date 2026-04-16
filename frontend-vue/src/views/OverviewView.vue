<script setup>
import { computed, onMounted, ref } from 'vue'

import { useApiError } from '../composables/useApiError'
import { api } from '../services/api'
import { useAppStore } from '../stores/app'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const appStore = useAppStore()
const { resolveError } = useApiError()

const loading = ref(false)
const history = ref({ count: 0, records: [] })
const activity = ref({ count: 0, records: [] })
const performance = ref({ count: 0, records: [] })

const service = computed(() => appStore.service.value || {})
const topPerformance = computed(() => performance.value.records || [])
const hasMultiModel = computed(() => topPerformance.value.length > 1)

async function loadData() {
  loading.value = true
  try {
    const [historyPayload, activityPayload, perfPayload] = await Promise.all([
      api.history(auth.token.value, 8),
      api.activity(auth.token.value, 8),
      api.modelPerformance(auth.token.value, 200),
    ])
    history.value = historyPayload
    activity.value = activityPayload
    performance.value = perfPayload
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
        <h2>系统总览</h2>
        <p>按功能拆分后的主入口页面。</p>
      </div>
      <button class="btn btn-ghost" :disabled="loading" @click="loadData">
        {{ loading ? '加载中...' : '刷新当前页' }}
      </button>
    </div>

    <div class="stat-grid">
      <article class="stat-item">
        <span>已发现模型数</span>
        <strong>{{ (service.models || []).length }}</strong>
      </article>
      <article class="stat-item">
        <span>历史记录条数</span>
        <strong>{{ history.count || 0 }}</strong>
      </article>
      <article class="stat-item">
        <span>我的最近操作</span>
        <strong>{{ activity.count || 0 }}</strong>
      </article>
      <article class="stat-item">
        <span>参与对比模型</span>
        <strong>{{ performance.count || 0 }}</strong>
      </article>
    </div>

    <div class="simple-grid">
      <section class="inner-card">
        <h3>最近历史</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>类型</th>
                <th>来源</th>
                <th>模型</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!(history.records || []).length">
                <td colspan="4">暂无数据</td>
              </tr>
              <tr v-for="item in history.records" :key="item.id">
                <td>{{ item.created_at }}</td>
                <td>{{ item.task_type }}</td>
                <td>{{ item.source_name }}</td>
                <td>{{ item.model_label || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="inner-card">
        <h3>模型表现摘要</h3>
        <p v-if="!topPerformance.length" class="small-text">暂无性能数据，先去执行推理任务。</p>
        <p v-else-if="!hasMultiModel" class="small-text">当前只使用了一个模型，显示单模型统计。</p>
        <p v-else class="small-text">已检测到多个模型，可在“模型性能对比”页面查看完整图表。</p>

        <div class="mini-chart" v-for="item in topPerformance.slice(0, 4)" :key="item.model_id || item.model_label">
          <div class="mini-chart-head">
            <span>{{ item.model_label }}</span>
            <span>{{ item.run_count }} 次</span>
          </div>
          <div class="mini-chart-row">
            <span>Avg FPS</span>
            <strong>{{ item.avg_fps }}</strong>
          </div>
          <div class="mini-chart-row">
            <span>Avg Latency</span>
            <strong>{{ item.avg_latency_seconds }} s</strong>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>
