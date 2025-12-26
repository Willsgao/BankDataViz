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
                  @click="toggleFlatMode"
                  :loading="loadingFlat"
                >
                  <el-icon><DataAnalysis /></el-icon>
                  {{ showFlatMode ? '数据二维化' : '数据扁平化' }}
                </el-button>
            </div>


          </div>

          <!-- 修改这里：添加条件渲染和错误处理 -->
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


            <!-- 修改表格显示逻辑 -->
            <div v-else class="handsontable-container">
              <!-- 使用v-show控制显示，避免组件销毁/重建 -->

              <!-- 原始模式：使用v-show隐藏，保持组件实例 -->
              <div v-show="!showFlatMode">
                <HandsontableExcelViewer
                  ref="originalViewer"
                  :excel-data="excelData"
                  :sheet-name="selectedSheet?.name || ''"
                  :pdf-id="selectedPdf?.id"
                  :excel-file-name="selectedExcelFile"
                  :key="`original-${selectedSheet?.name}-${excelData.length}`"
                />
              </div>

              <!-- 扁平化模式：只有有数据时才显示 -->
              <div v-show="showFlatMode && flatData.length > 0">
                <HandsontableExcelViewer
                  ref="flatViewer"
                  :excel-data="flatData"
                  :sheet-name="`扁平化_${selectedSheet?.name || ''}`"
                  :pdf-id="selectedPdf?.id"
                  :excel-file-name="selectedExcelFile"
                  :key="`flat-${selectedSheet?.name}-${flatData.length}`"
                />
              </div>

              <!-- 扁平化加载中的提示 -->
              <div v-if="showFlatMode && flatData.length === 0 && loadingFlat" class="loading-state">
                <el-icon class="is-loading"><Loading /></el-icon>
                正在扁平化数据...
              </div>

              <!-- 扁平化模式下但无数据的提示 -->
              <div v-if="showFlatMode && flatData.length === 0 && !loadingFlat" class="empty-state">
                <el-icon><Grid /></el-icon>
                <p>暂无扁平化数据</p>
                <p class="tip">点击"数据扁平化"按钮生成数据</p>
              </div>
            </div>

          </div>
        </div>

        <!-- 数据分析对话框 -->
        <DataAnalysisDialog
          v-model="showAnalysisDialog"
          :excel-data="excelData"
          :sheet-name="selectedSheet?.name || ''"
        />
      </template>


  </ThreeColumnLayout>
</template>

<script setup>


// 导入 Handsontable Excel 查看器
import HandsontableExcelViewer from '@/components/excel/HandsontableExcelViewer.vue'


