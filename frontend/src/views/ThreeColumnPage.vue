
<!-- frontend/src/views/ThreeColumnPage.vue -->
<template>
  <ThreeColumnLayout
    :filtered-pdf-count="filteredPdfCount"
    :table-count="tableCount"
    :is-middle-collapsed="isMiddleCollapsed"
    @toggle-middle="toggleMiddleCollapse"
  >

    <!-- 只修改模板的left部分 -->
    <template #left>
      <PdfPreview
        ref="pdfPreviewRef"
        :selected-pdf="selectedPdf"
        :pdf-url="pdfUrl"
        :current-page="currentPage"
        :download-loading="downloadLoading"
        @download-pdf="downloadPdf"
        @pdf-loaded="onPdfLoad"
      />
    </template>

    <!-- 只修改模板的middle-top部分 -->
    <template #middle-top>
      <div style="display: none;">
        {{ console.log('🔍🔍 传递给 PdfList 的数据:', { searchResults, isSearching }) }}
      </div>

      <PdfList
        :searchResults="searchResults"
        :isSearching="isSearching"
        :filteredPdfCount="filteredPdfCount"
        :selectedPdf="selectedPdf"
        @select-pdf="selectPdf"
      />
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
                               selectedSheet.excel_file === excelFile.excel_file,
                      'current-page': getPageFromSheetName(sheet.name) === currentPage
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
      <ExcelContent
          ref="excelContent"
          :key="`excel-content-${excelContentKey}`"
          :selected-sheet="selectedSheet"
          :selected-excel-file="selectedExcelFile"
          :selected-pdf="selectedPdf"
          :excel-data="excelData"
          :flat-data="flatData"
          :show-flat-mode="showFlatMode"
          :loading-excel="loadingExcel"
          :loading-flat="loadingFlat"
          :save-status="saveStatus"
          :modified-cells-count="modifiedCellsCount"
          :last-save-time="lastSaveTime"
          :saving="saving"
          :actual-has-unsaved-changes="actualHasUnsavedChanges"
          :is-dev="isDev"
          :sorted-sheets="getSortedSheets"
          @toggle-flat-mode="toggleFlatMode"
          @save-data="saveData"
          @restore-unsaved-data="restoreUnsavedData"
          @cell-changed="handleCellChanged"
          @data-changed="handleDataChanged"
          @unsaved-changes-updated="handleUnsavedChangesUpdated"
          @navigate-sheet="handleNavigateSheet"
        />
    </template>


  </ThreeColumnLayout>
</template>




<script setup>


// 这个应该放在最前面
import { ref, inject, computed, watch, onMounted, onUnmounted, nextTick, onBeforeUnmount, onUpdated, defineEmits, provide } from 'vue'
import * as ExcelKey from '@/utils/excelKeyUtils.js'

// 然后是组件导入
import ThreeColumnLayout from '@/layouts/ThreeColumnLayout.vue'
import PdfPreview from '@/components/threecolumns/PdfPreview.vue'
import PdfList from '@/components/threecolumns/PdfList.vue'
import ExcelContent from '@/components/threecolumns/ExcelContent.vue'

// 然后是工具函数
import { getApiUrl } from '@/utils/config'
import { ElMessage, ElMessageBox } from 'element-plus'


// 导入工具和组合函数
import { rebuildTwoDimensionalTable, extractTableInfoFromData } from '@/components/threecolumns/tableUtils'
import { useThreeColumnPage } from '@/components/threecolumns/useThreeColumnPage'
import { useDataManager } from '@/components/threecolumns/useDataManager'
import { useSheetOperations } from '@/components/threecolumns/useSheetOperations'

// 导入图标
import { Download, Close, Document, Grid, Loading, Timer } from '@element-plus/icons-vue'

// 导入工具
import excelDataCache from '@/utils/excelDataCache'
import dataManager from '@/utils/dataManager.js'
import sheetStateManager from '@/utils/SheetStateManager.js'

import cacheDebug from '@/utils/CacheDebugCenter';

// 新增：用于强制触发计算属性更新的响应式变量
const forceUnsavedUpdate = ref(0);
// 新增：记录当前PDF+Sheet的唯一标识（避免切换时状态混淆）


const sheetEverDirty = ref(false)


// 使用组合函数
const {
  // 状态
  selectedPdf,
  pdfUrl,
  downloadLoading,
  isMiddleCollapsed,
  showFlatMode,
  flatData,
  excelFiles,
  selectedSheet,
  selectedExcelFile,
  excelData,
  tableColumns,
  currentTableMode,

  // 计算属性
  filteredPdfCount,
  tableCount,

  // 方法
  selectPdf: selectPdfBase,
  loadExcelData,
  generateTableColumns,
  downloadPdf,
  getPageFromSheetName,
  getMaxPageFromSheets
} = useThreeColumnPage()

const {
  saving,
  saveType,
  lastSaveTime,
  saveStatus,
  modifiedCellsCount,
  initDataManagerContext,
  updateSaveStatus: updateSaveStatusUtil,
  hasUnsavedChangesInCurrentTable: hasUnsavedChangesUtil,
  saveDataFromManager
} = useDataManager()

const {
  loadingSheets,
  loadingExcel,
  loadingFlat,
  currentPage,
  totalPages,
  selectSheet: selectSheetOperation,
  toggleFlatMode: toggleFlatModeUtil,
  loadExcelSheets: loadExcelSheetsUtil,
  loadAllClassData: loadAllClassDataUtil
} = useSheetOperations(generateTableColumns)



// 🔥 完全替换 actualHasUnsavedChanges
const forceUpdateFlag = ref(0) // 强制响应式依赖
const lastGlobalState = ref(null) // 跟踪上次状态

// 🔥 监听全局状态变化
if (typeof window !== 'undefined') {
  // 每100ms检查一次全局状态
  setInterval(() => {
    const currentState = window.currentHasChanges
    if (currentState !== lastGlobalState.value) {
      console.log('🔄 全局状态变化，触发更新:', {
        旧值: lastGlobalState.value,
        新值: currentState
      })
      lastGlobalState.value = currentState
      forceUpdateFlag.value++ // 🔥 强制触发重新计算
    }
  }, 100)
}


const localSearchResults = ref([])
// 添加全局调试函数
// 修改为：
if (typeof window !== 'undefined') {
  window.debugTP = () => {
    console.log('🔍 ThreeColumnPage 调试:')
    console.log('注入的 searchResults:', searchResults.value)
    console.log('searchResults 长度:', searchResults.value.length)
    console.log('本地的 localSearchResults:', localSearchResults.value)

    if (searchResults.value.length > 0) {
      console.log('第一个文件:', searchResults.value[0])
      console.log('filename字段:', searchResults.value[0].filename)
    }
  }
}

const actualHasUnsavedChanges = computed(() => {
  // 🔥 强制依赖响应式变量
  forceUpdateFlag.value

  console.log('🔥🔥🔥 actualHasUnsavedChanges 被调用', {
    时间: new Date().toLocaleTimeString(),
    强制更新计数: forceUpdateFlag.value,
    全局状态: window.currentHasChanges
  })

  // 🔥 直接返回全局状态
  const result = typeof window !== 'undefined' ? window.currentHasChanges === true : false

  console.log('🎯 计算结果:', result)
  return result
})



// 专门用于导航切换的简单函数 - 放在 ThreeColumnPage.vue 的 setup 函数中
const navigateToSheet = async (sheet, excelFile) => {
  console.log('🧭🧭 专用导航函数: 切换到表格', {
    表格名称: sheet?.name,
    Excel文件: excelFile,
    当前选中: selectedSheet.value?.name
  })

  try {
    // 1. 安全检查
    if (!sheet || !excelFile) {
      throw new Error('导航参数缺失: sheet 或 excelFile 为空')
    }

    if (!selectedPdf.value) {
      throw new Error('请先选择PDF文件')
    }

    // 2. 如果是当前已选中的表格，直接返回（避免重复加载）
    if (selectedSheet.value?.name === sheet.name &&
        selectedExcelFile.value === excelFile) {
      console.log('📋 已是当前选中表格，跳过导航')
      return { success: true, skipped: true }
    }

    // 3. 快速更新选中状态（立即响应）
    selectedSheet.value = { ...sheet, excel_file: excelFile }
    selectedExcelFile.value = excelFile

    // 4. 清除旧数据，确保重新加载
    excelData.value = []
    flatData.value = []
    tableColumns.value = []

    // 等待DOM更新
    await nextTick()

    // 5. 直接调用数据加载，绕过复杂逻辑
    console.log('🎯 直接加载表格数据...')
    const result = await loadExcelData(sheet.name, excelFile, true) // true=强制刷新

    if (!result.success) {
      throw new Error(result.error || '数据加载失败')
    }

    // 6. 导航时默认显示原始模式，避免复杂判断
    showFlatMode.value = false
    if (currentTableMode) {
      currentTableMode.value = 'original'
    }

    console.log('✅ 专用导航完成', {
      数据行数: excelData.value?.length || 0,
      显示模式: showFlatMode.value ? '扁平化' : '原始'
    })

    return { success: true, navigated: true }

  } catch (error) {
    console.error('❌ 专用导航失败:', error)

    // 出错时恢复状态
    excelData.value = []
    flatData.value = []
    tableColumns.value = []
    showFlatMode.value = false

    ElMessage.error(`切换表格失败: ${error.message}`)
    return { success: false, error: error.message }
  }
}

// 修改现有的导航处理函数，使用专用函数
const handleNavigateSheet = async (navigationInfo) => {
  const { sheet, excelFile } = navigationInfo

  console.log('🔄 处理导航事件，使用专用导航函数')

  try {
    // 使用专用导航函数，而不是复杂的 selectSheetOperation
    const result = await navigateToSheet(sheet, excelFile)

    if (result.success) {
      if (!result.skipped) {
        console.log('✅ 导航处理完成')
      }
    } else {
      console.error('❌ 导航处理失败:', result.error)
    }

  } catch (error) {
    console.error('❌ 导航处理异常:', error)
    ElMessage.error('导航切换失败')
  }
}



// ----------------------------------------
// 获取排序后的sheet列表
const getSortedSheets = computed(() => {
  if (!excelFiles.value || excelFiles.value.length === 0) return []

  const allSheets = []

  // 收集所有sheet
  excelFiles.value.forEach(excelFile => {
    if (excelFile.sheets && Array.isArray(excelFile.sheets)) {
      excelFile.sheets.forEach(sheet => {
        const sheetInfo = parseSheetName(sheet.name)
        allSheets.push({
          ...sheet,
          excelFile: excelFile.excel_file,
          ...sheetInfo
        })
      })
    }
  })

  // 按规则排序
  return allSheets.sort((a, b) => {
    if (a.pageNumber !== b.pageNumber) {
      return a.pageNumber - b.pageNumber
    }
    if (a.tableIndex !== b.tableIndex) {
      return a.tableIndex - b.tableIndex
    }
    if (a.isStandard !== b.isStandard) {
      return a.isStandard ? -1 : 1
    }
    return a.originalName.localeCompare(b.originalName)
  })
})

// 当前sheet索引
const currentSheetIndex = computed(() => {
  if (!selectedSheet.value || !selectedExcelFile.value) return -1

  return getSortedSheets.value.findIndex(sheet =>
    sheet.name === selectedSheet.value.name &&
    sheet.excelFile === selectedExcelFile.value
  )
})

// 是否有上一页/下一页
const hasPreviousSheet = computed(() => currentSheetIndex.value > 0)
const hasNextSheet = computed(() =>
  currentSheetIndex.value >= 0 && currentSheetIndex.value < getSortedSheets.value.length - 1
)

// 当前页面信息
const currentPageInfo = computed(() => {
  if (currentSheetIndex.value < 0) return null

  const currentSheet = getSortedSheets.value[currentSheetIndex.value]

  // 获取所有不重复的页码
  const allPageNumbers = [...new Set(getSortedSheets.value
    .filter(s => s.isStandard)
    .map(s => s.pageNumber)
  )].sort((a, b) => a - b)

  const tablesInCurrentPage = getSortedSheets.value.filter(s =>
    s.pageNumber === currentSheet.pageNumber && s.isStandard
  )

  const currentPageIndex = allPageNumbers.indexOf(currentSheet.pageNumber)

  return {
    pageNumber: currentSheet.pageNumber,
    tableIndex: currentSheet.tableIndex,
    isLastTable: currentSheet.isLastTable,
    totalTablesInPage: tablesInCurrentPage.length,
    currentTablePosition: tablesInCurrentPage.findIndex(t =>
      t.name === currentSheet.name
    ) + 1,
    currentPagePosition: currentPageIndex + 1,
    totalPages: allPageNumbers.length
  }
})





// 🔥 新增：备用匹配函数
const fallbackKeyMatch = (key, currentPdfId, currentExcelFile, currentSheetName, tableType) => {
  // 方法2：使用前缀匹配（修复版）
  if (currentPdfId && currentExcelFile && currentSheetName) {
    // 修复：生成正确的前缀格式
    const expectedPrefix = `${currentPdfId}_${currentExcelFile}_${currentSheetName}_${tableType}_`;
    const simplePrefix = `${currentPdfId}_${currentExcelFile}_${currentSheetName}_`;

    const matches = key.startsWith(expectedPrefix) || key.startsWith(simplePrefix);

    if (matches) {
      console.log(`🔧 备用匹配成功: key=${key.slice(0, 60)}...`);
    }

    return matches;
  }

  // 兜底：如果无法确定上下文，认为匹配
  return true;
};

// 🔥 新增：修复 currentUniqueKey 的生成（确保一致性）
const currentUniqueKey = computed(() => {
  const pdfId = selectedPdf.value?.id;
  const excelFile = selectedExcelFile.value;
  const sheetName = selectedSheet.value?.name || selectedSheet.value;
  const tableType = showFlatMode.value ? 'flattened' : 'original';

  if (pdfId && excelFile && sheetName) {
    return `${pdfId}_${excelFile}_${sheetName}_${tableType}_`;
  }

  return '';
});


// ★ 立刻暴露，确保编译器看得见
defineExpose({ actualHasUnsavedChanges })

// ============ 组件方法 ============
const excelContentRef = ref(null)
const excelContent = ref(null)

// 中间区域折叠
const toggleMiddleCollapse = () => {
  isMiddleCollapsed.value = !isMiddleCollapsed.value
}

// PDF加载完成
const onPdfLoad = () => {
  console.log('PDF加载完成')
}

const currentData = computed(() =>
  showFlatMode.value
    ? excelContentRef.value?.flatData ?? []
    : excelContentRef.value?.tableData ?? []
)

const isDev = ref(process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'dev')



// 工具函数：不读取响应式数据，仅传参
const safeRefreshExcelContent = (hasUnsaved /* 布尔值 */) => {
  if (hasUnsaved) {
    console.log('⏸️ 编辑模式中，跳过 ExcelContent 强制刷新')
    return
  }
  excelContentKey.value++
}


// 或者更精确地，使用前缀键匹配（与 actualHasUnsavedChanges 计算一致）
const getRestorationKey = (pdfId, excelFile, sheetName, tableType) => {
  // 格式: pdfId_excelFile_sheetName_
  const prefix = ExcelKey.getPrefixKey(pdfId, excelFile, sheetName)
  return `${prefix}${tableType}`.replace(/_$/, '') // 移除末尾可能的多余下划线
}

// 注册草稿恢复任务（修正版）
const registerRestoration = (pdfId, excelFile, sheetName, tableType, draftData) => {
  const key = getRestorationKey(pdfId, excelFile, sheetName, tableType)

  // 先检查 localStorage 中是否真的有草稿
  const draftKey = ExcelKey.getDraftKey(pdfId, excelFile, sheetName, tableType)
  const raw = localStorage.getItem(draftKey)

  if (!raw) {
    console.log('📭 无草稿数据，不注册恢复任务')
    return false
  }

  pendingRestorations.value.set(key, {
    pdfId,
    excelFile,
    sheetName,
    tableType,
    draftKey, // 存储实际的 localStorage key
    draftData: JSON.parse(raw), // 重新解析确保最新
    registeredAt: Date.now(),
    attempts: 0
  })

  console.log('📝 注册草稿恢复任务:', {
    key,
    draftKey,
    修改数: JSON.parse(raw)?.modifications?.length || 0
  })
  return true
}


// 检查是否有待恢复的草稿（修正版）
const hasPendingRestoration = (pdfId, excelFile, sheetName, tableType) => {
  const key = getRestorationKey(pdfId, excelFile, sheetName, tableType)

  // 双重检查：内存中有记录 且 localStorage 中确实存在
  if (pendingRestorations.value.has(key)) {
    const record = pendingRestorations.value.get(key)
    const existsInStorage = !!localStorage.getItem(record.draftKey)

    if (!existsInStorage) {
      // 清理无效记录
      pendingRestorations.value.delete(key)
      return false
    }
    return true
  }
  return false
}


