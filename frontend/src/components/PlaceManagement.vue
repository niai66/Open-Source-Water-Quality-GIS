<template>
  <div class="place-management">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="search-bar">
        <span class="search-label">区域:</span>
        <input type="text" v-model="searchForm.district" placeholder="输入区域关键词搜索..."
          class="search-input" @keyup.enter="handleSearch" />
        <button class="btn btn-blue" @click="handleSearch">查询</button>
        <button class="btn btn-gray" @click="resetSearch">重置</button>
      </div>
      <div class="action-bar">
        <button class="btn btn-green" @click="triggerImport">导入 Excel</button>
        <button class="btn btn-orange" @click="handleExport('地名数据')" :disabled="exportLoading">
          {{ exportLoading ? '导出中...' : '导出 Excel' }}
        </button>
        <button class="btn btn-blue" @click="openAddDialog()">+ 新增地名</button>
        <input type="file" ref="fileInput" accept=".xlsx,.xls" style="display:none" @change="handleImport" />
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <el-table :data="tableData" border stripe v-loading="loading" style="width: 100%"
        :header-cell-style="{ background: '#0f3460', color: '#e0e6ed', fontWeight: 600 }"
        :cell-style="{ background: '#1a2744', color: '#e0e6ed', borderBottom: '1px solid #2c3e50' }">
        <el-table-column type="index" label="序号" width="65" align="center" />
        <el-table-column prop="PROVINCE" label="省份" width="100" />
        <el-table-column prop="COUNTY" label="市县" width="120" />
        <el-table-column prop="DISTRICT" label="区域" width="120" />
        <el-table-column prop="VILLAGE" label="地址/村庄" min-width="200" show-overflow-tooltip />
        <el-table-column prop="LONGITUDE" label="经度" width="130" align="center" />
        <el-table-column prop="LATITUDE" label="纬度" width="130" align="center" />
        <el-table-column prop="REMARK" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <button class="btn-action btn-edit" @click="openEditDialog(row)">编辑</button>
            <button class="btn-action btn-delete" @click="handleDelete(row.ID)">删除</button>
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
          <span class="modal-title">{{ isEdit ? '编辑地名' : '新增地名' }}</span>
          <button class="close-btn" @click="closeDialog">×</button>
        </div>
        <div class="modal-body">
          <el-form :model="form" label-position="top">
            <div class="form-row">
              <div class="form-col"><el-form-item label="省份"><el-input v-model="form.PROVINCE" /></el-form-item></div>
              <div class="form-col"><el-form-item label="市县"><el-input v-model="form.COUNTY" /></el-form-item></div>
            </div>
            <el-form-item label="区域"><el-input v-model="form.DISTRICT" /></el-form-item>
            <el-form-item label="地址/村庄"><el-input v-model="form.VILLAGE" /></el-form-item>
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
import { usePlaceApi } from '../composables/usePlaceApi'

const api = usePlaceApi('place', {
  PROVINCE: '', COUNTY: '', DISTRICT: '', VILLAGE: '',
  LONGITUDE: 0, LATITUDE: 0, REMARK: ''
})

api.searchForm.district = ''

const fieldMap = { PROVINCE: 'PROVINCE', COUNTY: 'COUNTY', DISTRICT: 'DISTRICT', VILLAGE: 'VILLAGE', LONGITUDE: 'LONGITUDE', LATITUDE: 'LATITUDE', REMARK: 'REMARK' }
const origEdit = api.openEditDialog
api.openEditDialog = (row) => origEdit(row, fieldMap)

// 解构所有模板需要用到的变量
const { searchForm, handleSearch, resetSearch, triggerImport, handleImport, handleExport,
  openAddDialog, openEditDialog, closeDialog, handleSubmit,
  fetchData, pagination, tableData, dialogVisible, isEdit, form, submitLoading, loading, exportLoading, fileInput } = api

onMounted(() => api.fetchData())
</script>

<style scoped>
.place-management { min-height: calc(100vh - 80px); }
</style>