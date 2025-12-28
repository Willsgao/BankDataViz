
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
            <h3>表格内容</h3>
            <div v-if="selectedSheet" class="header-info">
              <el-tag type="primary">{{ selectedSheet.name }}</el-tag>
            </div>
          </div>

          <div class="header-actions">
            <!-- 第一行：扁平化按钮 -->
            <div class="action-row">
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


            <el-button v-if="isDev" size="mini" type="warning" @click="runComprehensiveTest">
              全面测试
            </el-button>

            </div>

            <!-- 第二行：保存和恢复按钮组 -->
            <div class="action-row">
              <el-button-group size="small" class="save-buttons">
                <!-- 草稿保存按钮 -->
                <el-button
                  type="warning"
                  :disabled="!selectedSheet || !hasUnsavedChangesInCurrentTable()"
                  @click="saveData('draft')"
                  :loading="saving && saveType === 'draft'"
                >
                  <el-icon><Document /></el-icon>
                  保存草稿
                </el-button>

                <!-- 最终保存按钮 -->
                <el-button
                  type="success"
                  :disabled="!selectedSheet || !hasUnsavedChangesInCurrentTable()"
                  @click="saveData('final')"
                  :loading="saving && saveType === 'final'"
                >
                  <el-icon><Check /></el-icon>
                  最终保存
                </el-button>

                <!-- 恢复按钮 -->
                <el-button
                  type="info"
                  :disabled="!selectedSheet"
                  @click="restoreUnsavedData"
                >
                  <el-icon><Refresh /></el-icon>
                  恢复修改
                </el-button>
              </el-button-group>
            </div>
          </div>
        </div>

        <!-- ============ 新增：保存状态栏 ============ -->
        <div v-if="selectedSheet" class="save-status-bar">
          <div class="save-info">
            <el-tag :type="saveStatus.type" size="small">
              <el-icon><Timer /></el-icon>
              {{ saveStatus.text }}
            </el-tag>

            <span class="change-count" v-if="modifiedCellsCount > 0">
              已修改 {{ modifiedCellsCount }} 个单元格
            </span>

            <span class="last-save">
              最后保存: {{ formatTime(lastSaveTime) }}
            </span>
          </div>
        </div>

        <!-- Excel内容区域 -->
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

          <!-- 表格显示逻辑 -->
          <div v-else class="handsontable-container">
            <!-- 原始模式 -->
            <div v-show="!showFlatMode">
              <HandsontableExcelViewer
                ref="originalViewer"
                :excel-data="excelData"
                :sheet-name="selectedSheet?.name || ''"
                :pdf-id="selectedPdf?.id"
                :excel-file-name="selectedExcelFile"
                :key="`original-${selectedSheet?.name}-${excelData.length}`"
                @cell-changed="handleCellChanged"
                @data-changed="handleDataChanged"
              />
            </div>

            <!-- 扁平化模式 -->
            <div v-show="showFlatMode && flatData.length > 0">
              <HandsontableExcelViewer
                ref="flatViewer"
                :excel-data="flatData"
                :sheet-name="`扁平化_${selectedSheet?.name || ''}`"
                :pdf-id="selectedPdf?.id"
                :excel-file-name="selectedExcelFile"
                :key="`flat-${selectedSheet?.name}-${flatData.length}`"
                @cell-changed="handleCellChanged"
                @data-changed="handleDataChanged"
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
    </template>


  </ThreeColumnLayout>
</template>