const handleCellChanged = (cellInfo) => {
  cacheDebug.log('ThreeColumnPage', 'handleCellChanged', {
    cellInfo,
    selectedPdf: selectedPdf.value?.id,
    selectedSheet: selectedSheet.value?.name,
    tableType: showFlatMode.value ? 'flattened' : 'original'
  }, {
    unsavedCellsOriginal: window.unsavedCells?.original?.size || 0,
    unsavedCellsFlattened: window.unsavedCells?.flattened?.size || 0
  });

  console.log('🔥 handleCellChanged 入口 - cellInfo:', cellInfo)
  if (!cellInfo) {
    console.warn('⚠️ cellInfo 为空，直接返回')
    return
  }

  // 检查上下文是否完整
  if (!selectedPdf.value || !selectedExcelFile.value || !selectedSheet.value) {
    console.error('❌ 上下文不完整，无法记录修改:', {
      pdf: selectedPdf.value,
      excelFile: selectedExcelFile.value,
      sheet: selectedSheet.value
    })
    return
  }

  console.log('📝 ThreeColumnPage: 收到单元格修改:', cellInfo)

  const tableType = showFlatMode.value ? 'flattened' : 'original'

  // 🔥 关键修复1：确保有活跃上下文
  if (!sheetStateManager.getActiveContext()) {
    sheetStateManager.setActiveContext(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name || selectedSheet.value, // 兼容两种格式
      tableType
    )
    console.log('🔥 创建新上下文')
  }

  // 🔥 关键修复2：记录单元格修改
  const success = sheetStateManager.recordCellChange(
    cellInfo.row,
    cellInfo.col,
    cellInfo.oldValue || '',
    cellInfo.newValue,
    tableType
  )

  console.log('🔥 记录单元格修改结果:', {
    成功: success,
    修改: { row: cellInfo.row, col: cellInfo.col },
    当前上下文: sheetStateManager.getActiveContext()
  })

  // 🔥 关键修复3：更新全局状态
  if (typeof window !== 'undefined') {
    if (!window.unsavedCells) {
      window.unsavedCells = {
        original: new Set(),
        flattened: new Set()
      }
    }

    // 生成正确的cellKey
    const cellKey = ExcelKey.getCellKey(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name || selectedSheet.value,
      tableType,
      cellInfo.row,
      cellInfo.col
    )

    console.log('🔑 生成的cellKey:', cellKey)

    // 添加到对应的集合
    window.unsavedCells[tableType].add(cellKey)

    // 设置全局修改标志
    window.currentHasChanges = true

    console.log('🌍 更新全局状态:', {
      数量: window.unsavedCells[tableType].size,
      当前单元格: cellKey,
      完整集合: Array.from(window.unsavedCells[tableType])
    })
  }

  // ✅ 一次性脏锁：只要改过一次就永远亮
  sheetEverDirty.value = true
  console.log('🔓 清除最终保存锁定，按钮应该恢复')

  // 更新保存状态
  updateSaveStatus()

  // 🔥🔥🔥 关键修复：立即更新缓存，确保扁平化使用最新数据
  if (selectedPdf.value && selectedExcelFile.value && selectedSheet.value) {
    const pdfId = selectedPdf.value.id
    const excelFile = selectedExcelFile.value
    const sheetName = selectedSheet.value.name
    const tableType = showFlatMode.value ? 'flattened' : 'original'

    try {
      // 获取当前表格实例，读取最新数据
      const hot = getActiveHotInstance()
      if (hot && !hot.isDestroyed) {
        // 获取完整的表格数据
        const fullData = hot.getSourceData()

        // 🔥🔥 立即更新缓存，确保数据同步
        if (tableType === 'original') {
          excelDataCache.setOriginalData(pdfId, excelFile, sheetName, fullData)
          console.log('💾💾 原始数据缓存已更新（实时同步）:', {
            行数: fullData.length,
            修改的单元格: `[${cellInfo.row},${cellInfo.col}]`
          })
        } else {
          excelDataCache.setFlattenedData(pdfId, excelFile, sheetName, fullData)
          console.log('💾💾 扁平化数据缓存已更新（实时同步）:', {
            行数: fullData.length,
            修改的单元格: `[${cellInfo.row},${cellInfo.col}]`
          })
        }
      }
    } catch (error) {
      console.warn('⚠️ 更新数据缓存失败:', error.message)
    }
  }

  // 自动草稿：1 秒无操作即落盘
  autoSaveDraft()

  // 🔍 新增诊断代码（放在函数末尾）
  console.log('=== 缓存诊断开始 ===')
  const draftKey = ExcelKey.getDraftKey(
    selectedPdf.value?.id,
    selectedExcelFile.value,
    selectedSheet.value?.name,
    tableType
  )

  const raw = localStorage.getItem(draftKey)
  console.log('诊断结果:', {
    缓存键: draftKey,
    是否存在: !!raw,
    内容: raw ? JSON.parse(raw) : '无数据'
  })
  console.log('=== 缓存诊断结束 ===')
}

const handleCellChanged000 = (cellInfo) => {
  cacheDebug.log('ThreeColumnPage', 'handleCellChanged', {
    cellInfo,
    selectedPdf: selectedPdf.value?.id,
    selectedSheet: selectedSheet.value?.name,
    tableType: showFlatMode.value ? 'flattened' : 'original'
  }, {
    unsavedCellsOriginal: window.unsavedCells?.original?.size || 0,
    unsavedCellsFlattened: window.unsavedCells?.flattened?.size || 0
  });

  console.log('🔥 handleCellChanged 入口 - cellInfo:', cellInfo)
  if (!cellInfo) {
    console.warn('⚠️ cellInfo 为空，直接返回')
    return
  }

  // 检查上下文是否完整
  if (!selectedPdf.value || !selectedExcelFile.value || !selectedSheet.value) {
    console.error('❌ 上下文不完整，无法记录修改:', {
      pdf: selectedPdf.value,
      excelFile: selectedExcelFile.value,
      sheet: selectedSheet.value
    })
    return
  }

  console.log('📝 ThreeColumnPage: 收到单元格修改:', cellInfo)

  const tableType = showFlatMode.value ? 'flattened' : 'original'

  // 🔥 关键修复1：确保有活跃上下文
  if (!sheetStateManager.getActiveContext()) {
    sheetStateManager.setActiveContext(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name || selectedSheet.value, // 兼容两种格式
      tableType
    )
    console.log('🔥 创建新上下文')
  }

  // 🔥 关键修复2：记录单元格修改
  const success = sheetStateManager.recordCellChange(
    cellInfo.row,
    cellInfo.col,
    cellInfo.oldValue || '',
    cellInfo.newValue,
    tableType
  )

  console.log('🔥 记录单元格修改结果:', {
    成功: success,
    修改: { row: cellInfo.row, col: cellInfo.col },
    当前上下文: sheetStateManager.getActiveContext()
  })

  // 🔥 关键修复3：更新全局状态
  if (typeof window !== 'undefined') {
    if (!window.unsavedCells) {
      window.unsavedCells = {
        original: new Set(),
        flattened: new Set()
      }
    }

    // 生成正确的cellKey
    const cellKey = ExcelKey.getCellKey(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name || selectedSheet.value,
      tableType,
      cellInfo.row,
      cellInfo.col
    )

    console.log('🔑 生成的cellKey:', cellKey)

    // 添加到对应的集合
    window.unsavedCells[tableType].add(cellKey)

    // 设置全局修改标志
    window.currentHasChanges = true

    console.log('🌍 更新全局状态:', {
      数量: window.unsavedCells[tableType].size,
      当前单元格: cellKey,
      完整集合: Array.from(window.unsavedCells[tableType])
    })
  }


  // ✅ 一次性脏锁：只要改过一次就永远亮
  sheetEverDirty.value = true
  console.log('🔓 清除最终保存锁定，按钮应该恢复')

  // 更新保存状态
  updateSaveStatus()


  if (selectedPdf.value && selectedExcelFile.value && selectedSheet.value) {
    const pdfId = selectedPdf.value.id
    const excelFile = selectedExcelFile.value
    const sheetName = selectedSheet.value.name
    const tableType = showFlatMode.value ? 'flattened' : 'original'

    try {
      // 获取当前表格实例，读取最新数据
      const hot = getActiveHotInstance()
      if (hot && !hot.isDestroyed) {
        // 获取完整的表格数据
        const fullData = hot.getSourceData()

        // 更新缓存
        if (tableType === 'original') {
          excelDataCache.setOriginalData(pdfId, excelFile, sheetName, fullData)
          console.log('📦 原始数据缓存已更新:', {
            行数: fullData.length,
            修改的单元格: `[${cellInfo.row},${cellInfo.col}]`
          })
        } else {
          excelDataCache.setFlattenedData(pdfId, excelFile, sheetName, fullData)
          console.log('📦 扁平化数据缓存已更新:', {
            行数: fullData.length,
            修改的单元格: `[${cellInfo.row},${cellInfo.col}]`
          })
        }
      }
    } catch (error) {
      console.warn('⚠️ 更新数据缓存失败:', error.message)
    }
  }


  // 自动草稿：1 秒无操作即落盘
  autoSaveDraft()   // 立即存，无防抖

  // 🔍 新增诊断代码（放在函数末尾）
  console.log('=== 缓存诊断开始 ===')
  const draftKey = ExcelKey.getDraftKey(
    selectedPdf.value?.id,
    selectedExcelFile.value,
    selectedSheet.value?.name,
    tableType
  )

  const raw = localStorage.getItem(draftKey)
  console.log('诊断结果:', {
    缓存键: draftKey,
    是否存在: !!raw,
    内容: raw ? JSON.parse(raw) : '无数据'
  })
  console.log('=== 缓存诊断结束 ===')

}



const autoSaveDraft = () => {
  if (!selectedPdf.value || !selectedSheet.value) return

  const tableType = showFlatMode.value ? 'flattened' : 'original'
  const draftKey = ExcelKey.getDraftKey(
    selectedPdf.value.id,
    selectedExcelFile.value,
    selectedSheet.value.name,
    tableType
  )

  // 获取完整表格数据
  const hot = getActiveHotInstance()
  if (!hot || hot.isDestroyed) return

  const fullData = hot.getSourceData() || []
  const modifications = Array.from(window.unsavedCells[tableType] || [])

  if (modifications.length === 0 && fullData.length === 0) return

  // 保存完整数据 + 修改记录
  const draft = {
    fullData,           // 新增：完整表格数据
    modifications,      // 原有：修改记录
    savedAt: Date.now(),
    tableType
  }

  localStorage.setItem(draftKey, JSON.stringify(draft))
  console.log('💾 缓存成功:', { 数据行数: fullData.length, 修改数: modifications.length })
}


let isRestoring = false

const handleDataChanged = (dataInfo) => {
  console.log('📥 收到批量修改:', dataInfo)

  // 检查是否有选中的 sheet 和 pdf
  if (!selectedSheet.value || !selectedPdf.value) {
    console.warn('❌ 没有选中的 sheet 或 pdf，忽略修改')
    return
  }

  // 确定当前表类型
  const currentTableType = showFlatMode.value ? 'flattened' : 'original'
  console.log('🎯 当前表类型:', currentTableType)

  // 检查是否为编辑模式
  if (!dataInfo.isEditMode || !dataInfo.hasChanges) {
    console.log('⏸️ 非编辑模式或无修改，忽略')
    return
  }

  // 关键修复：检查是否已经有活跃上下文，如果有说明已经处理过
  const context = sheetStateManager.getActiveContext()
  if (context &&
      context.pdfId === selectedPdf.value.id &&
      context.excelFile === selectedExcelFile.value &&
      context.sheetName === selectedSheet.value.name &&
      context.tableType === currentTableType) {

    console.log('✅ 已有正确上下文，跳过批量记录以避免重复')
    return
  }

  console.log(`🔄 批量记录 ${dataInfo.allChanges?.length || 0} 个修改（${currentTableType}表）`)

  // 初始化 DataManager 上下文
  initDataManagerContext(selectedPdf.value, selectedSheet.value, selectedExcelFile.value)

  if (dataInfo.allChanges && dataInfo.allChanges.length > 0) {
    dataInfo.allChanges.forEach((change) => {

      // 关键修复：检查新值是否有效，避免空值覆盖
      if (change.newValue !== null && change.newValue !== '') {

        dataManager.recordCellChange(
          change.row,
          change.col,
          change.oldValue || '',
          change.newValue,
          currentTableType
        )

        sheetStateManager.recordCellChange(
          change.row,
          change.col,
          change.oldValue || '',
          change.newValue,
          currentTableType
        )
      } else {
        console.log(`⏸️ 跳过空值修改: [${change.row},${change.col}]`)
      }
    })
  }

  updateSaveStatus()
  updateExcelContent()
  autoSaveDraft()

  // ✅ 批量改动也要置锁
    if (dataInfo.allChanges?.length) {
      sheetEverDirty.value = true
    }

}



// ============ 主要业务方法 ============
const selectPdf = async (pdf) => {
  /* 0. 跨 PDF 草稿迁移：在旧 PDF 完全失效前把草稿迁走 */
  const oldPdfId = window.currentPdfId
  const oldSheet = window.currentSheetName
  const tableType = window.currentTableMode || 'original'

  if (oldPdfId && oldSheet) {
    const oldKey = ExcelKey.getBizDraftKey(oldPdfId, oldSheet, tableType)
    const newKey = ExcelKey.getBizDraftKey(pdf.id, oldSheet, tableType)

    if (oldKey !== newKey && localStorage.getItem(oldKey)) {
      localStorage.setItem(newKey, localStorage.getItem(oldKey))

      // ✅ 迁移完成立即验证
      console.log('🚚 迁移后旧 key 还存在？', !!localStorage.getItem(oldKey))
      console.log('🚚 迁移后新 key 有数据？', !!localStorage.getItem(newKey))
      console.log('🚚 跨PDF草稿迁移', { 旧: oldKey, 新: newKey })
    }
  }

  /* 1. 原有逻辑（半点不动） */
  const result = await selectPdfBase(pdf)
  if (result.success && result.fileId) {
    // 使用 disk_name 而不是 file_id
    const pdfId = pdf.disk_name || result.fileId
    await loadExcelSheets(pdfId)
    //await loadExcelSheets(result.fileId)


  }
}


// 加载Excel sheets（包装）
const loadExcelSheets = async (pdfId) => {
  return loadExcelSheetsUtil(
    pdfId,
    getApiUrl,
    excelFiles,
    loadingSheets,
    selectSheet
  )
}


const pdfPreviewRef = ref(null)
//++++++++++++++++++++++++++++++++
const selectSheet = async (sheet, excelFileName) => {
  try {
    console.log('🎯🎯 选择Sheet:', sheet?.name)

    if (!selectedPdf.value) {
      ElMessage.error('请先选择PDF文件')
      return { success: false }
    }

    // 1. 从sheet名称提取页码
    const targetPage = getPageFromSheetName(sheet.name)
    console.log('📄📄 目标页码:', targetPage)

    // 2. 无刷新页面跳转逻辑
    if (targetPage > 0 && targetPage !== currentPage.value) {
      console.log('🔄🔄 需要跳转到页面:', targetPage)

      let jumpSuccess = false

      // 优先使用PDF.js的无刷新跳转
      if (pdfPreviewRef.value && typeof pdfPreviewRef.value.jumpToPage === 'function') {
        try {
          console.log('🔄 尝试PDF.js无刷新跳转...')
          jumpSuccess = await pdfPreviewRef.value.jumpToPage(targetPage)

          if (jumpSuccess) {
            console.log('✅ PDF.js无刷新跳转成功')
          } else {
            console.warn('⚠️ PDF.js跳转返回失败，但不使用会重新加载的备用方法')
          }
        } catch (error) {
          console.error('❌❌ PDF.js跳转执行出错:', error)
        }
      } else {
        console.warn('⚠️ PDF.js跳转方法不可用')
      }

      // 更新当前页码状态
      currentPage.value = targetPage
      console.log('✅ 页码状态已更新:', targetPage)

      // 重要：不调用会重新加载PDF的备用方法
      console.log('🚫 已禁用会重新加载PDF的备用跳转方法')
    }

    // 3. 调用sheet选择操作
    let result
    if (typeof selectSheetOperation === 'function') {
      console.log('🔄 调用selectSheetOperation...')
      result = await selectSheetOperation(
        sheet,
        excelFileName,
        selectedPdf.value,
        selectedSheet,
        selectedExcelFile,
        sheetStateManager,
        excelData,
        tableColumns,
        flatData,
        showFlatMode,
        currentTableMode,
        loadExcelData,
        loadAllClassData
      )
    } else {
      console.warn('⚠️ selectSheetOperation不存在，使用备用逻辑')
      if (typeof loadExcelData === 'function') {
        result = await loadExcelData(sheet.name, excelFileName)
      } else {
        result = { success: true }
      }
    }

    // 4. 智能检测显示模式
    if (result && result.success) {
      console.log('✅ Sheet选择成功')

      setTimeout(() => {
        const hasFlattenedData = flatData.value && flatData.value.length > 0
        const shouldShowFlatMode = hasFlattenedData && !showFlatMode.value

        if (shouldShowFlatMode) {
          showFlatMode.value = true
          console.log('✅ 检测到扁平化数据，自动切换到扁平化模式')
        }
      }, 300)
    }

    return result || { success: true }

  } catch (error) {
    console.error('❌❌ selectSheet失败:', error)
    ElMessage.error(`选择表格失败: ${error.message}`)
    return { success: false, error: error.message }
  }
}

