<template>
  <div class="bank-data-page">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon">
          <FolderOpened />
        </el-icon>
        <div>
          <h1 class="page-title">
            银行数据
          </h1>
          <p class="page-subtitle">
            {{ excelTotal }} 个文档
          </p>
        </div>
      </div>
      <div class="header-actions">
        <el-button
          type="primary"
          :icon="Refresh"
          :loading="excelLoading"
          @click="loadExcelList"
        >
          刷新
        </el-button>
      </div>
    </div>

    <!-- 上传区域（仅管理员可见） -->
    <div
      v-if="canUpload"
      class="global-upload-section"
    >
      <el-upload
        class="upload-area"
        drag
        :action="uploadUrl"
        :headers="uploadHeaders"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
        accept=".xlsx,.xls,.docx,.doc,.pdf,.pptx,.ppt,.txt,.csv"
        :show-file-list="false"
      >
        <el-icon class="upload-icon">
          <Upload />
        </el-icon>
        <div class="upload-text">
          <span class="upload-title">拖拽文件到此处，或 <em>点击上传</em></span>
          <span class="upload-hint">支持 xlsx, xls, docx, doc, pdf, pptx, ppt, txt, csv 格式</span>
        </div>
      </el-upload>
    </div>

    <!-- 文档管理区域 -->
    <div class="doc-management-section">
      <!-- 分类筛选（单选） -->
      <div class="category-filter">
        <span class="filter-label">文档分类：</span>
        <el-radio-group
          v-model="selectedCategory"
          size="default"
          @change="loadExcelList"
        >
          <el-radio-button value="">
            全部
          </el-radio-button>
          <el-radio-button value="industry">
            银行行业数据库
          </el-radio-button>
          <el-radio-button value="single_bank">
            单家银行数据库
          </el-radio-button>
          <el-radio-button value="report">
            研究报告
          </el-radio-button>
          <el-radio-button value="guide">
            说明指南
          </el-radio-button>
          <el-radio-button value="other">
            其他资料
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 文档列表 -->
      <el-table
        v-loading="excelLoading"
        :data="excelFiles"
        stripe
        border
        size="small"
        class="excel-table"
      >
        <el-table-column
          prop="category"
          label="分类"
          width="200"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="getCategoryTagType(row.category)"
              size="small"
            >
              {{ getCategoryLabel(row.category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="filename"
          label="文件名"
          min-width="300"
        >
          <template #default="{ row }">
            <div class="file-cell">
              <el-icon class="file-icon">
                <Document />
              </el-icon>
              <span
                class="file-name"
                :title="row.filename"
              >{{ row.filename }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          prop="file_size_display"
          label="文件大小"
          width="90"
          align="center"
        />
        <el-table-column
          prop="description"
          label="描述"
          min-width="120"
        />
        <el-table-column
          prop="created_at"
          label="上传时间"
          width="160"
          align="center"
        />
        <el-table-column
          label="操作"
          width="200"
          align="center"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              :icon="Download"
              @click="handleDownload(row)"
            >
              下载
            </el-button>
            <el-button
              v-if="canDelete"
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 审核问题详情弹窗 -->
      <el-dialog
        v-model="showReviewDialog"
        title="审核详情"
        width="600px"
      >
        <div
          v-if="currentReviewFile"
          class="review-dialog-content"
        >
          <div class="review-file-info">
            <strong>文件:</strong> {{ currentReviewFile.filename }}
          </div>
          <el-divider />
          <div class="review-status-info">
            <el-tag
              :type="getReviewStatusType(currentReviewFile.review_status)"
              size="large"
            >
              {{ getReviewStatusLabel(currentReviewFile.review_status) }}
            </el-tag>
          </div>
          <div
            v-if="currentReviewFile.review_issues && currentReviewFile.review_issues.length > 0"
            class="review-issues"
          >
            <h4>检测到的问题:</h4>
            <ul>
              <li
                v-for="(issue, idx) in currentReviewFile.review_issues"
                :key="idx"
              >
                {{ issue }}
              </li>
            </ul>
          </div>
          <div
            v-if="currentReviewFile.reviewed_by"
            class="review-meta"
          >
            <small>审核人: {{ currentReviewFile.reviewed_by }}</small>
            <br>
            <small v-if="currentReviewFile.reviewed_at">审核时间: {{ currentReviewFile.reviewed_at }}</small>
          </div>
        </div>
        <template #footer>
          <el-button @click="showReviewDialog = false">
            关闭
          </el-button>
          <el-button
            v-if="currentReviewFile && (currentReviewFile.review_status === 'pending_review' || currentReviewFile.review_status === 'needs_reprocess')"
            type="success"
            @click="confirmCurrentReview"
          >
            确认审核通过
          </el-button>
        </template>
      </el-dialog>

      <!-- 分类选择弹窗（多选） -->
      <el-dialog
        v-model="showCategoryDialog"
        title="选择文档分类"
        width="500px"
        :close-on-click-modal="false"
      >
        <div class="category-dialog-content">
          <p class="category-tip">
            请为文件 "<strong>{{ pendingUploadFile?.name }}</strong>" 选择分类标签（可多选）：
          </p>
          <el-checkbox-group
            v-model="selectedDocCategories"
            class="category-checkbox-group"
          >
            <el-checkbox value="industry">
              <span class="category-label">银行行业数据库</span>
              <span class="category-desc">银行行业分类数据</span>
            </el-checkbox>
            <el-checkbox value="single_bank">
              <span class="category-label">单家银行数据库</span>
              <span class="category-desc">单一银行的数据报表</span>
            </el-checkbox>
            <el-checkbox value="report">
              <span class="category-label">研究报告</span>
              <span class="category-desc">行业研究报告、分析报告</span>
            </el-checkbox>
            <el-checkbox value="guide">
              <span class="category-label">说明指南</span>
              <span class="category-desc">系统使用说明、操作指南</span>
            </el-checkbox>
            <el-checkbox value="other">
              <span class="category-label">其他资料</span>
              <span class="category-desc">不属于上述分类的其他文档</span>
            </el-checkbox>
          </el-checkbox-group>
          <div class="description-input-wrapper">
            <p
              class="category-tip"
              style="margin-top: 20px;"
            >
              文档描述（可选）：
            </p>
            <el-input
              v-model="uploadDescription"
              type="textarea"
              :rows="2"
              placeholder="请输入文档描述（如：2024年度银行年报）"
              maxlength="200"
              show-word-limit
            />
          </div>
        </div>
        <template #footer>
          <el-button @click="cancelCategorySelect">
            取消
          </el-button>
          <el-button
            type="primary"
            :disabled="selectedDocCategories.length === 0"
            @click="confirmCategorySelect"
          >
            确认添加 ({{ selectedDocCategories.length }})
          </el-button>
        </template>
      </el-dialog>

      <!-- 分页 -->
      <div
        v-if="excelTotal > 0"
        class="excel-pagination"
      >
        <el-pagination
          v-model:current-page="excelPage"
          v-model:page-size="excelPageSize"
          :page-sizes="[10, 20, 50]"
          :total="excelTotal"
          layout="total, sizes, prev, pager, next"
          @size-change="loadExcelList"
          @current-change="loadExcelList"
        />
      </div>

      <!-- 空状态 -->
      <el-empty
        v-if="!excelLoading && excelFiles.length === 0"
        description="暂无文档数据"
        :image-size="80"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  FolderOpened, Refresh, Download, Upload, Document
} from '@element-plus/icons-vue'
import {
  updateExcelReview,
  getBankDocList, getBankDocDownloadUrl, deleteBankDoc
} from '@/api/bank'
import { getApiUrl } from '@/utils/config'

// ============================================================
// 状态
// ============================================================
const excelLoading = ref(false)
const excelFiles = ref([])
const excelTotal = ref(0)
const excelPage = ref(1)
const excelPageSize = ref(20)
const downloadCounts = ref({})
const excelFilters = ref({
  category: '',
  filename: '',
  uploader_name: '',
  dateRange: null
})

// 分类筛选状态（单选）
const selectedCategory = ref('')

// 分类选择弹窗状态（多选）
const showCategoryDialog = ref(false)
const pendingUploadFile = ref(null)
const pendingUploadResponse = ref(null)
const selectedDocCategories = ref([])
const uploadDescription = ref('')

// 审核相关状态
const showReviewDialog = ref(false)
const currentReviewFile = ref(null)
const reviewLoading = ref(false)

// 上传相关 - 使用独立的银行数据文档API
const uploadUrl = computed(() => getApiUrl('/bank-doc/upload'))
const uploadHeaders = computed(() => ({
  'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
}))

// ============================================================
// 计算属性
// ============================================================

// 权限判断
const currentUserRole = computed(() => localStorage.getItem('user_role') || '')
const currentPermissions = computed(() => {
  const perms = localStorage.getItem('permissions')
  return perms ? JSON.parse(perms) : []
})

// 是否为超级管理员
const isSuperAdmin = computed(() => currentUserRole.value === 'super_admin')

// 是否可以上传（超级管理员或拥有数据权限的管理员）
const canUpload = computed(() => {
  if (isSuperAdmin.value) return true
  return currentUserRole.value === 'admin' && currentPermissions.value.includes('data')
})

// 是否可以删除（与上传权限相同）
const canDelete = computed(() => canUpload.value)

const filteredBanks = computed(() => {
  if (!bankSearchKeyword.value.trim()) return banks.value
  const keyword = bankSearchKeyword.value.toLowerCase()
  return banks.value.filter(b =>
    b.bank_name.toLowerCase().includes(keyword) ||
    (b.bank_code && b.bank_code.toLowerCase().includes(keyword))
  )
})

// ============================================================
// 方法
// ============================================================

// ============================================================
// Excel 数据相关方法
// ============================================================
const loadExcelList = async () => {
  excelLoading.value = true
  try {
    const params = {
      page: excelPage.value,
      page_size: excelPageSize.value
    }

    // 使用分类筛选（单选）
    if (selectedCategory.value) {
      params.category = selectedCategory.value
    }
    if (excelFilters.value.filename) {
      params.filename = excelFilters.value.filename
    }
    if (excelFilters.value.uploader_name) {
      params.uploader_name = excelFilters.value.uploader_name
    }
    if (excelFilters.value.dateRange && excelFilters.value.dateRange.length === 2) {
      params.start_date = excelFilters.value.dateRange[0]
      params.end_date = excelFilters.value.dateRange[1]
    }

    // 使用新的银行数据文档API
    const res = await getBankDocList(params)
    if (res.success) {
      excelFiles.value = res.data.files || []
      excelTotal.value = res.data.total || 0
    }
  } catch (e) {
    console.error('加载文档列表失败:', e)
    ElMessage.error('加载文档列表失败')
  } finally {
    excelLoading.value = false
  }
}

// 审核状态相关方法
const getReviewStatusType = (status) => {
  const typeMap = {
    'auto': 'info',
    'pending_review': 'warning',
    'reviewed': 'success',
    'needs_reprocess': 'danger'
  }
  return typeMap[status] || 'info'
}

const getReviewStatusLabel = (status) => {
  const labelMap = {
    'auto': '自动',
    'pending_review': '待审核',
    'reviewed': '已审核',
    'needs_reprocess': '需重处理'
  }
  return labelMap[status] || status
}

// 分类辅助方法
const getCategoryLabel = (category) => {
  const labelMap = {
    'industry': '银行行业数据库',
    'single_bank': '单家银行数据库',
    'report': '研究报告',
    'guide': '说明指南',
    'other': '其他资料'
  }
  // 支持多分类（逗号分隔），转换为中文显示
  if (category && category.includes(',')) {
    return category.split(',').map(c => labelMap[c] || c).join('、')
  }
  return labelMap[category] || category || '未分类'
}

const getCategoryTagType = (category) => {
  const typeMap = {
    'industry': 'primary',
    'single_bank': 'success',
    'report': 'warning',
    'guide': '',
    'other': 'info'
  }
  return typeMap[category] || 'info'
}

const handleConfirmReview = (row) => {
  currentReviewFile.value = row
  showReviewDialog.value = true
}

const confirmCurrentReview = async () => {
  if (!currentReviewFile.value) return

  reviewLoading.value = true
  try {
    const res = await updateExcelReview(currentReviewFile.value.id, {
      review_status: 'reviewed',
      reviewed_by: '系统用户'
    })

    if (res.success) {
      ElMessage.success('审核确认成功')
      showReviewDialog.value = false
      currentReviewFile.value = null
      await loadExcelList()
    } else {
      ElMessage.error(res.error || '审核确认失败')
    }
  } catch (e) {
    console.error('审核确认失败:', e)
    ElMessage.error('审核确认失败')
  } finally {
    reviewLoading.value = false
  }
}

const resetExcelFilters = () => {
  excelFilters.value = {
    category: '',
    filename: '',
    uploader_name: '',
    dateRange: null
  }
  excelPage.value = 1
  loadExcelList()
}

const handleDownload = (row) => {
  const downloadUrl = getBankDocDownloadUrl(row.id)
  window.open(downloadUrl, '_blank')
  const current = downloadCounts.value[row.id] || 0
  downloadCounts.value[row.id] = current + 1
  downloadCounts.value = { ...downloadCounts.value }
}

// 删除文档
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件 "${row.filename}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await deleteBankDoc(row.id)
    if (res.success) {
      ElMessage.success('删除成功')
      loadExcelList()
    } else {
      ElMessage.error(res.error || '删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除失败:', e)
      ElMessage.error('删除失败')
    }
  }
}

// 上传相关方法
const beforeUpload = (file) => {
  const isValidType = ['.xlsx', '.xls', '.docx', '.doc', '.pdf'].some(ext =>
    file.name.toLowerCase().endsWith(ext)
  )
  if (!isValidType) {
    ElMessage.error('只能上传 xlsx, xls, docx, doc, pdf 格式的文件')
    return false
  }
  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return true
}

// 上传失败处理
const handleUploadError = (err, file, fileList) => {
  // 尝试解析错误响应
  let errorMsg = '文件上传失败'
  let errorData = null
  
  try {
    if (err.response) {
      errorData = err.response.data || err.response
    } else if (err.message) {
      const jsonMatch = err.message.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        errorData = JSON.parse(jsonMatch[0])
      }
    }
  } catch (e) {
    console.error('解析上传错误失败:', e)
  }
  
    // 检查是否是重复文件错误
    if (errorData && errorData.duplicate) {
      const existingFile = errorData.existing_file
      const fileName = existingFile?.filename || file.name
      
      ElMessageBox.confirm(
        `<div style="text-align:left">
          <p><strong>文件名：</strong>${fileName}</p>
          <p><strong>上传时间：</strong>${existingFile?.created_at || '未知'}</p>
          <p><strong>上传者：</strong>${existingFile?.uploader_name || '未知'}</p>
          <p><strong>文件大小：</strong>${existingFile?.file_size_display || '未知'}</p>
          <p style="color:#e6a23c;margin-top:10px;">是否用新文件替换原文件？</p>
        </div>`,
        '文件已存在',
        {
          confirmButtonText: '覆盖',
          cancelButtonText: '跳过',
          dangerouslyUseHTMLString: true,
          type: 'warning'
        }
      ).then(async () => {
        // 用户选择覆盖 - 使用自定义上传（带 overwrite 参数）
        const uploadData = new FormData()
        uploadData.append('file', file.raw)
        uploadData.append('overwrite', 'true')
        
        try {
          const uploadRes = await fetch(uploadUrl.value, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
            },
            body: uploadData
          })
          const result = await uploadRes.json()
          
          if (result.success) {
            ElMessage.success('文件覆盖成功')
            // 弹出分类选择
            pendingUploadFile.value = file.raw
            pendingUploadResponse.value = result
            selectedDocCategories.value = []
            showCategoryDialog.value = true
          } else {
            ElMessage.error(result.error || '覆盖失败')
          }
        } catch (e) {
          ElMessage.error('覆盖上传失败')
        }
      }).catch(() => {
        // 用户选择跳过
        ElMessage.warning('已跳过上传')
        loadExcelList()
      })
      return
    }
  
  // 其他错误
  if (errorData && errorData.error) {
    errorMsg = errorData.error
  } else if (err.message) {
    errorMsg = err.message
  }
  
  ElMessage.error(errorMsg)
}

