<template>
  <div class="stats-page">
    <div class="page-title">地名信息统计</div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon blue"><!-- 省图标 -->
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">省</div>
          <div class="stat-value">{{ stats.province_count }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green"><!-- 市图标 -->
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">市</div>
          <div class="stat-value">{{ stats.city_count }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon teal"><!-- 区县图标 -->
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 11H5"/><path d="M12 19V7"/></svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">区县</div>
          <div class="stat-value">{{ stats.district_count }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon blue2"><!-- 乡镇图标 -->
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
        <div class="stat-info">
          <div class="stat-label">乡镇街道</div>
          <div class="stat-value">{{ stats.town_count }}</div>
        </div>
      </div>
    </div>

    <!-- 统计表格 -->
    <div class="table-container">
      <el-table :data="detailData" border stripe v-loading="loading" style="width: 100%"
        :header-cell-style="{ background: '#0f3460', color: '#e0e6ed', fontWeight: 600 }"
        :cell-style="{ background: '#1a2744', color: '#e0e6ed', borderBottom: '1px solid #2c3e50' }">
        <el-table-column type="index" label="序号" width="65" align="center" />
        <el-table-column prop="province" label="省份" min-width="120" />
        <el-table-column prop="city" label="市县" min-width="120" />
        <el-table-column prop="district" label="区域" min-width="120" />
        <el-table-column label="乡镇/街道" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.town && row.village ? row.town + ' / ' + row.village : (row.town || row.village || '-') }}
          </template>
        </el-table-column>
        <el-table-column prop="count" label="地名数量" width="110" align="center">
          <template #default="{ row }"><span class="count-value">{{ row.count }}</span></template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.size"
          :total="pagination.total" :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper" background :pager-count="5"
          @size-change="fetchDetail" @current-change="fetchDetail" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const BASE_URL = 'http://127.0.0.1:8000'
const loading = ref(false)
const stats = reactive({ province_count: 0, city_count: 0, district_count: 0, town_count: 0 })
const detailData = ref([])
const pagination = reactive({ page: 1, size: 10, total: 0 })

const fetchStats = async () => {
  try {
    const res = await axios.get(`${BASE_URL}/places/stats`)
    Object.assign(stats, res.data)
  } catch { ElMessage.error('获取统计数据失败') }
}

const fetchDetail = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${BASE_URL}/places/stats/detail`, {
      params: { page: pagination.page, size: pagination.size }
    })
    detailData.value = res.data.items
    pagination.total = res.data.total
  } catch { ElMessage.error('获取统计明细失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchStats(); fetchDetail() })
</script>

<style scoped>
.stats-page { min-height: calc(100vh - 80px); }
.page-title { font-size: 20px; font-weight: bold; margin-bottom: 24px; color: #e0e6ed; }

/* --- 统计卡片 --- */
.stats-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
.stat-card {
  background: linear-gradient(135deg, #1a2744 0%, #0f3460 100%);
  border-radius: 12px; padding: 20px;
  display: flex; align-items: center; gap: 15px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.2); border-left: 4px solid;
}
.stat-card:nth-child(1) { border-left-color: #3498db; }
.stat-card:nth-child(2) { border-left-color: #2ecc71; }
.stat-card:nth-child(3) { border-left-color: #1abc9c; }
.stat-card:nth-child(4) { border-left-color: #3498db; }

.stat-icon {
  width: 48px; height: 48px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.stat-icon.blue { background-color: rgba(52,152,219,0.2); color: #3498db; }
.stat-icon.green { background-color: rgba(46,204,113,0.2); color: #2ecc71; }
.stat-icon.teal { background-color: rgba(26,188,156,0.2); color: #1abc9c; }
.stat-icon.blue2 { background-color: rgba(52,152,219,0.2); color: #3498db; }

.stat-info { flex: 1; }
.stat-label { font-size: 14px; color: #95a5a6; margin-bottom: 4px; }
.stat-value { font-size: 28px; font-weight: bold; color: #fff; }
.count-value { color: #3498db; font-weight: bold; font-size: 15px; }
</style>