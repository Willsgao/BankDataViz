
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
      <PdfList
        :search-results="searchResults"
        :is-searching="isSearching"
        :filtered-pdf-count="filteredPdfCount"
        :selected-pdf="selectedPdf"
        @toggle-middle="toggleMiddleCollapse"
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
        :save-type="saveType"
        :has-unsaved-changes="actualHasUnsavedChanges"
        :is-dev="isDev"
        @toggle-flat-mode="toggleFlatMode"
        @save-data="saveData"
        @restore-unsaved-data="restoreUnsavedData"
        @cell-changed="handleCellChanged"
        @data-changed="handleDataChanged"
        @update:modelValue="console.log('传递的值:', $event)"
        @unsaved-changes-updated="handleUnsavedChangesUpdated"
      />
    </template>


  </ThreeColumnLayout>
</template>




<script setup>

// 导入组件
import HandsontableExcelViewer from '@/components/excel/HandsontableExcelViewer.vue'
import ThreeColumnLayout from '@/layouts/ThreeColumnLayout.vue'

// 导入子组件
import PdfPreview from '@/components/threecolumns/PdfPreview.vue'
import PdfList from '@/components/threecolumns/PdfList.vue'
import SheetList from '@/components/threecolumns/SheetList.vue'
import ExcelContent from '@/components/threecolumns/ExcelContent.vue'
import SaveStatus from '@/components/threecolumns/SaveStatus.vue'

// 导入工具和组合函数
import { rebuildTwoDimensionalTable, extractTableInfoFromData } from '@/components/threecolumns/tableUtils'
import { useThreeColumnPage } from '@/components/threecolumns/useThreeColumnPage'
import { useDataManager } from '@/components/threecolumns/useDataManager'
import { useSheetOperations } from '@/components/threecolumns/useSheetOperations'

// 导入图标
import { Download, Close, Document, Grid, Loading, Timer } from '@element-plus/icons-vue'

// 导入工具
import { getApiUrl } from '@/utils/config'
import { ElMessage, ElMessageBox } from 'element-plus'
import excelDataCache from '@/utils/excelDataCache'
import dataManager from '@/utils/dataManager.js'
import sheetStateManager from '@/utils/SheetStateManager.js'

import { saveDraftToIndexedDB, clearDraftFromIndexedDB } from '@/utils/draftDB'

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
  loadExcelData: loadExcelDataBase,
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
  selectSheet: selectSheetUtil,
  toggleFlatMode: toggleFlatModeUtil,
  loadExcelSheets: loadExcelSheetsUtil,
  loadAllClassData: loadAllClassDataUtil
} = useSheetOperations(generateTableColumns)



// ============ 组件方法 ============

const excelContent = ref(null)

// 中间区域折叠
const toggleMiddleCollapse = () => {
  isMiddleCollapsed.value = !isMiddleCollapsed.value
}

// PDF加载完成
const onPdfLoad = () => {
  console.log('PDF加载完成')
}

const isDev = ref(process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'dev')


// 工具函数：不读取响应式数据，仅传参
const safeRefreshExcelContent = (hasUnsaved /* 布尔值 */) => {
  if (hasUnsaved) {
    console.log('⏸️ 编辑模式中，跳过 ExcelContent 强制刷新')
    return
  }
  excelContentKey.value++
}

// ThreeColumnPage.vue 第 320 行附近
const actualHasUnsavedChanges = computed(() => {
  const tableType = showFlatMode.value ? 'flattened' : 'original';

  const result = window.unsavedCells?.size > 0 ||
                sheetStateManager?.hasUnsavedChanges(tableType) ||
                modifiedCellsCount.value > 0;

  console.log('🚨 actualHasUnsavedChanges:', result, {
    全局: window.unsavedCells?.size || 0,
    管理器: sheetStateManager?.hasUnsavedChanges(tableType),
    计数: modifiedCellsCount.value
  });

  return result;
});


