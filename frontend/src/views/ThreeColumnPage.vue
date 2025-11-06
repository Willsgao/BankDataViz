<!-- frontend/src/views/ThreeColumnPage.vue -->
<template>
  <ThreeColumnLayout
    :filtered-pdf-count="filteredPdfCount"
    :table-count="tableCount"
    :is-middle-collapsed="isMiddleCollapsed"
    @toggle-middle="toggleMiddleCollapse"
  >
    <template #left>
      <div class="pdf-preview-container">
        <div v-if="selectedPdf" class="pdf-viewer">
          <div class="pdf-header">
            <h3>{{ selectedPdf.name }}</h3>
            <div class="header-actions">
              <el-button
                type="primary"
                size="small"
                @click="downloadPdf(selectedPdf)"
                :loading="downloadLoading"
              >
                <el-icon><Download /></el-icon>
                下载PDF
              </el-button>
            </div>
          </div>
          <div class="pdf-content">
            <!-- PDF预览区域 -->
            <iframe
              v-if="pdfUrl"
              :src="pdfUrl + '#page=' + currentPage"
              width="100%"
              height="100%"
              frameborder="0"
              @load="onPdfLoad"
              ref="pdfIframe"
              :key="pdfUrl + currentPage"
            ></iframe>
            <div v-else class="no-preview">
              <el-icon><Document /></el-icon>
              <p>无法加载PDF预览</p>
            </div>
          </div>
        </div>
        <div v-else class="pdf-placeholder">
          <el-icon><Document /></el-icon>
          <p>请从右侧选择PDF文件进行预览</p>
        </div>
      </div>
    </template>

    <template #middle-top>
      <div class="pdf-list">
        <div class="collapse-control">
          <el-tooltip content="折叠中间区域" placement="top">
            <el-button
              size="small"
              circle
              @click.stop="toggleMiddleCollapse"
              class="collapse-btn"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
        <div v-if="isSearching" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          搜索中...
        </div>
        <div v-else-if="filteredPdfCount === 0" class="empty-state">
          <p>暂无搜索结果</p>
          <p class="tip">在右上角搜索框输入PDF名称关键字</p>
        </div>
        <div v-else class="pdf-items">
          <div
            v-for="pdf in searchResults"
            :key="pdf.id || pdf.name"
            class="pdf-item"
            :class="{ 'active': selectedPdf && selectedPdf.id === pdf.id }"
            @click="selectPdf(pdf)"
          >
            <el-icon><Document /></el-icon>
            <span class="pdf-name">{{ pdf.name }}</span>
            <el-tag v-if="pdf.matchType" size="small" type="success">
              {{ pdf.matchType }}
            </el-tag>
          </div>
        </div>
      </div>
    </template>

    <template #middle-bottom>
      <div class="table-list-container">
        <div class="section-header">
          <span class="section-title">表格名称列表</span>
          <el-tag type="info">{{ tableCount }} 个表格</el-tag>
        </div>
        <div class="table-content">
          <div v-if="loadingSheets" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载表格列表中...
          </div>
          <div v-else-if="excelFiles.length === 0" class="empty-state">
            <p>暂无表格数据</p>
            <p class="tip">选中的PDF没有对应的Excel文件</p>
          </div>
          <div v-else class="excel-files-container">
            <div
              v-for="excelFile in excelFiles"
              :key="excelFile.excel_file"
              class="excel-file-item"
            >
              <div class="excel-file-header">
                <el-icon><Document /></el-icon>
                <span class="excel-file-name">{{ excelFile.excel_file }}</span>
                <el-tag size="small" type="info">
                  {{ excelFile.total_sheets }} 个表
                </el-tag>
              </div>
              <div class="sheet-items">
                <div
                  v-for="sheet in excelFile.sheets"
                  :key="`${excelFile.excel_file}-${sheet.name}`"
                  class="sheet-item"
                  :class="{
                    'active': selectedSheet &&
                             selectedSheet.name === sheet.name &&
                             selectedSheet.excel_file === excelFile.excel_file
                  }"
                  @click="selectSheet(sheet, excelFile.excel_file)"
                >
                  <el-icon><Grid /></el-icon>
                  <span class="sheet-name">{{ sheet.name }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template #right>
      <div class="excel-content-container">
        <div class="section-header">
          <div class="header-left">
            <h3>Excel表格内容</h3>
            <div v-if="selectedSheet" class="header-info">
              <el-tag type="primary">{{ selectedSheet.name }}</el-tag>
              <span v-if="excelData.length > 0" class="data-count">
                共 {{ excelData.length }} 行数据
              </span>
            </div>
          </div>
          <div class="header-actions">
            <el-button
              type="primary"
              size="small"
              :disabled="!selectedSheet || excelData.length === 0"
              @click="showAnalysisDialog = true"
            >
              <el-icon><DataAnalysis /></el-icon>
              数据可视化分析
            </el-button>
          </div>
        </div>

        <!-- 原有的表格内容保持不变 -->
        <div class="excel-content">
          <div v-if="!selectedSheet" class="placeholder">
            <el-icon><Grid /></el-icon>
            <p>请选择表格查看内容</p>
          </div>
          <div v-else-if="loadingExcel" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载表格数据中...
          </div>
          <div v-else-if="excelData.length === 0" class="empty-state">
            <p>表格为空</p>
          </div>
          <div v-else class="excel-table-container">
            <el-table
              :data="excelData"
              border
              stripe
              height="100%"
              style="width: 100%"
              empty-text="暂无数据"
            >
              <el-table-column
                v-for="column in tableColumns"
                :key="column.prop"
                :prop="column.prop"
                :label="column.label"
                :min-width="column.width || 120"
                show-overflow-tooltip
              >
                <template #default="scope">
                  <span>{{ scope.row[column.prop] }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <!-- 替换为独立的数据分析组件 -->
      <DataAnalysisDialog
        v-model="showAnalysisDialog"
        :excel-data="excelData"
        :sheet-name="selectedSheet?.name || ''"
      />
    </template>


  </ThreeColumnLayout>
</template>

<script setup>
import ThreeColumnLayout from '@/layouts/ThreeColumnLayout.vue'
import { Document, Loading, Download, Close, Grid, DataAnalysis } from '@element-plus/icons-vue'
import { ref, inject, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'


// 导入独立的数据分析组件
import DataAnalysisDialog from '@/components/analysis/DataAnalysisDialog.vue'



// 从 App.vue 注入搜索数据
const searchResults = inject('searchResults', [])
const isSearching = inject('isSearching', ref(false))

// 新增状态
const selectedPdf = ref(null)
const pdfUrl = ref('')
const downloadLoading = ref(false)
const isMiddleCollapsed = ref(false)

// Excel 相关状态
const sheetList = ref([])
const excelFiles = ref([]) // 改为存储Excel文件列表
const selectedSheet = ref(null)
const selectedExcelFile = ref('')
const excelData = ref([])
const tableColumns = ref([])
const loadingSheets = ref(false)
const loadingExcel = ref(false)

// 新增：分析相关状态
const showAnalysisDialog = ref(false)
const selectedAnalysisType = ref('score-distribution')
const loadingAnalysis = ref(false)
const loadingLLM = ref(false)
const customPrompt = ref('')
const llmAnalysisResult = ref('')
const commentStats = ref([])

// 计算属性
const filteredPdfCount = computed(() => searchResults.value.length)
const tableCount = computed(() => {
  return excelFiles.value.reduce((total, file) => total + file.sheets.length, 0)
})


// 切换中间区域折叠状态
const toggleMiddleCollapse = () => {
  isMiddleCollapsed.value = !isMiddleCollapsed.value
}


// 修改状态变量
const currentPage = ref(1)
const totalPages = ref(0)
const pdfIframe = ref(null)


const getPdfUrlWithPage = () => {
  if (!pdfUrl.value) return ''
  return `${pdfUrl.value}#page=${currentPage.value}`
}

// 修改从sheet名称提取页码的方法
const extractPageFromSheetName = (sheetName) => {
  const pageMatch = sheetName.match(/P(\d+)_/)
  if (pageMatch && pageMatch[1]) {
    const pageNum = parseInt(pageMatch[1])
    if (pageNum > 0) {
      currentPage.value = pageNum
      // 延迟跳转确保iframe已加载
      setTimeout(() => {
        updatePdfPage()
      }, 100)
      return pageNum
    }
  }
  return null
}

// 修改selectSheet方法
const selectSheet = async (sheet, excelFileName) => {
  selectedSheet.value = {
    ...sheet,
    excel_file: excelFileName
  }
  selectedExcelFile.value = excelFileName

  // 自动提取并跳转到对应页码
  const pageNum = extractPageFromSheetName(sheet.name)
  console.log(`📄 从sheet名称 "${sheet.name}" 提取到页码: ${pageNum}`)

  loadingExcel.value = true
  try {
    if (sheet.name === '目录') {
      await loadAllClassData(excelFileName)
    } else {
      await loadExcelData(sheet.name, excelFileName)
    }
  } catch (error) {
    console.error('加载表格数据失败:', error)
    ElMessage.error('加载表格数据失败')
    excelData.value = []
    tableColumns.value = []
  } finally {
    loadingExcel.value = false
  }
}

// 监听选中的PDF变化，清空相关数据 - 保留这个监听器！
watch(selectedPdf, (newPdf, oldPdf) => {
  if (newPdf?.id !== oldPdf?.id) {
    selectedSheet.value = null
    excelData.value = []
    tableColumns.value = []
    currentPage.value = 1 // 新增：切换PDF时重置为第1页
    console.log('🔄 切换到新PDF，清空数据并重置为第1页')
  }
})

// 添加监听，当sheet变化时自动跳转
watch(selectedSheet, (newSheet) => {
  if (newSheet && newSheet.name) {
    const pageNum = extractPageFromSheetName(newSheet.name)
    if (pageNum) {
      console.log(`🎯 自动跳转到第 ${pageNum} 页`)
      ElMessage.info(`已跳转到PDF第 ${pageNum} 页`)
    }
  }
})

// 在 script setup 部分添加这个方法
const updatePdfPage = () => {
  if (pdfIframe.value && pdfUrl.value) {
    // 通过修改iframe的src来跳转页面
    const iframe = pdfIframe.value
    const currentSrc = iframe.src.split('#')[0]
    iframe.src = `${currentSrc}#page=${currentPage.value}`
  }
}

// 修改页面导航方法（移除goToPage）
const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    updatePdfPage()
    console.log(`⬅️ 切换到上一页: ${currentPage.value}`)
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    updatePdfPage()
    console.log(`➡️ 切换到下一页: ${currentPage.value}`)
  }
}

// 获取所有sheet中的最大页码（用于设置总页数）
const getMaxPageFromSheets = () => {
  let maxPage = 1
  excelFiles.value.forEach(file => {
    file.sheets.forEach(sheet => {
      const pageNum = getPageFromSheetName(sheet.name)
      if (pageNum && pageNum > maxPage) {
        maxPage = pageNum
      }
    })
  })
  return maxPage
}

// 监听excelFiles变化，更新总页数
watch(excelFiles, (newFiles) => {
  if (newFiles && newFiles.length > 0) {
    const maxPage = getMaxPageFromSheets()
    totalPages.value = Math.max(maxPage, totalPages.value)
    console.log(`📊 根据sheets计算总页数: ${totalPages.value}`)
  }
})







// 选择PDF文件
const selectPdf = async (pdf) => {
  console.log('选中PDF:', pdf)
  selectedPdf.value = pdf
  selectedSheet.value = null
  excelFiles.value = []
  excelData.value = []
  tableColumns.value = []

  try {
    // 获取PDF文件的URL
    let fileId = pdf.id
    if (!fileId) {
      // 如果没有ID，尝试通过文件名查找
      console.log('PDF没有ID，尝试通过文件名查找:', pdf.name)
      const fileResponse = await fetch(`/api/search-pdf?keyword=${encodeURIComponent(pdf.name)}`)
      if (fileResponse.ok) {
        const fileData = await fileResponse.json()
        const matchedFile = fileData.files.find(f => f.name === pdf.name)
        if (matchedFile && matchedFile.id) {
          fileId = matchedFile.id
          console.log('通过文件名找到ID:', fileId)
        }
      }
    }

    if (fileId) {
      // 通过文件ID获取PDF内容
      pdfUrl.value = `/api/file-by-id/${fileId}`
      console.log('设置PDF预览URL:', pdfUrl.value)

      // 根据PDF ID获取对应的Excel sheet列表
      console.log('开始加载Excel sheets，PDF ID:', fileId)
      await loadExcelSheets(fileId)
    } else {
      // 备用方案：通过文件名获取
      console.log('使用文件名作为备用方案:', pdf.name)
      pdfUrl.value = `/api/file/${encodeURIComponent(pdf.name)}`
      console.log('设置备用PDF预览URL:', pdfUrl.value)
    }

    ElMessage.success(`已加载PDF: ${pdf.name}`)
  } catch (error) {
    console.error('加载PDF失败:', error)
    ElMessage.error('加载PDF失败')
  }
}

// 加载Excel sheet列表
const loadExcelSheets = async (pdfId) => {
  console.log('开始加载Excel sheets，PDF ID:', pdfId)
  loadingSheets.value = true
  excelFiles.value = []

  try {
    const response = await fetch(`/api/excel-sheets/${pdfId}`)
    console.log('Excel sheets API响应状态:', response.status)

    if (response.ok) {
      const data = await response.json()
      console.log('Excel sheets API返回数据:', data)
      excelFiles.value = data.excel_files || []
      console.log('解析后的Excel文件列表:', excelFiles.value)

      // 如果有sheet，默认选中第一个文件的第一个sheet
      if (excelFiles.value.length > 0 && excelFiles.value[0].sheets.length > 0) {
        const firstFile = excelFiles.value[0]
        const firstSheet = firstFile.sheets[0]
        console.log('默认选中第一个sheet:', firstSheet, '来自文件:', firstFile.excel_file)
        await selectSheet(firstSheet, firstFile.excel_file)
      } else {
        console.log('没有找到Excel sheets或sheets为空')
        ElMessage.info('该PDF没有对应的表格数据')
      }
    } else {
      console.log('Excel sheets API请求失败，状态码:', response.status)
      const errorText = await response.text()
      console.log('错误响应:', errorText)
      excelFiles.value = []
      ElMessage.warning('该PDF没有对应的Excel文件')
    }
  } catch (error) {
    console.error('加载Excel sheet列表失败:', error)
    excelFiles.value = []
    ElMessage.error('加载表格列表失败')
  } finally {
    loadingSheets.value = false
  }
}




// 新增：加载所有班级数据
const loadAllClassData = async (excelFileName) => {
  if (!selectedPdf.value) return

  try {
    const pdfId = selectedPdf.value.id
    // 首先获取目录信息
    const directoryResponse = await fetch(`/api/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/目录`)

    if (!directoryResponse.ok) {
      throw new Error('无法加载目录数据')
    }

    const directoryData = await directoryResponse.json()

    // 从目录中获取所有班级sheet名称
    const classSheets = directoryData.rows.map(row => ({
      sheetName: row.sheet_name,
      tableName: row.table_name
    })).filter(item => item.sheetName && item.sheetName !== '目录')

    console.log('发现班级sheets:', classSheets)

    // 并行加载所有班级数据
    const classDataPromises = classSheets.map(async (classItem) => {
      try {
        const response = await fetch(`/api/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/${encodeURIComponent(classItem.sheetName)}`)
        if (response.ok) {
          const data = await response.json()
          return {
            className: classItem.sheetName,
            tableName: classItem.tableName,
            data: data.rows,
            totalRows: data.total_rows
          }
        }
      } catch (error) {
        console.error(`加载班级 ${classItem.sheetName} 数据失败:`, error)
        return null
      }
    })

    const allClassData = (await Promise.all(classDataPromises)).filter(Boolean)

    // 设置合并后的数据（用于显示）
    excelData.value = mergeClassDataForDisplay(allClassData)
    tableColumns.value = generateDirectoryTableColumns()

    // 保存所有班级数据用于分析
    window.allClassData = allClassData

    ElMessage.success(`已加载 ${allClassData.length} 个班级的数据`)

  } catch (error) {
    console.error('加载所有班级数据失败:', error)
    throw error
  }
}

// 合并班级数据用于显示
const mergeClassDataForDisplay = (allClassData) => {
  return allClassData.map(classData => ({
    班级名称: classData.className,
    表格类型: classData.tableName,
    数据条数: classData.totalRows,
    平均总分: calculateClassAverageScore(classData.data)
  }))
}

// 计算班级平均分
const calculateClassAverageScore = (classData) => {
  const scores = classData.map(row => parseInt(row.总分 || row['总分'] || 0)).filter(score => !isNaN(score))
  if (scores.length === 0) return 0
  return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
}

// 生成目录表格的列配置
const generateDirectoryTableColumns = () => {
  return [
    { prop: '班级名称', label: '班级名称', width: 120 },
    { prop: '表格类型', label: '表格类型', width: 120 },
    { prop: '数据条数', label: '数据条数', width: 100 },
    { prop: '平均总分', label: '平均总分', width: 100 }
  ]
}



// 加载Excel数据
const loadExcelData = async (sheetName, excelFileName) => {
  if (!selectedPdf.value) {
    console.error('没有选中的PDF')
    return
  }

  console.log('开始加载Excel数据，sheet:', sheetName, '文件:', excelFileName)

  try {
    const pdfId = selectedPdf.value.id
    const apiUrl = `/api/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/${encodeURIComponent(sheetName)}`
    console.log('请求Excel数据API:', apiUrl)

    const response = await fetch(apiUrl)
    console.log('Excel数据API响应状态:', response.status)

    if (response.ok) {
      const data = await response.json()
      console.log('Excel数据API返回数据:', data)
      excelData.value = data.rows || []
      console.log('解析后的Excel数据行数:', excelData.value.length)
      generateTableColumns(data.rows)
      ElMessage.success(`已加载表格: ${sheetName}`)
    } else {
      const errorData = await response.json().catch(() => ({ error: '未知错误' }))
      console.log('Excel数据API请求失败:', errorData)
      excelData.value = []
      tableColumns.value = []
      ElMessage.warning(`无法加载表格数据: ${errorData.error || '未知错误'}`)
    }
  } catch (error) {
    console.error('加载Excel数据失败:', error)
    throw error
  }
}

// 生成表格列配置
const generateTableColumns = (data) => {
  if (!data || data.length === 0) {
    console.log('没有数据，清空表格列')
    tableColumns.value = []
    return
  }

  // 从第一行数据获取列名
  const firstRow = data[0]
  tableColumns.value = Object.keys(firstRow).map(key => ({
    prop: key,
    label: key,
    width: 120
  }))
  console.log('生成的表格列:', tableColumns.value)
}




// 下载PDF文件
const downloadPdf = async (pdf) => {
  if (!pdf) return

  downloadLoading.value = true
  try {
    let downloadUrl = ''

    if (pdf.id) {
      downloadUrl = `/api/file-by-id/${pdf.id}`
    } else {
      downloadUrl = `/api/file/${encodeURIComponent(pdf.name)}`
    }

    // 创建隐藏的下载链接
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = pdf.name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('开始下载PDF文件')
  } catch (error) {
    console.error('下载PDF失败:', error)
    ElMessage.error('下载PDF失败')
  } finally {
    downloadLoading.value = false
  }
}


</script>

<style scoped>

/* 新增：分析按钮相关样式 */
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-actions {
  flex-shrink: 0;
}

.data-count {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.pdf-list {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.collapse-control {
  padding: 8px 12px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: flex-end;
}

.collapse-btn {
  transform: rotate(45deg);
  transition: transform 0.3s ease;
}

.collapse-btn:hover {
  transform: rotate(45deg) scale(1.1);
}

.loading-state {
  padding: 20px;
  text-align: center;
  color: #909399;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #909399;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.tip {
  font-size: 12px;
  margin-top: 8px;
}

.pdf-items, .sheet-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.pdf-item, .sheet-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  gap: 8px;
  transition: background-color 0.2s;
}

.pdf-item:hover, .sheet-item:hover {
  background: #f5f7fa;
}

.pdf-item.active, .sheet-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.pdf-item:last-child, .sheet-item:last-child {
  border-bottom: none;
}

.pdf-name, .sheet-name {
  flex: 1;
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* PDF预览样式 */
.pdf-preview-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.pdf-viewer {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.pdf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
}

.pdf-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}



.pdf-content {
  flex: 1;
  min-height: 0;
  background: #f8f9fa;
}

.pdf-content iframe {
  display: block;
}

.no-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.no-preview .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.pdf-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  text-align: center;
  padding: 20px;
}

.pdf-placeholder .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

/* 表格列表样式 */

.excel-files-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.excel-file-item {
  margin-bottom: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}

.excel-file-item:last-child {
  margin-bottom: 0;
}

.excel-file-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  gap: 8px;
}

.excel-file-name {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sheet-items {
  background: white;
}

.sheet-item {
  display: flex;
  align-items: center;
  padding: 10px 16px 10px 32px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  gap: 8px;
  transition: background-color 0.2s;
}

.sheet-item:hover {
  background: #f5f7fa;
}

.sheet-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.sheet-item:last-child {
  border-bottom: none;
}

.sheet-name {
  flex: 1;
  font-size: 13px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}



.table-list-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.section-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.section-title {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.table-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* Excel内容样式 */
.excel-content-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.excel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.placeholder .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.excel-table-container {
  flex: 1;
  min-height: 0;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}


.pdf-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sheet-item.current-page {
  background: #fff2e8;
  border-left: 3px solid #ff7d00;
}

.sheet-item.current-page .sheet-name {
  color: #ff7d00;
  font-weight: 600;
}

/* 优化标签显示 */
.sheet-item .el-tag {
  margin-left: auto;
  flex-shrink: 0;
}

</style>