import ThreeColumnLayout from '@/layouts/ThreeColumnLayout.vue'
import { Document, Loading, Download, Close, Grid, DataAnalysis } from '@element-plus/icons-vue'
import { getApiUrl, getBackendUrl } from '@/utils/config'
import { ref, inject, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import excelDataCache from '@/utils/excelDataCache'

// 导入数据分析组件
import DataAnalysisDialog from '@/components/analysis/DataAnalysisDialog.vue'


// 从 App.vue 注入搜索数据
const searchResults = inject('searchResults', [])
const isSearching = inject('isSearching', ref(false))

// 新增状态
const selectedPdf = ref(null)
const pdfUrl = ref('')
const downloadLoading = ref(false)
const isMiddleCollapsed = ref(false)

// 当前状态：使用 ref 替代
const showFlatMode = ref(false) // 新增：是否处于扁平化模式
const flatData = ref([]) // 新增：扁平化数据
const flatColumns = ref([]) // 新增：扁平化列配置
const loadingFlat = ref(false) // 新增：扁平化加载状态

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


// 切换扁平化模式
const toggleFlatMode = async () => {
  if (!selectedSheet.value || !selectedPdf.value) {
    ElMessage.warning('请先选择表格')
    return
  }

  if (showFlatMode.value) {
    // 当前是扁平化模式，切换回原始模式
    await switchToOriginalMode()
  } else {
    // 当前是原始模式，切换到扁平化模式
    await switchToFlatMode()
  }
}

// 切换到原始模式
const switchToOriginalMode = async () => {
  console.log('🔄 切换到原始模式')

  const pdfId = selectedPdf.value.id
  const excelFile = selectedExcelFile.value
  const sheetName = selectedSheet.value.name

  // 从缓存获取原始数据
  const originalData = excelDataCache.getOriginalData(pdfId, excelFile, sheetName)

  if (!originalData || originalData.length === 0) {
    console.warn('原始数据缓存为空，重新加载')
    // 重新加载数据
    await loadExcelData(sheetName, excelFile)
    return
  }

  // 显示原始数据
  excelData.value = originalData
  generateTableColumns(originalData)
  showFlatMode.value = false

  ElMessage.success('已切换回原始表格模式')
}

// 切换到扁平化模式
const switchToFlatMode = async () => {
  console.log('🔄 切换到扁平化模式')

  const pdfId = selectedPdf.value.id
  const excelFile = selectedExcelFile.value
  const sheetName = selectedSheet.value.name

  // 检查是否有扁平化数据缓存
  const cachedFlattened = excelDataCache.getFlattenedData(pdfId, excelFile, sheetName)

  if (cachedFlattened && cachedFlattened.length > 0) {
    console.log('📦 使用缓存的扁平化数据')
    // 使用缓存数据
    flatData.value = cachedFlattened
    showFlatMode.value = true
    ElMessage.success('已切换到扁平化模式（使用缓存）')
  } else {
    console.log('🔄 无缓存，调用API生成扁平化数据')
    // 调用API生成扁平化数据
    await convertToFlatData()
  }
}





// 在 script setup 部分添加这个函数
const convertDualHeaderToTable = (dualHeaderData) => {
  if (!dualHeaderData || dualHeaderData.length === 0) {
    return []
  }

  console.log('🔄 转换双表头数据为二维表格')

  const metadata = dualHeaderData[0]?.__metadata || {}
  const horizontalHeaders = metadata.horizontal_headers || []
  const verticalHeaders = metadata.vertical_headers || []
  const topLeftCell = metadata.top_left_cell || ''

  console.log('📋 元数据:', {
    左上角: topLeftCell,
    横向表头数: horizontalHeaders.length,
    纵向表头数: verticalHeaders.length,
    总行数: dualHeaderData.length
  })

  // 查找表头行和数据行
  let headerRow = null
  const dataRows = []

  for (let i = 1; i < dualHeaderData.length; i++) { // 跳过元数据行
    const row = dualHeaderData[i]
    if (row?.__is_first_row) {
      headerRow = row
    } else if (row?.__is_data_row) {
      dataRows.push(row)
    }
  }

  if (!headerRow) {
    console.error('❌ 未找到表头行')
    return []
  }

  // 构建二维表格
  const table = []

  // 第一行：左上角 + 横向表头
  const firstRow = [topLeftCell]
  for (let i = 0; i < horizontalHeaders.length; i++) {
    const headerKey = `H_${i + 1}`
    const value = headerRow[headerKey] || horizontalHeaders[i] || ``
    firstRow.push(value)
  }
  table.push(firstRow)

  // 数据行：纵向表头 + 数据
  dataRows.forEach((dataRow, rowIndex) => {
    const row = []

    // 纵向表头
    const verticalHeader = dataRow.__vertical_header ||
                          verticalHeaders[rowIndex] ||
                          ``
    row.push(verticalHeader)

    // 数据单元格
    for (let i = 0; i < horizontalHeaders.length; i++) {
      const headerKey = `H_${i + 1}`
      const value = dataRow[headerKey] ?? ''
      row.push(value)
    }

    table.push(row)
  })

  console.log('✅ 双表头转换完成:', {
    总行数: table.length,
    总列数: table[0]?.length || 0,
    布局: `(1,1) = ${table[1]?.[1] || '空'}`
  })

  return table
}



// 在convertToFlatData方法中添加重建二维表格的逻辑
const convertToFlatData = async () => {
  if (!selectedSheet.value || !selectedPdf.value) {
    ElMessage.warning('请先选择表格')
    return
  }

  loadingFlat.value = true

  const pdfId = selectedPdf.value.id
  const excelFile = selectedExcelFile.value
  const sheetName = selectedSheet.value.name

  try {
    console.log('🔄 开始数据扁平化处理...')

    // 步骤1：从缓存获取当前sheet的双表头数据
    const currentOriginalData = excelDataCache.getOriginalData(pdfId, excelFile, sheetName)
    if (!currentOriginalData || currentOriginalData.length === 0) {
      throw new Error('原始数据为空，无法转换')
    }

    console.log('📊 从缓存获取的原始数据:', {
      数据类型: typeof currentOriginalData[0],
      总行数: currentOriginalData.length,
      第一行: currentOriginalData[0]
    })

    // 步骤2：重建原始二维表格数据
    const tableData = rebuildTwoDimensionalTable(currentOriginalData)

    if (!tableData || tableData.length === 0) {
      throw new Error('无法重建二维表格数据')
    }

    console.log('✅ 重建的二维表格数据:', {
      行数: tableData.length,
      列数: tableData[0]?.length || 0,
      表格样本: tableData.slice(0, Math.min(3, tableData.length))
    })

    // 步骤3：从表格中提取必要信息用于source_info
    const tableInfo = extractTableInfoFromData(currentOriginalData, tableData)

    // 步骤4：构建请求数据
    const requestData = {
      table_data: tableData,
      source_info: {
        table_name: sheetName,
        bank_name: "中国建设银行",
        page_num: tableInfo.pageNum || extractPageFromSheetName(sheetName) || 1,
        default_unit: tableInfo.defaultUnit || "",
        default_currency: tableInfo.defaultCurrency || "人民币",
        default_report_period: tableInfo.reportPeriod || "",
        entity: "本集团"
      }
    }

    console.log('📤 发送扁平化请求数据:', requestData)

    // 步骤5：调用扁平化API
    const response = await fetch(getApiUrl('/excel-flatten'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData)
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }))
      throw new Error(errorData.error || 'API调用失败')
    }

    const result = await response.json()
    console.log('✅ API响应成功:', result)

    // 检查返回格式
    if (result.rows && Array.isArray(result.rows)) {
        console.log('📊 接收到双表头格式数据:', {
            总行数: result.rows.length,
            格式: '双表头格式'
        })

        // 保存原始的双表头格式数据
        excelDataCache.setFlattenedData(pdfId, excelFile, sheetName, result.rows)

        // 显示扁平化数据（直接使用rows，这是双表头格式）
        flatData.value = result.rows
        showFlatMode.value = true

        ElMessage.success(`数据扁平化成功，生成 ${result.rows.length} 行数据`)
    } else if (result.success && result.long_format_data) {
        // 兼容旧格式
        console.log('📊 接收到旧格式长格式数据')
        excelDataCache.setFlattenedData(pdfId, excelFile, sheetName, result.long_format_data)
        flatData.value = result.long_format_data
        showFlatMode.value = true
        ElMessage.success('数据扁平化成功')
    } else {
        throw new Error(result.error || '转换失败')
    }

  } catch (error) {
    console.error('数据扁平化失败:', error)
    ElMessage.error(`转换失败: ${error.message}`)

    // 重置状态
    showFlatMode.value = false
    flatData.value = []
  } finally {
    loadingFlat.value = false
    const currentSheet = excelDataCache.getCurrentSheet()
    if (currentSheet) {
      excelDataCache.setFlatteningState(currentSheet.pdfId, currentSheet.excelFile, currentSheet.sheetName, false)
    }
  }
}

