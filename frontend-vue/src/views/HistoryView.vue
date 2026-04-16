<script setup>
import { onMounted, ref } from 'vue'

import { useApiError } from '../composables/useApiError'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const { resolveError } = useApiError()

const loading = ref(false)
const history = ref({ count: 0, records: [] })
const activity = ref({ count: 0, records: [] })

async function loadData() {
  loading.value = true
  try {
    const [historyPayload, activityPayload] = await Promise.all([
      api.history(auth.token.value, 120),
      api.activity(auth.token.value, 120),
    ])
    history.value = historyPayload
    activity.value = activityPayload
  } catch (error) {
    alert(resolveError(error))
  } finally {
    loading.value = false
  }
}

async function exportHistory(format) {
  try {
    await api.exportHistory(format, auth.token.value)
  } catch (error) {
    alert(resolveError(error))
  }
}

onMounted(loadData)
</script>

<template>
  <section class="page-card">
    <div class="page-head">
      <div>
        <h2>历史与审计</h2>
        <p>这里集中查看系统历史和当前用户操作记录。</p>
      </div>
      <div class="inline-actions">
        <button class="btn btn-ghost" :disabled="loading" @click="loadData">{{ loading ? '刷新中...' : '刷新' }}</button>
        <button class="btn btn-ghost" @click="exportHistory('csv')">导出 CSV</button>
        <button class="btn btn-ghost" @click="exportHistory('xls')">导出 XLS</button>
      </div>
    </div>

    <section class="inner-card">
      <h3>系统历史记录（全部任务）</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>类型</th>
              <th>来源</th>
              <th>模型</th>
              <th>检测数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!(history.records || []).length">
              <td colspan="6">暂无历史记录</td>
            </tr>
            <tr v-for="item in history.records" :key="item.id">
              <td>{{ item.created_at }}</td>
              <td>{{ item.task_type }}</td>
              <td>{{ item.source_name }}</td>
              <td>{{ item.model_label || '-' }}</td>
              <td>{{ item.summary?.detection_count || 0 }}</td>
              <td>
                <div class="inline-actions">
                  <a v-if="item.result_url" :href="item.result_url" target="_blank" class="link-pill">结果</a>
                  <a v-if="item.preview_url" :href="item.preview_url" target="_blank" class="link-pill">预览</a>
                  <a v-if="item.csv_url" :href="item.csv_url" target="_blank" class="link-pill">CSV</a>
                  <a v-if="item.meta_url" :href="item.meta_url" target="_blank" class="link-pill">详情</a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="inner-card">
      <h3>我的操作审计（数据库）</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>任务</th>
              <th>模型</th>
              <th>检测数</th>
              <th>耗时</th>
              <th>记录ID</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!(activity.records || []).length">
              <td colspan="6">暂无个人审计记录</td>
            </tr>
            <tr v-for="item in activity.records" :key="item.id">
              <td>{{ item.created_at }}</td>
              <td>{{ item.task_type }}</td>
              <td>{{ item.model_label || item.model_id || '-' }}</td>
              <td>{{ item.detection_count || 0 }}</td>
              <td>{{ item.latency_seconds || 0 }} s</td>
              <td>{{ item.record_id || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