// 完全禁用会重新加载PDF的备用方法
const jumpToPageFallback = (pageNumber) => {
  console.log('🚫🚫🚫 备用跳转方法已被禁用')
  console.warn('⚠️ 为避免PDF重新加载和流量消耗，已永久禁用iframe跳转方法')
  console.log('💡 提示：请确保PDF.js方案正常工作')
  return false
}





// useThreeColumnPage.js 中的 restoreUnsavedModifications 函数
const restoreUnsavedModifications = async (pdfId, excelFile, sheetName, tableType) => {
    console.log('🔄🔄 开始恢复未保存修改...');

    try {
        // 1. 检查是否有未保存修改
        const unsavedCells = window.unsavedCells?.[tableType];
        if (!unsavedCells || unsavedCells.size === 0) {
            console.log('📭📭 没有未保存修改需要恢复');
            return;
        }

        // 2. 获取表格实例
        const hotInstance = await getHotInstanceAsync();
        if (!hotInstance || hotInstance.isDestroyed) {
            console.warn('⚠️ 无法获取表格实例，跳过恢复');
            return;
        }

        // 3. 过滤出当前sheet的修改
        const currentSheetModifications = [];
        for (const cellKey of unsavedCells) {
            if (typeof cellKey === 'string') {
                const parsed = ExcelKey.parseCellKey(cellKey);
                if (parsed &&
                    parsed.pdfId === pdfId &&
                    parsed.excelFile === excelFile &&
                    parsed.sheetName === sheetName &&
                    parsed.tableType === tableType) {
                    currentSheetModifications.push(parsed);
                }
            }
        }

        console.log(`📝📝 找到 ${currentSheetModifications.length} 个未保存修改需要恢复`);

        if (currentSheetModifications.length === 0) {
            console.log('📭📭 当前sheet没有未保存修改');
            return;
        }

        // 4. 从localStorage获取修改的具体值
        const draftKey = ExcelKey.getDraftKey ?
            ExcelKey.getDraftKey(pdfId, excelFile, sheetName, tableType) :
            `excel_draft_${pdfId}_${excelFile}_${sheetName}_${tableType}`;

        const draftData = localStorage.getItem(draftKey);

        if (!draftData) {
            console.log('📭📭 没有找到草稿数据');
            return;
        }

        let modifications = [];
        try {
            const draft = JSON.parse(draftData);
            modifications = draft.modifications || [];
            console.log(`📦📦 从草稿中加载 ${modifications.length} 个修改`);
        } catch (e) {
            console.warn('❌❌ 解析草稿数据失败:', e);
            return;
        }

        // 5. 应用修改到表格
        if (modifications.length > 0) {
            console.log('🔄🔄 开始应用修改到表格...');

            hotInstance.suspendRender(); // 暂停渲染，提高性能

            let appliedCount = 0;
            modifications.forEach(mod => {
                try {
                    // 检查行列是否有效
                    if (mod.row >= 0 && mod.col >= 0 &&
                        mod.row < hotInstance.countRows() &&
                        mod.col < hotInstance.countCols()) {

                        // 应用新值到表格
                        hotInstance.setDataAtCell(mod.row, mod.col, mod.newValue, 'restore');
                        appliedCount++;

                        console.log(`✅ 恢复修改: [${mod.row},${mod.col}] = "${mod.newValue}"`);
                    }
                } catch (error) {
                    console.warn(`⚠️ 恢复修改失败 [${mod.row},${mod.col}]:`, error);
                }
            });

            hotInstance.resumeRender(); // 恢复渲染
            console.log(`🎯🎯 成功应用 ${appliedCount} 个修改到表格`);

            if (appliedCount > 0) {
                ElMessage.success(`已恢复 ${appliedCount} 处未保存修改`);
            }
        }

    } catch (error) {
        console.error('❌❌ 恢复未保存修改失败:', error);
    }
};


// 提取草稿恢复逻辑
const restoreDraftIfNeeded = async (hot, pdfId, excelFile, sheetName, tableType) => {
  try {
    const key = ExcelKey.getBizDraftKey(pdfId, sheetName, tableType)
    const raw = localStorage.getItem(key)

    if (!raw) return

    const draft = JSON.parse(raw)
    if (!draft.modifications?.length) return

    console.log('🟢 恢复草稿数据:', draft.modifications.length, '处修改')

    hot.suspendRender()
    draft.modifications.forEach(m => {
      if (m.row >= 0 && m.col >= 0) {
        hot.setDataAtCell(m.row, m.col, m.newValue, 'restore')
      }
    })
    hot.resumeRender()

  } catch (error) {
    console.warn('⚠️ 草稿恢复非致命错误:', error.message)
    // 不阻断主流程
  }
}



// 加载所有班级数据（包装）
const loadAllClassData = async (excelFileName) => {
  return loadAllClassDataUtil(
    excelFileName,
    selectedPdf.value,
    getApiUrl,
    excelData,
    tableColumns
  )
}




const toggleFlatMode000 = async () => {
  console.log('🔄🔄 切换扁平化模式...')

  if (!selectedSheet.value || !selectedPdf.value) {
    ElMessage.warning('请先选择表格')
    return
  }

  try {
    const wasFlatMode = showFlatMode.value

    // 扁平化文件特殊处理
    const isFlattenedFile = selectedExcelFile.value && selectedExcelFile.value.toLowerCase().includes('flattened_')
    if (isFlattenedFile) {
      console.log('✅ 扁平化文件，只切换显示模式')
      showFlatMode.value = !wasFlatMode
      currentTableMode.value = showFlatMode.value ? 'flattened' : 'original'
      if (window.currentTableMode) {
        window.currentTableMode = currentTableMode.value
      }
      return
    }

    console.log('🔄🔄 非扁平化文件，执行正常切换逻辑')

    if (!wasFlatMode) {
      // 🔥🔥 切换到扁平化模式 - 强制使用实时数据
      console.log('🔀🔀🔀🔀 强制切换到扁平化模式（绕过缓存）')

      const pdfId = String(selectedPdf.value.id) // 修复数据类型
      const excelFile = selectedExcelFile.value
      const sheetName = selectedSheet.value.name

      // 🔥🔥 关键修复：强制清除所有缓存
      console.log('🧹🧹🧹🧹 强制清除所有缓存')

      // 清除会话缓存
      if (sessionCacheManager) {
        sessionCacheManager.delete(pdfId, excelFile, sheetName)
        console.log('✅ 清除会话缓存')
      }

      // 清除内存缓存
      const cacheKey = `${pdfId}_${excelFile}_${sheetName}`
      if (window.sheetDataCache) {
        delete window.sheetDataCache[cacheKey]
        console.log('✅ 清除内存缓存')
      }

      // 清除其他缓存
      if (excelDataCache) {
        if (excelDataCache.deleteFlattenedData) {
          excelDataCache.deleteFlattenedData(pdfId, excelFile, sheetName)
          console.log('✅ 清除excelDataCache缓存')
        }
      }

      // 🔥🔥 强制设置空数据，确保重新生成
      flatData.value = []
      await nextTick() // 等待DOM更新

      console.log('🎯🎯 强制使用实时数据生成...')

      // 直接调用实时生成函数，不检查缓存
      await generateFlattenedDataWithRealTimeData(pdfId, excelFile, sheetName)

      console.log('✅✅ 实时数据生成完成')

    } else {
      // 切换回原始模式
      console.log('🔀🔀🔀🔀 切换回原始模式')
      sheetStateManager.setActiveContext(
        selectedPdf.value.id,
        selectedExcelFile.value,
        selectedSheet.value.name,
        'original'
      )
      showFlatMode.value = false
      flatData.value = []

      if (selectedSheet.value) {
        await loadExcelData(selectedSheet.value.name, selectedExcelFile.value)
      }
      ElMessage.success('已切换回原始模式')
    }

  } catch (error) {
    console.error('❌❌ 切换失败:', error)
    ElMessage.error(`切换失败: ${error.message}`)
    // 出错时回退到原始模式
    showFlatMode.value = false
    flatData.value = []
  }
}


const toggleFlatMode = async () => {
  console.log('🔄🔄 切换扁平化模式...')

  if (!selectedSheet.value || !selectedPdf.value) {
    ElMessage.warning('请先选择表格')
    return
  }

  try {
    const wasFlatMode = showFlatMode.value

    // 扁平化文件特殊处理
    const isFlattenedFile = selectedExcelFile.value && selectedExcelFile.value.toLowerCase().includes('flattened_')
    if (isFlattenedFile) {
      console.log('✅ 扁平化文件，只切换显示模式')
      showFlatMode.value = !wasFlatMode
      // 🔥🔥 修复：移除不存在的 currentTableMode 引用
      // currentTableMode.value = showFlatMode.value ? 'flattened' : 'original' // ❌ 删除这行
      if (window.currentTableMode) {
        window.currentTableMode = showFlatMode.value ? 'flattened' : 'original' // ✅ 直接设置
      }
      return
    }

    console.log('🔄🔄 非扁平化文件，执行正常切换逻辑')

    if (!wasFlatMode) {
      // 🔥🔥 切换到扁平化模式 - 强制使用实时数据
      console.log('🔀🔀🔀🔀 强制切换到扁平化模式（绕过缓存）')

      const pdfId = String(selectedPdf.value.id) // 修复数据类型
      const excelFile = selectedExcelFile.value
      const sheetName = selectedSheet.value.name

      // 🔥🔥 关键修复：强制清除所有缓存
      console.log('🧹🧹🧹🧹 强制清除所有缓存')

      // 清除会话缓存
      if (sessionCacheManager) {
        sessionCacheManager.delete(pdfId, excelFile, sheetName)
        console.log('✅ 清除会话缓存')
      }

      // 清除内存缓存
      const cacheKey = `${pdfId}_${excelFile}_${sheetName}`
      if (window.sheetDataCache) {
        delete window.sheetDataCache[cacheKey]
        console.log('✅ 清除内存缓存')
      }

      // 清除其他缓存
      if (excelDataCache) {
        if (excelDataCache.deleteFlattenedData) {
          excelDataCache.deleteFlattenedData(pdfId, excelFile, sheetName)
          console.log('✅ 清除excelDataCache缓存')
        }
      }

      // 🔥🔥 强制设置空数据，确保重新生成
      flatData.value = []
      await nextTick() // 等待DOM更新

      console.log('🎯🎯 强制使用实时数据生成...')

      // 直接调用实时生成函数，不检查缓存
      await generateFlattenedDataWithRealTimeData(pdfId, excelFile, sheetName)

      // 🔥🔥 修复：设置窗口状态
      if (window.currentTableMode) {
        window.currentTableMode = 'flattened'
      }

      console.log('✅✅ 实时数据生成完成')

    } else {
      // 切换回原始模式
      console.log('🔀🔀🔀🔀 切换回原始模式')
      sheetStateManager.setActiveContext(
        selectedPdf.value.id,
        selectedExcelFile.value,
        selectedSheet.value.name,
        'original'
      )
      showFlatMode.value = false
      flatData.value = []

      // 🔥🔥 修复：设置窗口状态
      if (window.currentTableMode) {
        window.currentTableMode = 'original'
      }

      if (selectedSheet.value) {
        await loadExcelData(selectedSheet.value.name, selectedExcelFile.value)
      }
      ElMessage.success('已切换回原始模式')
    }

  } catch (error) {
    console.error('❌❌ 切换失败:', error)
    ElMessage.error(`切换失败: ${error.message}`)
    // 出错时回退到原始模式
    showFlatMode.value = false
    flatData.value = []

    // 🔥🔥 修复：出错时也设置状态
    if (window.currentTableMode) {
      window.currentTableMode = 'original'
    }
  }
}


// 在 toggleFlatMode 函数之前添加这个函数
const generateFlattenedDataWithRealTimeData = async (pdfId, excelFile, sheetName) => {
  console.log('🎯🎯 使用实时数据生成扁平化数据...')

  try {
    // 🔥🔥🔥 关键修复1：检查编辑模式
    const isEditing = window.isEditMode?.value || false
    if (isEditing) {
      console.error('❌❌❌❌ 错误：编辑模式下禁止数据扁平化！')
      ElMessage.error('当前处于编辑模式，请先退出编辑模式再进行扁平化操作')
      throw new Error('编辑模式下禁止数据转换')
    }

    // 🔥🔥🔥 关键修复2：检查必要的全局变量
    if (typeof window === 'undefined' || !window.flatData || !window.showFlatMode) {
      console.error('❌❌❌❌ 错误：缺少必要的全局变量')
      throw new Error('系统环境不完整，无法进行数据转换')
    }

    // 🔥🔥 再次确认清除缓存
    if (sessionCacheManager) {
      sessionCacheManager.delete(pdfId, excelFile, sheetName)
      console.log('✅ 会话缓存已清除')
    }

    // 获取当前表格数据
    const hotInstance = getHotInstanceWithCache ? getHotInstanceWithCache() : window.hotInstance
    if (!hotInstance || hotInstance.isDestroyed) {
      console.error('❌❌ 无法获取有效的表格实例')
      throw new Error('表格实例无效或已销毁')
    }

    const currentTableData = hotInstance.getSourceData()
    console.log('📊📊 实时表格数据:', {
      行数: currentTableData?.length || 0,
      数据类型: Array.isArray(currentTableData) ? '数组' : typeof currentTableData
    })

    if (!currentTableData || currentTableData.length === 0) {
      throw new Error('表格数据为空')
    }

    // 🔥🔥🔥 关键修复3：安全的数据转换
    let tableData = currentTableData

    // 检查是否需要重建二维表格
    if (typeof rebuildTwoDimensionalTable === 'function') {
      try {
        tableData = rebuildTwoDimensionalTable(currentTableData)
        console.log('✅ 重建的二维表格:', {
          行数: tableData.length,
          列数: tableData[0]?.length || 0
        })
      } catch (error) {
        console.warn('⚠️ 二维表格重建失败，使用原始数据:', error)
        tableData = currentTableData
      }
    } else {
      console.log('ℹ️  rebuildTwoDimensionalTable 函数不存在，使用原始数据')
      tableData = currentTableData
    }

    if (!tableData || tableData.length === 0) {
      throw new Error('无法获取有效的表格数据')
    }

    // 准备API请求
    const requestData = {
      table_data: tableData,
      table_metadata: {
        name: sheetName,
        pdf_id: pdfId,
        excel_file: excelFile
      },
      marks_info: {
        row_marks: [],
        col_marks: [],
        timestamp: Date.now()
      }
    }

    console.log('📤📤 发送实时API请求...', {
      表名: sheetName,
      数据行数: tableData.length,
      请求大小: JSON.stringify(requestData).length
    })

    const response = await fetch(getApiUrl('/excel-flatten'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-Source': 'frontend-realtime'
      },
      body: JSON.stringify(requestData)
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ API请求失败:', { status: response.status, error: errorText })
      throw new Error(`API请求失败: HTTP ${response.status} - ${errorText}`)
    }

    const result = await response.json()
    console.log('📥📥 API响应:', {
      成功: result.success,
      数据行数: result.rows?.length || result.data?.length || 0
    })

    if (result.success) {
      let flattenedData = []

      // 安全解析响应数据
      if (result.rows && Array.isArray(result.rows)) {
        flattenedData = result.rows
      } else if (result.long_format_data && Array.isArray(result.long_format_data)) {
        flattenedData = result.long_format_data
      } else if (result.data && Array.isArray(result.data)) {
        flattenedData = result.data
      } else if (Array.isArray(result)) {
        flattenedData = result
      } else {
        // 尝试查找响应中的第一个数组字段
        for (const key in result) {
          if (Array.isArray(result[key]) && result[key].length > 0) {
            flattenedData = result[key]
            console.log('🔍 从字段获取数据:', key)
            break
          }
        }
      }

      if (flattenedData.length > 0) {
        console.log('✅ 实时数据生成成功:', {
          数据行数: flattenedData.length,
          第一行样本: flattenedData[0]
        })

        // 🔥🔥🔥 关键修复4：安全设置数据
        try {
          // 使用全局变量设置数据
          if (window.flatData && typeof window.flatData.value !== 'undefined') {
            window.flatData.value = flattenedData
          } else {
            console.warn('⚠️  window.flatData 不可用，尝试直接设置')
            flatData.value = flattenedData
          }

          if (window.showFlatMode && typeof window.showFlatMode.value !== 'undefined') {
            window.showFlatMode.value = true
          } else {
            showFlatMode.value = true
          }

          console.log('✅ 数据设置完成', {
            扁平化数据行数: flattenedData.length,
            显示模式: true
          })

          ElMessage.success(`扁平化数据生成成功（${flattenedData.length}行）`)
          return flattenedData

        } catch (setError) {
          console.error('❌❌ 设置数据失败:', setError)
          throw new Error(`数据设置失败: ${setError.message}`)
        }

      } else {
        console.warn('⚠️ API返回空数据，响应结构:', Object.keys(result))
        throw new Error('API返回空数据或数据格式不正确')
      }
    } else {
      throw new Error(result.error || result.message || 'API处理失败')
    }

  } catch (error) {
    console.error('❌❌ 实时数据生成失败:', error)

    // 出错时确保状态正确
    if (window.showFlatMode && typeof window.showFlatMode.value !== 'undefined') {
      window.showFlatMode.value = false
    } else if (showFlatMode) {
      showFlatMode.value = false
    }

    ElMessage.error(`扁平化失败: ${error.message}`)
    throw error
  }
}