// ================ 新增：关键的重建函数 ================

/**
 * 从双表头数据重建原始二维表格
 * @param {Array} dualHeaderData 双表头格式的数据
 * @returns {Array} 二维表格数据
 */
const rebuildTwoDimensionalTable = (dualHeaderData) => {
  if (!dualHeaderData || dualHeaderData.length === 0) {
    console.error('❌ 数据为空，无法重建')
    return []
  }

  console.log('🔧 开始重建二维表格...')

  // 打印输入数据以便调试
  console.log('📥 输入数据格式检查:')
  dualHeaderData.forEach((row, idx) => {
    if (idx < 3) { // 只打印前3行
      console.log(`  行${idx}:`, {
        类型: row.__metadata ? '元数据' : row.__is_first_row ? '表头行' : row.__is_data_row ? '数据行' : '其他',
        行表头: row.__vertical_header,
        H_1: row.H_1,
        H_2: row.H_2
      })
    }
  })

  // 步骤1：查找元数据行
  const metadataRow = dualHeaderData.find(row => row?.__metadata)
  const metadata = metadataRow?.__metadata || {}

  const hasDualHeaders = metadata.has_dual_headers || false
  const horizontalHeaders = metadata.horizontal_headers || []
  const verticalHeaders = metadata.vertical_headers || []
  const topLeftCell = metadata.top_left_cell || ''

  console.log('📋 元数据信息:', {
    hasDualHeaders,
    左上角单元格: topLeftCell,
    横向表头: horizontalHeaders,
    纵向表头: verticalHeaders
  })

  // 步骤2：查找表头行和数据行
  const headerRow = dualHeaderData.find(row => row?.__is_first_row)
  const dataRows = dualHeaderData.filter(row => row?.__is_data_row)

  if (!headerRow) {
    console.error('❌ 未找到表头行')
    return []
  }

  console.log('📋 找到:', {
    表头行: !!headerRow,
    数据行数: dataRows.length
  })

  // 步骤3：重建二维表格
  const table = []

  if (hasDualHeaders) {
    // 情况1：双表头结构
    console.log('🔄 处理双表头结构...')

    // 第一行：左上角单元格 + 横向表头
    const firstRow = [topLeftCell || '']

    // 从headerRow获取横向表头值
    for (let i = 0; i < horizontalHeaders.length; i++) {
      const headerKey = `H_${i + 1}`
      const headerValue = headerRow[headerKey] !== undefined ? headerRow[headerKey] : horizontalHeaders[i] || ``
      firstRow.push(String(headerValue))
    }
    table.push(firstRow)

    console.log('📊 重建的表头行:', firstRow)

    // 数据行：纵向表头 + 数据
    dataRows.forEach((dataRow, rowIndex) => {
      const row = []

      // 纵向表头 - 直接使用__vertical_header
      const verticalHeader = dataRow.__vertical_header || ''
      row.push(String(verticalHeader))

      console.log(`📊 处理第${rowIndex+1}行，行表头: "${verticalHeader}"`)

      // 数据单元格
      for (let i = 0; i < horizontalHeaders.length; i++) {
        const headerKey = `H_${i + 1}`
        const cellValue = dataRow[headerKey] !== undefined ? dataRow[headerKey] : ''
        row.push(cellValue)
      }

      table.push(row)
    })
  }

  console.log('✅ 重建完成:', {
    总行数: table.length,
    总列数: table[0]?.length || 0,
    第一行: table[0],
    第一列前几个值: table.slice(1, 6).map(row => row[0])
  })

  // 检查是否有"列标记"行
  const columnMarkRowIndex = table.findIndex(row => row[0] && String(row[0]).includes('列标记'))
  if (columnMarkRowIndex >= 0) {
    console.log(`✅ 找到列标记行: 第${columnMarkRowIndex}行，内容: ${table[columnMarkRowIndex]}`)
  }

  // 检查是否有"行标记"列
  if (table.length > 0) {
    const firstRow = table[0]
    const rowMarkColumnIndex = firstRow.findIndex(cell => cell && String(cell).includes('行标记'))
    if (rowMarkColumnIndex >= 0) {
      console.log(`✅ 找到行标记列: 第${rowMarkColumnIndex}列，表头: "${firstRow[rowMarkColumnIndex]}"`)
    }
  }

  return table
}