const handleUploadSuccess = (response, file, fileList) => {
  // 保存上传响应，弹出分类选择弹窗
  pendingUploadFile.value = file.raw
  pendingUploadResponse.value = response
  selectedDocCategories.value = []
  uploadDescription.value = ''
  showCategoryDialog.value = true
}

// 确认分类选择
import { updateBankDoc } from '@/api/bank'

const confirmCategorySelect = async () => {
  if (!selectedDocCategories.value || selectedDocCategories.value.length === 0 || !pendingUploadResponse.value) return

  try {
    // 从响应中获取文件ID
    const fileId = pendingUploadResponse.value.data?.id || pendingUploadResponse.value.id
    if (fileId) {
      // 发送多分类和描述到后端
      await updateBankDoc(fileId, { 
        categories: selectedDocCategories.value,
        description: uploadDescription.value
      })
      
      ElMessage.success(`文件上传成功，已标记为"${selectedDocCategories.value.map(c => getCategoryLabel(c)).join('、')}"`)
    }
    showCategoryDialog.value = false
    loadExcelList()
  } catch (e) {
    console.error('更新分类失败:', e)
    ElMessage.error('文件已上传，但分类设置失败')
    loadExcelList()
  }

  // 清理状态
  pendingUploadFile.value = null
  pendingUploadResponse.value = null
  selectedDocCategories.value = []
}

