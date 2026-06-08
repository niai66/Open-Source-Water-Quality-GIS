import { ref, reactive } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const BASE_URL = 'http://127.0.0.1:8000'

/**
 * 通用 CRUD Composable（适配老师工程化路由）
 * @param {string} module 路由模块前缀，如 'place' → /place/add, /place/export
 * @param {object} defaultForm 表单默认值
 */
export function usePlaceApi(module, defaultForm) {
  const loading = ref(false)
  const exportLoading = ref(false)
  const submitLoading = ref(false)
  const tableData = ref([])
  const dialogVisible = ref(false)
  const isEdit = ref(false)
  const currentId = ref(null)
  const fileInput = ref(null)
  const searchForm = reactive({})
  const pagination = reactive({ page: 1, size: 10, total: 0 })
  const form = reactive({ ...defaultForm })

  // ── 查询列表 ──
  const fetchData = async () => {
    loading.value = true
    try {
      const res = await axios.get(`${BASE_URL}/${module}/list`, {
        params: { ...searchForm, page: pagination.page, size: pagination.size }
      })
      if (res.data.code === 200) {
        tableData.value = res.data.data.list
        pagination.total = res.data.data.total
      }
    } catch { ElMessage.error('获取列表失败') }
    finally { loading.value = false }
  }

  // ── 搜索/重置 ──
  const handleSearch = () => { pagination.page = 1; fetchData() }
  const resetSearch = () => {
    Object.keys(searchForm).forEach(k => searchForm[k] = '')
    handleSearch()
  }

  // ── 弹窗 ──
  const openAddDialog = () => {
    isEdit.value = false
    currentId.value = null
    Object.assign(form, { ...defaultForm })
    dialogVisible.value = true
  }

  const openEditDialog = (row, fieldMap) => {
    isEdit.value = true
    currentId.value = row.ID
    const data = {}
    for (const key of Object.keys(defaultForm)) {
      data[key] = row[fieldMap?.[key] || key] ?? defaultForm[key]
    }
    Object.assign(form, data)
    dialogVisible.value = true
  }

  const closeDialog = () => { dialogVisible.value = false }

  // ── 提交 ──
  const handleSubmit = async () => {
    submitLoading.value = true
    try {
      const url = isEdit.value
        ? `${BASE_URL}/${module}/update/${currentId.value}`
        : `${BASE_URL}/${module}/add`
      const method = isEdit.value ? 'put' : 'post'
      const res = await axios[method](url, form)
      if (res.data.code === 200) {
        ElMessage.success(res.data.msg)
        dialogVisible.value = false
        fetchData()
      }
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || '操作失败')
    } finally { submitLoading.value = false }
  }

  // ── 删除 ──
  const handleDelete = async (id) => {
    try {
      await ElMessageBox.confirm('确定要删除这条记录吗？', '提示', {
        confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
      })
      const res = await axios.delete(`${BASE_URL}/${module}/delete/${id}`)
      if (res.data.code === 200) {
        ElMessage.success('删除成功')
        fetchData()
      }
    } catch (err) { if (err !== 'cancel') ElMessage.error('删除失败') }
  }

  // ── 导出 ──
  const handleExport = async (prefix = module) => {
    exportLoading.value = true
    try {
      const res = await axios.get(`${BASE_URL}/${module}/export`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      const date = new Date().toLocaleDateString().replace(/\//g, '')
      link.download = `${prefix}_${date}.xlsx`
      link.click()
      window.URL.revokeObjectURL(url)
      ElMessage.success('导出成功')
    } catch { ElMessage.error('导出失败') }
    finally { exportLoading.value = false }
  }

  // ── 导入 ──
  const triggerImport = () => {
    fileInput.value.value = ''
    fileInput.value.click()
  }

  const handleImport = async (e) => {
    const file = e.target.files[0]
    e.target.value = ''
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await axios.post(`${BASE_URL}/${module}/import`, formData)
      if (res.data.code === 200) {
        ElMessage.success(res.data.msg)
        fetchData()
      }
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || '导入失败')
    }
  }

  return {
    loading, exportLoading, submitLoading,
    tableData, dialogVisible, isEdit, currentId, fileInput,
    searchForm, pagination, form,
    fetchData, handleSearch, resetSearch,
    openAddDialog, openEditDialog, closeDialog, handleSubmit,
    handleDelete, handleExport, triggerImport, handleImport
  }
}