/**
 * 从数据中提取表格信息
 */
const extractTableInfoFromData = (dualHeaderData, tableData) => {
  const info = {
    pageNum: 1,
    defaultUnit: "",
    defaultCurrency: "人民币",
    reportPeriod: ""
  }

  // 尝试从表头提取信息
  if (tableData.length > 0 && tableData[0].length > 0) {
    const firstRow = tableData[0]

    // 检查是否包含单位信息
    const unitKeywords = ['万元', '亿元', '元', '%', '百分比']
    firstRow.forEach(cell => {
      const cellStr = String(cell)
      unitKeywords.forEach(keyword => {
        if (cellStr.includes(keyword)) {
          if (keyword === '%' || keyword === '百分比') {
            info.defaultUnit = "%"
          } else {
            info.defaultUnit = keyword
          }
        }
      })
    })

    // 检查是否包含报告期信息
    const periodPatterns = [
      /20\d{2}年/, /20\d{2}年度/, /20\d{2}年.*季度/,
      /第[一二三四1-4]季度/, /Q[1-4]/, /上半年/, /下半年/
    ]

    firstRow.forEach(cell => {
      const cellStr = String(cell)
      periodPatterns.forEach(pattern => {
        const match = cellStr.match(pattern)
        if (match) {
          info.reportPeriod = match[0]
        }
      })
    })
  }

  console.log('📋 提取的表格信息:', info)
  return info
}


// 将二维数组转换为Handsontable格式
const convertToHandsontableFormat = (twoDArray) => {
  if (!Array.isArray(twoDArray) || twoDArray.length === 0) {
    return []
  }

  // 第一行作为表头
  const headers = twoDArray[0]

  // 其余行作为数据
  return twoDArray.slice(1).map(row => {
    const obj = {}
    headers.forEach((header, index) => {
      obj[header] = row[index] || ''
    })
    return obj
  })
}