// 取消分类选择
const cancelCategorySelect = () => {
  showCategoryDialog.value = false
  pendingUploadFile.value = null
  pendingUploadResponse.value = null
  selectedDocCategories.value = []
  uploadDescription.value = ''
  ElMessage.warning('文件已上传，可随时在文件列表中修改分类')
  loadExcelList()
}

const getBankTagType = (type) => {
  const map = { '国有大型银行': '', '股份制银行': 'warning', '城市商业银行': 'success', '农村商业银行': 'info' }
  return map[type] || 'info'
}

// ============================================================
// 生命周期
// ============================================================
onMounted(() => {
  loadExcelList()
})
</script>

<style scoped>
.bank-data-page {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 20px;
  box-sizing: border-box;
}

/* 顶部标题 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  background: #fff;
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-icon { font-size: 36px; color: #409EFF; }
.page-title { margin: 0; font-size: 20px; font-weight: 700; color: #1a1a2e; }
.page-subtitle { margin: 2px 0 0; font-size: 13px; color: #909399; }
.header-actions { display: flex; align-items: center; gap: 10px; }

/* 全局上传区域 */
.global-upload-section {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
  margin-bottom: 20px;
}

.global-upload-section .upload-area {
  width: 100%;
}

.global-upload-section .upload-area :deep(.el-upload-dragger) {
  padding: 40px 20px;
  border: 2px dashed #d9d9d9;
  border-radius: 12px;
  background: #fafafa;
  transition: all .2s;
}