// 在 ThreeColumnPage.vue 中添加新函数
const convertToFlatDataWithRealTimeData = async (tableData, pdfId, excelFile, sheetName) => {
  console.log('🔄🔄 使用实时数据进行扁平化处理...')

  try {
    // 准备请求数据
    const requestData = {
      table_data: tableData,
      table_metadata: {
        name: sheetName
      },
      marks_info: {
        row_marks: [],  // 后端会智能处理
        col_marks: []   // 后端会智能处理
      }
    }

    console.log('📤📤 发送扁平化请求数据（实时数据）:', {
      表数据行数: requestData.table_data.length,
      表数据列数: requestData.table_data[0]?.length || 0,
      表格名称: sheetName
    })

    // 调用扁平化API
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
    console.log('📥📥 扁平化API返回数据:', result)

    // 处理API响应
    if (result.success) {
      let flattenedData = []

      // 处理多种可能的响应格式
      if (result.rows && Array.isArray(result.rows)) {
        flattenedData = result.rows
      } else if (result.long_format_data && Array.isArray(result.long_format_data)) {
        flattenedData = result.long_format_data
      } else if (result.data && Array.isArray(result.data)) {
        flattenedData = result.data
      } else if (Array.isArray(result)) {
        flattenedData = result
      } else {
        // 尝试查找响应中的第一个数组字段
        for (const key in result) {
          if (Array.isArray(result[key])) {
            flattenedData = result[key]
            break
          }
        }
      }

      if (flattenedData.length > 0) {
        console.log('✅ 接收到扁平化数据（实时）:', {
          总行数: flattenedData.length,
          第一行样本: flattenedData[0]
        })

        // 保存到缓存
        excelDataCache.setFlattenedData(pdfId, excelFile, sheetName, flattenedData)

        // 缓存到 IndexedDB
        try {
          await dataManager.saveFlattenedData(flattenedData, tableData)
        } catch (cacheError) {
          console.warn('缓存到 IndexedDB 失败:', cacheError)
        }

        // 更新状态
        const currentContext = sheetStateManager.getActiveContext()
        if (currentContext &&
            currentContext.pdfId === pdfId &&
            currentContext.excelFile === excelFile &&
            currentContext.sheetName === sheetName) {
          sheetStateManager.setData('flattened', flattenedData)
        }

        // 显示扁平化数据
        flatData.value = flattenedData
        showFlatMode.value = true

        ElMessage.success(`数据扁平化成功，生成 ${flattenedData.length} 行数据`)

      } else {
        console.log('📝📝 表格为空或无数据可转换')
        flatData.value = []
        showFlatMode.value = true
        ElMessage.info('表格为空或无数据可转换')
      }

    } else {
      throw new Error(result.error || '后端处理失败')
    }

  } catch (error) {
    console.error('❌❌ 数据扁平化失败:', error)
    throw error // 重新抛出错误
  }
}



// 添加清除缓存的方法
const clearFlattenedCache = async (pdfId, excelFile, sheetName) => {
  try {
    console.log('🧹 清除扁平化缓存...')

    // 1. 清除 IndexedDB 缓存
    if (dataManager && dataManager.indexedDBManager) {
      // 设置上下文
      dataManager.setContext({ pdfId, excelFile, sheetName })

      // 尝试删除缓存
      await dataManager.indexedDBManager.deleteFlattenedCache(pdfId, excelFile, sheetName)
      console.log('✅ IndexedDB 缓存已清除')
    }

    // 2. 清除内存缓存（如果有）
    if (excelDataCache) {
      // 尝试不同的方法名
      const clearMethods = ['deleteFlattenedData', 'removeFlattenedData', 'clearFlattenedData']
      for (const method of clearMethods) {
        if (typeof excelDataCache[method] === 'function') {
          excelDataCache[method](pdfId, excelFile, sheetName)
          console.log(`✅ 使用 ${method} 清除内存缓存`)
          break
        }
      }

      // 如果以上方法都不存在，尝试设置为 null
      if (typeof excelDataCache.setFlattenedData === 'function') {
        excelDataCache.setFlattenedData(pdfId, excelFile, sheetName, null)
        console.log('✅ 通过设置为 null 清除内存缓存')
      }
    }

  } catch (error) {
    console.warn('⚠️ 清除缓存时出错:', error.message)
    // 不清除缓存不是致命错误，继续执行
  }
}


/**
 * 恢复 localStorage 草稿
 * @param {boolean} silent - true=静默恢复/false=弹框询问
 */
const restoreDraftIfExists = (pdfId, excelFile, sheetName, tableType, silent = false) => {

  const key = ExcelKey.getBizDraftKey(pdfId, sheetName, tableType)
  const raw = localStorage.getItem(key)
  if (!raw) return

  let draft
  try {
    draft = JSON.parse(raw)
  } catch (e) {
    console.error('❌ 草稿解析失败:', e)
    return
  }

  if (!draft.modifications?.length) return

  // 静默模式：直接恢复
  if (silent) {
    applyDraftModifications(draft, tableType)
    console.log('✅ 草稿已静默恢复', draft.modifications.length, '处')
    return
  }

  // 非静默：弹框询问
  ElMessageBox.confirm(
    `检测到未提交的草稿（${draft.modifications.length} 处修改），是否恢复？`,
    '草稿恢复',
    {
      confirmButtonText: '恢复',
      cancelButtonText: '丢弃',
      type: 'info'
    }
  ).then(() => {
    applyDraftModifications(draft, tableType)
    ElMessage.success('草稿已恢复，可继续编辑')
  }).catch(() => {
    localStorage.removeItem(key)
    ElMessage.info('已丢弃草稿')
  })
}



const applyDraftModifications = async (draft, tableType) => {
  // ✅ 先确保基础数据存在
  if (draft.fullData) {
    // 重新设置完整数据
    if (tableType === 'original') {
      excelData.value = draft.fullData
    } else {
      flatData.value = draft.fullData
    }
    await nextTick()
  }

  // 然后再恢复修改
  const hot = getActiveHotInstance()
  if (hot && !hot.isDestroyed) {
    hot.suspendRender()
    draft.modifications.forEach(item => {
      hot.setDataAtCell(item.row, item.col, item.newValue, 'restore')
    })
    hot.resumeRender()
  }
}


// 更新保存状态（包装）
const updateSaveStatus = () => {
  updateSaveStatusUtil(selectedSheet.value, selectedPdf.value, sheetStateManager)
}


const hasUnsavedChangesInCurrentTable = () => {
  // 1. 必须选中有表格
  if (!selectedSheet.value) {
    console.log('❌ 没有选中表格，保存按钮禁用')
    return false
  }

  // 2. 直接看当前表格的实际数据（这是最可靠的）
  const tableType = showFlatMode.value ? 'flattened' : 'original'

  /* ===== 新增：最终保存锁定（只影响 final，不影响 draft） ===== */
  const lastFinal = sheetStateManager.getLastFinalSavedCount(tableType)
  if (lastFinal !== null) {
    const nowSaved = sheetStateManager.getSavedCount(tableType)
    if (nowSaved <= lastFinal) {
      console.log('🔒 已最终保存，无新修改，锁定存后台按钮')
      return false          // 直接锁死，下面逻辑不再走
    }
  }
  /* =========================================================== */

  const currentData = showFlatMode.value ? excelContentRef.value?.flatData ?? [] : excelContentRef.value?.tableData ?? []


  console.log('🔍 检查保存条件:', {
    表格: selectedSheet.value.name,
    表类型: tableType,
    数据行数: currentData?.length || 0,
    全局修改数: window.unsavedCells?.size || 0
  })

  // 3. 关键修复：直接检查 sheetStateManager 中当前表格的修改
  if (sheetStateManager) {
    const context = sheetStateManager.getActiveContext()
    if (context &&
        context.pdfId === selectedPdf.value?.id &&
        context.excelFile === selectedExcelFile.value &&
        context.sheetName === selectedSheet.value.name &&
        context.tableType === tableType) {

      const hasChanges = sheetStateManager.hasUnsavedChanges(tableType)
      console.log('✅ sheetStateManager 确认有修改:', hasChanges)
      return hasChanges
    }
  }

  // 4. 如果状态管理器没找到，再看全局状态
  const hasGlobalChanges = window.unsavedCells?.size > 0
  console.log('🌍 使用全局状态判断:', hasGlobalChanges)

  return hasGlobalChanges
}

// 添加一个强制更新的 key
const excelContentKey = ref(0)


// 在 ThreeColumnPage.vue 中
const monitorSaveButtons = () => {
  // 只在开发环境运行
  if (!isDev.value) return

  // 清除之前的定时器
  if (window.saveButtonMonitorInterval) {
    clearInterval(window.saveButtonMonitorInterval)
  }

  // 设置新的定时器
  window.saveButtonMonitorInterval = setInterval(() => {
    // 这里先暂时注释掉，避免干扰
    // 等调试完成后再启用
  }, 3000) // 3秒检查一次
}


// 在 ThreeColumnPage.vue 中添加调试
const debugPropsToExcelContent = computed(() => {
  const result = {
    selectedSheet: selectedSheet.value?.name,
    hasUnsavedChanges: actualHasUnsavedChanges.value,
    actualHasUnsavedChangesValue: actualHasUnsavedChanges.value,
    modifiedCellsCount: modifiedCellsCount.value
  }

  console.log('🚨 ThreeColumnPage -> ExcelContent 传递的值:', result)
  return result
})




// 组合方案1和方案3
const goToPreviousSheet = async () => {
  if (!hasPreviousSheet.value) return

  const previousSheet = getSortedSheets.value[currentSheetIndex.value - 1]
  console.log('📄📄📄📄 导航到上一表格')

  try {
    // === 方案1：修复调用顺序 ===

    // 1. 先停止所有进行中的操作
    if (loadingExcel.value) {
      console.log('⏸⏸ 停止当前加载中的操作')
      // 这里可以添加取消逻辑
    }

    // 2. 立即更新当前sheet状态
    selectedSheet.value = { ...previousSheet }
    selectedExcelFile.value = previousSheet.excelFile

    // 3. 清空旧数据，确保重新加载
    excelData.value = []
    flatData.value = []
    tableColumns.value = []

    // 4. 等待DOM更新
    await nextTick()

    // 5. 使用专用的同步导航函数
    const navResult = await navigateToSheet(previousSheet, previousSheet.excelFile)

    if (!navResult.success) {
      throw new Error(navResult.error || '导航失败')
    }

    // === 方案3：数据加载状态监控 ===

    // 6. 等待数据加载完成
    try {
      await waitForDataLoad(5000) // 5秒超时
      console.log('✅ 数据加载确认完成')
    } catch (error) {
      console.warn('⚠️ 数据加载可能未完成:', error.message)
      // 不抛出错误，继续执行后续操作
    }

    // 7. 最后进行PDF页面跳转
    const targetPage = getPageFromSheetName(previousSheet.name)
    if (pdfPreviewRef.value && targetPage > 0) {
      // 使用setTimeout确保数据加载优先
      setTimeout(() => {
        pdfPreviewRef.value.jumpToPage(targetPage)
        currentPage.value = targetPage
      }, 100)
    }

    console.log('✅ 上一页导航完成')
  } catch (error) {
    console.error('❌❌ 上一页导航失败:', error)
    ElMessage.error(`切换表格失败: ${error.message}`)
  }
}

// 方案3的数据加载监控函数
const waitForDataLoad = async (timeout = 3000) => {
  const startTime = Date.now()

  while (Date.now() - startTime < timeout) {
    // 根据当前模式检查对应的数据
    const currentData = showFlatMode.value ? flatData.value : excelData.value
    if (currentData && currentData.length > 0) {
      console.log('✅ 数据加载完成，行数:', currentData.length)
      return true // 数据已加载
    }
    await new Promise(resolve => setTimeout(resolve, 100))
  }

  throw new Error(`数据加载超时（${timeout}ms）`)
}

// 同样修复下一页函数
const goToNextSheet = async () => {
  if (!hasNextSheet.value) return

  const nextSheet = getSortedSheets.value[currentSheetIndex.value + 1]
  console.log('📄📄📄📄 导航到下一表格')

  try {
    // === 方案1：修复调用顺序 ===
    if (loadingExcel.value) {
      console.log('⏸⏸ 停止当前加载中的操作')
    }

    selectedSheet.value = { ...nextSheet }
    selectedExcelFile.value = nextSheet.excelFile
    excelData.value = []
    flatData.value = []
    tableColumns.value = []

    await nextTick()

    const navResult = await navigateToSheet(nextSheet, nextSheet.excelFile)
    if (!navResult.success) {
      throw new Error(navResult.error || '导航失败')
    }

    // === 方案3：数据加载状态监控 ===
    try {
      await waitForDataLoad(5000)
      console.log('✅ 数据加载确认完成')
    } catch (error) {
      console.warn('⚠️ 数据加载可能未完成:', error.message)
    }

    const targetPage = getPageFromSheetName(nextSheet.name)
    if (pdfPreviewRef.value && targetPage > 0) {
      setTimeout(() => {
        pdfPreviewRef.value.jumpToPage(targetPage)
        currentPage.value = targetPage
      }, 100)
    }

    console.log('✅ 下一页导航完成')
  } catch (error) {
    console.error('❌❌ 下一页导航失败:', error)
    ElMessage.error(`切换表格失败: ${error.message}`)
  }
}


// 修改 sessionCacheManager 的 set 方法，添加调试日志
const sessionCacheManager = {
  cache: new Map(),

  getKey(pdfId, excelFile, sheetName) {
    return `${pdfId}_${excelFile}_${sheetName}`
  },

  get(pdfId, excelFile, sheetName) {
    const key = this.getKey(pdfId, excelFile, sheetName)
    const data = this.cache.get(key)
    console.log('🔍🔍 会话缓存检查:', {
      key,
      存在缓存: !!data,
      缓存数据长度: data?.length || 0
    })
    return data
  },

  set(pdfId, excelFile, sheetName, data) {
    const key = this.getKey(pdfId, excelFile, sheetName)
    console.log('💾💾 设置会话缓存:', {
      key,
      数据长度: data?.length || 0,
      调用栈: new Error().stack // 显示调用来源
    })
    this.cache.set(key, data)
  },

  delete(pdfId, excelFile, sheetName) {
    const key = this.getKey(pdfId, excelFile, sheetName)
    console.log('🧹🧹 删除会话缓存:', { key })
    this.cache.delete(key)
  },

  clear() {
    console.log('🧹🧹 清空所有会话缓存')
    this.cache.clear()
  }
}


// 页面卸载时清理缓存
onUnmounted(() => {
  sessionCacheManager.clear()
})



// 在 ThreeColumnPage.vue 的模板部分，检查 ExcelContent 组件的使用
watch(() => actualHasUnsavedChanges.value, (newVal) => {
  console.log('🚨 ThreeColumnPage -> ExcelContent: 传递 hasUnsavedChanges', {
    值: newVal,
    时间: new Date().toLocaleTimeString(),
    类型: typeof newVal
  })

  // 验证传递给 ExcelContent 的值 - 修复这里的语法错误
  console.log('📤 传递给 ExcelContent 的 props:', {
    selectedSheet: selectedSheet.value?.name,
    hasUnsavedChanges: newVal,
    modifiedCellsCount: modifiedCellsCount.value
  })
}, { immediate: true })


// 或者在 render 时检查
onUpdated(() => {
  console.log('🔄 ThreeColumnPage 更新，actualHasUnsavedChanges:', actualHasUnsavedChanges.value)
})


// 监听 ExcelContent 的 unsaved-changes-updated 事件
const handleUnsavedChangesUpdated = (hasChanges) => {
  console.log('📤 ThreeColumnPage: 收到 unsaved-changes-updated 事件', {
    是否有修改: hasChanges,
    时间: new Date().toLocaleTimeString()
  })

  // 这里可以更新页面状态或触发其他操作
  // 例如更新页面标题或显示提示
  if (hasChanges) {
    document.title = `* ${selectedSheet.value?.name} - 表格编辑`
  } else {
    document.title = `${selectedSheet.value?.name} - 表格编辑`
  }
}