const handleCellChanged = (cellInfo) => {
  console.log('📝 ThreeColumnPage: 收到单元格修改:', cellInfo);

  // 检查当前上下文
  const currentContext = sheetStateManager.getActiveContext();
  const tableType = showFlatMode.value ? 'flattened' : 'original';

  // 🔥 关键修复：如果没有上下文，立即创建
  if (!currentContext && selectedPdf.value && selectedExcelFile.value && selectedSheet.value) {
    sheetStateManager.setActiveContext(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name,
      tableType
    );
    console.log('🔥 紧急创建上下文');
  }

  // 确保有正确的上下文
  if (selectedPdf.value && selectedExcelFile.value && selectedSheet.value) {
    const context = {
      pdfId: selectedPdf.value.id,
      excelFile: selectedExcelFile.value,
      sheetName: selectedSheet.value.name,
      tableType: tableType
    };

    // 再次确认上下文
    sheetStateManager.setActiveContext(
      context.pdfId,
      context.excelFile,
      context.sheetName,
      context.tableType
    );
  }

  // 记录到 sheetStateManager
  const success = sheetStateManager.recordCellChange(
    cellInfo.row,
    cellInfo.col,
    cellInfo.oldValue || '',
    cellInfo.newValue,
    tableType
  );

  console.log('🔥 记录单元格修改结果:', {
    成功: success,
    修改: { row: cellInfo.row, col: cellInfo.col },
    当前上下文: sheetStateManager.getActiveContext()
  });

  // 强制更新全局状态
  if (typeof window !== 'undefined') {
    if (!window.unsavedCells) window.unsavedCells = new Set();
    const key = `${cellInfo.row},${cellInfo.col}`;
    window.unsavedCells.add(key);
    window.currentHasChanges = true;
    console.log('🌍 更新全局状态:', {
      数量: window.unsavedCells.size,
      当前单元格: key
    });
  }

  // 立即更新保存状态
  updateSaveStatus();
};



const handleDataChanged = (dataInfo) => {
  console.log('📥 收到批量修改:', dataInfo)

  // 检查是否有选中的 sheet 和 pdf
  if (!selectedSheet.value || !selectedPdf.value) {
    console.warn('❌ 没有选中的 sheet 或 pdf，忽略修改')
    return
  }

  // 确定当前表类型
  const currentTableType = showFlatMode.value ? 'flattened' : 'original'

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
}



// ============ 主要业务方法 ============