.global-upload-section .upload-area :deep(.el-upload-dragger:hover) {
  border-color: #409EFF;
  background: #ecf5ff;
}

.global-upload-section .upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 12px;
}

.global-upload-section .upload-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.global-upload-section .upload-title {
  font-size: 14px;
  color: #606266;
}

.global-upload-section .upload-title em {
  color: #409EFF;
  font-style: normal;
}

.global-upload-section .upload-hint {
  font-size: 12px;
  color: #909399;
}

/* Tab 区域 */
.tab-section {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
  padding: 20px;
}

.bank-data-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.bank-data-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}

.tab-content {
  min-height: 400px;
}

/* 分类卡片样式 */
.industry-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.industry-card {
  background: #fafafa;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all .2s;
  border: 1px solid #f0f0f0;
}

.industry-card:hover {
  background: #f5f7ff;
  border-color: #409EFF;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
}

.industry-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: #fff;
  flex-shrink: 0;
}

.industry-info {
  flex: 1;
}

.industry-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.industry-count {
  font-size: 13px;
  color: #909399;
}

/* 单家银行样式 */
.single-bank-search {
  margin-bottom: 20px;
}

.single-bank-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.single-bank-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 10px;
  cursor: pointer;
  transition: all .2s;
  border: 1px solid transparent;
}