// 生成扁平化列配置
const generateFlatColumns = (firstRow) => {
  if (!Array.isArray(firstRow)) {
    return []
  }

  return firstRow.map((header, index) => ({
    prop: header,
    label: header || `列${index + 1}`,
    width: 120
  }))
}

// 监听原始数据变化，重置扁平化状态
watch(excelData, (newData) => {
  if (newData.length === 0) {
    showFlatMode.value = false
    flatData.value = []
  }
})

// 监听Sheet切换，重置扁平化状态
watch(selectedSheet, () => {
  showFlatMode.value = false
  flatData.value = []
})


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
      // const fileResponse = await fetch(`/api/search-pdf?keyword=${encodeURIComponent(pdf.name)}`)
      const fileResponse = await fetch(getApiUrl(`/search-pdf?keyword=${encodeURIComponent(pdf.name)}`))

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
      // pdfUrl.value = `/api/file-by-id/${fileId}`
      pdfUrl.value = getBackendUrl(`/api/file-by-id/${fileId}`)
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
    // const response = await fetch(`/api/excel-sheets/${pdfId}`)
    const response = await fetch(getApiUrl(`/excel-sheets/${pdfId}`))
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
    // const directoryResponse = await fetch(`/api/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/目录`)
    const directoryResponse = await fetch(getApiUrl(`/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/目录`))

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
        // const response = await fetch(`/api/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/${encodeURIComponent(classItem.sheetName)}`)
        const response = await fetch(getApiUrl(`/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/${encodeURIComponent(classItem.sheetName)}`))
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

    const apiUrl = getApiUrl(`/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/${encodeURIComponent(sheetName)}`)
    console.log('请求Excel数据API:', apiUrl)

    const response = await fetch(apiUrl)
    console.log('Excel数据API响应状态:', response.status)

    if (response.ok) {
      const data = await response.json()
      console.log('Excel数据API返回数据:', data)

      // 保存到缓存
      excelDataCache.setOriginalData(pdfId, excelFileName, sheetName, data.rows || [])

      // 设置当前sheet
      excelDataCache.setCurrentSheet(pdfId, excelFileName, sheetName)

      // 如果是目录sheet，特殊处理
      if (sheetName === '目录') {
        await loadAllClassData(excelFileName)
      } else {
        excelData.value = data.rows || []
        generateTableColumns(data.rows)
      }

      // 重置扁平化状态
      showFlatMode.value = false
      flatData.value = []

      // 更新按钮文本（根据缓存状态）
      updateFlatButtonText(pdfId, excelFileName, sheetName)

      ElMessage.success(`已加载表格: ${sheetName}`)

      // 调试输出
      excelDataCache.debug()
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

// 更新扁平化按钮文本
const updateFlatButtonText = (pdfId, excelFile, sheetName) => {
  const hasFlattened = excelDataCache.hasFlattenedData(pdfId, excelFile, sheetName)
  // 这个信息可以在模板中使用，但现在我们保持现有逻辑
  console.log(`扁平化缓存状态: ${hasFlattened ? '有缓存' : '无缓存'}`)
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


// 在 script setup 中添加这个函数
const getPageFromSheetName = (sheetName) => {
  const pageMatch = sheetName.match(/P(\d+)_/)
  if (pageMatch && pageMatch[1]) {
    return parseInt(pageMatch[1])
  }
  return null
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
  width: 100%;
  height: 100%;
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

/* Handsontable容器样式 - 修复 */
.handsontable-container {
  height: 100%;
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

.handsontable-container > div {
  height: 100%;
  width: 100%;
}

/* 确保隐藏的组件不占位 */
.handsontable-container > div[style*="display: none"] {
  display: none !important;
}

/* 扁平化加载中的提示 */
.handsontable-container .loading-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.95);
  z-index: 10;
  color: #606266;
  gap: 12px;
}

.handsontable-container .loading-state .el-icon {
  font-size: 32px;
  color: #409eff;
}

/* 扁平化模式下但无数据的提示 */
.handsontable-container .empty-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: white;
  z-index: 10;
  color: #909399;
  text-align: center;
  padding: 20px;
  gap: 12px;
}

.handsontable-container .empty-state .el-icon {
  font-size: 48px;
  margin-bottom: 8px;
  opacity: 0.5;
}

.handsontable-container .empty-state .tip {
  font-size: 12px;
  color: #c0c4cc;
}
</style>