// 选择PDF（包装）
const selectPdf = async (pdf) => {
  const result = await selectPdfBase(pdf)
  if (result.success && result.fileId) {
    await loadExcelSheets(result.fileId)
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


// ThreeColumnPage.vue - 只修复 tableType 逻辑
const selectSheet = async (sheet, excelFileName) => {
  console.log('🎯 选择Sheet:', {
    sheet: sheet?.name,
    excelFile: excelFileName,
    pdf: selectedPdf.value?.id
  })

  // 先调用原有的 selectSheetUtil
  const result = await selectSheetUtil(
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

  // 关键：在调用 selectSheetUtil 后设置 SheetStateManager 上下文
  if (sheet && selectedPdf.value) {
    // 修改这里：根据实际显示模式确定表类型
    const tableType = showFlatMode.value ? 'flattened' : 'original'

    sheetStateManager.setActiveContext(
      selectedPdf.value.id,
      excelFileName,
      sheet.name,
      tableType
    )

    console.log('🎯 设置 SheetStateManager 上下文:', {
      pdfId: selectedPdf.value.id,
      excelFile: excelFileName,
      sheetName: sheet.name,
      tableType: tableType,
      确保一致: `showFlatMode=${showFlatMode.value}, tableType=${tableType}`
    })

    // 立即检查上下文和保存状态
    const context = sheetStateManager.getActiveContext()
    const hasUnsavedChanges = sheetStateManager.hasUnsavedChanges(tableType)

    console.log('🔍 选择后状态检查:', {
      上下文: context,
      有未保存修改: hasUnsavedChanges,
      未保存数量: sheetStateManager.getUnsavedChangesCount(tableType),
      当前显示模式: showFlatMode.value ? '扁平化' : '原始'
    })
  }

  nextTick(() => {
      console.log('🔄 强制更新保存按钮状态');
      updateSaveStatus();
    })

    // 如果存在草稿，就不再重新加载原始数据
    const tableType = showFlatMode.value ? 'flattened' : 'original'
    const draftKey = `excel_draft_${selectedPdf.value.id}_${excelFileName}_${sheet.name}_${tableType}`
    const hasDraft = !!localStorage.getItem(draftKey)

    if (hasDraft) {
      console.log('🟢 存在草稿，跳过 loadExcelData')
      nextTick(() => setTimeout(() => restoreDraft(), 600))
    } else {
      console.log('🔵 无草稿，正常加载原始数据')
      nextTick(async () => {
        await loadExcelData(sheet.name, excelFileName)
      })
    }


  return result
}

// 加载Excel数据（包装）
const loadExcelData = async (sheetName, excelFileName) => {
  const result = await loadExcelDataBase(sheetName, excelFileName, getApiUrl)

  if (result.success) {
    const pdfId = selectedPdf.value.id

    // 保存到缓存
    excelDataCache.setOriginalData(pdfId, excelFileName, sheetName, result.data)
    excelDataCache.setCurrentSheet(pdfId, excelFileName, sheetName)

    // 保存到状态管理器
    const currentContext = sheetStateManager.getActiveContext()
    if (currentContext &&
        currentContext.pdfId === pdfId &&
        currentContext.excelFile === excelFileName &&
        currentContext.sheetName === sheetName) {
      sheetStateManager.setData('original', result.data)
    }

    // 重置模式
    currentTableMode.value = 'original'
    window.currentTableMode = 'original'
    showFlatMode.value = false
    flatData.value = []

    // 设置数据
    excelData.value = result.data
    generateTableColumns(result.data)

    ElMessage.success(`已加载表格: ${sheetName}`)

    return { success: true }
  } else {
    ElMessage.warning(`无法加载表格数据: ${result.error}`)
    return { success: false, error: result.error }
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


// ThreeColumnPage.vue - 修复 toggleFlatMode 函数
const toggleFlatMode = async () => {
  console.log('🔄 切换扁平化模式...')

  if (!selectedSheet.value || !selectedPdf.value) {
    ElMessage.warning('请先选择表格')
    return
  }

  try {
    // 保存切换前的状态
    const wasFlatMode = showFlatMode.value
    const newTableType = !wasFlatMode ? 'flattened' : 'original'

    console.log('📊 切换信息:', {
      当前模式: wasFlatMode ? '扁平化' : '原始',
      目标模式: !wasFlatMode ? '扁平化' : '原始',
      表类型: newTableType,
      sheet: selectedSheet.value.name
    })

    // 关键：先更新上下文
    sheetStateManager.setActiveContext(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name,
      newTableType
    )

    console.log('✅ 上下文已更新:', {
      pdfId: selectedPdf.value.id,
      excelFile: selectedExcelFile.value,
      sheetName: selectedSheet.value.name,
      tableType: newTableType
    })

    // 如果当前是原始模式，切换到扁平化
    if (!wasFlatMode) {
      console.log('🔀 切换到扁平化模式')

      // 清除可能存在的旧缓存
      try {
        if (dataManager && dataManager.indexedDBManager) {
          await dataManager.indexedDBManager.deleteFlattenedCache(
            selectedPdf.value.id,
            selectedExcelFile.value,
            selectedSheet.value.name
          )
          console.log('🧹 已清除旧缓存')
        }
      } catch (clearError) {
        console.warn('⚠️ 清除缓存失败:', clearError.message)
      }

      // 直接调用 API 函数
      await convertToFlatData()

      // 检查是否成功
      if (flatData.value.length > 0) {
        // 再次确认上下文（因为convertToFlatData可能会重置）
        sheetStateManager.setActiveContext(
          selectedPdf.value.id,
          selectedExcelFile.value,
          selectedSheet.value.name,
          'flattened'
        )

        console.log('✅ 扁平化成功:', flatData.value.length, '行')
        ElMessage.success(`数据扁平化成功，${flatData.value.length}行`)
      }

    } else {
      // 切换回原始模式
      console.log('🔀 切换回原始模式')

      // 上下文已经在上面更新了，这里只需确认
      sheetStateManager.setActiveContext(
        selectedPdf.value.id,
        selectedExcelFile.value,
        selectedSheet.value.name,
        'original'
      )

      showFlatMode.value = false
      flatData.value = []

      // 重新加载原始数据
      if (selectedSheet.value) {
        await loadExcelData(selectedSheet.value.name, selectedExcelFile.value)
      }

      ElMessage.success('已切换回原始模式')
    }

  } catch (error) {
    console.error('❌ 切换失败:', error)
    ElMessage.error(`切换失败: ${error.message}`)
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
  const currentData = showFlatMode.value ? flatData.value : excelData.value

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



/**
 * 恢复 localStorage 草稿
 * 带详细日志，方便确认数据差异
 */
const restoreDraft = async (retry = 0) => {
  if (!selectedPdf.value || !selectedSheet.value || !selectedExcelFile.value) {
    console.log('⏹️ restoreDraft: 缺少选中项，直接返回')
    return
  }

  const tableType = showFlatMode.value ? 'flattened' : 'original'
  const draftKey = `excel_draft_${selectedPdf.value.id}_${selectedExcelFile.value}_${selectedSheet.value.name}_${tableType}`

  const raw = localStorage.getItem(draftKey)
  console.log('🔍 restoreDraft: 读取草稿 key =', draftKey)
  console.log('🔍 restoreDraft: raw 是否存在 =', !!raw)
  if (!raw) return

  let draft
  try {
    draft = JSON.parse(raw)
  } catch (e) {
    console.error('❌ restoreDraft: 解析草稿失败', e)
    return
  }

  console.log('📦 restoreDraft: 草稿内容', {
    数据行数: draft.data?.length,
    修改条数: draft.modifications?.length,
    表类型: draft.tableType,
    保存时间: new Date(draft.timestamp).toLocaleString()
  })

  // 1. 获取 Handsontable 实例
  const viewer = showFlatMode.value
    ? excelContent.value?.$refs?.flatViewer
    : excelContent.value?.$refs?.originalViewer

  const hot = viewer?.getSafeHotInstance?.()
  if (!hot) {
    if (retry < 10) {
      console.warn(`⚠️ 表格实例未就绪，${retry + 1}/10 重试...`)
      return setTimeout(() => restoreDraft(retry + 1), 150)
    }
    console.error('❌ 实例始终未就绪，放弃恢复草稿')
    return
  }

  // 2. ===== 数据对比 =====
  const currentData = hot.getData()          // 当前表格数据
  const draftData = draft.data               // 草稿数据
  console.log('📊 数据对比', {
    当前行数: currentData.length,
    草稿行数: draftData.length,
    示例当前: currentData[2],
    示例草稿: draftData[2]
  })

  // 3. 写入草稿数据（静默）
  hot.loadData(draftData)
  console.log('✅ 已调用 hot.loadData(draftData)')

  // 4. ★★★ 把草稿数据写回「数据源」，防止下次 loadExcelData 冲掉草稿 ★★★
  const pdfId   = selectedPdf.value.id
  const excel   = selectedExcelFile.value
  const sheet   = selectedSheet.value.name

  if (tableType === 'original') {
    excelDataCache.setOriginalData(pdfId, excel, sheet, draftData)
  } else {
    excelDataCache.setFlattenedData(pdfId, excel, sheet, draftData)
  }
  sheetStateManager.setData(tableType, draftData)

  // 5. 补录修改记录
  if (draft.modifications?.length) {
    draft.modifications.forEach(m => {
      sheetStateManager.recordCellChange(m.row, m.col, m.oldValue, m.newValue, tableType)
      console.log('📝 补录修改', `[${m.row},${m.col}]`, `${m.oldValue} → ${m.newValue}`)
    })
  }

  // 6. 全局未保存集合
  if (typeof window !== 'undefined') {
    window.unsavedCells = new Set(draft.modifications.map(m => `${m.row},${m.col}`))
    window.currentHasChanges = window.unsavedCells.size > 0
  }

  // 7. 刷新红色样式
  viewer?.updateModifiedCellsStyle?.()
  console.log('🎨 已调用 updateModifiedCellsStyle')

  // 8. 刷新按钮状态
  updateSaveStatus()

  console.log('✅ 草稿恢复完成', {
    恢复单元格数: draft.modifications.length,
    表类型: tableType,
    sheet: selectedSheet.value.name
  })
  ElMessage.success(`已恢复草稿（${draft.modifications.length} 处修改）`)
}


const saveData = async (type) => {
  console.log('💾 ThreeColumnPage: 保存数据', type)

  // 检查是否有选中的表格
  if (!selectedPdf.value || !selectedSheet.value || !selectedExcelFile.value) {
    ElMessage.warning('请先选择表格')
    return { success: false, error: '未选择表格' }
  }

  // 检查是否有未保存修改
  const currentTableType = showFlatMode.value ? 'flattened' : 'original'
  const hasChanges = window.unsavedCells?.size > 0 || sheetStateManager.hasUnsavedChanges(currentTableType)

  if (!hasChanges) {
    ElMessage.warning('没有需要保存的修改')
    return { success: false, error: '没有修改' }
  }

  console.log('✅ 满足保存条件:', {
    表格: selectedSheet.value.name,
    保存类型: type,
    当前表类型: currentTableType,
    有未保存修改: hasChanges
  })

  // 设置保存状态
  saving.value = true
  saveType.value = type

  try {
    // 1. 获取当前未保存的修改 - 关键修复部分
    let unsavedModifications = []

    // 关键：优先检查全局状态
    if (window.unsavedCells?.size > 0) {
      console.log('✅ 检测到全局未保存修改，数量:', window.unsavedCells.size)

      // 获取当前表格数据
      const currentData = showFlatMode.value ? flatData.value : excelData.value

      // 获取表格实例（用于读取单元格值）
      const hotInstance = getActiveHotInstance()

      // 构建修改记录
      for (const key of window.unsavedCells) {
        const [row, col] = key.split(',').map(Number)
        let newValue = ''

        // 尝试获取单元格值
        if (hotInstance && hotInstance.getDataAtCell) {
          newValue = hotInstance.getDataAtCell(row, col) || ''
        } else if (currentData && currentData[row]) {
          // 从数据数组中获取
          newValue = currentData[row][col] || ''
        }

        unsavedModifications.push({
          row,
          col,
          oldValue: '', // 旧值可能无法获取
          newValue: newValue,
          saved: false,
          timestamp: Date.now(),
          tableType: currentTableType
        })
      }

      console.log(`✅ 已构建 ${unsavedModifications.length} 个修改记录`)
    } else {
      // 回退到 sheetStateManager
      unsavedModifications = sheetStateManager.getModifications(currentTableType)
        .filter(mod => !mod.saved)
    }

    console.log('📤 准备保存的修改:', {
      类型: type,
      表类型: currentTableType,
      修改数: unsavedModifications.length,
      全局未保存数: window.unsavedCells?.size || 0
    })

    // 2. 获取当前数据 - 直接从响应式数据获取
    let currentData = null
    let hotInstance = null

    if (showFlatMode.value) {
      // 扁平化模式：直接从 flatData 获取数据
      currentData = flatData.value
      console.log('📊 从 flatData 获取数据:', currentData?.length || 0, '行')

      // 尝试获取实例（可选）
      if (excelContent.value?.$refs?.flatViewer) {
        hotInstance = excelContent.value.$refs.flatViewer
      }
    } else {
      // 原始模式：直接从 excelData 获取数据
      currentData = excelData.value
      console.log('📊 从 excelData 获取数据:', currentData?.length || 0, '行')

      // 尝试获取实例（可选）
      if (excelContent.value?.$refs?.originalViewer) {
        hotInstance = excelContent.value.$refs.originalViewer
      }
    }

    // 如果数据为空，尝试从缓存获取
    if (!currentData || currentData.length === 0) {
      console.warn('⚠️ 表格数据为空，尝试从缓存获取')
      const pdfId = selectedPdf.value.id
      const excelFile = selectedExcelFile.value
      const sheetName = selectedSheet.value.name

      if (showFlatMode.value) {
        currentData = excelDataCache.getFlattenedData(pdfId, excelFile, sheetName)
      } else {
        currentData = excelDataCache.getOriginalData(pdfId, excelFile, sheetName)
      }
    }

    if (!currentData || currentData.length === 0) {
      throw new Error('无法获取表格数据')
    }

    console.log('✅ 成功获取表格数据:', currentData.length, '行')

    if (type === 'draft') {
      // 1. 落库 localStorage
      const storageKey = `excel_draft_${selectedPdf.value.id}_${selectedExcelFile.value}_${selectedSheet.value.name}_${currentTableType}`
      const draftData = {
        data: currentData,
        modifications: unsavedModifications,
        totalChanges: unsavedModifications.length,
        timestamp: Date.now(),
        tableType: currentTableType,
        pdfId: selectedPdf.value.id,
        excelFile: selectedExcelFile.value,
        sheetName: selectedSheet.value.name
      }
      localStorage.setItem(storageKey, JSON.stringify(draftData))

      // 2. 立即把修改写进当前表格（内存 + 缓存 + 重绘）
      const updatedData = currentData.map(row => [...row])          // 深拷贝一行
      unsavedModifications.forEach(m => {
        if (updatedData[m.row] && updatedData[m.row][m.col] !== undefined) {
          updatedData[m.row][m.col] = m.newValue
        }
      })

      if (currentTableType === 'original') {
        excelData.value = updatedData
        excelDataCache.setOriginalData(
          selectedPdf.value.id,
          selectedExcelFile.value,
          selectedSheet.value.name,
          updatedData
        )
      } else {
        flatData.value = updatedData
        excelDataCache.setFlattenedData(
          selectedPdf.value.id,
          selectedExcelFile.value,
          selectedSheet.value.name,
          updatedData
        )
      }

      // 3. 通知 Handsontable 重绘
      const hot = getActiveHotInstance()
      if (hot) hot.loadData(updatedData)

      // 4. 标记已保存 & 刷新组件
      sheetStateManager.markChangesAsSaved(currentTableType)
      excelContentKey.value++        // 强制重渲染

      // ★★★ 新增：把合并后的数据写回缓存，保证下次加载拿到的是“含草稿”版本 ★★★
      const pdfId   = selectedPdf.value.id
      const excel   = selectedExcelFile.value
      const sheet   = selectedSheet.value.name
      if (currentTableType === 'original') {
        excelDataCache.setOriginalData(pdfId, excel, sheet, updatedData)
      } else {
        excelDataCache.setFlattenedData(pdfId, excel, sheet, updatedData)
      }
      sheetStateManager.setData(currentTableType, updatedData)

      ElMessage.success(`草稿已保存 (${unsavedModifications.length} 处修改)`)
    } else if (type === 'final') {
      // ============ 最终保存（调用后端API）============
      try {
        const response = await fetch(getApiUrl('/save-excel'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            pdf_id: selectedPdf.value.id,
            excel_file: selectedExcelFile.value,
            sheet_name: selectedSheet.value.name,
            table_type: currentTableType,
            modifications: unsavedModifications,
            total_changes: unsavedModifications.length,
            data: currentData // 使用当前数据
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const result = await response.json()

        if (result.success) {
          // 后端保存成功后，标记为已保存
          sheetStateManager.markChangesAsSaved(currentTableType)

          // 清除未保存状态
          sheetStateManager.clearUnsavedChanges(currentTableType)

          // 退出编辑模式（如果有实例的话）
          if (hotInstance && hotInstance.updateSettings) {
            hotInstance.updateSettings({ readOnly: true })
          }

          const saveMessage = `最终保存成功 (${result.saved_count || unsavedModifications.length}处修改)`
          saveStatus.value = {
            type: 'success',
            text: saveMessage
          }
          ElMessage.success(saveMessage)

          // 强制刷新组件
          nextTick(() => {
            excelContentKey.value++
          })
        } else {
          throw new Error(result.error || '后端保存失败')
        }
      } catch (error) {
        console.error('❌ 调用后端API失败:', error)
        throw new Error(`后端保存失败: ${error.message}`)
      }
    }

    // 更新保存状态
    updateSaveStatus()
    lastSaveTime.value = Date.now()

    // 更新全局状态
    if (typeof window !== 'undefined') {
      window.unsavedCells = new Set()
      window.currentHasChanges = false
    }

    return {
      success: true,
      message: type === 'draft' ? '草稿已保存' : '最终保存成功',
      data: {
        saved_cells: unsavedModifications,
        total_saved: unsavedModifications.length
      }
    }
  } catch (error) {
    console.error('❌ 保存过程中出错:', error)
    saveStatus.value = {
      type: 'error',
      text: `保存失败: ${error.message}`
    }
    ElMessage.error(`保存失败: ${error.message}`)
    return {
      success: false,
      error: error.message
    }
  } finally {
    saving.value = false
    saveType.value = ''
  }
}


// ============ 其他方法保持原有逻辑 ============
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
          // 先清除旧缓存，再保存新数据
          await dataManager.deleteFlattenedData() // 如果这个方法存在

          // 或者使用 update 方法
          await dataManager.saveFlattenedData(result.rows, currentOriginalData)
          console.log('📦 扁平化数据已缓存到 IndexedDB')
        } catch (cacheError) {
          console.warn('⚠️ 缓存到 IndexedDB 失败:', cacheError)
          // 尝试其他方式
          try {
            // 如果是主键冲突，尝试更新
            if (cacheError.name === 'ConstraintError') {
              console.log('尝试更新现有缓存...')
              await dataManager.updateFlattenedData(result.rows, currentOriginalData)
            }
          } catch (updateError) {
            console.warn('⚠️ 更新缓存也失败:', updateError.message)
          }
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
          await saveData('draft')
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

const getActiveHotInstance = () => {
  // 优先通过 ExcelContent 暴露的方法拿实例
  const viewer = excelContent.value?.$refs?.[
    showFlatMode.value ? 'flatViewer' : 'originalViewer'
  ];
  if (viewer?.getSafeHotInstance) return viewer.getSafeHotInstance();
  if (viewer?.hotInstance) return viewer.hotInstance;

  // 兜底：读全局
  return window.__excelHotInstance || null;
};


onMounted(() => {
  // 绑定 ESC 键退出编辑模式
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && actualHasUnsavedChanges.value) {
      console.log('⌨️ ESC 键按下，尝试退出编辑模式')
      exitEditMode()
    }
  })

  // 修改这里：使用 isDev.value 而不是 props.isDev
  if (isDev.value) {
    monitorSaveButtons()
  }
})

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



// ============ 生命周期和监听器 ============
import { ref, inject, computed, watch, onMounted, onUnmounted, nextTick,
onBeforeUnmount, onUpdated, defineEmits  } from 'vue'

const searchResults = inject('searchResults', [])
const isSearching = inject('isSearching', ref(false))

const sheetStateUpdateTrigger = ref(0)

const emit = defineEmits([
  'save-success',                // 保存成功
  'unsaved-changes-updated',     // 未保存修改更新
  'cell-changed',                // 单元格修改
  'data-changed',                // 数据修改
  'toggle-flat-mode',            // 切换扁平化模式
  'restore-unsaved-data'         // 恢复未保存数据
])

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


// 添加监听，确保值正确传递
watch(actualHasUnsavedChanges, (newVal) => {
  console.log('🚨 ThreeColumnPage -> ExcelContent 传递的值:', {
    hasUnsavedChanges: newVal,
    时间: new Date().toLocaleTimeString(),
    类型: typeof newVal,
    布尔值: newVal === true || newVal === false
  })
}, { immediate: true })

// 添加一个手动检查函数
const checkExcelContentProps = () => {
  if (excelContent.value) {
    console.log('🔍 ExcelContent 实例:', {
      props: excelContent.value.$props,
      hasUnsavedChangesProp: excelContent.value.$props.hasUnsavedChanges
    })
  }
}




onMounted(() => {
  // 绑定 ESC 键退出编辑模式
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && actualHasUnsavedChanges.value) {
      console.log('⌨️ ESC 键按下，尝试退出编辑模式')
      exitEditMode()
    }
  })

  // 初始化时强制设置按钮状态
  nextTick(() => {
    if (selectedSheet.value) {
      console.log('🎯 初始按钮状态检查')
      // 手动更新一次
      updateSaveStatus()
    }
  })
})


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
        await saveData('draft')
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

// 方式 B：不管环境，先挂出来（调完再删）
// window.sheetStateManager = sheetStateManager
// window.debugSaveButton = debugSaveButton
// window.actualHasUnsavedChanges = actualHasUnsavedChanges

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