.single-bank-item:hover {
  background: #ecf5ff;
  border-color: #409EFF;
}

.bank-avatar-sm {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}

.bank-detail-info {
  flex: 1;
}

.bank-detail-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.bank-detail-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bank-detail-code {
  font-size: 12px;
  color: #c0c4cc;
}

.bank-detail-arrow {
  color: #c0c4cc;
  font-size: 16px;
}

/* 上传区域 */
.upload-section {
  margin-bottom: 20px;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  padding: 40px 20px;
  border: 2px dashed #d9d9d9;
  border-radius: 12px;
  background: #fafafa;
  transition: all .2s;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: #409EFF;
  background: #ecf5ff;
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 12px;
}

.upload-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-title {
  font-size: 14px;
  color: #606266;
}

.upload-title em {
  color: #409EFF;
  font-style: normal;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
}

/* 筛选面板 */
.excel-filter-panel {
  padding: 16px 20px;
  background: #fafafa;
  border-radius: 10px;
  margin-bottom: 16px;
}

.excel-filter-panel :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 12px;
}

.excel-filter-panel :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

/* 文档列表 */
.excel-table :deep(.el-table__header-wrapper) {
  background: #fafafa;
}

.file-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-cell .file-icon {
  font-size: 18px;
  color: #67c23a;
  flex-shrink: 0;
}

