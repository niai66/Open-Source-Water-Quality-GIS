<template>
  <div class="stock-place-management">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="search-bar">
        <span class="search-label">地址:</span>
        <input type="text" v-model="searchForm.address" placeholder="输入地址关键词搜索..."
          class="search-input" @keyup.enter="handleSearch" />
        <button class="btn btn-blue" @click="handleSearch">查询</button>
        <button class="btn btn-gray" @click="resetSearch">重置</button>
      </div>
      <div class="action-bar">
        <button class="btn btn-green" @click="triggerImport">批量导入</button>
        <button class="btn btn-orange" @click="handleExport('存量地名处理')" :disabled="exportLoading">
          {{ exportLoading ? '导出中...' : '导出 Excel' }}
        </button>
        <button class="btn btn-blue" @click="openAddDialog">+ 新增</button>
        <input type="file" ref="fileInput" accept=".xlsx,.xls" style="display:none" @change="handleImport" />
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <el-table :data="tableData" border stripe v-loading="loading" style="width: 100%"
        :header-cell-style="{ background: '#0f3460', color: '#e0e6ed', fontWeight: 600 }"
        :cell-style="{ background: '#1a2744', color: '#e0e6ed', borderBottom: '1px solid #2c3e50' }">
        <el-table-column type="index" label="序号" width="65" align="center" />
        <el-table-column prop="BATCHNO" label="批次号" width="180" show-overflow-tooltip />
        <el-table-column prop="ORIGINAL_ADDRESS" label="原始地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="STANDARDIZEDADDRESS" label="规范化地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="LONGITUDE" label="经度" width="130" align="center" />
        <el-table-column prop="LATITUDE" label="纬度" width="130" align="center" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span :class="row.STATE === '1' ? 'status-used' : 'status-unused'">
              {{ row.STATE === '1' ? '已使用' : '未使用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <button class="btn-action btn-edit" @click="openEditDialog(row)">编辑</button>
            <button v-if="row.STATE === '1'" class="btn-action btn-cancel" @click="handleCancel(row.ID)">取消应用</button>
            <button v-else class="btn-action btn-apply" @click="handleApply(row.ID)">应用</button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.size"
        :total="pagination.total" :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper" background :pager-count="5"
        @size-change="fetchData" @current-change="fetchData" />
    </div>

    <!-- 新增/编辑弹窗 -->
    <div class="modal-overlay" v-if="dialogVisible" @click.self="closeDialog">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">{{ isEdit ? '编辑存量地名' : '新增存量地名' }}</span>
          <button class="close-btn" @click="closeDialog">×</button>
        </div>
        <div class="modal-body">
          <el-form :model="form" label-position="top">
            <div class="form-row">
              <div class="form-col">
                <el-form-item label="批次号"><el-input v-model="form.BATCHNO" /></el-form-item>
              </div>
              <div class="form-col">
                <el-form-item label="状态">
                  <el-select v-model="form.STATE" style="width:100%">
                    <el-option label="未使用" value="0" />
                    <el-option label="已使用" value="1" />
                  </el-select>
                </el-form-item>
              </div>
            </div>
            <el-form-item label="原始地址"><el-input v-model="form.ORIGINAL_ADDRESS" /></el-form-item>
            <el-form-item label="规范化地址"><el-input v-model="form.STANDARDIZEDADDRESS" /></el-form-item>
            <div class="form-row">
              <div class="form-col"><el-form-item label="经度"><el-input-number v-model="form.LONGITUDE" :precision="7" :step="0.001" style="width:100%" /></el-form-item></div>
              <div class="form-col"><el-form-item label="纬度"><el-input-number v-model="form.LATITUDE" :precision="7" :step="0.001" style="width:100%" /></el-form-item></div>
            </div>
            <el-form-item label="备注"><el-input v-model="form.REMARK" type="textarea" :rows="3" /></el-form-item>
          </el-form>
        </div>
        <div class="modal-footer">
          <button class="btn btn-gray" @click="closeDialog">取消</button>
          <button class="btn btn-blue" @click="handleSubmit" :disabled="submitLoading">
            {{ submitLoading ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePlaceApi } from '../composables/usePlaceApi'

const BASE_URL = 'http://127.0.0.1:8000'

const api = usePlaceApi('stock_place', {
  BATCHNO: '', ORIGINAL_ADDRESS: '', STANDARDIZEDADDRESS: '',
  LONGITUDE: 0, LATITUDE: 0, STATE: '0', REMARK: ''
})
api.searchForm.address = ''

const fieldMap = {
  BATCHNO: 'BATCHNO', ORIGINAL_ADDRESS: 'ORIGINAL_ADDRESS',
  STANDARDIZEDADDRESS: 'STANDARDIZEDADDRESS', LONGITUDE: 'LONGITUDE',
  LATITUDE: 'LATITUDE', STATE: 'STATE', REMARK: 'REMARK'
}
const origEdit = api.openEditDialog
api.openEditDialog = (row) => origEdit(row, fieldMap)

// ── 应用/取消应用（本页独有） ──
const handleApply = async (id) => {
  try {
    await ElMessageBox.confirm('确定要应用这条记录吗？状态将改为已使用。', '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'info'
    })
    const res = await axios.put(`${BASE_URL}/stock_place/apply/${id}`)
    if (res.data.code === 200) { ElMessage.success(res.data.msg); api.fetchData() }
  } catch (err) { if (err !== 'cancel') ElMessage.error('操作失败') }
}

const handleCancel = async (id) => {
  try {
    await ElMessageBox.confirm('确定要取消应用吗？状态将改为未使用。', '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'info'
    })
    const res = await axios.put(`${BASE_URL}/stock_place/cancel/${id}`)
    if (res.data.code === 200) { ElMessage.success(res.data.msg); api.fetchData() }
  } catch (err) { if (err !== 'cancel') ElMessage.error('操作失败') }
}

// 暴露到模板
const { searchForm, handleSearch, resetSearch, triggerImport, handleImport, handleExport,
  openAddDialog, openEditDialog, closeDialog, handleSubmit,
  fetchData, pagination, tableData, dialogVisible, isEdit, form, submitLoading, loading, exportLoading, fileInput } = api

onMounted(() => api.fetchData())
</script>

<style scoped>
.stock-place-management { min-height: calc(100vh - 80px); }
</style>