// ==========  工具：异步等 Handsontable 实例  ==========

/**
 * 恢复 localStorage 草稿
 * 带详细日志，方便确认数据差异
 */
const restoreDraft = async () => {
  if (isRestoring) return
  isRestoring = true

  try {
    console.log('🔄 开始恢复草稿流程...')

    if (!selectedPdf.value || !selectedSheet.value || !selectedExcelFile.value) {
      console.log('⏹️ 缺少必要参数')
      return
    }

    const tableType = showFlatMode.value ? 'flattened' : 'original'
    const draftKey = ExcelKey.getDraftKey(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name,
      tableType
    )
    const raw = localStorage.getItem(draftKey)
    if (!raw) {
      console.log('📭 无草稿数据')
      return
    }

    let draft
    try {
      draft = JSON.parse(raw)
    } catch (e) {
      console.error('❌ 草稿解析失败:', e)
      return
    }

    console.log('📦 草稿内容:', {
      修改条数: draft.modifications?.length || 0,
      表类型: draft.tableType,
      保存时间: draft.timestamp ? new Date(draft.timestamp).toLocaleString() : '未知'
    })

    if (!draft.modifications || draft.modifications.length === 0) {
      console.log('📭 草稿中无修改内容')
      return
    }

    let hot = null
    while (!hot) {
      hot = await getHotInstanceAsync()
      if (!hot) {
        console.log('⏳ 实例未就绪，等待 200ms 后重试...')
        await new Promise(r => setTimeout(r, 200))
      }
    }

    console.log('✅ 成功获取表格实例')

    const viewer = showFlatMode.value
      ? excelContent.value?.$refs?.flatViewer
      : excelContent.value?.$refs?.originalViewer

    if (!viewer) {
      console.error('❌ 无法获取表格组件')
      ElMessage.warning('表格组件未加载')
      return
    }

    const maxRow = hot.countRows()
    const maxCol = hot.countCols()

    const validChanges = draft.modifications
      .filter(m => {
        const r = Number(m.row)
        const c = Number(m.col)
        return Number.isInteger(r) && r >= 0 && r < maxRow &&
               Number.isInteger(c) && c >= 0 && c < maxCol
      })
      .map(m => [Number(m.row), Number(m.col), m.newValue || ''])

    if (validChanges.length > 0) {
      try {
        hot.suspendRender()
        for (const change of validChanges) {
          hot.setDataAtCell(change[0], change[1], change[2])
        }
        hot.resumeRender()
        console.log(`✅ 已应用 ${validChanges.length} 处修改`)
      } catch (error) {
        console.error('❌ 应用修改失败:', error)
        validChanges.forEach(change => {
          try {
            hot.setDataAtCell(change[0], change[1], change[2])
          } catch (e) {
            console.warn('设置单元格失败:', change, e)
          }
        })
      }
    }

    draft.modifications.forEach(m => {
      sheetStateManager.recordCellChange(m.row, m.col, m.oldValue, m.newValue, tableType)
    })

    if (typeof window !== 'undefined') {
      // 只恢复当前表类型的修改
      const cells = new Set(draft.modifications.map(m =>
           ExcelKey.getCellKey(
             selectedPdf.value.id,
             selectedExcelFile.value,
             selectedSheet.value.name,
             tableType,
             m.row,
             m.col
           )
         ))

      window.unsavedCells[tableType] = cells
      window.currentHasChanges = cells.size > 0
    }

    if (viewer.updateModifiedCellsStyle) {
      viewer.updateModifiedCellsStyle()
    }

    updateSaveStatus()
    ElMessage.success(`已恢复 ${draft.modifications.length} 处修改`)
  } finally {
    isRestoring = false
  }
}



// 修复 markCacheAsBackendData 函数
const markCacheAsBackendData = () => {
    // 🔥🔥 关键修复：使用正确的参数来源
    const pdfId = selectedPdf.value?.id;
    const excelFile = selectedExcelFile.value; // 直接使用响应式变量
    const sheetName = selectedSheet.value?.name;

    if (!pdfId || !excelFile || !sheetName) {
        console.warn('❌ 标记缓存失败：参数不完整', { pdfId, excelFile, sheetName });
        return;
    }

    const tableType = showFlatMode.value ? 'flattened' : 'original';

    try {
        const cacheKey = `${pdfId}_${excelFile}_${sheetName}`;

        console.log('🏷️🏷️ 设置后端数据标记:', { cacheKey, tableType });

        // 设置全局标记
        if (!window.cacheMetadata) window.cacheMetadata = {};
        window.cacheMetadata[cacheKey] = {
            source: 'backend',
            lastSaved: Date.now(),
            tableType: tableType,
            pdfId: pdfId,
            excelFile: excelFile,
            sheetName: sheetName
        };

        console.log('✅ 缓存标记设置成功');

    } catch (error) {
        console.warn('⚠️ 标记缓存失败:', error);
    }
};

// 同样修复 markCacheAsFrontendModified 函数
const markCacheAsFrontendModified = () => {
    const pdfId = selectedPdf.value?.id;
    const excelFile = selectedExcelFile.value; // 直接使用响应式变量
    const sheetName = selectedSheet.value?.name;

    if (!pdfId || !excelFile || !sheetName) {
        console.warn('❌ 标记前端修改失败：参数不完整', { pdfId, excelFile, sheetName });
        return;
    }

    const tableType = showFlatMode.value ? 'flattened' : 'original';

    try {
        const cacheKey = `${pdfId}_${excelFile}_${sheetName}`;

        if (!window.cacheMetadata) window.cacheMetadata = {};
        window.cacheMetadata[cacheKey] = {
            source: 'frontend_modified',
            lastModified: Date.now(),
            tableType: tableType,
            pdfId: pdfId,
            excelFile: excelFile,
            sheetName: sheetName
        };

        console.log('🔧🔧 缓存标记为前端修改:', { cacheKey });

    } catch (error) {
        console.warn('⚠️ 标记前端修改失败:', error);
    }
};



/**
 * 获取表格实例（带缓存）
 */
const getHotInstanceWithCache = () => {
    if (window.hotInstanceCache && !window.hotInstanceCache.isDestroyed) {
        return window.hotInstanceCache;
    }
    return null;
};

/**
 * 更新修改单元格计数显示
 */
const updateModifiedCellsCount = () => {
    const count = unsavedCells.value?.size || 0;
    modifiedCellsCount.value = count;
    hasUnsavedChanges.value = count > 0;

    console.log('🔢 修改单元格计数更新:', {
        未保存单元格数: count,
        是否有未保存修改: hasUnsavedChanges.value
    });

    // 通知父组件
    if (typeof onUnsavedChangesUpdated === 'function') {
        onUnsavedChangesUpdated(hasUnsavedChanges.value, count);
    }
};

/**
 * 异步获取表格实例
 */
/**
 * 异步获取表格实例（合并版本）
 */
const getHotInstanceAsync = async (retry = 0, maxRetry = 5) => {
    if (retry >= maxRetry) {
        console.warn('❌❌ 获取表格实例失败，达到最大重试次数');
        return null;
    }

    // 方法1：先尝试缓存获取（快速）
    let hot = getHotInstanceWithCache();
    if (hot && !hot.isDestroyed) {
        console.log('✅✅ 从缓存获取表格实例成功');
        return hot;
    }

    // 方法2：检查 ExcelContent 组件
    if (excelContent.value && selectedSheet.value) {
        const viewer = showFlatMode.value
            ? excelContent.value.$refs?.flatViewer
            : excelContent.value.$refs?.originalViewer;

        if (viewer?.getSafeHotInstance) {
            hot = viewer.getSafeHotInstance();
            if (hot && !hot.isDestroyed) {
                console.log('✅✅ 从组件获取表格实例成功');
                // 更新缓存
                window.hotInstanceCache = hot;
                return hot;
            }
        }
    }

    // 方法3：等待重试
    console.log(`⏳⏳ 等待表格实例，重试: ${retry + 1}/${maxRetry}`);
    await new Promise(resolve => setTimeout(resolve, 200));
    return getHotInstanceAsync(retry + 1, maxRetry);
};


// useThreeColumnPage.js 中的 clearModificationStatesOnly 函数
const clearModificationStatesOnly = async () => {
    console.log('🧹🧹 清除修改状态，保留缓存数据...');

    try {
        if (!selectedPdf.value || !selectedExcelFile.value || !selectedSheet.value) {
            console.warn('❌ 清除状态失败：缺少必要参数');
            return;
        }

        const pdfId = selectedPdf.value.id;
        const excelFile = selectedExcelFile.value;
        const sheetName = selectedSheet.value.name;
        const tableType = showFlatMode.value ? 'flattened' : 'original';

        console.log('📋 清除参数:', { pdfId, excelFile, sheetName, tableType });

        // 1. 清除全局修改状态
        window.currentHasChanges = false;
        window.modifiedCellsCount = 0;
        window.unsavedCellsCount = 0;
        console.log('✅ 全局修改状态已清除');

        // 2. 安全地清除未保存单元格集合
        if (window.unsavedCells) {
            if (window.unsavedCells instanceof Set) {
                window.unsavedCells.clear();
                console.log('✅ Set 结构的 unsavedCells 已清空');
            } else if (Array.isArray(window.unsavedCells)) {
                window.unsavedCells.length = 0;
                console.log('✅ Array 结构的 unsavedCells 已清空');
            } else if (typeof window.unsavedCells === 'object') {
                // 对象结构：{ original: Set, flattened: Set }
                if (window.unsavedCells.original) {
                    window.unsavedCells.original.clear();
                    console.log('✅ original 表未保存单元格已清空');
                }
                if (window.unsavedCells.flattened) {
                    window.unsavedCells.flattened.clear();
                    console.log('✅ flattened 表未保存单元格已清空');
                }
            } else {
                window.unsavedCells = new Set();
                console.log('✅ 重新初始化 unsavedCells 为 Set');
            }
        } else {
            window.unsavedCells = new Set();
            console.log('✅ 初始化 unsavedCells 为 Set');
        }

        // 3. 清除本地存储的草稿
        const draftKey = ExcelKey.getDraftKey ?
            ExcelKey.getDraftKey(pdfId, excelFile, sheetName, tableType) :
            `excel_draft_${pdfId}_${excelFile}_${sheetName}_${tableType}`;

        localStorage.removeItem(draftKey);
        console.log('✅ 已清除本地存储草稿:', draftKey);

        // 4. 清除索引
        const indexKey = ExcelKey.getIndexKey ?
            ExcelKey.getIndexKey(pdfId, excelFile) :
            `excel_draft_index_${pdfId}_${excelFile}`;

        const index = JSON.parse(localStorage.getItem(indexKey) || '[]');
        const newIndex = index.filter(key => !key.includes(draftKey));
        localStorage.setItem(indexKey, JSON.stringify(newIndex));
        console.log('✅ 草稿索引已更新，新索引长度:', newIndex.length);

        // 5. 清除 sheetStateManager 的状态
        if (sheetStateManager) {
            console.log('🔧 开始清除 sheetStateManager 状态...');

            // 尝试不同的清除方法
            const clearMethods = [
                'clearModifications',
                'clearUnsavedChanges',
                'resetState',
                'clearAllModifications'
            ];

            let cleared = false;
            for (const method of clearMethods) {
                if (typeof sheetStateManager[method] === 'function') {
                    try {
                        if (method === 'clearModifications' || method === 'clearUnsavedChanges') {
                            sheetStateManager[method](tableType);
                        } else {
                            sheetStateManager[method]();
                        }
                        console.log(`✅ 使用 ${method} 清除状态成功`);
                        cleared = true;
                        break;
                    } catch (e) {
                        console.warn(`⚠️ ${method} 清除失败:`, e.message);
                    }
                }
            }

            if (!cleared) {
                console.warn('⚠️ 所有清除方法都失败，尝试手动重置');
                // 手动重置关键状态
                if (sheetStateManager.modifiedCells) {
                    sheetStateManager.modifiedCells.clear();
                }
                if (sheetStateManager.unsavedCells) {
                    sheetStateManager.unsavedCells.clear();
                }
                if (sheetStateManager.modifiedCellsCount !== undefined) {
                    sheetStateManager.modifiedCellsCount = 0;
                }
            }
        } else {
            console.warn('⚠️ sheetStateManager 不存在');
        }

        // 6. 清除最终保存锁定
        if (sheetStateManager && sheetStateManager.clearLastFinalSavedCount) {
            try {
                // sheetStateManager.clearLastFinalSavedCount(tableType);
                console.log('✅ 最终保存计数已清除');
            } catch (e) {
                console.warn('⚠️ 清除最终保存计数失败:', e.message);
            }
        }

        // 7. 重置脏标记
        sheetEverDirty.value = false;
        console.log('✅ 脏标记已重置');

        // 8. 清除响应式状态
        if (unsavedCells.value && unsavedCells.value.clear) {
            unsavedCells.value.clear();
            console.log('✅ 响应式 unsavedCells 已清空');
        }
        if (historyCells.value && historyCells.value.clear) {
            historyCells.value.clear();
            console.log('✅ 响应式 historyCells 已清空');
        }

        // 9. 重置计数器
        // unsavedCellsTick.value = 0;
        // console.log('✅ 未保存单元格计数器已重置');

        // 10. 更新修改单元格计数显示
        updateModifiedCellsCount();
        console.log('✅ 修改单元格计数显示已更新');

        // 11. 🔥🔥 关键：保留缓存数据，不清除缓存
        console.log('💾💾 保留缓存数据，只清除修改状态');

        // 验证缓存数据是否还存在
        let cachedData = null;
        if (tableType === 'flattened') {
            cachedData = excelDataCache.getFlattenedData ?
                excelDataCache.getFlattenedData(pdfId, excelFile, sheetName) : null;
        } else {
            cachedData = excelDataCache.getOriginalData ?
                excelDataCache.getOriginalData(pdfId, excelFile, sheetName) : null;
        }

        console.log('🔍 缓存数据验证:', {
            缓存是否存在: !!cachedData,
            缓存行数: cachedData?.length || 0,
            缓存类型: tableType
        });

        // 12. 清除样式
        const hot = getHotInstanceWithCache();
        if (hot && !hot.isDestroyed) {
            try {
                // 清除所有单元格样式
                hot.updateSettings({ cell: [] }, false);
                hot.render();
                console.log('✅ 表格样式已清除');
            } catch (error) {
                console.warn('⚠️ 清除表格样式失败:', error);
            }
        }

        // 13. 清除缓存标记（可选，根据需求决定）
        const cacheMarkKey = ExcelKey.getDraftKey ?
            ExcelKey.getDraftKey(pdfId, excelFile, sheetName, tableType) :
            `excel_draft_${pdfId}_${excelFile}_${sheetName}_${tableType}`;

        if (window.cacheMetadata && window.cacheMetadata[cacheMarkKey]) {
            // 可以选择保留后端数据标记，只清除前端修改标记
            if (window.cacheMetadata[cacheMarkKey]?.source === 'frontend_modified') {
                delete window.cacheMetadata[cacheMarkKey];
                console.log('✅ 前端修改缓存标记已清除');
            } else {
                console.log('💾 保留后端数据缓存标记:', window.cacheMetadata[cacheMarkKey]);
            }
        }

        console.log('🎉🎉 修改状态清除完成，缓存数据保留');

        // 触发更新
        nextTick(() => {
            updateModifiedCellsCount();
            if (typeof onUnsavedChangesUpdated === 'function') {
                onUnsavedChangesUpdated(false, 0);
            }
        });

    } catch (error) {
        console.error('❌❌ 清除修改状态失败:', error);
    }
};