.file-cell .file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.description-text {
  color: #909399;
  font-size: 12px;
}

.excel-pagination {
  padding: 16px 20px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid #f0f0f0;
  margin-top: 16px;
}

/* 审核相关样式 */
.review-auto {
  color: #909399;
  font-size: 12px;
}

.review-dialog-content {
  padding: 8px 0;
}

.review-file-info {
  margin-bottom: 12px;
  font-size: 14px;
}

.review-status-info {
  margin-bottom: 16px;
}

.review-issues {
  background: #fdf6ec;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.review-issues h4 {
  margin: 0 0 8px;
  color: #e6a23c;
  font-size: 14px;
}

.review-issues ul {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  font-size: 13px;
}

.review-issues li {
  margin-bottom: 4px;
}

.review-meta {
  color: #909399;
  font-size: 12px;
  text-align: right;
}

/* 银行详情弹窗 */
.bank-detail-content {
  padding: 0;
}

.bank-detail-header {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 20px;
}

.detail-avatar-lg {
  width: 80px;
  height: 80px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.detail-info h2 {
  margin: 0 0 8px;
  font-size: 22px;
  color: #1a1a2e;
}

.detail-info p {
  margin: 0 0 12px;
  font-size: 14px;
  color: #909399;
}

.detail-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.bank-detail-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.detail-stat-item {
  background: #fafafa;
  border-radius: 10px;
  padding: 20px;
  text-align: center;
}

.detail-stat-label {
  display: block;
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.detail-stat-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #409EFF;
}

/* 响应式 */
@media (max-width: 1200px) {
  .industry-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 分类筛选样式 */
.category-filter {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.category-filter :deep(.el-checkbox-button__inner) {
  border-radius: 4px;
  margin-right: 4px;
}

/* 分类选择弹窗样式 */
.category-dialog-content {
  padding: 10px 0;
}

.category-tip {
  margin: 0 0 20px;
  font-size: 14px;
  color: #606266;
}

.category-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.category-checkbox-group :deep(.el-checkbox) {
  display: flex;
  align-items: flex-start;
  padding: 12px 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-right: 0;
  margin-left: 0;
  transition: all .2s;
}

.category-checkbox-group :deep(.el-checkbox:hover) {
  border-color: #409EFF;
  background: #ecf5ff;
}

.category-checkbox-group :deep(.el-checkbox.is-checked) {
  border-color: #409EFF;
  background: #ecf5ff;
}

.category-checkbox-group :deep(.el-checkbox__label) {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.category-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.category-desc {
  font-size: 12px;
  color: #909399;
}
</style>