<script setup>
// 1. 导入部分
import HandsontableExcelViewer from '@/components/excel/HandsontableExcelViewer.vue'
import ThreeColumnLayout from '@/layouts/ThreeColumnLayout.vue'
import {
  Download, Edit, Check, Warning, DataAnalysis, Close, More, Menu, Document,
  Grid, InfoFilled, Position, CopyDocument, Lock, Calendar, Finished, MagicStick, Bug,
  Refresh, Timer  // 确保 DataAnalysis 也在导入列表中
} from '@element-plus/icons-vue'
import { getApiUrl, getBackendUrl } from '@/utils/config'
import { ref, inject, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import excelDataCache from '@/utils/excelDataCache'
import DataAnalysisDialog from '@/components/analysis/DataAnalysisDialog.vue'

// ============ 新增导入 ============
import dataManager from '@/utils/dataManager.js'  // 导入数据管理器
import sheetStateManager, { SheetStateManager } from '@/utils/SheetStateManager.js'


// 2. 注入搜索数据
const searchResults = inject('searchResults', [])
const isSearching = inject('isSearching', ref(false))

// 3. 定义所有状态变量
const selectedPdf = ref(null)
const pdfUrl = ref('')
const downloadLoading = ref(false)
const isMiddleCollapsed = ref(false)
const showFlatMode = ref(false)
const flatData = ref([])
const loadingFlat = ref(false)
const sheetList = ref([])
const excelFiles = ref([])
const selectedSheet = ref(null)
const selectedExcelFile = ref('')
const excelData = ref([])
const tableColumns = ref([])
const loadingSheets = ref(false)
const loadingExcel = ref(false)
const showAnalysisDialog = ref(false)
const currentPage = ref(1)
const totalPages = ref(0)
const pdfIframe = ref(null)

const currentTableMode = ref('original')

// ============ 新增状态变量 ============
const saving = ref(false)  // 保存中状态
const saveType = ref('')   // 保存类型：draft/temp/final
const lastSaveTime = ref(null)  // 最后保存时间
const saveStatus = ref({  // 保存状态显示
  type: 'info',
  text: '未修改'
})

// 4. 计算属性
const filteredPdfCount = computed(() => searchResults.value.length)
const tableCount = computed(() => {
  return excelFiles.value.reduce((total, file) => total + file.sheets.length, 0)
})


const originalViewer = ref(null)
const flatViewer = ref(null)

// . 添加一个全局状态来追踪修改
const hasGlobalChanges = ref(false)
const globalModifiedCount = ref(0)

// . 修改 hasChanges 计算属性
const hasChanges = computed(() => {
  return globalModifiedCount.value > 0
})

const modifiedCellsCount = ref(0)

const handleCellChanged = (cellInfo) => {
  console.log('📥 收到单元格修改:', {
    row: cellInfo.row,
    col: cellInfo.col,
    当前显示的表: showFlatMode.value ? '扁平化表' : '原始表'
  });

  if (!cellInfo.isEditMode) {
    console.log('⏸️ 非编辑模式，忽略')
    return
  }

  // 关键：根据当前显示的表类型来记录
  const tableType = showFlatMode.value ? 'flattened' : 'original'

  // 记录到状态管理器
  const recordResult = sheetStateManager.recordCellChange(
    cellInfo.row,
    cellInfo.col,
    cellInfo.oldValue || '',
    cellInfo.newValue,
    tableType
  )

  if (recordResult) {
    // 立即更新UI状态
    updateSaveStatus()

    // 立即获取当前查看器并标记单元格
    setTimeout(() => {
      const viewerRef = showFlatMode.value ? flatViewer.value : originalViewer.value
      if (viewerRef && viewerRef.markSavedCells) {
        const cellKey = `${cellInfo.row},${cellInfo.col}`
        // 标记为未保存（红色）
        viewerRef.markSavedCells([cellKey])
        console.log(`🎨 单元格标记: [${cellInfo.row},${cellInfo.col}] 为未保存`)
      }
    }, 100)
  }
}


const handleDataChanged = (dataInfo) => {
  console.log('📥 收到批量修改:', {
    totalChanges: dataInfo.totalChanges,
    isEditMode: dataInfo.isEditMode,
    当前显示的表: showFlatMode.value ? '扁平化表' : '原始表',
    事件中的表类型: dataInfo.tableType || 'unknown'
  })

  // 关键：检查表类型是否匹配
  const currentTableType = showFlatMode.value ? 'flattened' : 'original'
  const eventTableType = dataInfo.tableType || 'original'

  if (currentTableType !== eventTableType) {
    console.warn(`⚠️ 表类型不匹配: 当前${currentTableType}, 事件${eventTableType}，忽略`)
    return
  }

  if (!dataInfo.isEditMode || !dataInfo.hasChanges) {
    console.log('⏸️ 非编辑模式或无修改，忽略')
    return
  }

  // 确保有选中的 sheet
  if (!selectedSheet.value || !selectedPdf.value) {
    console.warn('❌ 没有选中的 sheet 或 pdf，忽略修改')
    return
  }

  initDataManagerContext()

  // 根据当前显示的表类型记录
  const tableType = showFlatMode.value ? 'flattened' : 'original'

  if (dataInfo.allChanges && dataInfo.allChanges.length > 0) {
    console.log(`🔄 批量记录 ${dataInfo.allChanges.length} 个修改（${tableType}表）`)

    dataInfo.allChanges.forEach((change) => {
      // ============ 原有逻辑 ============
      dataManager.recordCellChange(
        change.row,
        change.col,
        change.oldValue || '',
        change.newValue,
        tableType
      )

      // ============ 新增：记录到状态管理器 ============
      sheetStateManager.recordCellChange(
        change.row,
        change.col,
        change.oldValue || '',
        change.newValue,
        tableType
      )
    })
  }

  updateSaveStatus()
}


const handleEditStatusChanged = (statusInfo) => {
  console.log('🎛️ [ThreeColumnPage] 编辑状态变化:', statusInfo)
  // 可以在这里更新UI显示，但不影响核心逻辑
}




// 5. 定义方法（按照原有顺序，只修改需要的方法）
const toggleMiddleCollapse = () => {
  isMiddleCollapsed.value = !isMiddleCollapsed.value
}

// ============ 原有方法保持顺序 ============
const getPdfUrlWithPage = () => {
  if (!pdfUrl.value) return ''
  return `${pdfUrl.value}#page=${currentPage.value}`
}

const extractPageFromSheetName = (sheetName) => {
  const pageMatch = sheetName.match(/P(\d+)_/)
  if (pageMatch && pageMatch[1]) {
    const pageNum = parseInt(pageMatch[1])
    if (pageNum > 0) {
      currentPage.value = pageNum
      setTimeout(() => {
        updatePdfPage()
      }, 100)
      return pageNum
    }
  }
  return null
}


const selectSheet = async (sheet, excelFileName) => {
  console.log('🔄 选择sheet:', {
    sheet名称: sheet.name,
    excel文件: excelFileName,
    当前PDF: selectedPdf.value?.id
  })

  // ============ 第1步：重置所有状态 ============
  // 1.1 更新UI状态
  selectedSheet.value = { ...sheet, excel_file: excelFileName }
  selectedExcelFile.value = excelFileName

  // 1.2 重置显示模式为原始表
  currentTableMode.value = 'original'
  window.currentTableMode = 'original'
  showFlatMode.value = false
  flatData.value = []
  console.log('📊 显示模式已重置为原始表')

  // ============ 第2步：设置状态管理器上下文 ============
  if (!selectedPdf.value) {
    console.error('❌ 无法设置上下文：没有选中的PDF')
    ElMessage.error('请先选择PDF文件')
    return
  }

  // 2.1 设置状态管理器上下文
  sheetStateManager.setActiveContext(
    selectedPdf.value.id,
    excelFileName,
    sheet.name,
    'original'  // 新sheet总是从原始表开始
  )

  // 2.2 检查该sheet是否有历史修改记录（只做检查，不自动恢复）
  const sheetState = sheetStateManager.getActiveSheetState()
  if (sheetState) {
    const originalUnsaved = sheetState.stats.original.unsavedCount
    const flattenedUnsaved = sheetState.stats.flattened.unsavedCount

    if (originalUnsaved > 0 || flattenedUnsaved > 0) {
      console.log('📝 检测到历史修改记录:', {
        原始表未保存: originalUnsaved,
        扁平化表未保存: flattenedUnsaved
      })
      // 只在控制台提示，不自动恢复
      // 用户可以通过"恢复修改"按钮手动恢复
    }
  }

  // ============ 第3步：设置原有数据管理器上下文 ============
  // （保持原有逻辑，后续会逐步迁移到新状态管理器）
  initDataManagerContext()
  console.log('🔗 原有数据管理器上下文已设置')

  // ============ 第4步：处理PDF页面跳转 ============
  const pageNum = extractPageFromSheetName(sheet.name)
  if (pageNum) {
    console.log(`📄 从sheet名称提取到页码: ${pageNum}`)
    // PDF页面跳转会在数据加载完成后触发
  }

  // ============ 第5步：加载表格数据 ============
  loadingExcel.value = true

  try {
    // 5.1 根据sheet类型加载数据
    if (sheet.name === '目录') {
      console.log('📁 加载目录数据...')
      await loadAllClassData(excelFileName)

      // 保存目录数据到状态管理器
      if (excelData.value.length > 0) {
        sheetStateManager.setData('original', excelData.value)
        console.log(`✅ 目录数据已保存到状态管理器: ${excelData.value.length}行`)
      }
    } else {
      console.log(`📊 加载普通sheet数据: ${sheet.name}`)
      await loadExcelData(sheet.name, excelFileName)

      // excelData已在loadExcelData中更新并保存到状态管理器
    }

    // ============ 第6步：加载完成后处理 ============
    console.log('✅ 数据加载完成，开始后续处理...')

    // 6.1 更新保存状态显示
    updateSaveStatus()

    // 6.2 检查状态管理器中的未保存修改
    const context = sheetStateManager.getActiveContext()
    if (context) {
      const unsavedModifications = sheetStateManager.getModifications(context.tableType)
        .filter(mod => !mod.saved)

      if (unsavedModifications.length > 0) {
        console.log('💡 检测到未保存修改，等待用户手动恢复:', {
          表类型: context.tableType,
          未保存数: unsavedModifications.length
        })

        // 可选：显示一个非模态提示，告诉用户有修改可以恢复
        setTimeout(() => {
          ElMessage.info({
            message: `检测到 ${unsavedModifications.length} 处未保存修改，可点击"恢复修改"按钮恢复`,
            duration: 5000,
            showClose: true
          })
        }, 1000)
      }
    }

    // 6.3 检查原有数据管理器中的修改记录（保持兼容）
    const originalChanges = await dataManager.getChangesByTableType('original')
    const flatChanges = await dataManager.getChangesByTableType('flat')

    if (originalChanges.length > 0 || flatChanges.length > 0) {
      console.log('💡 原有数据管理器检测到未保存修改:', {
        原始表: originalChanges.length,
        扁平化表: flatChanges.length
      })

      // 如果有修改，在控制台提示用户，但不自动弹窗
      // 用户可以通过"恢复修改"按钮手动恢复
    }

    // 6.4 显示成功消息
    ElMessage.success(`已加载表格: ${sheet.name}`)

    // 6.5 如果有PDF页码，跳转
    if (pageNum && pageNum !== currentPage.value) {
      setTimeout(() => {
        currentPage.value = pageNum
        updatePdfPage()
        console.log(`🎯 PDF已跳转到第 ${pageNum} 页`)
        ElMessage.info(`PDF已跳转到第 ${pageNum} 页`)
      }, 300)
    }



  } catch (error) {
    console.error('❌ 加载表格数据失败:', error)
    ElMessage.error(`加载表格数据失败: ${error.message}`)

    // 重置数据
    excelData.value = []
    tableColumns.value = []
    flatData.value = []

    // 重置状态管理器数据
    if (sheetStateManager.getActiveContext()?.sheetName === sheet.name) {
      sheetStateManager.setData('original', [])
      sheetStateManager.setData('flattened', [])
    }

  } finally {
    loadingExcel.value = false
    console.log('🏁 selectSheet 流程结束')
  }
}



// 修改 toggleFlatMode 方法
const toggleFlatMode = async () => {
  if (!selectedSheet.value || !selectedPdf.value) {
    ElMessage.warning('请先选择表格')
    return
  }

  // 更新模式状态
  if (showFlatMode.value) {
    // 切换到原始模式
    currentTableMode.value = 'original'
    window.currentTableMode = 'original'

    // ✅ 更新状态管理器上下文
    sheetStateManager.setActiveContext(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name,
      'original'
    )

    await switchToOriginalMode()
  } else {
    // 切换到扁平化模式
    currentTableMode.value = 'flat'
    window.currentTableMode = 'flat'

    // ✅ 更新状态管理器上下文
    sheetStateManager.setActiveContext(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name,
      'flattened'
    )

    const cachedData = await getCachedFlattenedData()

    if (cachedData && cachedData.length > 0) {
      flatData.value = cachedData
      showFlatMode.value = true
      ElMessage.success('已切换到扁平化模式')
    } else {
      await switchToFlatMode()
    }
  }

  console.log('🔄 表格模式切换:', {
    新模式: currentTableMode.value,
    显示扁平化: showFlatMode.value
  })
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

// 修改 switchToFlatMode 方法
const switchToFlatMode = async () => {
  console.log('🔄 切换到扁平化模式')

  const pdfId = selectedPdf.value.id
  const excelFile = selectedExcelFile.value
  const sheetName = selectedSheet.value.name

  const cachedFlattened = excelDataCache.getFlattenedData(pdfId, excelFile, sheetName)

  if (cachedFlattened && cachedFlattened.length > 0) {
    console.log('📦 使用缓存的扁平化数据')
    flatData.value = cachedFlattened
    showFlatMode.value = true
    ElMessage.success('已切换到扁平化模式（使用缓存）')
  } else {
    console.log('🔄 无缓存，调用API生成扁平化数据')
    await convertToFlatData()
  }
}


// 调试方法
const debugDataManager = () => {
  console.log('=== DataManager 状态调试 ===')
  console.log('1. dataManager 实例:', dataManager)
  console.log('2. 当前上下文:', dataManager.currentContext)
  console.log('3. 修改记录:', dataManager.modifiedCells)
  console.log('4. 修改数量:', dataManager.getChangeCount())
  console.log('5. 是否有未保存修改:', dataManager.hasUnsavedChanges())

  // 模拟一个单元格修改
  console.log('6. 模拟记录一个修改...')
  dataManager.recordCellChange(0, 0, '旧值', '新值')
  console.log('   模拟后修改数量:', dataManager.getChangeCount())
  console.log('=== 调试结束 ===')

  // 显示弹窗
  ElMessageBox.alert(
    `DataManager状态:<br/>
     上下文PDF: ${dataManager.currentContext.pdfId}<br/>
     上下文Sheet: ${dataManager.currentContext.sheetName}<br/>
     修改数量: ${dataManager.getChangeCount()}<br/>
     修改记录: ${dataManager.modifiedCells.size}<br/>
     选中PDF: ${selectedPdf.value?.id}<br/>
     选中Sheet: ${selectedSheet.value?.name}`,
    'DataManager调试'
  )
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

        // 保存原始的双表头格式数据到内存缓存
        excelDataCache.setFlattenedData(pdfId, excelFile, sheetName, result.rows)

        // ============ 新增：缓存到 IndexedDB ============
        // 设置数据管理器上下文
        dataManager.setContext({
          pdfId: pdfId,
          excelFile: excelFile,
          sheetName: sheetName
        })

        // 缓存扁平化数据到 IndexedDB
        try {
          await dataManager.saveFlattenedData(result.rows, currentOriginalData)
          console.log('📦 扁平化数据已缓存到 IndexedDB')
        } catch (cacheError) {
          console.warn('⚠️ 缓存到 IndexedDB 失败:', cacheError)
          // 缓存失败不影响主要功能，只记录警告
        }

        // ✅ 新增：保存扁平化数据到状态管理器
        const currentContext = sheetStateManager.getActiveContext()
        if (currentContext &&
            currentContext.pdfId === pdfId &&
            currentContext.excelFile === excelFile &&
            currentContext.sheetName === sheetName) {
          sheetStateManager.setData('flattened', result.rows)
          console.log(`📦 扁平化数据已保存到状态管理器: ${result.rows.length}行`)
        }

        // 显示扁平化数据（直接使用rows，这是双表头格式）
        flatData.value = result.rows
        showFlatMode.value = true

        ElMessage.success(`数据扁平化成功，生成 ${result.rows.length} 行数据`)

    } else if (result.success && result.long_format_data) {
        // 兼容旧格式
        console.log('📊 接收到旧格式长格式数据')

        // 保存到内存缓存
        excelDataCache.setFlattenedData(pdfId, excelFile, sheetName, result.long_format_data)

        // ============ 新增：缓存到 IndexedDB ============
        // 设置数据管理器上下文
        dataManager.setContext({
          pdfId: pdfId,
          excelFile: excelFile,
          sheetName: sheetName
        })

        // 缓存扁平化数据到 IndexedDB
        try {
          await dataManager.saveFlattenedData(result.long_format_data, currentOriginalData)
          console.log('📦 扁平化数据已缓存到 IndexedDB')
        } catch (cacheError) {
          console.warn('⚠️ 缓存到 IndexedDB 失败:', cacheError)
        }

        // ✅ 新增：保存扁平化数据到状态管理器
        const currentContext = sheetStateManager.getActiveContext()
        if (currentContext &&
            currentContext.pdfId === pdfId &&
            currentContext.excelFile === excelFile &&
            currentContext.sheetName === sheetName) {
          sheetStateManager.setData('flattened', result.long_format_data)
          console.log(`📦 扁平化数据已保存到状态管理器: ${result.long_format_data.length}行`)
        }

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

// 保持原有的 rebuildTwoDimensionalTable、extractTableInfoFromData 等方法...
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


// ============ 新增方法（放在原有方法之后）============
/**
 * 格式化时间显示
 */
const formatTime = (timestamp) => {
  if (!timestamp) return '从未保存'
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * 初始化数据管理器上下文
 */
// 修改 initDataManagerContext 函数
const initDataManagerContext = () => {
  console.log('🔍 initDataManagerContext 被调用，检查参数:')
  console.log('   selectedPdf.value:', selectedPdf.value)
  console.log('   selectedSheet.value:', selectedSheet.value)
  console.log('   selectedExcelFile.value:', selectedExcelFile.value)

  // 检查是否有必要的参数
  if (!selectedPdf.value) {
    console.warn('❌ 缺少 selectedPdf')
    return
  }

  if (!selectedSheet.value) {
    console.warn('❌ 缺少 selectedSheet')
    return
  }

  if (!selectedExcelFile.value) {
    console.warn('❌ 缺少 selectedExcelFile')
    return
  }

  // 确保有所有必要的数据
  const context = {
    pdfId: selectedPdf.value.id,
    excelFile: selectedExcelFile.value,
    sheetName: selectedSheet.value.name,
    sessionId: null
  }

  console.log('✅ 设置上下文:', context)
  dataManager.setContext(context)

  // 验证设置是否成功
  setTimeout(() => {
    console.log('🔍 验证上下文设置:')
    console.log('   当前manager上下文:', dataManager.currentContext)
    console.log('   PDF ID匹配:', dataManager.currentContext.pdfId === selectedPdf.value.id)
    console.log('   Sheet匹配:', dataManager.currentContext.sheetName === selectedSheet.value.name)
  }, 100)
}

const updateSaveStatus = () => {
  // 如果没有选中sheet，显示默认状态
  if (!selectedSheet.value || !selectedPdf.value) {
    saveStatus.value = {
      type: 'info',
      text: '请选择表格'
    };
    modifiedCellsCount.value = 0;
    return;
  }

  const context = sheetStateManager.getActiveContext();
  if (!context) {
    saveStatus.value = {
      type: 'info',
      text: '状态未初始化'
    };
    return;
  }

  // 获取当前表类型的修改统计
  const tableType = context.tableType || 'original';
  const stats = sheetStateManager.getModificationStats();

  if (!stats) {
    saveStatus.value = {
      type: 'info',
      text: '加载中...'
    };
    return;
  }

  const tableStats = stats[tableType];
  const hasUnsaved = tableStats.unsaved > 0;
  const hasSaved = tableStats.saved > 0;

  // 更新全局修改计数（用于保存按钮）
  modifiedCellsCount.value = tableStats.unsaved;

  // 根据状态显示不同的消息
  if (!hasUnsaved && !hasSaved) {
    saveStatus.value = {
      type: 'info',
      text: '未修改'
    };
  } else if (hasUnsaved) {
    saveStatus.value = {
      type: 'warning',
      text: `${tableStats.unsaved}个单元格未保存`
    };
  } else if (hasSaved) {
    saveStatus.value = {
      type: 'success',
      text: `已保存 (${tableStats.saved}处修改)`
    };
  }

  console.log('📊 保存状态更新:', {
    表类型: tableType,
    未保存: tableStats.unsaved,
    已保存: tableStats.saved,
    状态: saveStatus.value.text
  });
}


const testStateSync = () => {
  console.log('=== 状态同步测试 ===')

  // 1. 测试当前上下文
  const context = sheetStateManager.getActiveContext()
  console.log('当前上下文:', context)

  // 2. 测试修改计数
  const originalUnsaved = sheetStateManager.getUnsavedChangesCount('original')
  const flattenedUnsaved = sheetStateManager.getUnsavedChangesCount('flattened')
  console.log('未保存修改:', {
    原始表: originalUnsaved,
    扁平化表: flattenedUnsaved,
    总计: originalUnsaved + flattenedUnsaved
  })

  // 3. 测试保存按钮状态
  const canSave = hasUnsavedChangesInCurrentTable()
  console.log('保存按钮是否可用:', canSave)

  // 4. 测试保存状态显示
  console.log('保存状态显示:', saveStatus.value)

  // 5. 完整调试信息
  sheetStateManager.debugState()

  ElMessage.info('状态同步测试完成，查看控制台')
}


/**
 * 保存数据
 * @param {string} type - 保存类型：draft/final
 */
const saveData = async (type = 'draft') => {
  if (!selectedPdf.value || !selectedSheet.value) {
    ElMessage.warning('请先选择表格')
    return
  }

  // 关键：从状态管理器获取当前表类型的修改
  const context = sheetStateManager.getActiveContext()
  if (!context) {
    ElMessage.warning('无法获取当前表格上下文')
    return
  }

  const tableType = context.tableType || 'original'
  const modifications = sheetStateManager.getModifications(tableType)
  const unsavedModifications = modifications.filter(mod => !mod.saved)

  if (unsavedModifications.length === 0) {
    ElMessage.warning(`当前${tableType === 'flattened' ? '扁平化' : '原始'}表没有需要保存的修改`)
    return
  }

  saving.value = true
  saveType.value = type

  try {
    if (type === 'draft') {
      // 草稿保存到本地
      console.log(`💾 开始草稿保存 (${tableType}表):`, {
        修改数量: unsavedModifications.length,
        表类型: tableType
      })

      // ============ 原有逻辑：保存到dataManager ============
      const result = await dataManager.manualSave()

      if (result.success) {
        // ============ 新增：标记状态管理器中的修改为已保存 ============
        sheetStateManager.markChangesAsSaved(tableType)

        lastSaveTime.value = Date.now()
        saveStatus.value = {
          type: 'success',
          text: `草稿已保存 (${unsavedModifications.length}处修改)`
        }

        ElMessage.success(`草稿已保存到本地（${tableType === 'flattened' ? '扁平化' : '原始'}表）`)

        // 标记单元格为已保存样式
        setTimeout(() => {
          const viewerRef = showFlatMode.value ? flatViewer.value : originalViewer.value
          if (viewerRef && viewerRef.markSavedCells) {
            const savedCellKeys = unsavedModifications.map(c => `${c.row},${c.col}`)
            viewerRef.markSavedCells(savedCellKeys)
          }
        }, 300)
      }

    } else if (type === 'final') {
      // 最终保存到服务器 - 保持原有逻辑
      console.log(`🚀 开始最终保存 (${tableType}表):`, {
        修改数量: unsavedModifications.length,
        表类型: tableType
      })

      // 构建请求数据
      const saveData = {
        pdf_id: selectedPdf.value.id,
        excel_file: selectedExcelFile.value,
        sheet_name: selectedSheet.value.name,
        table_type: tableType,  // 新增：保存表类型
        modified_cells: unsavedModifications.map(mod => ({
          row: mod.row,
          col: mod.col,
          old_value: mod.oldValue,
          new_value: mod.newValue,
          table_type: mod.tableType
        })),
        total_changes: unsavedModifications.length
      }

      // 调用保存API
      const response = await fetch(getApiUrl('/save-excel-data'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(saveData)
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }))
        throw new Error(errorData.error || '保存失败')
      }

      const result = await response.json()
      console.log('✅ 最终保存成功:', result)

      // 标记为已保存
      sheetStateManager.markChangesAsSaved(tableType)

      lastSaveTime.value = Date.now()
      saveStatus.value = {
        type: 'success',
        text: `最终保存成功 (${unsavedModifications.length}处修改)`
      }

      ElMessage.success(`最终保存成功（${tableType === 'flattened' ? '扁平化' : '原始'}表）`)

      // 处理最终保存后的逻辑
      if (result.reload_required) {
        ElMessage.info('正在重新加载最新数据...')
        await loadExcelData(selectedSheet.value.name, selectedExcelFile.value)
      }

      // 标记单元格为已保存样式
      setTimeout(() => {
        const viewerRef = showFlatMode.value ? flatViewer.value : originalViewer.value
        if (viewerRef && viewerRef.markSavedCells) {
          const savedCellKeys = unsavedModifications.map(c => `${c.row},${c.col}`)
          viewerRef.markSavedCells(savedCellKeys)
        }
      }, 300)
    }

  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error(`保存失败: ${error.message}`)
  } finally {
    // ============ 在这里添加保存后处理 ============
    saving.value = false
    saveType.value = ''

    // ✅ 新增：强制更新保存状态
    updateSaveStatus()

    // ✅ 新增：保存状态到持久化存储
    setTimeout(() => {
      sheetStateManager.saveStateToStorage()
    }, 100)
  }
}


const runComprehensiveTest = async () => {
  console.log('🧪 === 开始全面测试 ===');

  // 1. 测试基础状态
  console.log('1. 基础状态测试:');
  console.log('  当前PDF:', selectedPdf.value?.id);
  console.log('  当前Sheet:', selectedSheet.value?.name);

  const context = sheetStateManager.getActiveContext();
  console.log('  当前表类型:', context?.tableType);

  // 2. 测试数据状态
  console.log('2. 数据状态测试:');
  console.log('  原始数据:', sheetStateManager.hasData('original') ? '有' : '无');
  console.log('  扁平化数据:', sheetStateManager.hasData('flattened') ? '有' : '无');

  // 3. 测试修改记录
  console.log('3. 修改记录测试:');
  const stats = sheetStateManager.getModificationStats();
  console.log('  修改统计:', stats);

  // 4. 测试保存状态
  console.log('4. 保存状态测试:');
  const canSave = hasUnsavedChangesInCurrentTable();
  console.log('  保存按钮是否可用:', canSave);
  console.log('  保存状态显示:', saveStatus.value);

  // 5. 测试持久化（修改这里）
  console.log('5. 持久化测试:');
  try {
    const saveResult = sheetStateManager.saveStateToStorage();
    console.log('  保存到localStorage:', saveResult ? '成功' : '失败');

    // 测试加载
    const savedData = localStorage.getItem('sheetStateManager');
    console.log('  localStorage数据大小:', savedData ? savedData.length : 0);

  } catch (error) {
    console.error('  持久化测试失败:', error);
  }

  // 6. 移除有问题的构造函数测试，改为其他测试
  console.log('6. 其他功能测试:');
  console.log('  清除未保存修改测试...');
  const beforeClear = sheetStateManager.getUnsavedChangesCount();
  sheetStateManager.clearUnsavedChanges();
  const afterClear = sheetStateManager.getUnsavedChangesCount();
  console.log(`    清除前: ${beforeClear}, 清除后: ${afterClear}`);

  console.log('✅ === 全面测试完成 ===');

  ElMessage.success('全面测试完成，请查看控制台');
}


// 需要添加的辅助函数
const generateVersion = () => {
  // 简单的版本号生成，例如：v1.0.20240125.1
  const now = new Date()
  const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '')
  const hourStr = now.getHours().toString().padStart(2, '0')
  const minStr = now.getMinutes().toString().padStart(2, '0')
  return `v1.0.${dateStr}.${hourStr}${minStr}`
}

const downloadResultFile = (url, filename) => {
  const link = document.createElement('a')
  link.href = url
  link.download = filename || 'modified_excel.xlsx'
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  setTimeout(() => {
    document.body.removeChild(link)
  }, 100)
}


/**
 * 保存后标记已保存单元格
 */
const markSavedCellsAfterSave = async () => {
  if (!selectedPdf.value || !selectedSheet.value) return

  // 获取当前活动的 ExcelViewer
  const excelViewerRef = showFlatMode.value ? flatViewer.value : originalViewer.value

  if (!excelViewerRef || !excelViewerRef.markSavedCells) {
    console.warn('无法获取 ExcelViewer 实例或 markSavedCells 方法')
    return
  }

  // 获取当前的所有修改单元格
  const currentChanges = dataManager.getChanges()
  if (currentChanges.length === 0) return

  // 转换为单元格键格式
  const savedCellKeys = currentChanges.map(change => {
    if (Array.isArray(change)) {
      const [row, col] = change
      return `${row},${col}`
    } else if (change.row !== undefined && change.col !== undefined) {
      return `${change.row},${change.col}`
    }
    return null
  }).filter(Boolean)

  if (savedCellKeys.length > 0) {
    const result = excelViewerRef.markSavedCells(savedCellKeys)
    console.log('标记已保存单元格结果:', result)
  }
}


/**
 * 显示下载选项
 */
const showDownloadOption = (downloadUrl, fileName) => {
  // 可以添加一个小的下载按钮或提示
  console.log('📥 可下载文件:', { downloadUrl, fileName })

  // 或者自动创建下载链接
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = fileName || 'modified_excel.xlsx'
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

/**
 * 最终保存后的处理
 */
const handleFinalSave = async (result) => {
  console.log('✅ 最终保存处理:', result)

  // 1. 重置修改计数（dataManager 中已清除）
  // 不需要再重置 modifiedCellsCount.value，因为 dataManager.clearChanges() 已处理

  // 2. 如果需要，重新加载数据
  if (result.reload_required && selectedSheet.value) {
    ElMessage.info('正在重新加载最新数据...')
    await loadExcelData(selectedSheet.value.name, selectedExcelFile.value)
  }

  // 3. 清理相关的缓存
  if (result.clear_cache) {
    const pdfId = selectedPdf.value.id
    const excelFile = selectedExcelFile.value
    const sheetName = selectedSheet.value.name

    // 清理内存缓存
    excelDataCache.clearFlattenedData(pdfId, excelFile, sheetName)
  }

  // 4. 记录保存历史
  recordSaveHistory(result)
}

/**
 * 记录保存历史（可选）
 */
const recordSaveHistory = (result) => {
  const historyItem = {
    pdf_id: selectedPdf.value.id,
    sheet_name: selectedSheet.value.name,
    timestamp: Date.now(),
    changes_count: dataManager.getChangeCount(),
    result: result
  }

  // 保存到本地存储或IndexedDB
  try {
    localStorage.setItem(
      `last_save_${selectedPdf.value.id}_${selectedSheet.value.name}`,
      JSON.stringify(historyItem)
    )
  } catch (error) {
    console.warn('记录保存历史失败:', error)
  }
}



/**
 * 手动恢复未保存的修改（用户主动触发）
 */
const restoreUnsavedData = async () => {
  if (!selectedPdf.value || !selectedSheet.value) {
    ElMessage.warning('请先选择表格')
    return
  }

  console.log('🔄 用户手动触发恢复修改')

  // 从状态管理器获取当前表类型的未保存修改
  const context = sheetStateManager.getActiveContext()
  if (!context) {
    ElMessage.warning('无法获取当前表格上下文')
    return
  }

  const tableType = context.tableType || 'original'
  const unsavedModifications = sheetStateManager.getModifications(tableType)
    .filter(mod => !mod.saved)

  console.log('📊 恢复检查（状态管理器）:', {
    表类型: tableType,
    未保存修改数: unsavedModifications.length,
    当前显示的表: showFlatMode.value ? '扁平化表' : '原始表'
  })

  // 如果没有修改，直接返回
  if (unsavedModifications.length === 0) {
    // 也检查一下另一种表类型是否有修改
    const otherTableType = tableType === 'original' ? 'flattened' : 'original'
    const otherModifications = sheetStateManager.getModifications(otherTableType)
      .filter(mod => !mod.saved)

    if (otherModifications.length > 0) {
      ElMessageBox.confirm(
        `检测到 <b>${otherTableType === 'flattened' ? '扁平化' : '原始'}表格</b> 的 ${otherModifications.length} 处修改，但当前显示的是${tableType === 'flattened' ? '扁平化' : '原始'}表格。<br/><br/>
        是否切换到${otherTableType === 'flattened' ? '扁平化' : '原始'}表格查看这些修改？`,
        '检测到修改',
        {
          confirmButtonText: `切换到${otherTableType === 'flattened' ? '扁平化' : '原始'}表格`,
          cancelButtonText: '留在当前表格',
          distinguishCancelAndClose: true,
          dangerouslyUseHTMLString: true,
          type: 'info'
        }
      ).then(() => {
        console.log(`🔄 用户选择切换到${otherTableType}表格`)
        if ((otherTableType === 'flattened' && !showFlatMode.value) ||
            (otherTableType === 'original' && showFlatMode.value)) {
          toggleFlatMode()
        }
      }).catch(() => {
        console.log('⏸️ 用户选择留在当前表格')
      })
    } else {
      ElMessage.info('没有发现需要恢复的修改')
    }
    return
  }

  // 显示确认对话框
  ElMessageBox.confirm(
    `检测到 <b>${tableType === 'flattened' ? '扁平化' : '原始'}表格</b> 的 ${unsavedModifications.length} 处修改，是否恢复？<br/><br/>
    <small style="color: #666;">注意：恢复将覆盖当前表格的内容</small>`,
    `恢复${tableType === 'flattened' ? '扁平化' : '原始'}表格修改`,
    {
      confirmButtonText: '恢复',
      cancelButtonText: '丢弃',
      distinguishCancelAndClose: true,
      dangerouslyUseHTMLString: true,
      type: 'warning'
    }
  ).then(async () => {
    console.log(`✅ 用户确认恢复${tableType}表格修改`)

    // 根据表类型恢复
    if (tableType === 'original') {
      await applyChangesToOriginalViewer(unsavedModifications)
    } else {
      await applyChangesToFlatViewer(unsavedModifications)
    }

    // 标记为已恢复（但不标记为已保存）
    // 用户可以继续编辑这些单元格

    ElMessage.success(`已恢复 ${unsavedModifications.length} 处${tableType === 'flattened' ? '扁平化' : '原始'}表格修改`)

  }).catch((action) => {
    if (action === 'cancel') {
      console.log(`🗑️ 用户丢弃${tableType}表格修改`)
      // 丢弃修改
      sheetStateManager.clearUnsavedChanges(tableType)
      ElMessage.info(`已丢弃${tableType === 'flattened' ? '扁平化' : '原始'}表格的修改`)

      // 更新UI状态
      updateSaveStatus()
    }
  })
}


/**
 * 应用修改到扁平化表格
 */
const applyChangesToFlatViewer = async (changes) => {
  if (!flatViewer.value || !flatData.value.length) {
    console.error('❌ 扁平化表格未加载')
    return
  }

  const hot = flatViewer.value.getSafeHotInstance()
  if (!hot) {
    console.error('❌ 无法获取扁平化表格实例')
    return
  }

  console.log('🎯 应用到扁平化表格，修改数:', changes.length)

  const batchChanges = []
  const cellKeys = []

  changes.forEach((change, index) => {
    const { row, col, newValue } = change

    // 验证坐标是否在扁平化表格范围内
    if (row < 0 || col < 0 || row >= hot.countRows() || col >= hot.countCols()) {
      console.warn(`⚠️ 跳过无效坐标 [${row},${col}]，扁平化表格尺寸: ${hot.countRows()}x${hot.countCols()}`)
      return
    }

    batchChanges.push([Number(row), Number(col), newValue])
    cellKeys.push(`${row},${col}`)

    console.log(`  扁平化表格修改 [${row},${col}]: "${newValue}"`)
  })

  if (batchChanges.length > 0) {
    try {
      // 批量应用修改
      hot.setDataAtCell(batchChanges)
      console.log(`✅ 已应用 ${batchChanges.length} 个修改到扁平化表格`)

      // 重要：应用后不立即标记为已保存
      // 这样可以保持"未保存"状态，用户保存时这些修改会被包含

      // 如果修改中有已保存的记录，需要标记样式
      const savedChanges = changes.filter(change => change.saved)
      if (savedChanges.length > 0) {
        setTimeout(() => {
          if (flatViewer.value.markSavedCells) {
            const savedCellKeys = savedChanges.map(c => `${c.row},${c.col}`)
            flatViewer.value.markSavedCells(savedCellKeys)
            console.log(`🟢 已标记 ${savedCellKeys.length} 个已保存单元格`)
          }
        }, 300)
      }

      // 强制重新渲染以确保样式生效
      setTimeout(() => {
        hot.render()
        console.log('🔄 扁平化表格已重新渲染')
      }, 100)

    } catch (error) {
      console.error('❌ 应用到扁平化表格失败:', error)

      // 备选方案：逐个应用
      try {
        console.log('🔄 尝试逐个应用修改...')
        batchChanges.forEach(([row, col, value]) => {
          hot.setDataAtCell(row, col, value)
        })
        console.log('✅ 已逐个应用修改')
      } catch (error2) {
        console.error('❌ 逐个应用也失败:', error2)
        ElMessage.error('恢复修改失败，请刷新页面重试')
      }
    }
  } else {
    console.log('ℹ️ 没有有效的修改需要应用')
  }
}


// 修改 applyChangesToOriginalViewer
const applyChangesToOriginalViewer = async (changes) => {
  if (!originalViewer.value || !excelData.value.length) {
    console.error('❌ 原始表格未加载')
    return
  }

  const hot = originalViewer.value.getSafeHotInstance()
  if (!hot) {
    console.error('❌ 无法获取原始表格实例')
    return
  }

  console.log('🎯 应用到原始表格，修改数:', changes.length)

  const batchChanges = []
  const savedCellKeys = []

  changes.forEach((change, index) => {
    const { row, col, newValue } = change

    // 验证坐标是否在原始表格范围内
    if (row < 0 || col < 0 || row >= hot.countRows() || col >= hot.countCols()) {
      console.warn(`⚠️ 跳过无效坐标 [${row},${col}]，原始表格尺寸: ${hot.countRows()}x${hot.countCols()}`)
      return
    }

    batchChanges.push([Number(row), Number(col), newValue])
    savedCellKeys.push(`${row},${col}`)

    console.log(`  原始表格修改 [${row},${col}]: "${newValue}"`)
  })

  if (batchChanges.length > 0) {
    try {
      hot.setDataAtCell(batchChanges)
      console.log(`✅ 已应用 ${batchChanges.length} 个修改到原始表格`)

      // 重要：应用后不标记为已保存，保持"未保存"状态
      // 这样用户保存时，这些修改会被包含在内

    } catch (error) {
      console.error('❌ 应用到原始表格失败:', error)
    }
  }
}



/**
 * 自动应用已保存的修改到表格（恢复样式）
 */
const applySavedModifications = async () => {
  const context = sheetStateManager.getActiveContext()
  if (!context) return

  const tableType = context.tableType || 'original'
  const allModifications = sheetStateManager.getModifications(tableType)

  if (allModifications.length === 0) return

  // 分离已保存和未保存的修改
  const savedModifications = allModifications.filter(mod => mod.saved)
  const unsavedModifications = allModifications.filter(mod => !mod.saved)

  console.log('🎨 应用已保存修改样式:', {
    表类型: tableType,
    已保存: savedModifications.length,
    未保存: unsavedModifications.length
  })

  if (savedModifications.length === 0) return

  // 获取对应的表格实例
  const viewerRef = showFlatMode.value ? flatViewer.value : originalViewer.value
  if (!viewerRef || !viewerRef.markSavedCells) {
    console.warn('❌ 无法标记已保存单元格：表格实例无效')
    return
  }

  // 构建已保存单元格的键
  const savedCellKeys = savedModifications.map(mod => `${mod.row},${mod.col}`)

  // 标记为已保存样式
  const result = viewerRef.markSavedCells(savedCellKeys)
  console.log('✅ 已保存单元格样式恢复:', result)

  // 如果有未保存修改，也需要标记（但用不同样式）
  if (unsavedModifications.length > 0) {
    // 这会在进入编辑模式时自动处理
    console.log(`💡 还有 ${unsavedModifications.length} 个未保存修改等待恢复`)
  }
}

/**
 * 标准化change格式
 */
const normalizeChange = (change) => {
  console.log('🔄 normalizeChange 输入:', change)

  // 如果已经是标准格式
  if (change && change.row !== undefined && change.col !== undefined && change.newValue !== undefined) {
    console.log('✅ 已为标准格式')
    return change
  }

  // 数组格式 [row, col, old, new]
  if (Array.isArray(change) && change.length >= 4) {
    console.log('✅ 检测到数组格式')
    return {
      row: change[0],
      col: change[1],
      oldValue: change[2],
      newValue: change[3]
    }
  }

  // 检测常见键名
  const possibleKeys = {
    row: ['row', 'rowIndex', 'r', '_row', 'Row', 'rowIndex', 'row_index'],
    col: ['col', 'colIndex', 'c', '_col', 'column', 'Column', 'colIndex', 'col_index'],
    newValue: ['newValue', 'new', 'value', 'val', '_value', 'Value', 'new_value']
  }

  const normalized = {}

  // 查找row
  for (const key of possibleKeys.row) {
    if (change[key] !== undefined) {
      normalized.row = change[key]
      console.log(`🔍 找到row键: ${key} = ${change[key]}`)
      break
    }
  }

  // 查找col
  for (const key of possibleKeys.col) {
    if (change[key] !== undefined) {
      normalized.col = change[key]
      console.log(`🔍 找到col键: ${key} = ${change[key]}`)
      break
    }
  }

  // 查找newValue
  for (const key of possibleKeys.newValue) {
    if (change[key] !== undefined) {
      normalized.newValue = change[key]
      console.log(`🔍 找到newValue键: ${key} = ${change[key]}`)
      break
    }
  }

  // 如果还没有找到，尝试其他方式
  if (normalized.row === undefined && change[0] !== undefined) {
    normalized.row = change[0]
  }

  if (normalized.col === undefined && change[1] !== undefined) {
    normalized.col = change[1]
  }

  if (normalized.newValue === undefined && change[3] !== undefined) {
    normalized.newValue = change[3]
  }

  console.log('🔄 标准化结果:', normalized)
  return normalized
}




/**
 * 判断是否为扁平化数据修改
 */
const isFlatDataChange = (change) => {
  // 根据你的扁平化数据结构来判断
  // 例如，检查内容是否匹配扁平化数据的列名

  if (change.contentKey && change.contentKey.includes('_flat_')) {
    return true
  }

  // 或者检查列索引
  if (change.col >= flatDataColumnCount) {
    return true
  }

  return false
}

/**
 * 在扁平化数据中查找匹配的单元格
 */
const findMatchingCellInFlatData = (originalChange) => {
  // 这里需要实现一个映射算法
  // 从原始表格坐标映射到扁平化表格坐标

  const { row: origRow, col: origCol, newValue } = originalChange

  // 简单示例：假设扁平化表格有固定的结构
  // 实际情况需要根据你的扁平化算法来定

  if (flatData.value.length > 0) {
    // 在扁平化数据中查找包含相同内容的行
    for (let flatRow = 0; flatRow < flatData.value.length; flatRow++) {
      const flatRowData = flatData.value[flatRow]

      // 检查是否有列包含类似的内容
      for (let flatCol = 0; flatCol < Object.keys(flatRowData).length; flatCol++) {
        const colName = Object.keys(flatRowData)[flatCol]
        if (flatRowData[colName] === newValue) {
          console.log(`🔍 找到匹配: 原始[${origRow},${origCol}] -> 扁平化[${flatRow},${flatCol}]`)
          return {
            row: flatRow,
            col: flatCol,
            newValue
          }
        }
      }
    }
  }

  return null
}



/**
 * 应用恢复的修改到表格
 */
const applyRestoredChanges = async (changes) => {
  if (!changes || changes.length === 0) return

  console.log('🔄 应用恢复的修改:', changes)

  // 获取当前活动的 ExcelViewer
  const excelViewerRef = showFlatMode.value ? flatViewer.value : originalViewer.value

  if (!excelViewerRef) {
    console.error('❌ ExcelViewer 实例未找到')
    return
  }

  // 获取 Handsontable 实例
  const hot = excelViewerRef.getSafeHotInstance()
  if (!hot) {
    console.error('❌ Handsontable 实例未找到')
    return
  }

  // 批量修改单元格数据 - 注意格式
  const batchChanges = []
  changes.forEach((change, index) => {
    // 检查 change 的格式
    console.log(`  ${index + 1}. 恢复 change:`, change)

    // 注意：changes 格式可能来自不同来源，需要处理
    if (Array.isArray(change)) {
      // 格式: [row, col, old, new, timestamp]
      const [row, col, oldValue, newValue, timestamp] = change
      console.log(`    [${row},${col}]: "${oldValue}" -> "${newValue}"`)
      batchChanges.push([row, col, newValue])
    } else if (change.row !== undefined && change.col !== undefined) {
      // 格式: {row, col, old, new, timestamp}
      const { row, col, old, new: newValue } = change
      console.log(`    [${row},${col}]: "${old}" -> "${newValue}"`)
      batchChanges.push([row, col, newValue])
    } else if (change.rowIndex !== undefined && change.colIndex !== undefined) {
      // 格式: {rowIndex, colIndex, ...}
      const { rowIndex, colIndex, newValue } = change
      console.log(`    [${rowIndex},${colIndex}]: -> "${newValue}"`)
      batchChanges.push([rowIndex, colIndex, newValue])
    } else {
      console.warn(`⚠️ 未知的change格式:`, change)
    }
  })

  console.log('📋 批量修改列表:', batchChanges)

  // 批量应用修改
  if (batchChanges.length > 0) {
    try {
      // 方法1: 使用 setDataAtCell
      hot.setDataAtCell(batchChanges)
      console.log('✅ 已批量应用恢复的修改到表格')
    } catch (error) {
      console.error('❌ 应用修改失败:', error)

      // 尝试方法2: 逐个设置
      try {
        batchChanges.forEach(([row, col, value]) => {
          hot.setDataAtCell(row, col, value)
        })
        console.log('✅ 已逐个应用恢复的修改')
      } catch (error2) {
        console.error('❌ 逐个应用也失败:', error2)
        ElMessage.error('恢复修改失败，请刷新页面重试')
      }
    }
  } else {
    console.log('ℹ️ 没有有效的修改需要应用')
  }

  // 更新保存状态
  updateSaveStatus()

  // 标记为已保存样式
  setTimeout(() => {
    if (excelViewerRef.markSavedCells) {
      // 构建单元格键数组
      const savedCellKeys = []
      changes.forEach(change => {
        if (Array.isArray(change)) {
          const [row, col] = change
          savedCellKeys.push(`${row},${col}`)
        } else if (change.row !== undefined && change.col !== undefined) {
          savedCellKeys.push(`${change.row},${change.col}`)
        }
      })

      if (savedCellKeys.length > 0) {
        const result = excelViewerRef.markSavedCells(savedCellKeys)
        console.log('🎨 标记已保存样式结果:', result)
      }
    }
  }, 800)
}


/**
 * 检查当前表格是否有未保存修改
 */
const hasUnsavedChangesInCurrentTable = () => {
  if (!selectedSheet.value || !selectedPdf.value) {
    return false
  }

  const context = sheetStateManager.getActiveContext()
  if (!context) {
    return false
  }

  // 直接检查状态管理器中的未保存计数
  const tableType = context.tableType || 'original'
  const stats = sheetStateManager.getModificationStats()

  if (!stats || !stats[tableType]) {
    return false
  }

  const hasUnsaved = stats[tableType].unsaved > 0

  console.log('🔍 保存按钮状态检查:', {
    表类型: tableType,
    未保存数: stats[tableType].unsaved,
    是否可保存: hasUnsaved
  })

  return hasUnsaved
}


/**
 * 辅助函数：直接从DOM获取表格实例
 */
const getSafeHotInstanceFromDom = () => {
  try {
    // 尝试通过类名查找表格容器
    const container = document.querySelector('.handsontable-container .ht_master')
    if (container && container.__hotInstance) {
      return container.__hotInstance
    }

    // 或者查找 Handsontable 的根元素
    const hotRoot = document.querySelector('[data-handsontable="true"]')
    if (hotRoot && hotRoot.__hotInstance) {
      return hotRoot.__hotInstance
    }
  } catch (error) {
    console.warn('无法从DOM获取表格实例:', error)
  }
  return null
}

/**
 * 辅助函数：直接应用修改到表格实例
 */
const applyChangesDirectlyToHot = (hot, changes) => {
  const batchChanges = []
  changes.forEach((change, index) => {
    const { row, col, newValue } = change
    batchChanges.push([row, col, newValue])
  })

  if (batchChanges.length > 0) {
    hot.setDataAtCell(batchChanges)
    console.log('✅ 已直接应用恢复的修改')

    // 触发重新渲染
    setTimeout(() => {
      hot.render()
    }, 100)
  }
}


const debugSaveState = () => {
  console.log('=== 保存状态调试 ===')

  // 1. 检查状态管理器
  const context = sheetStateManager.getActiveContext()
  console.log('当前上下文:', context)

  // 2. 检查修改统计
  const stats = sheetStateManager.getModificationStats()
  console.log('修改统计:', stats)

  if (context && stats) {
    const tableType = context.tableType || 'original'
    const tableStats = stats[tableType]
    console.log(`${tableType}表统计:`, tableStats)
    console.log(`是否有未保存修改: ${tableStats.unsaved > 0}`)
  }

  // 3. 检查UI状态
  console.log('UI状态:')
  console.log('  selectedSheet:', !!selectedSheet.value)
  console.log('  selectedPdf:', !!selectedPdf.value)
  console.log('  hasUnsavedChangesInCurrentTable():', hasUnsavedChangesInCurrentTable())
  console.log('  saveStatus:', saveStatus.value)

  // 4. 检查保存按钮状态
  const saveBtn = document.querySelector('.save-buttons .el-button')
  if (saveBtn) {
    console.log('保存按钮:', {
      是否禁用: saveBtn.disabled,
      文本: saveBtn.textContent.trim()
    })
  }

  ElMessage.info('保存状态调试完成，查看控制台')
}



/**
 * 缓存扁平化数据
 */
const cacheFlattenedData = async () => {
  if (!flatData.value || flatData.value.length === 0) {
    console.warn('没有扁平化数据可缓存')
    return
  }

  initDataManagerContext()

  try {
    const cacheKey = await dataManager.saveFlattenedData(
      flatData.value,
      excelData.value
    )

    if (cacheKey) {
      console.log('📦 扁平化数据已缓存:', cacheKey)
      ElMessage.success('扁平化数据已缓存')
    }
  } catch (error) {
    console.error('缓存扁平化数据失败:', error)
  }
}

/**
 * 获取缓存的扁平化数据
 */
const getCachedFlattenedData = async () => {
  initDataManagerContext()

  const cachedData = await dataManager.getFlattenedData()

  if (cachedData) {
    console.log('📦 使用缓存的扁平化数据')
    return cachedData
  }

  return null
}

// ============ 保持原有的其他方法 ============
// selectPdf, loadExcelSheets, loadAllClassData, loadExcelData, generateTableColumns 等...

// 修改 watch(selectedPdf) 监听器
watch(selectedPdf, (newPdf, oldPdf) => {
  if (newPdf?.id !== oldPdf?.id) {
    console.log('🔄 切换到新PDF，清理旧状态');

    // 清理UI状态
    selectedSheet.value = null;
    excelData.value = [];
    tableColumns.value = [];
    flatData.value = [];
    currentPage.value = 1;

    // 清理状态管理器
    if (oldPdf?.id) {
      // 可选：清理旧PDF的所有状态
      // sheetStateManager.clearSheetState(oldPdf.id, '', '');
    }

    // 重置原有数据管理器
    dataManager.setContext({
      pdfId: newPdf?.id || null,
      excelFile: null,
      sheetName: null
    });

    // 重置显示模式
    showFlatMode.value = false;
    currentTableMode.value = 'original';

    console.log('✅ PDF切换完成，状态已重置');
  }
})

watch(selectedSheet, (newSheet, oldSheet) => {
  if (newSheet?.name !== oldSheet?.name || newSheet?.excel_file !== oldSheet?.excel_file) {
    if (newSheet && selectedPdf.value) {
      initDataManagerContext()
    }

    showFlatMode.value = false
    flatData.value = []
    updateSaveStatus()
  }
})

watch(excelData, (newData, oldData) => {
  updateSaveStatus()
})


// 在 onMounted 中添加状态监听
onMounted(() => {
  console.log('🚀 ThreeColumnPage 挂载');

  // ============ 1. 强制全局暴露（开发必须）============
  try {
    // 无条件暴露多个别名
    window.sheetStateManager = sheetStateManager;
    window.$sheetManager = sheetStateManager;
    window.$sheet = sheetStateManager;
    window.sheetSM = sheetStateManager;

    console.log('🔧 状态管理器已全局暴露');
    console.log('  可用变量: sheetStateManager, $sheetManager, $sheet, sheetSM');

    // 立即验证暴露是否成功
    setTimeout(() => {
      console.log('✅ 暴露验证结果:');
      console.log('  sheetStateManager:', typeof window.sheetStateManager);
      console.log('  是否有debugState方法:', !!window.sheetStateManager?.debugState);
      console.log('  实例ID:', sheetStateManager?.constructor?.name);
    }, 50);

  } catch (exposeError) {
    console.error('❌ 全局暴露失败:', exposeError);
  }

  // ============ 2. 加载保存的状态 ============
  try {
    console.log('📂 尝试加载保存的状态...');
    const loadResult = sheetStateManager.loadStateFromStorage();
    console.log(`  加载结果: ${loadResult ? '成功' : '失败或空数据'}`);

    // 立即显示当前状态
    setTimeout(() => {
      console.log('📊 当前状态管理器内容:');
      console.log('  活跃上下文:', sheetStateManager.getActiveContext());
      console.log('  Sheet数量:', sheetStateManager.sheetStates?.size || 0);
    }, 100);

  } catch (loadError) {
    console.warn('⚠️ 状态加载失败（继续运行）:', loadError.message);
    // 清理可能损坏的数据
    try {
      localStorage.removeItem('sheetStateManager');
      console.log('🧹 已清理损坏的localStorage数据');
    } catch (cleanError) {
      console.log('ℹ️ 清理localStorage失败:', cleanError.message);
    }
  }

  // ============ 3. 定期保存状态（每30秒） ============
  const saveInterval = setInterval(() => {
    try {
      const saveResult = sheetStateManager.saveStateToStorage();
      if (saveResult) {
        console.log('💾 定时保存成功');
      }
    } catch (saveError) {
      console.warn('⚠️ 定时保存失败:', saveError.message);
    }
  }, 30000);

  // ============ 4. 原有的其他初始化代码 ============
  try {
    dataManager.setupPageProtection();
    console.log('🛡️ 页面保护已设置');
  } catch (dmError) {
    console.warn('⚠️ 数据管理器初始化失败:', dmError.message);
  }

  // ============ 5. 定期更新保存状态（每2秒） ============
  const updateInterval = setInterval(() => {
    try {
      updateSaveStatus();
    } catch (updateError) {
      console.warn('⚠️ 状态更新失败:', updateError.message);
    }
  }, 2000);

  // ============ 6. 在页面卸载时清理 ============
  onUnmounted(() => {
    console.log('🧹 ThreeColumnPage 卸载，开始清理...');

    // 清理定时器
    clearInterval(saveInterval);
    clearInterval(updateInterval);
    console.log('  定时器已清理');

    // 最后保存一次状态
    try {
      sheetStateManager.saveStateToStorage();
      console.log('  最终状态已保存');
    } catch (finalSaveError) {
      console.warn('  最终保存失败:', finalSaveError.message);
    }

    // 可选：清理全局变量（避免内存泄漏）
    if (process.env.NODE_ENV === 'development') {
      delete window.sheetStateManager;
      delete window.$sheetManager;
      delete window.$sheet;
      delete window.sheetSM;
      console.log('  全局变量已清理');
    }

    console.log('✅ 清理完成');
  });

  // ============ 7. 额外调试：暴露便捷测试方法 ============
  if (process.env.NODE_ENV === 'development' || import.meta.env?.MODE === 'development') {
    window.$test = {
      // 状态管理器快捷访问
      manager: sheetStateManager,
      debug: () => sheetStateManager.debugState(),
      stats: () => sheetStateManager.getModificationStats(),
      context: () => sheetStateManager.getActiveContext(),

      // 当前页面状态
      pdf: () => selectedPdf.value,
      sheet: () => selectedSheet.value,
      data: () => excelData.value,
      flatData: () => flatData.value,

      // 保存状态
      canSave: () => hasUnsavedChangesInCurrentTable(),
      saveStatus: () => saveStatus.value,

      // 实用方法
      updateStatus: () => updateSaveStatus(),
      clearLocalStorage: () => {
        localStorage.removeItem('sheetStateManager');
        console.log('🧹 localStorage 已清理');
        return '已清理';
      }
    };

    console.log('🔧 调试工具已暴露到 window.$test');
    console.log('  使用 $test.debug() 查看状态');
    console.log('  使用 $test.stats() 查看统计');
    console.log('  使用 $test.clearLocalStorage() 清理数据');
  }

  // ============ 8. 最终确认 ============
  console.log('✅ ThreeColumnPage 初始化完成');
  console.log('ℹ️ 请打开控制台使用调试工具');
});


onUnmounted(() => {
  console.log('🧹 ThreeColumnPage 卸载，清理资源')
})





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

      // 设置状态管理器上下文（先设置基础信息，sheet稍后设置）
      sheetStateManager.setActiveContext(fileId, '', '', 'original')
      console.log('📌 状态管理器：PDF上下文已设置')

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


const loadExcelData = async (sheetName, excelFileName) => {
  if (!selectedPdf.value) {
    console.error('没有选中的PDF')
    return
  }

  console.log('开始加载Excel数据，sheet:', sheetName, '文件:', excelFileName)

  loadingExcel.value = true

  try {
    const pdfId = selectedPdf.value.id
    const apiUrl = getApiUrl(`/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/${encodeURIComponent(sheetName)}`)

    const response = await fetch(apiUrl)

    if (response.ok) {
      const data = await response.json()

      // 1. 保存到原有缓存（保持兼容）
        excelDataCache.setOriginalData(pdfId, excelFileName, sheetName, data.rows || [])
        excelDataCache.setCurrentSheet(pdfId, excelFileName, sheetName)

        // 2. ✅ 新增：保存到状态管理器
        // 检查是否与当前活跃上下文匹配
        const currentContext = sheetStateManager.getActiveContext()
        if (currentContext &&
            currentContext.pdfId === pdfId &&
            currentContext.excelFile === excelFileName &&
            currentContext.sheetName === sheetName) {

          sheetStateManager.setData('original', data.rows || [])
          console.log(`📦 原始数据已保存到状态管理器: ${data.rows?.length || 0}行`)
        }

      // 重置模式
      currentTableMode.value = 'original'
      window.currentTableMode = 'original'
      showFlatMode.value = false
      flatData.value = []
      console.log('🔄 加载新sheet，重置为原始模式')

      // 如果是目录sheet，特殊处理
      if (sheetName === '目录') {
        await loadAllClassData(excelFileName)
      } else {
        excelData.value = data.rows || []
        generateTableColumns(data.rows)
      }

      // ✅ 新增：延迟应用已保存的修改样式
        setTimeout(() => {
          applySavedModifications()
        }, 500)

      ElMessage.success(`已加载表格: ${sheetName}`)

      // ============ 关键修改：移除自动恢复逻辑 ============
      // 不自动恢复，只在控制台记录
      initDataManagerContext()
      const originalChanges = await dataManager.getChangesByTableType('original')
      const flatChanges = await dataManager.getChangesByTableType('flat')

      if (originalChanges.length > 0 || flatChanges.length > 0) {
        console.log('📊 加载完成，检测到未保存修改:', {
          原始表: originalChanges.length,
          扁平化表: flatChanges.length
        })
        // 不自动弹窗，等待用户手动触发
      }

    } else {
      const errorData = await response.json().catch(() => ({ error: '未知错误' }))
      excelData.value = []
      tableColumns.value = []
      ElMessage.warning(`无法加载表格数据: ${errorData.error || '未知错误'}`)
    }

  } catch (error) {
    console.error('加载Excel数据失败:', error)
    throw error
  } finally {
    loadingExcel.value = false
  }
}

/**
 * 检查并提示恢复
 */
const checkAndPromptForRestore = async (pdfId, excelFile, sheetName) => {
  console.log('🔍 检查是否需要恢复修改...')

  initDataManagerContext()

  // 获取两种表的修改
  const originalChanges = await dataManager.getChangesByTableType('original')
  const flatChanges = await dataManager.getChangesByTableType('flat')

  console.log('📊 检查结果:', {
    原始表修改: originalChanges.length,
    扁平化表修改: flatChanges.length
  })

  // 情况1：两种表都有修改
  if (originalChanges.length > 0 && flatChanges.length > 0) {
    console.log('⚠️ 两种表都有修改，显示选择对话框')
    showRestoreChoiceDialog(originalChanges, flatChanges)
    return
  }

  // 情况2：只有原始表有修改
  if (originalChanges.length > 0 && flatChanges.length === 0) {
    console.log('💡 只有原始表有修改，当前显示原始表')

    // 延迟显示确认对话框
    setTimeout(() => {
      showConfirmAndRestore(originalChanges, '原始表')
    }, 1000)
    return
  }

  // 情况3：只有扁平化表有修改
  if (flatChanges.length > 0 && originalChanges.length === 0) {
    console.log('💡 只有扁平化表有修改，但当前显示原始表')

    // 询问用户是否切换到扁平化表格
    setTimeout(() => {
      ElMessageBox.confirm(
        `检测到 <b>扁平化表格</b> 的 ${flatChanges.length} 处修改，但当前显示的是原始表格。<br/><br/>
        是否切换到扁平化表格查看这些修改？`,
        '检测到修改',
        {
          confirmButtonText: '切换到扁平化表格',
          cancelButtonText: '留在原始表格',
          distinguishCancelAndClose: true,
          dangerouslyUseHTMLString: true,
          type: 'info'
        }
      ).then(() => {
        console.log('🔄 用户选择切换到扁平化表格')
        // 这里触发切换到扁平化模式
        if (!showFlatMode.value) {
          toggleFlatMode()
        }
      }).catch(() => {
        console.log('⏸️ 用户选择留在原始表格')
      })
    }, 1000)
    return
  }

  // 情况4：都没有修改
  console.log('ℹ️ 没有检测到任何修改')
}


/**
 * 显示恢复选择对话框
 */
const showRestoreChoiceDialog = async (originalChanges, flatChanges) => {
  return new Promise((resolve) => {
    ElMessageBox.confirm(
      `检测到两种表格的修改：<br/>
      📊 <b>原始表格</b>：${originalChanges.length} 处修改<br/>
      📈 <b>扁平化表格</b>：${flatChanges.length} 处修改<br/><br/>
      请选择要恢复哪种修改？`,
      '选择恢复类型',
      {
        confirmButtonText: '恢复原始表格修改',
        cancelButtonText: '恢复扁平化表格修改',
        distinguishCancelAndClose: true,
        dangerouslyUseHTMLString: true,
        type: 'warning'
      }
    ).then(() => {
      console.log('✅ 用户选择恢复原始表格修改')
      showConfirmAndRestore(originalChanges, '原始表').then(resolve)
    }).catch(() => {
      console.log('✅ 用户选择恢复扁平化表格修改')
      showConfirmAndRestore(flatChanges, '扁平化表').then(resolve)
    })
  })
}

/**
 * 显示确认恢复对话框
 */
const showConfirmAndRestore = async (changes, tableType) => {
  return new Promise((resolve) => {
    ElMessageBox.confirm(
      `检测到 <b>${tableType}</b> 的 ${changes.length} 处修改，是否恢复？<br/><br/>
      <small style="color: #666;">注意：恢复将覆盖当前表格的内容</small>`,
      `恢复${tableType}修改`,
      {
        confirmButtonText: '恢复',
        cancelButtonText: '丢弃',
        distinguishCancelAndClose: true,
        dangerouslyUseHTMLString: true,
        type: 'warning'
      }
    ).then(async () => {
      console.log(`✅ 用户确认恢复${tableType}修改`)

      // 根据表类型恢复
      if (tableType === '原始表') {
        await applyChangesToOriginalViewer(changes)
      } else {
        await applyChangesToFlatViewer(changes)
      }

      ElMessage.success(`已恢复 ${changes.length} 处${tableType}修改`)
      resolve()
    }).catch((action) => {
      if (action === 'cancel') {
        console.log(`🗑️ 用户丢弃${tableType}修改`)
        // 丢弃修改
        const tableTypeKey = tableType === '原始表' ? 'original' : 'flat'
        dataManager.clearChangesByTableType(tableTypeKey)
        ElMessage.info(`已丢弃${tableType}的修改`)
      }
      resolve()
    })
  })
}

// ============ 新增辅助函数：恢复已保存数据状态 ============
/**
 * 恢复已保存数据的状态（颜色标记）
 */
const restoreSavedDataState = async (pdfId, excelFile, sheetName) => {
  console.log('🔄 开始恢复已保存数据状态:', { pdfId, excelFile, sheetName })

  // 1. 初始化数据管理器上下文
  initDataManagerContext()

  // 2. 延迟执行，确保表格已渲染
  setTimeout(async () => {
    try {
      // 3. 从数据管理器获取保存历史
      const savedHistory = await dataManager.getSavedHistory()

      if (savedHistory && savedHistory.changes && savedHistory.changes.length > 0) {
        console.log('📦 发现已保存的历史修改:', savedHistory.changes.length, '处')

        // 4. 需要获取 HandsontableExcelViewer 的 useExcelEdit 实例
        const excelViewerRef = showFlatMode.value ? flatViewer.value : originalViewer.value

        if (excelViewerRef && excelViewerRef.getSafeHotInstance) {
          const hot = excelViewerRef.getSafeHotInstance()
          if (hot) {
            // 5. 遍历保存的历史，标记已保存单元格
            savedHistory.changes.forEach((change, index) => {
              const { row, col, newValue } = change

              // 检查单元格是否存在
              if (row < hot.countRows() && col < hot.countCols()) {
                const cellKey = `${row},${col}`

                // 需要调用 useExcelEdit 的方法来标记已保存
                // 由于 useExcelEdit 是独立组合式函数，我们需要通过某种方式访问它
                // 这里可以通过暴露的API或直接操作样式

                // 方法A：直接操作样式（临时方案）
                markCellAsSavedDirectly(hot, row, col)

                console.log(`🟢 标记已保存单元格: [${row},${col}] = "${newValue}"`)
              } else {
                console.warn(`⚠️ 单元格超出范围: [${row},${col}]`)
              }
            })

            // 6. 强制重新渲染以显示样式
            hot.render()

            console.log('✅ 已保存数据状态恢复完成')

            // 显示提示
            if (savedHistory.changes.length > 0) {
              setTimeout(() => {
                ElMessage.info(`已恢复 ${savedHistory.changes.length} 处已保存的修改标记`)
              }, 500)
            }
          }
        } else {
          console.warn('❌ 无法获取表格实例')
        }
      } else {
        console.log('ℹ️ 没有发现已保存的历史修改')
      }
    } catch (error) {
      console.error('❌ 恢复已保存数据状态失败:', error)
    }
  }, 1000) // 延迟1秒确保表格完全加载
}

/**
 * 直接标记单元格为已保存（临时方案）
 */
const markCellAsSavedDirectly = (hot, row, col) => {
  try {
    // 获取当前单元格配置
    const currentCellConfig = hot.getSettings().cell || []

    // 检查是否已有配置
    const existingConfigIndex = currentCellConfig.findIndex(
      config => config.row === row && config.col === col
    )

    if (existingConfigIndex >= 0) {
      // 更新现有配置
      const className = currentCellConfig[existingConfigIndex].className || ''
      if (!className.includes('saved-modified-cell')) {
        currentCellConfig[existingConfigIndex].className =
          className + ' saved-modified-cell'
      }
    } else {
      // 添加新配置
      currentCellConfig.push({
        row: row,
        col: col,
        className: 'saved-modified-cell'
      })
    }

    // 应用更新
    hot.updateSettings({
      cell: currentCellConfig
    }, false)

  } catch (error) {
    console.warn(`⚠️ 直接标记单元格失败 [${row},${col}]:`, error)
  }
}

/**
 * 更好的方案：通过数据管理器与 useExcelEdit 交互
 */
/**
 * 更好的方案：通过数据管理器与 useExcelEdit 交互
 */
const restoreSavedCellsViaDataManager = async () => {
  if (!selectedPdf.value || !selectedSheet.value) {
    return
  }

  console.log('🔄 通过数据管理器恢复已保存单元格')

  // 1. 确保数据管理器上下文正确
  initDataManagerContext()

  // 2. 获取未保存的编辑
  const result = await dataManager.restoreUnsavedEdits()

  if (result.success && result.changes && result.changes.length > 0) {
    console.log('📝 发现需要恢复的编辑:', result.changes.length)

    // 3. 获取当前活动的 ExcelViewer
    const excelViewerRef = showFlatMode.value ? flatViewer.value : originalViewer.value

    if (excelViewerRef && excelViewerRef.restoreCellStates) {
      // 调用子组件的方法
      excelViewerRef.restoreCellStates(result.changes)
      console.log('✅ 已调用子组件恢复单元格状态')
    } else {
      console.warn('❌ 子组件没有恢复状态的方法或未找到组件')
      // 备选方案：通过全局事件
      window.dispatchEvent(new CustomEvent('restore-cell-states', {
        detail: { changes: result.changes }
      }))
    }
  }
}


// 在 HandsontableExcelViewer.vue 的 script 部分添加：
const restoreCellStates = (changes) => {
  console.log('📥 收到恢复单元格状态请求:', changes?.length || 0)

  if (!changes || changes.length === 0) return

  const hot = getSafeHotInstance()
  if (!hot) return

  // 清空现有的已保存记录
  savedCells.value.clear()

  // 添加新的已保存记录
  changes.forEach(change => {
    if (change.row !== undefined && change.col !== undefined) {
      const cellKey = `${change.row},${change.col}`
      savedCells.value.add(cellKey)
    }
  })

  // 更新样式
  updateModifiedCellsStyle(true)

  console.log('✅ 单元格状态恢复完成:', {
    已保存单元格数: savedCells.value.size
  })
}


// 在 script setup 顶部添加
const isDev = process.env.NODE_ENV === 'development' || import.meta.env?.MODE === 'development';
console.log('环境模式:', process.env.NODE_ENV || import.meta.env?.MODE, '是否为开发环境:', isDev);

// 暴露到window用于调试
if (isDev) {
  window.$debug = {
    sheetStateManager,
    dataManager,
    excelDataCache,
    runComprehensiveTest,
    updateSaveStatus: () => updateSaveStatus(),
    debugState: () => sheetStateManager.debugState()
  };
  console.log('🔧 调试工具已暴露到 window.$debug');
}



// 暴露方法给父组件
defineExpose({
  // 这些方法现在需要通过 ref 调用子组件的方法
  debugDataManager,
  initDataManagerContext,
  updateSaveStatus,
  saveData,
  // 如果需要暴露子组件方法，可以通过 ref 代理
  getExcelViewerRef: () => showFlatMode.value ? flatViewer.value : originalViewer.value
})



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


/* ============ 按钮布局样式 ============ */
.header-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0; /* 防止溢出 */
}

.action-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* 保存按钮组样式 */
.save-buttons {
  display: flex;
  gap: 1px; /* 按钮组内部紧密排列 */
}

.save-buttons .el-button {
  padding: 6px 10px;
  border-radius: 0; /* 移除圆角使按钮组更紧凑 */
}

.save-buttons .el-button:first-child {
  border-top-left-radius: 4px;
  border-bottom-left-radius: 4px;
}

.save-buttons .el-button:last-child {
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .header-actions {
    gap: 6px;
  }

  .action-row {
    gap: 6px;
  }

  .save-buttons .el-button {
    padding: 5px 8px;
    font-size: 12px;
  }
}

/* 在移动设备上进一步调整 */
@media (max-width: 768px) {
  .header-actions {
    width: 100%;
  }

  .action-row {
    justify-content: flex-start;
    width: 100%;
  }

  .save-buttons {
    width: 100%;
  }

  .save-buttons .el-button {
    flex: 1; /* 等宽按钮 */
    justify-content: center;
  }
}

</style>