const saveData = async () => {
  console.log('💾💾💾💾💾💾💾💾 保存数据 - 区分表类型...');

  if (!selectedPdf.value || !selectedSheet.value || !selectedExcelFile.value) {
    ElMessage.warning('请先选择表格');
    return { success: false, error: '未选择表格' };
  }

  const currentTableType = showFlatMode.value ? 'flattened' : 'original';
  saving.value = true;

  try {
    /* ===== 1. 获取当前表格数据（前端修改后的） ===== */
    const hotInstance = getActiveHotInstance();
    if (!hotInstance) {
      throw new Error('无法获取表格实例');
    }

    const currentTableData = hotInstance.getSourceData();

    // 🔥🔥🔥 关键修复：使用UUID而不是数字ID
    const pdfId = selectedPdf.value.disk_name || selectedPdf.value.id;
    console.log('🔍🔍 保存使用的PDF ID:', {
      数字ID: selectedPdf.value.id,
      UUID: selectedPdf.value.disk_name,
      最终使用的pdfId: pdfId
    });

    console.log('📊📊📊📊 保存时的数据:', {
      行数: currentTableData.length,
      表类型: currentTableType,
      来源: '前端缓存（修改后）',
      使用的PDF_ID: pdfId
    });

    /* ===== 2. 根据表类型选择不同的API ===== */
    let apiUrl, savePayload;

    if (currentTableType === 'original') {
      apiUrl = '/excel/save-final';
      savePayload = {
        pdf_id: pdfId,  // ✅ 使用UUID
        excel_file: selectedExcelFile.value,
        sheet_name: selectedSheet.value.name,
        table_type: 'original',
        data: currentTableData,
        timestamp: Date.now()
      };
      console.log('📤📤 保存原始数据到Excel文件');
    } else {
      apiUrl = '/excel/save-flattened';
      savePayload = {
        pdf_id: pdfId,  // ✅ 使用UUID
        excel_file: selectedExcelFile.value,
        sheet_name: selectedSheet.value.name,
        table_type: 'flattened',
        flattened_data: currentTableData,
        original_data: excelData.value,
        timestamp: Date.now()
      };
      console.log('📤📤 保存扁平化数据到专门存储');
    }

    const response = await fetch(getApiUrl(apiUrl), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(savePayload)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();
    console.log('📥📥📥📥 保存API返回:', result);

    /* ===== 3. 保存成功后的处理 ===== */
    if (result.success) {
      console.log(`✅ ${currentTableType === 'original' ? '原始' : '扁平化'}数据保存成功`);

      // 🔥🔥🔥 关键添加：清理会话缓存（因为数据已改变）
      if (sessionCacheManager) {
        sessionCacheManager.delete(
          selectedPdf.value.id,  // 注意：这里用数字ID，不是UUID
          selectedExcelFile.value,
          selectedSheet.value.name
        );
        console.log('🧹 保存成功，清理会话缓存');
      }

      // 清除缓存并重新加载（原有逻辑保持不变）
      if (excelDataCache.deleteOriginalData) {
        excelDataCache.deleteOriginalData(pdfId, selectedExcelFile.value, selectedSheet.value.name);
      }
      if (excelDataCache.deleteFlattenedData) {
        excelDataCache.deleteFlattenedData(pdfId, selectedExcelFile.value, selectedSheet.value.name);
      }
      console.log('🗑🗑️🗑🗑️ 缓存数据已清除');

      // 设置后端数据标记
      const cacheMarkKey = ExcelKey.getDraftKey ?
        ExcelKey.getDraftKey(pdfId, selectedExcelFile.value, selectedSheet.value.name, currentTableType) :
        `excel_draft_${pdfId}_${selectedExcelFile.value}_${selectedSheet.value.name}_${currentTableType}`;

      if (!window.cacheMetadata) window.cacheMetadata = {};
      window.cacheMetadata[cacheMarkKey] = {
        source: 'backend',
        lastSaved: Date.now(),
        tableType: currentTableType
      };

      console.log('🏷🏷️🏷🏷️ 设置后端数据标记:', { cacheMarkKey });

      // 清除修改状态
      await clearModificationStatesOnly();

      // 重新从后端加载数据
      const loadResult = await loadExcelData(selectedSheet.value.name, selectedExcelFile.value);

      console.log('🔍🔍🔍🔍 保存后重新加载结果:', {
        成功: loadResult.success,
        来源: loadResult.fromCache ? '缓存' : 'API',
        数据长度: loadResult.data?.length
      });

      if (loadResult.success) {
        ElMessage.success(currentTableType === 'original' ? '原始数据保存成功' : '扁平化数据保存成功');
      }

      return { success: true, message: '保存成功' };
    } else {
      throw new Error(result.error || '后端保存失败');
    }

  } catch (error) {
    console.error('❌❌❌❌❌❌❌❌ 保存失败:', error);
    ElMessage.error(`保存失败: ${error.message}`);
    return { success: false, error: error.message };
  } finally {
    saving.value = false;
  }
};



// 修复后的清理缓存函数
const clearCacheAfterSave = async () => {
  console.log('🧹🧹 确认后端保存成功后，清理前端缓存...');

  try {
    // 1. 清除全局修改状态
    window.currentHasChanges = false;
    window.modifiedCellsCount = 0;
    window.unsavedCellsCount = 0;

    // 2. 安全地清除未保存单元格集合
    if (window.unsavedCells && typeof window.unsavedCells === 'object') {
      // 检查是否是 Set 类型
      if (window.unsavedCells instanceof Set) {
        const originalSize = window.unsavedCells.size;
        window.unsavedCells.clear();
        console.log(`✅ 清除了 ${originalSize} 个未保存单元格`);
      } else if (Array.isArray(window.unsavedCells)) {
        // 如果是数组，清空数组
        window.unsavedCells.length = 0;
        console.log(`✅ 清除了数组形式的未保存单元格`);
      } else {
        // 如果是普通对象，重新赋值为空 Set
        window.unsavedCells = new Set();
        console.log(`✅ 重置未保存单元格集合`);
      }
    } else {
      // 如果不存在或不是对象，创建新的 Set
      window.unsavedCells = new Set();
      console.log(`✅ 创建新的未保存单元格集合`);
    }

    // 3. 清除本地存储的草稿
    const draftKey = `excel_draft_${selectedPdf.value.id}_${selectedExcelFile.value}_${selectedSheet.value.name}_${showFlatMode.value ? 'flattened' : 'original'}`;
    localStorage.removeItem(draftKey);
    console.log('✅ 已清除本地存储草稿:', draftKey);

    // 4. 清除索引
    const indexKey = `excel_draft_index_${selectedPdf.value.id}_${selectedExcelFile.value}`;
    const index = JSON.parse(localStorage.getItem(indexKey) || '[]');
    const newIndex = index.filter(key => !key.includes(draftKey));
    localStorage.setItem(indexKey, JSON.stringify(newIndex));

    // 5. 清除内存中的数据缓存
    if (window.sheetDataCache) {
      const cacheKey = `${selectedPdf.value.id}_${selectedExcelFile.value}_${selectedSheet.value.name}`;
      delete window.sheetDataCache[cacheKey];
      console.log('✅ 已清除数据缓存:', cacheKey);
    }

    // 6. 清除 sheetStateManager 的状态
    if (window.sheetStateManager && typeof window.sheetStateManager.clearModifications === 'function') {
      window.sheetStateManager.clearModifications();
      console.log('✅ 已清除 sheetStateManager 状态');
    }

    // 7. 强制重新加载当前sheet的数据
    await reloadCurrentSheetData();

    console.log('🎉 所有缓存清理完成');

  } catch (error) {
    console.error('❌ 清理缓存失败:', error);
    // 不抛出错误，避免影响主保存流程
  }
};

// 重新加载数据的函数（简化版，避免错误）
const reloadCurrentSheetData = async () => {
  const sheetName = selectedSheet.value.name;
  if (!sheetName) {
    console.warn('⚠️ 没有选中的sheet，跳过重新加载');
    return;
  }

  try {
    console.log('🔄 强制重新加载数据:', sheetName);

    // 简单的方式：清除缓存，让组件自动重新加载
    if (window.sheetDataCache) {
      const cacheKey = `${selectedPdf.value.id}_${selectedExcelFile.value}_${sheetName}`;
      delete window.sheetDataCache[cacheKey];
      console.log('✅ 已清除缓存，触发重新加载');
    }

    // 触发组件更新（如果有相关函数）
    if (typeof forceUpdate === 'function') {
      forceUpdate();
    }

    console.log('✅ 数据重新加载触发完成');

  } catch (error) {
    console.error('❌ 重新加载数据失败:', error);
    // 忽略错误，不影响主流程
  }
};



// 🔥🔥 新增：数据验证和格式化函数
const validateTableData = (rawData) => {
  if (!rawData || !Array.isArray(rawData)) {
    console.warn('⚠️ 原始数据为空或不是数组，返回空数组');
    return [];
  }

  console.log('🔍🔍 数据验证 - 原始数据格式:', {
    类型: typeof rawData,
    是否为数组: Array.isArray(rawData),
    长度: rawData.length,
    第一行类型: typeof rawData[0],
    第一行内容: rawData[0]
  });

  // 处理各种数据格式，确保最终输出二维数组
  const processedData = rawData.map((row, index) => {
    try {
      if (Array.isArray(row)) {
        // 已经是数组格式，直接返回
        return row.map(cell => {
          // 处理单元格数据，确保不是undefined或null
          return cell === undefined || cell === null ? '' : cell;
        });
      }
      else if (typeof row === 'object' && row !== null) {
        // 对象格式：转换为数组
        if (row.H_1 !== undefined) {
          // 处理 H_1, H_2, H_3... 格式
          const rowArray = [];
          let colIndex = 1;
          while (row[`H_${colIndex}`] !== undefined) {
            rowArray.push(row[`H_${colIndex}`] || '');
            colIndex++;
          }
          return rowArray;
        } else {
          // 其他对象格式，按属性名排序后转换为数组
          return Object.entries(row)
            .filter(([key]) => !key.startsWith('__')) // 过滤元数据
            .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
            .map(([, value]) => value || '');
        }
      }
      else {
        // 基本数据类型，包装成单元素数组
        return [row || ''];
      }
    } catch (error) {
      console.warn(`⚠️ 处理第${index}行数据时出错:`, error);
      return []; // 返回空行而不是中断处理
    }
  }).filter(row => {
    // 过滤空行：空数组或所有单元格都为空的行
    if (!Array.isArray(row) || row.length === 0) return false;
    return row.some(cell => cell !== '' && cell !== null && cell !== undefined);
  });

  console.log('✅✅ 数据验证完成:', {
    原始行数: rawData.length,
    处理後行数: processedData.length,
    样本数据: processedData.slice(0, 3)
  });

  return processedData;
};

// 🔥🔥 增强的 getActiveHotInstance 函数
const getActiveHotInstance = () => {
  console.log('🔍🔍 获取表格实例...');

  if (!excelContent.value) {
    console.warn('❌ ExcelContent 组件引用为空');
    return null;
  }

  try {
    // 根据当前模式获取对应的查看器
    const viewer = showFlatMode.value
      ? excelContent.value.$refs?.flatViewer
      : excelContent.value.$refs?.originalViewer;

    if (!viewer) {
      console.warn('❌ 表格查看器未找到:', {
        当前模式: showFlatMode.value ? '扁平化' : '原始',
        可用引用: Object.keys(excelContent.value.$refs || {})
      });
      return null;
    }

    // 尝试多种方法获取实例
    let hotInstance = null;

    if (typeof viewer.getSafeHotInstance === 'function') {
      hotInstance = viewer.getSafeHotInstance();
      console.log('✅ 通过 getSafeHotInstance() 获取实例');
    }
    else if (viewer.hotInstance) {
      hotInstance = viewer.hotInstance;
      console.log('✅ 通过 hotInstance 属性获取实例');
    }
    else if (viewer.$refs?.hot?.hotInstance) {
      hotInstance = viewer.$refs.hot.hotInstance;
      console.log('✅ 通过嵌套引用获取实例');
    }
    else {
      console.warn('❌ 无法通过任何方法获取实例');
      return null;
    }

    // 检查实例状态
    if (!hotInstance) {
      console.warn('❌ 获取到的实例为空');
      return null;
    }

    if (hotInstance.isDestroyed) {
      console.warn('❌ 表格实例已销毁');
      return null;
    }

    console.log('✅✅ 成功获取表格实例:', {
      行数: hotInstance.countRows?.(),
      列数: hotInstance.countCols?.()
    });

    return hotInstance;

  } catch (error) {
    console.error('❌ 获取表格实例时出错:', error);
    return null;
  }
};

// 🔥🔥 新增：调试函数，用于验证数据一致性
const debugDataConsistency = () => {
  if (!selectedPdf.value || !selectedSheet.value) {
    console.log('❌ 未选择表格，无法调试');
    return;
  }

  console.group('🔍🔍 数据一致性调试');

  // 1. 从表格实例获取数据
  const hotInstance = getActiveHotInstance();
  const instanceData = hotInstance?.getData?.() || [];

  // 2. 从缓存获取数据
  const cachedData = showFlatMode.value
    ? excelDataCache.getFlattenedData(
        selectedPdf.value.id,
        selectedExcelFile.value,
        selectedSheet.value.name
      )
    : excelDataCache.getOriginalData(
        selectedPdf.value.id,
        selectedExcelFile.value,
        selectedSheet.value.name
      );

  // 3. 从组件状态获取数据
  const stateData = showFlatMode.value ? flatData.value : excelData.value;

  console.log('📊 数据来源对比:', {
    '表格实例': instanceData.length + ' 行',
    '缓存数据': (cachedData?.length || 0) + ' 行',
    '组件状态': stateData.length + ' 行'
  });

  console.log('📋 数据样本对比:');
  console.log('表格实例样本:', instanceData.slice(0, 2));
  console.log('缓存数据样本:', cachedData?.slice(0, 2));
  console.log('组件状态样本:', stateData.slice(0, 2));

  // 检查是否有未保存的修改
  const tableType = showFlatMode.value ? 'flattened' : 'original';
  const unsavedCount = window.unsavedCells?.[tableType]?.size || 0;
  console.log('📝 未保存修改:', unsavedCount + ' 处');

  console.groupEnd();

  return {
    instanceData,
    cachedData,
    stateData,
    hasDifferences: unsavedCount > 0
  };
};

// 暴露调试函数到全局
if (typeof window !== 'undefined') {
  window.debugDataConsistency = debugDataConsistency;
  window.getCurrentTableData = () => {
    const hotInstance = getActiveHotInstance();
    return hotInstance?.getData?.() || [];
  };
}



// 🔥 新增：数据格式转换函数
function convertFrontendToBackendFormat(frontendData) {
  if (!frontendData || !Array.isArray(frontendData)) {
    console.warn('⚠️ 前端数据为空或不是数组');
    return [];
  }

  console.log('🔄 转换前端数据格式...');
  console.log('📊 原始数据:', {
    行数: frontendData.length,
    第一行类型: typeof frontendData[0],
    第一行内容: frontendData[0]
  });

  const backendData = [];

  for (let i = 0; i < frontendData.length; i++) {
    const row = frontendData[i];

    if (Array.isArray(row)) {
      // 已经是数组格式，直接使用
      backendData.push(row);
      console.log(`✅ 行${i}: 使用数组格式 (${row.length}列)`);
    }
    else if (typeof row === 'object' && row !== null) {
      // 对象格式：需要转换
      if (row.H_1 !== undefined) {
        // 提取 H_1, H_2, H_3, ... 字段
        const rowArray = [];
        let colIndex = 1;

        while (row[`H_${colIndex}`] !== undefined) {
          rowArray.push(row[`H_${colIndex}`]);
          colIndex++;
        }

        if (rowArray.length > 0) {
          backendData.push(rowArray);
          console.log(`✅ 行${i}: 对象转数组 (${rowArray.length}列)`);
        } else {
          console.warn(`⚠️ 行${i}: 对象格式但无H_*字段`);
        }
      }
      else if (row.__metadata || row.__is_first_row) {
        // 跳过元数据行
        console.log(`⏭️ 行${i}: 跳过元数据行`);
        continue;
      }
      else {
        // 其他对象格式，尝试提取所有值
        const rowArray = Object.values(row).filter(val =>
          !(typeof val === 'string' && val.startsWith('__'))
        );
        if (rowArray.length > 0) {
          backendData.push(rowArray);
          console.log(`✅ 行${i}: 对象值转数组 (${rowArray.length}列)`);
        } else {
          console.warn(`⚠️ 行${i}: 无法转换的对象格式`);
        }
      }
    }
    else {
      // 其他格式（字符串、数字等）
      backendData.push([row]);
      console.log(`✅ 行${i}: 简单值转数组`);
    }
  }

  console.log('📈 转换完成:', {
    转换前行数: frontendData.length,
    转换后行数: backendData.length,
    样本数据: backendData.slice(0, 2)
  });

  return backendData;
}


// 从sheet名称中提取页码
const extractPageFromSheetName = (sheetName) => {
  if (!sheetName) return 1

  try {
    // 尝试匹配 P001, P002 等格式
    const pageMatch = sheetName.match(/P(\d+)/i)
    if (pageMatch) {
      return parseInt(pageMatch[1])
    }

    // 尝试匹配 页1, 页2 等格式
    const chineseMatch = sheetName.match(/页(\d+)/)
    if (chineseMatch) {
      return parseInt(chineseMatch[1])
    }

    return 1
  } catch (error) {
    console.warn('⚠️ 提取页码失败:', error)
    return 1
  }
}



// 🔥 添加单表头数据转换函数
const convertSingleHeaderToTable = (singleHeaderData) => {
  console.log('🔄 将单表头数据转换为二维表格...')

  if (!singleHeaderData || singleHeaderData.length === 0) {
    return []
  }

  try {
    const tableData = []

    // 检查第一行是否为表头
    const firstRow = singleHeaderData[0]

    if (Array.isArray(firstRow)) {
      // 已经是二维数组，直接返回
      console.log('✅ 数据已经是二维数组格式')
      return singleHeaderData
    }

    if (typeof firstRow === 'object') {
      // 对象数组格式 - 转换为二维数组
      console.log('🔄 将对象数组转换为二维数组...')

      // 提取表头（从第一个对象的键）
      const headers = Object.keys(firstRow).filter(key => !key.startsWith('__'))
      console.log('📊 提取的表头:', headers)

      // 添加表头行
      tableData.push(headers)

      // 添加数据行
      for (const row of singleHeaderData) {
        const rowData = []
        for (const key of headers) {
          rowData.push(row[key] || '')
        }
        tableData.push(rowData)
      }
    } else {
      // 其他格式，直接包装
      console.log('⚠️ 未知数据格式，直接包装')
      tableData.push([firstRow])
    }

    console.log('✅ 单表头转换完成:', {
      输入行数: singleHeaderData.length,
      输出行数: tableData.length,
      列数: tableData[0]?.length || 0
    })

    return tableData

  } catch (error) {
    console.error('❌ 单表头转换失败:', error)
    return []
  }
}



const convertToFlatData_DEPRECATED  = async () => {
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

    // 步骤1：获取当前数据
    let currentOriginalData = excelDataCache.getOriginalData(pdfId, excelFile, sheetName)

    if (!currentOriginalData || currentOriginalData.length === 0) {
      console.log('📦 缓存无数据，尝试从当前显示数据获取...')
      currentOriginalData = excelData.value
    }

    if (!currentOriginalData || currentOriginalData.length === 0) {
      console.log('🔄 重新加载原始数据...')
      const loadResult = await loadExcelData(sheetName, excelFile)
      if (!loadResult.success) {
        throw new Error('无法加载原始表格数据')
      }
      currentOriginalData = excelData.value
    }

    if (!currentOriginalData || currentOriginalData.length === 0) {
      throw new Error('原始数据为空，无法转换')
    }

    console.log('📊 用于转换的原始数据:', {
      数据类型: typeof currentOriginalData[0],
      总行数: currentOriginalData.length,
      第一行: currentOriginalData[0],
      第一行列数: currentOriginalData[0]?.length || 0
    })

    // 步骤2：重建二维表格数据
    const tableData = rebuildTwoDimensionalTable(currentOriginalData)

    if (!tableData || tableData.length === 0) {
      throw new Error('无法重建二维表格数据')
    }

    console.log('✅ 重建的二维表格数据:', {
      行数: tableData.length,
      列数: tableData[0]?.length || 0,
      表格样本: tableData.slice(0, Math.min(3, tableData.length))
    })

    // 步骤3：准备请求数据
    const requestData = {
      table_data: tableData,
      table_metadata: {
        name: sheetName
      },
      marks_info: {
        row_marks: [],  // 后端会智能处理
        col_marks: []   // 后端会智能处理
      }
    }

    console.log('📤 发送扁平化请求数据:', {
      表数据行数: requestData.table_data.length,
      表数据列数: requestData.table_data[0]?.length || 0,
      表格名称: sheetName
    })

    // 步骤4：调用扁平化API
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
    console.log('📥 扁平化API返回数据:', result)

    // 步骤5：处理API响应
    if (result.success) {
      let flattenedData = []

      // 处理多种可能的响应格式
      if (result.rows && Array.isArray(result.rows)) {
        flattenedData = result.rows
      } else if (result.long_format_data && Array.isArray(result.long_format_data)) {
        flattenedData = result.long_format_data
      } else if (result.data && Array.isArray(result.data)) {
        flattenedData = result.data
      } else if (Array.isArray(result)) {
        flattenedData = result
      } else {
        // 尝试查找响应中的第一个数组字段
        for (const key in result) {
          if (Array.isArray(result[key])) {
            flattenedData = result[key]
            break
          }
        }
      }

      if (flattenedData.length > 0) {
        console.log('✅ 接收到扁平化数据:', {
          总行数: flattenedData.length,
          第一行样本: flattenedData[0]
        })

        // 保存到缓存
        excelDataCache.setFlattenedData(pdfId, excelFile, sheetName, flattenedData)

        // 缓存到 IndexedDB
        try {
          await dataManager.saveFlattenedData(flattenedData, tableData)
        } catch (cacheError) {
          console.warn('缓存到 IndexedDB 失败:', cacheError)
        }

        // 更新状态
        const currentContext = sheetStateManager.getActiveContext()
        if (currentContext &&
            currentContext.pdfId === pdfId &&
            currentContext.excelFile === excelFile &&
            currentContext.sheetName === sheetName) {
          sheetStateManager.setData('flattened', flattenedData)
        }

        // 显示扁平化数据
        flatData.value = flattenedData
        showFlatMode.value = true

        ElMessage.success(`数据扁平化成功，生成 ${flattenedData.length} 行数据`)

      } else {
        console.log('📝 表格为空或无数据可转换')
        flatData.value = []
        showFlatMode.value = true
        ElMessage.info('表格为空或无数据可转换')
      }

    } else {
      throw new Error(result.error || '后端处理失败')
    }

  } catch (error) {
    console.error('❌ 数据扁平化失败:', error)
    ElMessage.error(`转换失败: ${error.message}`)

    showFlatMode.value = false
    flatData.value = []

    if (selectedSheet.value) {
      await loadExcelData(selectedSheet.value.name, selectedExcelFile.value)
    }
  } finally {
    loadingFlat.value = false
  }
}




/**
 * 获取缓存的扁平化数据
 */
const getCachedFlattenedData = async () => {
  // 确保有选中的PDF、Sheet和Excel文件
  if (!selectedPdf.value || !selectedSheet.value || !selectedExcelFile.value) {
    console.warn('❌ 无法获取缓存：缺少必要的选择信息')
    return null
  }

  // 传递正确的参数
  initDataManagerContext(
    selectedPdf.value,
    selectedSheet.value,
    selectedExcelFile.value
  )

  const cachedData = await dataManager.getFlattenedData()

  if (cachedData) {
    console.log('📦 使用缓存的扁平化数据')
    return cachedData
  }

  return null
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




// 在 ThreeColumnPage.vue 的 setup 函数中添加 exitEditMode 函数
const exitEditMode = async () => {
  console.log('🔚 退出编辑模式')

  // 1. 检查当前是否在编辑模式
  // 获取 Handsontable 实例
  const hotInstance = getActiveHotInstance()
  if (!hotInstance) {
    console.log('❌ 无法获取表格实例')
    return false
  }

  // 2. 检查当前表格是否是只读状态
  const isReadOnly = hotInstance.getSettings().readOnly
  console.log('📊 当前表格只读状态:', isReadOnly)

  if (isReadOnly === false) {
    console.log('🎯 当前在编辑模式，准备退出')

    try {
      // 3. 方法1: 通过 Handsontable 设置退出编辑模式
      hotInstance.updateSettings({
        readOnly: true
      })
      console.log('✅ 已设置表格为只读模式')

      // 4. 方法2: 如果有未保存修改，提示用户
      if (actualHasUnsavedChanges.value) {
        const confirmResult = await ElMessageBox.confirm(
          '您有未保存的修改，是否保存后再退出？',
          '退出编辑模式',
          {
            confirmButtonText: '保存并退出',
            cancelButtonText: '直接退出',
            type: 'warning'
          }
        )

        if (confirmResult) {
          // 用户选择保存后退出
          console.log('💾 用户选择保存后退出')
          await saveData()
        } else {
          // 用户选择直接退出，放弃修改
          console.log('🗑️ 用户选择直接退出，放弃修改')
          const tableType = showFlatMode.value ? 'flattened' : 'original'
          sheetStateManager.clearUnsavedChanges(tableType)
          updateSaveStatus()
        }
      }

      // 5. 方法3: 重新加载数据（最彻底的方法）
      if (selectedSheet.value && selectedExcelFile.value) {
        console.log('🔄 重新加载表格数据确保退出编辑模式')
        await loadExcelData(selectedSheet.value.name, selectedExcelFile.value)
      }

      // 6. 更新全局编辑模式状态
      if (window.setGlobalEditMode) {
        window.setGlobalEditMode(false)
      }

      // 7. 显示成功消息
      ElMessage.success('已退出编辑模式')

      return true

    } catch (error) {
      console.error('❌ 退出编辑模式失败:', error)
      if (error !== 'cancel') {
        ElMessage.error(`退出编辑模式失败: ${error.message}`)
      }
      return false
    }

  } else {
    console.log('ℹ️ 当前已经在只读模式')
    ElMessage.info('当前已经在只读模式')
    return true
  }
}

// 暴露给全局调试
if (typeof window !== 'undefined') {
  window.exitEditMode = exitEditMode
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



// 当有修改时，强制刷新 ExcelContent
const updateExcelContent = () => {
  safeRefreshExcelContent(actualHasUnsavedChanges.value)
  console.log('🔄 强制刷新 ExcelContent, key:', excelContentKey.value)
}


const sheetStateUpdateTrigger = ref(0)

const emit = defineEmits([
  'save-success',                // 保存成功
  'unsaved-changes-updated',     // 未保存修改更新
  'cell-changed',                // 单元格修改
  'data-changed',                // 数据修改
  'toggle-flat-mode',            // 切换扁平化模式
  'restore-unsaved-data'         // 恢复未保存数据
])


// 修改为：
const handleSearch = inject('handleSearch', null)
const searchResults = inject('searchResults', [])
const isSearching = inject('isSearching', false)

// 在 inject 后添加
console.log('🔍🔍 ThreeColumnPage inject 的数据:', {
  searchResults,
  isSearching
})


watch(searchResults, (newVal) => {
  console.log('🔍🔍 ThreeColumnPage searchResults 变化:', newVal)
  console.log('🔍🔍 数据长度:', newVal?.length)
}, { immediate: true, deep: true })

watch(isSearching, (newVal) => {
  console.log('🔍🔍 ThreeColumnPage isSearching 变化:', newVal)
}, { immediate: true })

// 安全访问
console.log('🔍 ThreeColumnPage 接收的搜索结果:', {
  结果数量: searchResults?.length || 0,    // ✅ 去掉 .value
  搜索中: isSearching,                    // ✅ 去掉 .value
  有搜索函数: !!handleSearch
})


// 4. 检查计算属性
const displayedPdfs = computed(() => {
  console.log('计算 displayedPdfs，searchResults:', searchResults.value?.length)

  // 如果有搜索结果，使用搜索结果
  if (searchResults.value && searchResults.value.length > 0) {
    console.log('使用搜索结果，数量:', searchResults.value.length)
    return searchResults.value
  }

  // 否则使用默认PDF列表
  console.log('使用默认PDF列表')
  return pdfList.value || []  // 或者你的默认PDF列表
})


const searchPdfFilesCompatible = async (keyword = '') => {
  try {
    isSearching.value = true
    console.log(`🔍 搜索PDF: '${keyword}'`)

    const apiUrl = `/search-pdf-compatible?keyword=${encodeURIComponent(keyword)}&limit=100`
    const response = await fetch(getApiUrl(apiUrl))

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const result = await response.json()
    console.log('📥 后端返回完整数据:', result)

    if (result.files && Array.isArray(result.files)) {
      searchResults.value = result.files

      // 🔥 详细调试信息
      console.log('🔍🔍🔍 搜索完成，详细数据检查:')
      console.log('数据长度:', searchResults.value.length)

      if (searchResults.value.length > 0) {
        const firstPdf = searchResults.value[0]
        console.log('📊 第一个PDF的所有字段:', Object.keys(firstPdf))
        console.log('📊 第一个PDF完整数据:', firstPdf)

        // 检查所有可能的文件名字段
        console.log('🔤 文件名字段检查:')
        console.log('- filename:', firstPdf.filename)
        console.log('- name:', firstPdf.name)
        console.log('- raw_filename:', firstPdf.raw_filename)
        console.log('- bank_name:', firstPdf.bank_name)
        console.log('- original_name:', firstPdf.original_name)
      }
    }

  } catch (error) {
    console.error('❌ 搜索失败:', error)
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}




const searchPdfFilesCompatible111 = async (keyword = '') => {
  try {
    isSearching.value = true
    console.log(`🔍🔍 新版本搜索PDF: '${keyword}'`)

    // 🔥🔥 关键修复：使用正确的API路径
    const apiUrl = `/search-pdf-compatible?keyword=${encodeURIComponent(keyword)}&limit=100`

    console.log('🔗 请求URL:', apiUrl)

    const response = await fetch(getApiUrl(apiUrl))

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const result = await response.json()

    console.log('📥 后端返回:', {
      文件数: result.files ? result.files.length : 0,
      总数量: result.count
    })

    if (result.files) {
      searchResults.value = result.files
      console.log(`✅ 新版本搜索完成，找到 ${searchResults.value.length} 个文件`)

      // 调试：打印第一个文件的数据格式
      if (searchResults.value.length > 0) {
        console.log('📊 搜索返回的数据格式:', {
          id: searchResults.value[0].id,
          file_id: searchResults.value[0].file_id,
          filename: searchResults.value[0].filename,
          disk_name: searchResults.value[0].disk_name
        })
      }
    } else {
      searchResults.value = []
      console.log('⚠️ 新版本搜索返回空结果')
    }

  } catch (error) {
    console.error('❌❌ 新版本搜索失败:', error)
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}



// 🔥🔥 防抖函数（保持不变）
function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// 🔥🔥 修改：创建兼容的搜索处理函数
const handleSearchInputCompatible = debounce((keyword) => {
  console.log('🔍 处理搜索输入:', keyword)
  searchPdfFilesCompatible(keyword)
}, 300)



// 搜索版本控制
const useNewSearch = ref(true) // 默认使用旧版本，可以逐步切换

// 🔥🔥 统一的搜索入口函数
const unifiedSearchPdfFiles = async (keyword = '') => {
  if (useNewSearch.value) {
    // 使用新版本（数据库搜索）
    await searchPdfFilesCompatible(keyword)
  } else {
    // 使用旧版本（保持现有逻辑）
    // 这里调用现有的搜索函数，保持完全不变
    console.log('🔍 使用旧版本搜索逻辑')
    // 现有的搜索逻辑会通过 inject('searchResults') 自动更新
  }
}

// 🔥🔥 统一的搜索输入处理
const handleSearchInputUnified = debounce((keyword) => {
  unifiedSearchPdfFiles(keyword)
}, 300)

// 提供统一的搜索函数给子组件
provide('searchPdfFiles', unifiedSearchPdfFiles)
provide('handleSearchInput', handleSearchInputUnified)

// 🔥🔥 添加调试函数，用于比较数据格式
const debugSearchDataFormat = () => {
  console.group('🔍🔍 搜索数据格式调试')

  if (searchResults.value.length > 0) {
    const sampleFile = searchResults.value[0]
    console.log('📊 当前搜索结果的格式:', {
      '是否有id字段': 'id' in sampleFile,
      '是否有file_id字段': 'file_id' in sampleFile,
      '是否有filename字段': 'filename' in sampleFile,
      '是否有disk_name字段': 'disk_name' in sampleFile,
      'id值': sampleFile.id,
      'file_id值': sampleFile.file_id,
      'filename值': sampleFile.filename,
      'disk_name值': sampleFile.disk_name,
      '所有字段': Object.keys(sampleFile)
    })
  } else {
    console.log('📭 搜索结果为空')
  }

  console.groupEnd()
}

// 暴露给全局用于调试
if (typeof window !== 'undefined') {
  window.debugSearchDataFormat = debugSearchDataFormat
  window.toggleSearchVersion = () => {
    useNewSearch.value = !useNewSearch.value
    console.log(`🔄 切换搜索版本: ${useNewSearch.value ? '新版本(数据库)' : '旧版本'}`)
    ElMessage.info(`搜索版本: ${useNewSearch.value ? '新版本(数据库)' : '旧版本'}`)
  }
}



// 监听器
watch(selectedPdf, (newPdf, oldPdf) => {
  if (newPdf?.id !== oldPdf?.id) {
    console.log('🔄 切换到新PDF，清理旧状态')

    selectedSheet.value = null
    excelData.value = []
    tableColumns.value = []
    flatData.value = []
    currentPage.value = 1

    dataManager.setContext({
      pdfId: newPdf?.id || null,
      excelFile: null,
      sheetName: null
    })

    showFlatMode.value = false
    currentTableMode.value = 'original'
  }
})

watch(excelFiles, (newFiles) => {
  if (newFiles && newFiles.length > 0) {
    const maxPage = getMaxPageFromSheets(newFiles)
    totalPages.value = Math.max(maxPage, totalPages.value)
    console.log(`📊 根据sheets计算总页数: ${totalPages.value}`)
  }
})





// 监听1：未保存单元格变化
watch(
  () => {
    const tableType = showFlatMode.value ? 'flattened' : 'original';
    const unsavedSet = window.unsavedCells?.[tableType];

    return {
      tableType,
      unsavedCount: unsavedSet?.size || 0,
      // 转换为数组确保深度监听有效
      unsavedArray: unsavedSet ? Array.from(unsavedSet) : [],
      timestamp: Date.now()
    };
  },
  (newVal, oldVal) => {
    if (newVal.unsavedCount !== oldVal?.unsavedCount) {
      console.log('🔍 未保存单元格数量变化:', {
        模式: newVal.tableType,
        从: oldVal?.unsavedCount,
        到: newVal.unsavedCount
      });
      forceUnsavedUpdate.value++;
    }
  },
  { deep: true, immediate: true }
);

// 监听2：扁平化模式切换（关键！）
watch(
  () => showFlatMode.value,
  (newMode, oldMode) => {
    console.log('🎯 扁平化模式切换:', {
      从: oldMode ? '扁平化' : '原始',
      到: newMode ? '扁平化' : '原始'
    });

    // 延迟触发更新，确保DOM已更新
    nextTick(() => {
      forceUnsavedUpdate.value++;
      console.log('✅ 模式切换后强制更新状态');
    });
  }
);

// 监听3：Sheet切换时重置状态
watch(
  () => selectedSheet.value,
  (newSheet, oldSheet) => {
    if (newSheet?.name !== oldSheet?.name) {
      console.log('📋 Sheet切换，重置未保存状态');
      // 清空所有未保存状态
      if (window.unsavedCells) {
        window.unsavedCells.original?.clear();
        window.unsavedCells.flattened?.clear();
      }
      forceUnsavedUpdate.value++;
    }
  }
);



// 在ThreeColumnPage.vue中添加调试
watch(() => actualHasUnsavedChanges.value, (newVal, oldVal) => {
  console.log('🔄🔄🔄 ThreeColumnPage actualHasUnsavedChanges 变化:', {
    旧值: oldVal,
    新值: newVal,
    时间: new Date().toLocaleTimeString(),
    传递给ExcelContent: newVal
  })
})

// 检查模板中的传递
console.log('🔍 检查传递给ExcelContent的props:', {
  hasUnsavedChanges: actualHasUnsavedChanges.value,
  actualHasUnsavedChanges: actualHasUnsavedChanges.value
})


// 新增：监听全局未保存单元格变化，实时刷新状态
watch(
  () => {
    const tableType = showFlatMode.value ? 'flattened' : 'original';
    // 问题1：没有使用 tableType
    return window.unsavedCells?.size || 0; // ❌ 直接返回整个 Set 的 size
  },
  () => {
    // 问题2：tableType 变量在回调中不可用
    forceUnsavedUpdate.value++;
    console.log('🔍 全局未保存单元格变化，触发父组件状态更新');
  },
  { deep: true, immediate: true }
);

// 添加一个手动检查函数
const checkExcelContentProps = () => {
  if (excelContent.value) {
    console.log('🔍 ExcelContent 实例:', {
      props: excelContent.value.$props,
      hasUnsavedChangesProp: excelContent.value.$props.hasUnsavedChanges
    })
  }
}



// 在 ThreeColumnPage.vue 的 setup 中添加
watch(searchResults, (newVal) => {
  console.log('🔍 ThreeColumnPage searchResults 变化:', newVal)
  console.log('数据长度:', newVal.length)
  if (newVal.length > 0) {
    console.log('第一个文件:', newVal[0])
  }
}, { immediate: true, deep: true })


// ============ 新添加的监听器 ============

// 1. 监听选中的sheet，联动PDF页码（新加）
watch(() => selectedSheet.value, (newSheet, oldSheet) => {
  if (newSheet?.name !== oldSheet?.name) {
    console.log('📋📋 Sheet切换，联动PDF页码');

    // 从sheet名称中提取页码
    const pageNum = getPageFromSheetName(newSheet?.name);
    if (pageNum && pageNum > 0) {
      currentPage.value = pageNum;
      console.log(`🔄🔄 根据sheet名称更新PDF页码: ${pageNum}`);
    }

    // 清空所有未保存状态
    if (window.unsavedCells) {
      window.unsavedCells.original?.clear();
      window.unsavedCells.flattened?.clear();
    }
    forceUnsavedUpdate.value++;
  }
}, { immediate: true });

// 2. 监听excelFiles变化，更新总页数（新加，但可能和现有的有重复）
watch(excelFiles, (newFiles) => {
  if (newFiles && newFiles.length > 0) {
    const maxPage = getMaxPageFromSheets(newFiles);
    totalPages.value = Math.max(maxPage, totalPages.value);
    console.log(`📊📊 根据sheets计算总页数: ${totalPages.value}`);
  }
}, { immediate: true });


onUnmounted(() => {
  console.log('🧹 ThreeColumnPage 卸载')
})



onBeforeUnmount(() => {
  // 检查是否有未保存修改
  if (hasUnsavedChangesInCurrentTable()) {
    console.log('⚠️ 页面离开，有未保存修改')

    // 自动保存草稿（静默保存）
    const autoSave = async () => {
      try {
        await saveData()
        console.log('✅ 自动保存草稿成功')
      } catch (error) {
        console.error('❌ 自动保存失败:', error)
      }
    }

    // 延迟保存，避免阻塞页面跳转
    setTimeout(autoSave, 100)
  }
})

// 调试函数
const debugSaveButton = () => {
  console.group('🔍 ThreeColumnPage 保存按钮状态调试')

  console.log('1. 当前选择:')
  console.log('   - Sheet:', selectedSheet.value?.name)
  console.log('   - PDF:', selectedPdf.value?.id)
  console.log('   - Excel文件:', selectedExcelFile.value)

  console.log('2. SheetStateManager 状态:')
  console.log('   - 管理器是否存在:', !!sheetStateManager)

  const activeContext = sheetStateManager?.getActiveContext()
  console.log('   - 活跃上下文:', activeContext)

  if (activeContext) {
    const tableType = activeContext.tableType
    const stats = sheetStateManager.getModificationStats()
    console.log('   - 表类型:', tableType)
    console.log('   - 修改统计:', stats)
    console.log('   - 有未保存修改?', sheetStateManager.hasUnsavedChanges(tableType))
  }

  console.log('3. 计算 hasUnsavedChangesInCurrentTable():')
  const canSave = hasUnsavedChangesInCurrentTable()
  console.log('   - 结果:', canSave)
  console.log('   - 传递给ExcelContent的值:', canSave)

  console.log('4. 保存按钮应该:')
  console.log('   - 禁用?', !selectedSheet.value || !canSave)
  console.log('   - 可用?', selectedSheet.value && canSave)

  console.groupEnd()

  return canSave
}

// 暴露给全局用于调试
if (typeof window !== 'undefined') {
  window.debugSaveButton = debugSaveButton
  window.debugThreeColumnPage = {
    checkSaveState: debugSaveButton,
    getSelectedSheet: () => selectedSheet.value,
    getSelectedPdf: () => selectedPdf.value,
    getSelectedExcelFile: () => selectedExcelFile.value,
    hasUnsavedChanges: () => hasUnsavedChangesInCurrentTable()
  }
}


// 解析sheet名称的辅助函数
const parseSheetName = (sheetName) => {
  // 格式1: P100_1_T_名称 (带_T_的，是最后一表)
  const formatWithT = sheetName.match(/^P(\d+)_(\d+)_T_(.+)$/)
  if (formatWithT) {
    return {
      isStandard: true,
      pageNumber: parseInt(formatWithT[1]),
      tableIndex: parseInt(formatWithT[2]),
      isLastTable: true,
      tableName: formatWithT[3],
      originalName: sheetName
    }
  }

  // 格式2: P100_2_名称 (不带_T_的，不是最后一表)
  const formatWithoutT = sheetName.match(/^P(\d+)_(\d+)_(.+)$/)
  if (formatWithoutT) {
    return {
      isStandard: true,
      pageNumber: parseInt(formatWithoutT[1]),
      tableIndex: parseInt(formatWithoutT[2]),
      isLastTable: false,
      tableName: formatWithoutT[3],
      originalName: sheetName
    }
  }

  // 非标准格式
  return {
    isStandard: false,
    pageNumber: 9999,
    tableIndex: 9999,
    isLastTable: false,
    tableName: sheetName,
    originalName: sheetName
  }
}



// 添加测试修改记录
const addTestModification = () => {
  if (!selectedSheet.value || !selectedPdf.value) {
    console.log('❌ 请先选择表格')
    return
  }

  const tableType = showFlatMode.value ? 'flattened' : 'original'

  // 确保上下文设置正确
  sheetStateManager.setActiveContext(
    selectedPdf.value.id,
    selectedExcelFile.value,
    selectedSheet.value.name,
    tableType
  )

  // 记录一个测试修改
  const success = sheetStateManager.recordCellChange(
    0, 0,
    `old value ${Date.now()}`,
    `new value ${Date.now()}`,
    tableType
  )

  if (success) {
    console.log('✅ 记录了一个测试修改')

    // 立即检查状态
    setTimeout(() => {
      debugSaveButton()
      console.log('💡 现在检查保存按钮:', {
        当前表格: selectedSheet.value.name,
        表类型: tableType,
        有修改: sheetStateManager.hasUnsavedChanges(tableType),
        ExcelContent应该可用: hasUnsavedChangesInCurrentTable()
      })
    }, 100)

    ElMessage.success('已添加测试修改，请检查保存按钮状态')
  } else {
    console.log('❌ 记录修改失败')
    ElMessage.error('记录修改失败，请检查控制台')
  }
}

/* ===== 调试专用：把关键引用挂到 window ===== */
// 方式 A：仅开发环境（不会报错）
if (typeof process !== 'undefined' && process.env && process.env.NODE_ENV === 'development') {
  window.sheetStateManager = sheetStateManager
  window.debugSaveButton = debugSaveButton
  window.actualHasUnsavedChanges = actualHasUnsavedChanges
}

onMounted(() => {
  // ============ 1. 强制修复 window.unsavedCells 结构 ============
  console.log('🔧 onMounted: 开始初始化');
  console.log('初始 window.unsavedCells:', window.unsavedCells);
  console.log('是Set吗:', window.unsavedCells instanceof Set);

  if (!window.unsavedCells || window.unsavedCells instanceof Set) {
    console.log('🔄 强制修复 window.unsavedCells 结构');

    const originalSet = new Set();
    const flattenedSet = new Set();

    if (window.unsavedCells instanceof Set) {
      console.log('📦 从 Set 迁移数据...');
      const setArray = Array.from(window.unsavedCells);
      console.log('迁移前 Set 内容:', setArray);

      for (const key of setArray) {
        console.log('处理 key:', key, '类型:', typeof key);

        if (typeof key === 'string') {
          const parts = key.split(',');
          console.log('解析 parts:', parts, '长度:', parts.length);

          if (parts.length === 3) {
            // 格式: "row,col,tableType"
            if (parts[2] === 'flattened') {
              flattenedSet.add(key);
              console.log('→ 添加到 flattened');
            } else if (parts[2] === 'original') {
              originalSet.add(key);
              console.log('→ 添加到 original');
            } else {
              // 未知表类型，根据当前模式决定
              const currentType = showFlatMode.value ? 'flattened' : 'original';
              const newKey = `${parts[0]},${parts[1]},${currentType}`;
              if (currentType === 'flattened') {
                flattenedSet.add(newKey);
                console.log('→ 根据当前模式添加到 flattened');
              } else {
                originalSet.add(newKey);
                console.log('→ 根据当前模式添加到 original');
              }
            }
          } else if (parts.length === 2) {
            // 格式: "row,col" - 根据当前显示模式判断
            const currentType = showFlatMode.value ? 'flattened' : 'original';
            const newKey = `${parts[0]},${parts[1]},${currentType}`;
            if (currentType === 'flattened') {
              flattenedSet.add(newKey);
              console.log('→ "row,col" 格式添加到 flattened');
            } else {
              originalSet.add(newKey);
              console.log('→ "row,col" 格式添加到 original');
            }
          } else {
            console.warn('⚠️ 无法解析的格式:', key);
          }
        } else if (key && typeof key === 'object') {
          // 处理对象格式
          console.log('处理对象:', key);
          if (key.row !== undefined && key.col !== undefined) {
            const currentType = showFlatMode.value ? 'flattened' : 'original';
            const newKey = `${key.row},${key.col},${currentType}`;
            if (currentType === 'flattened') {
              flattenedSet.add(newKey);
              console.log('→ 对象格式添加到 flattened');
            } else {
              originalSet.add(newKey);
              console.log('→ 对象格式添加到 original');
            }
          }
        }
      }
    }

    window.unsavedCells = {
      original: originalSet,
      flattened: flattenedSet
    };

  }

  // 确保两个 Set 都存在
  if (!window.unsavedCells.original || !(window.unsavedCells.original instanceof Set)) {
    window.unsavedCells.original = new Set();
  }
  if (!window.unsavedCells.flattened || !(window.unsavedCells.flattened instanceof Set)) {
    window.unsavedCells.flattened = new Set();
  }


  // ============ 2. 挂载其他核心变量到 window ============
  window.showFlatMode = showFlatMode;
  window.sheetStateManager = sheetStateManager;

  // ============ 3. 上下文同步函数 ============
  const syncWindow = () => {
    window.currentPdfId = selectedPdf.value?.id ?? null;
    window.currentExcelFile = selectedExcelFile.value ?? null;
    window.currentSheetName = selectedSheet.value?.name ?? null;
    window.currentTableType = showFlatMode.value ? 'flattened' : 'original';
  };

  syncWindow(); // 立即执行一次
  watch([selectedPdf, selectedExcelFile, selectedSheet, showFlatMode], syncWindow);

  // ============ 4. 键盘事件监听 ============
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && actualHasUnsavedChanges.value) {
      console.log('⌨️ ESC 键按下，尝试退出编辑模式');
      exitEditMode();
    }
  });

  // ============ 5. 一键验收命令 ============
  window.checkIsolation = () => {
    const t = showFlatMode.value ? 'flattened' : 'original';
    return {
      当前模式: t,
      修改池size: window.unsavedCells[t]?.size ?? 0,
      状态管理器有改动: sheetStateManager.hasUnsavedChanges(t),
      按钮亮灭一致: document.querySelector('.save-buttons .el-button')?.disabled === !(window.unsavedCells[t]?.size > 0),
      另一模式改动未丢: window.unsavedCells[t === 'original' ? 'flattened' : 'original']?.size ?? 0
    };
  };

  console.log('🔍 已挂载 window.checkIsolation()，在控制台直接调用即可验收隔离');

  // ============ 6. 开发环境监控 ============
  if (isDev.value) {
    monitorSaveButtons();
  }

  // ============ 7. 初始按钮状态检查和草稿恢复 ============
  nextTick(() => {
    if (selectedSheet.value) {
      console.log('🎯 初始按钮状态检查');
      updateSaveStatus();
    }
    restoreDraftIfExists();
  });

  // ============ 8. 暴露全局调试方法 ============
  if (typeof window !== 'undefined') {
    window.exitEditMode = exitEditMode;
  }

  console.log('✅ onMounted 初始化完成');
});



// 🔥 新增：手动测试函数
const testCellChange = () => {
  console.group('🧪 手动测试单元格修改')

  console.log('1. 当前状态检查:')
  console.log('   window.unsavedCells 存在:', !!window.unsavedCells)
  console.log('   window.unsavedCells.original 大小:', window.unsavedCells?.original?.size || 0)
  console.log('   selectedPdf:', selectedPdf.value?.id)
  console.log('   selectedSheet:', selectedSheet.value?.name)
  console.log('   selectedExcelFile:', selectedExcelFile.value)

  // 模拟单元格修改
  const testCellInfo = {
    row: 1,
    col: 1,
    oldValue: '原值',
    newValue: '新值'
  }

  console.log('2. 模拟单元格修改:', testCellInfo)

  // 手动调用 handleCellChanged
  console.log('3. 调用 handleCellChanged...')
  handleCellChanged(testCellInfo)

  console.log('4. 调用后状态检查:')
  console.log('   window.unsavedCells.original 大小:', window.unsavedCells?.original?.size || 0)
  console.log('   window.unsavedCells.original 内容:', Array.from(window.unsavedCells?.original || []))

  const result = {
    beforeSize: 0,
    afterSize: window.unsavedCells?.original?.size || 0,
    success: (window.unsavedCells?.original?.size || 0) > 0
  }

  console.log('5. 测试结果:', result)
  console.groupEnd()

  return result
}

// 🔥 暴露给全局调试
if (typeof window !== 'undefined') {
  window.testCellChange = testCellChange
  console.log('✅ testCellChange 函数已暴露到全局')
}



// 在 ThreeColumnPage.vue 中添加全局调试函数
if (typeof window !== 'undefined') {
  window.debugSearchResults = () => {
    console.log('🔍 全局调试搜索数据:')
    console.log('searchResults:', searchResults.value)
    console.log('searchResults 长度:', searchResults.value.length)

    if (searchResults.value.length > 0) {
      const firstPdf = searchResults.value[0]
      console.log('第一个PDF的字段:', Object.keys(firstPdf))
      console.log('第一个PDF的数据:', firstPdf)
      console.log('filename字段:', firstPdf.filename)
      console.log('name字段:', firstPdf.name)
      console.log('raw_filename字段:', firstPdf.raw_filename)
    }
  }
}


</script>




<style scoped>
/* 新增：分析按钮相关样式 */


.header-actions {
  flex-shrink: 0;
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