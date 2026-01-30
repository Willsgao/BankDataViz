<template>
  <div class="excel-content-container">
    <!-- 第一行：标题 + 按钮（32 px） -->
    <div class="section-header">
      <div class="header-main">
        <div class="header-left">
          <h3>表格</h3>
          <div v-if="selectedSheet" class="header-info">
            <el-tag type="primary">{{ selectedSheet.name }}</el-tag>
          </div>
        </div>

        <div class="header-actions">
          <div class="action-row">
            <!-- 新增：导航按钮 -->
            <div class="navigation-buttons">
              <el-button
                size="small"
                :disabled="!hasPreviousSheet"
                @click="goToPreviousSheet"
                title="上一页"
              >
                <el-icon><ArrowLeft /></el-icon>
                上一页
              </el-button>

              <el-button
                size="small"
                :disabled="!hasNextSheet"
                @click="goToNextSheet"
                title="下一页"
              >
                下一页
                <el-icon><ArrowRight /></el-icon>
              </el-button>

              <span v-if="currentPageInfo" class="page-indicator">
                第{{ currentPageInfo.pageNumber }}页
                (表{{ currentPageInfo.currentTablePosition }}/{{ currentPageInfo.totalTablesInPage }})
              </span>
            </div>



            <!-- 主功能：大按钮 -->
            <el-button
              type="primary"
              size="default"
              :disabled="!props.selectedSheet || excelData.length === 0"
              @click="handleSmartToggle(
                props.selectedSheet,
                props.selectedPdf,
                props.selectedExcelFile,
                showFlatMode,
                excelData,
                flatData,
                () => $emit('toggle-flat-mode')
              )"
              :loading="loadingFlat"
              :key="`flat-button-${showFlatMode}`"
            >
              <el-icon><DataAnalysis /></el-icon>
              {{ showFlatMode ? '二维化' : '扁平化' }}
            </el-button>

            <div class="save-buttons">
              <el-button
              type="success"
              size="small"
              :disabled="!enableSaveButtons || saving"
              @click="triggerSave"
              :loading="saving"
            >
              <el-icon><Check /></el-icon>
              保存
            </el-button>
            </div>

          </div>
        </div>
      </div>
    </div>

    <!-- 当前单元格信息（有值才显示） -->
    <template v-if="currentCell.position">
      <div class="cell-info-container">
        <el-tag size="small">{{ currentCell.position }}</el-tag>
        <el-tag size="small" :type="currentCell.isRange ? 'warning' : 'info'">
          {{ currentCell.isRange ? '选区' : currentCell.type }}
        </el-tag>

        <template v-if="currentCell.isRange">
          <span class="cell-txt">
            {{ currentCell.content }}
            <span v-if="currentCell.rangeInfo" class="range-details">
              ({{ currentCell.rangeInfo.rowCount }}行 × {{ currentCell.rangeInfo.colCount }}列)
            </span>
          </span>
        </template>
        <template v-else>
          <span class="cell-txt">{{ currentCell.content }}</span>
        </template>
      </div>
    </template>

    <!-- 表格区域：自动撑满剩余高度 -->
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

      <!-- 表格显示 -->
      <div v-else class="handsontable-container">
        <div v-show="!showFlatMode">
          <HandsontableExcelViewer
            ref="originalViewer"
            :excel-data="excelData"
            :sheet-name="selectedSheet?.name || ''"
            :pdf-id="selectedPdf?.id"
            :excel-file-name="selectedExcelFile"
            :flat-data="flatData"
            :key="`original-${selectedSheet?.name}-${excelData.length}`"
            @cell-changed="handleCellChanged"
            @data-changed="handleDataChanged"
            @cell-change="handleSheetCellChange"
            @instance-ready="handleInstanceReady"
            @edit-status-changed="handleEditStatusChanged"
            @global-flatten-complete="handleGlobalFlattenComplete"
          />
        </div>

        <div v-show="showFlatMode">
          <HandsontableExcelViewer
            ref="flatViewer"
            :excel-data="flatData"
            :sheet-name="`扁平化_${selectedSheet?.name || ''}`"
            :pdf-id="selectedPdf?.id"
            :excel-file-name="selectedExcelFile"
            :key="`flat-${selectedSheet?.name}-${flatData.length}`"
            @cell-changed="handleCellChanged"
            @data-changed="handleDataChanged"
            @cell-change="handleSheetCellChange"
            @instance-ready="handleInstanceReady"
            @edit-status-changed="handleEditStatusChanged"
            @global-flatten-complete="handleGlobalFlattenComplete"
          />
        </div>

        <div v-if="showFlatMode && flatData.length === 0 && loadingFlat" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          正在扁平化数据...
        </div>

        <div v-if="showFlatMode && flatData.length === 0 && !loadingFlat" class="empty-state">
          <el-icon><Grid /></el-icon>
          <p>暂无扁平化数据</p>
          <p class="tip">点击"数据扁平化"按钮生成数据</p>
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import SaveStatus from './SaveStatus.vue'

import * as ExcelKey from '@/utils/excelKeyUtils.js'
import sheetStateManager from '@/utils/SheetStateManager.js'

import HandsontableExcelViewer from '@/components/excel/HandsontableExcelViewer.vue'
import {
  DataAnalysis, Document, Check, Refresh, Timer, Grid, Loading, ArrowLeft, ArrowRight
} from '@element-plus/icons-vue'
import { defineProps, defineEmits, ref, computed, watch, nextTick, onMounted   } from 'vue'


import { ElMessage } from 'element-plus'

import { useSheetOperations  } from './useSheetOperations.js'
const sheetOperations = useSheetOperations()  // 可能需要参数
const { handleSmartToggle, checkIfFlattenedData  } = sheetOperations


/* ===== 给模板用的空壳变量（先让渲染不报错） ===== */
const emptyCount = ref(0)          // 空白单元格数量
const stats = ref({                // 选中区域统计
  rowCount: 0,
  numericCount: 0,
  sum: 0,
  average: 0,
  max: 0,
  min: 0
})

// 当前单元格信息（空壳先占位）
const currentCell = ref({
  position: '',
  content: '',
  type: '文本',
  isNumeric: false
})

// 监听子组件的选中事件
const handleCellSelected000 = (cell) => {
  currentCell.value = cell
}


// 监听子组件的选中事件
// 监听子组件的选中事件
const handleCellSelected = (cell) => {
  console.log('🔍🔍 收到选择事件:', cell)

  // 检查是否是选区（多个单元格）
  if (cell.isRange && cell.range) {
    // 多个单元格选区
    currentCell.value = {
      position: `R${cell.range.start.row + 1}C${cell.range.start.col + 1}:R${cell.range.end.row + 1}C${cell.range.end.col + 1}`,
      content: `选中 ${cell.totalCells || 0} 个单元格`,
      type: '选区',
      isNumeric: false,
      isRange: true,
      rangeInfo: {
        rowCount: cell.range.end.row - cell.range.start.row + 1,
        colCount: cell.range.end.col - cell.range.start.col + 1,
        totalCells: cell.totalCells || 0
      }
    }
  } else {
    // 单个单元格
    currentCell.value = {
      position: cell.position || '',
      content: cell.content || '',
      type: cell.type || '文本',
      isNumeric: cell.isNumeric || false,
      isRange: false
    }
  }

  console.log('✅ 更新后的currentCell:', currentCell.value)
}


// 存后台按钮启用条件
const enableFinalButton = computed(() => {
  console.log('🔍 [存后台按钮] 启用条件检查:', {
    时间: new Date().toLocaleTimeString(),
    有sheet: !!props.selectedSheet,
    全局unsavedCells数量: window.unsavedCells?.size || 0,
    状态管理器修改数: sheetStateManager?.getUnsavedChangesCount?.(props.showFlatMode ? 'flattened' : 'original') || 0
  })

  if (!props.selectedSheet) {
    return false
  }

  // 检查未保存修改
  const hasUnsaved =
    (window.unsavedCells?.size > 0) ||
    (sheetStateManager?.hasUnsavedChanges(props.showFlatMode ? 'flattened' : 'original'))

  console.log('  ✅ 是否有未保存修改:', hasUnsaved)
  return hasUnsaved
})



/* ===== 后续你可以把真实数据接进来 ===== */
// 例：当 Handsontable 抛出选中事件时
const handleSelection = (sel) => {
  stats.value = sel                    // 真实统计对象
  emptyCount.value = sel.emptyCount    // 真实空白数
}

const forceRefreshKey = ref(0)
const forceUpdateKey = ref(0)

const props = defineProps({
  selectedSheet: Object,
  selectedExcelFile: String,
  selectedPdf: Object,
  excelData: {
    type: Array,
    default: () => []
  },
  flatData: {
    type: Array,
    default: () => []
  },
  showFlatMode: Boolean,
  loadingExcel: Boolean,
  loadingFlat: Boolean,
  saveStatus: {
    type: Object,
    default: () => ({ type: 'info', text: '' })
  },
  modifiedCellsCount: {
    type: Number,
    default: 0
  },
  lastSaveTime: Number,
  saving: Boolean,
  saveType: String,
  hasUnsavedChanges: {  // 注意这里的名称
    type: Boolean,
    default: false,
    required: false
  },
  isDev: {
    type: Boolean,
    default: false
  },
  // 新增：接收父组件透传的 actualHasUnsavedChanges（核心修复）
  actualHasUnsavedChanges: {
    type: Boolean,
    default: false,
    required: false
  },
  sortedSheets: {
    type: Array,
    default: () =>[]
  }

})

// ============ 新增状态 ============
const originalViewer = ref(null)
const flatViewer = ref(null)
const localUnsavedChanges = ref(0)


const savingDraft = ref(false)
const savingFinal = ref(false)


const handleSmartToggleWrapper = () => {
  handleSmartToggle(
    props.selectedSheet,
    props.selectedPdf,
    props.selectedExcelFile,
    showFlatMode,
    excelData,
    flatData,
    () => $emit('toggle-flat-mode')
  )
}

/* 存后台可点条件：有未保存且不在保存中 */
const canSaveFinal = computed(() =>
  !savingFinal.value && (window.unsavedCells?.size > 0 || sheetStateManager.hasUnsavedChanges(props.showFlatMode ? 'flattened' : 'original'))
)


// 触发保存的方法
const triggerSave = () => {
  console.log('💾 ExcelContent: 保存按钮点击')
  // 触发父组件的 save-data 事件
  emit('save-data')
}


// ExcelContent.vue - 在 script 部分添加
const handleInstanceReady = (instanceInfo) => {
  console.log('📡 ExcelContent: 收到实例就绪事件', instanceInfo)

  // 透传给父组件
  emit('instance-ready', instanceInfo)

  // 同时更新本地状态（如果需要）
  if (instanceInfo.tableType === 'original') {
    console.log('✅ 原始表格实例就绪')
  } else {
    console.log('✅ 扁平化表格实例就绪')
  }
}

/* 存草稿：纯前端，永远可点 */
async function handleSaveDraft() {
  savingDraft.value = true
  try {
    // 1. 取当前数据
    const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value
    const key = ExcelKey.getDraftKey(props.selectedPdf.id,
        props.selectedExcelFile,
        props.selectedSheet.name,
        props.showFlatMode ? 'flattened' : 'original')


    // 2. 写 localStorage（确保字符串化）
    const draft = {
      data: viewer.tableData,
      modifications: Array.from(window.unsavedCells?.[props.showFlatMode ? 'flattened' : 'original'] || []),
      savedAt: Date.now()
    }
    localStorage.setItem(key, JSON.stringify(draft))

    // 3. 立即读回验证（控制台可查）
    const back = JSON.parse(localStorage.getItem(key))
    console.log('【草稿验证】', key, back)

    ElMessage.success('草稿已保存')
  } catch (e) {
    console.error('草稿失败', e)
    ElMessage.error('草稿保存失败')
  } finally {
    savingDraft.value = false
  }
}

/* 存后台：调接口 + 防重复 */
async function handleSaveFinal() {
  if (!canSaveFinal.value) return
  savingFinal.value = true
  try {
    const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value
    const payload = {
      pdf_id: props.selectedPdf.id,
      excel_file: props.selectedExcelFile,
      sheet_name: props.selectedSheet.name,
      table_type: props.showFlatMode ? 'flattened' : 'original',
      modifications: Array.from(window.unsavedCells || []).map(key => {
        const [row, col] = key.split(',').map(Number)
        return { row, col, oldValue: '', newValue: viewer.tableData[row][col] || '' }
      }),
      data: viewer.tableData
    }
    await axios.post('/api/excel/save-final', payload)
    // 成功 → 清前端未保存状态
    // window.unsavedCells.clear()
    window.unsavedCells?.[props.showFlatMode ? 'flattened' : 'original']?.clear()
    sheetStateManager.markChangesAsSaved(props.showFlatMode ? 'flattened' : 'original')
    emit('unsaved-changes-updated', false)
    ElMessage.success('已保存到后台')
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '后台保存失败')
  } finally {
    savingFinal.value = false
  }
}


// 原有事件处理（向上传递）
const handleCellChanged = (cellInfo) => {
  console.log('📝 [ExcelContent] 单元格修改:', cellInfo)
  emit('cell-changed', cellInfo)
}

const handleDataChanged = (changeInfo) => {
  console.log('📊 [ExcelContent] 数据修改汇总:', changeInfo)
  emit('data-changed', changeInfo)
}

const handleEditStatusChanged = (status) => {
  console.log('🎛️ [ExcelContent] 编辑状态变化:', status)
  // 可以在这里处理编辑状态变化
}

// ============ 辅助函数 ============
const updateLocalUnsavedChanges = () => {
  if (window.sheetStateManager) {
    localUnsavedChanges.value = window.sheetStateManager.getUnsavedChangesCount()
  }
}




// 添加计算属性来调试按钮状态
const debugSaveButtonState = computed(() => {

  return !props.selectedSheet || !props.hasUnsavedChanges
})

// 在 ExcelContent.vue 中添加 props 验证
watch(() => props.hasUnsavedChanges, (newVal, oldVal) => {
  console.log('✅ ExcelContent: 接收到 hasUnsavedChanges props', {
    旧值: oldVal,
    新值: newVal,
    时间: new Date().toLocaleTimeString(),
    数据类型: typeof newVal,
    是否为布尔值: typeof newVal === 'boolean',
    值本身: newVal
  })
}, { immediate: true })

// 添加 DOM 检查函数
const checkButtonDOMState = () => {
  setTimeout(() => {
    const buttons = document.querySelectorAll('.save-buttons .el-button')

    buttons.forEach((btn, idx) => {
      const shouldDisable = !props.selectedSheet || !props.hasUnsavedChanges
      const isDisabled = btn.disabled
      const isWrong = isDisabled !== shouldDisable

    })
  }, 100)
}

// 监听整体扁平化完成事件
const handleGlobalFlattenComplete = (eventData) => {
  console.log('📥 ExcelContent: 接收整体扁平化数据', eventData)

  // 处理返回的扁平化数据
  handleGlobalFlattenedData(eventData.flattenedData)
}

// 处理整体扁平化数据
const handleGlobalFlattenedData = (flattenedData) => {
  try {
    console.log('🔄 处理整体扁平化数据', {
      数据行数: flattenedData.length,
      第一行样本: flattenedData[0]
    })

    // 1. 更新扁平化数据
    if (Array.isArray(flattenedData) && flattenedData.length > 0) {
      // 清空现有数据
      props.flatData.length = 0

      // 添加新数据（确保响应式更新）
      flattenedData.forEach(row => {
        props.flatData.push(row)
      })

      console.log('✅ 扁平化数据已更新', {
        新数据行数: props.flatData.length
      })
    }

    // 2. 自动切换到扁平化模式（如果当前不是的话）
    if (!props.showFlatMode) {
      console.log('🔄 自动切换到扁平化模式')
      // 触发父组件切换模式
      emit('toggle-flat-mode')
    }

    // 3. 更新表格显示
    nextTick(() => {
      // 强制刷新表格显示
      if (flatViewer.value) {
        const hotInstance = flatViewer.value.getSafeHotInstance?.()
        if (hotInstance && !hotInstance.isDestroyed) {
          hotInstance.render()
          console.log('✅ 表格已刷新显示')
        }
      }
    })

  } catch (error) {
    console.error('❌ 处理整体扁平化数据失败:', error)
    ElMessage.error('处理扁平化数据失败')
  }
}

// 在 mounted 和每次 props 变化时检查
onMounted(() => {
  console.log('🚀 ExcelContent mounted, 检查按钮初始状态')
  checkButtonDOMState()
})

watch(() => props.hasUnsavedChanges, () => {
  console.log('🔄 hasUnsavedChanges 变化，重新检查按钮')
  checkButtonDOMState()
})

watch(() => props.selectedSheet, () => {
  console.log('🔄 selectedSheet 变化，重新检查按钮')
  checkButtonDOMState()
})


// 添加监听
watch(() => props.hasUnsavedChanges, (newVal) => {
  console.log('🎯 props.hasUnsavedChanges 变化:', newVal)
}, { immediate: true })

// 直接使用导入的实例，而不是 window.sheetStateManager
const handleSheetCellChange = (changeData) => {
  console.log('📦 [ExcelContent] 收到单元格修改:', changeData)

  if (!sheetStateManager) {
    console.warn('⚠️ sheetStateManager 未初始化')
    return
  }

  // 获取当前表类型
  const tableType = props.showFlatMode ? 'flattened' : 'original'

  // 设置活跃上下文
  if (props.selectedSheet && props.selectedPdf && props.selectedExcelFile) {
    sheetStateManager.setActiveContext(
      props.selectedPdf.id,
      props.selectedExcelFile,
      props.selectedSheet.name,
      tableType
    )
  }

  // 记录每个修改
  changeData.changes.forEach(([row, col, oldValue, newValue]) => {
    try {
      const success = sheetStateManager.recordCellChange(
        row,
        col,
        oldValue,
        newValue,
        tableType
      )

      // 2. 🔥 关键：同步到全局 Set（让按钮/样式生效）
    const cellKey = ExcelKey.getCellKey(
      props.selectedPdf.id,
      props.selectedExcelFile,
      props.selectedSheet.name,
      tableType,
      row,
      col
    );
    if (!window.unsavedCells) {
      window.unsavedCells = { original: new Set(), flattened: new Set() };
    }
    window.unsavedCells[tableType].add(cellKey);

    } catch (error) {
      console.error('❌ 记录修改失败:', error)
    }
  })

  // 更新本地状态
  updateLocalUnsavedChanges()

  // 触发保存状态更新
  emit('unsaved-changes-updated', true)
}


// ExcelContent.vue - 添加 watch
watch(() => props.showFlatMode, (newMode, oldMode) => {
  console.log('🔄 ExcelContent: 扁平化模式变化', {
    旧模式: oldMode,
    新模式: newMode,
    当前sheet: props.selectedSheet?.name
  })

  // 重新计算保存按钮状态
  if (props.selectedSheet) {
    // 强制重新计算
    setTimeout(() => {
      console.log('🔄 强制更新保存按钮状态')
      // 触发重新渲染
      checkSaveButtons()
    }, 50)
  }
}, { immediate: true })



// 调试函数
const checkSaveButtons = () => {
  console.group('🔍 ExcelContent 保存按钮状态检查')
  const noSheet = !props.selectedSheet
  const noChanges = !enableSaveButtons.value
  const shouldDisable = noSheet || noChanges
  console.log('   - 按钮应该禁用?', shouldDisable)

  console.log('4. 当前DOM按钮状态:')
  setTimeout(() => {
    const saveButtons = document.querySelectorAll('.save-buttons .el-button')
    saveButtons.forEach((btn, idx) => {
      console.log(`   按钮${idx + 1}:`, {
        文本: btn.textContent,
        是否禁用: btn.disabled,
        类名: btn.className
      })
    })
  }, 100) // 延迟确保DOM已更新

  console.groupEnd()

  return enableSaveButtons.value
}

// 暴露给全局调试
if (typeof window !== 'undefined') {
  window.checkExcelContentButtons = checkSaveButtons
  window.debugExcelContent = {
    checkButtons: checkSaveButtons,
    getProps: () => ({
      hasUnsavedChanges: props.hasUnsavedChanges,
      selectedSheet: props.selectedSheet,
      selectedPdf: props.selectedPdf,
      selectedExcelFile: props.selectedExcelFile
    }),
    enableSaveButtons: () => enableSaveButtons.value
  }
}


/* ===== 本地实时状态：决定按钮亮灭 ===== */
const localHasUnsaved = computed(() => {
  if (!props.selectedSheet) {
    console.log('❌ localHasUnsaved: 无选中的 sheet，返回 false')
    return false
  }

  const t = props.showFlatMode ? 'flattened' : 'original'

  // 🔥 修复调试信息显示
  console.group('🔍🔍🔍 localHasUnsaved 详细检查')
  console.log('targetSet大小:', window.unsavedCells?.[t]?.size ?? 0)
  console.log('sheetStateManager存在:', !!sheetStateManager)
  console.log('sheetStateManager结果:', sheetStateManager?.hasUnsavedChanges?.(t) ?? false)
  console.groupEnd()

  // 1. 优先读全局 Set
  const targetSetSize = window.unsavedCells?.[t]?.size ?? 0
  if (targetSetSize > 0) {
    console.log('✅✅✅ 方式1: window.unsavedCells 检测到修改，返回 true')
    return true
  }

  // 2. 兜底读状态管理器
  const sheetManagerResult = sheetStateManager?.hasUnsavedChanges?.(t) ?? false
  console.log('🔄 方式2: sheetStateManager 结果:', sheetManagerResult)

  return sheetManagerResult
})



/* 统一的条件：有选中 sheet 且有未保存修改 */
// 🔥 替换 enableSaveButtons 计算属性
const enableSaveButtons = computed(() => {
  console.log('🔍🔍🔍 enableSaveButtons 计算:', {
    时间: new Date().toLocaleTimeString(),
    有sheet: !!props.selectedSheet,
    sheet名称: props.selectedSheet?.name,
    hasUnsavedChanges: props.hasUnsavedChanges,           // 旧prop
    actualHasUnsavedChanges: props.actualHasUnsavedChanges, // 新prop
    使用哪个: 'actualHasUnsavedChanges'
  })

  // 🔥 关键修复：使用 actualHasUnsavedChanges
  const result = props.selectedSheet && props.actualHasUnsavedChanges
  console.log('✅ enableSaveButtons 结果:', result)
  return result
})


// 计算属性
const allSheets = computed(() => props.sortedSheets)

const currentSheetIndex = computed(() => {
  if (!props.selectedSheet || !props.selectedExcelFile) return -1

  return allSheets.value.findIndex(sheet =>
    sheet.name === props.selectedSheet.name &&
    sheet.excelFile === props.selectedExcelFile
  )
})

const hasPreviousSheet = computed(() => currentSheetIndex.value > 0)
const hasNextSheet = computed(() =>
  currentSheetIndex.value >= 0 && currentSheetIndex.value < allSheets.value.length - 1
)

const currentPageInfo = computed(() => {
  if (currentSheetIndex.value < 0) return null

  const currentSheet = allSheets.value[currentSheetIndex.value]

  // 获取所有不重复的页码
  const allPageNumbers = [...new Set(allSheets.value
    .filter(s => s.isStandard)
    .map(s => s.pageNumber)
  )].sort((a, b) => a - b)

  const tablesInCurrentPage = allSheets.value.filter(s =>
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


// 只修改这一处：将 excelFileName 改为 excelFile
const goToPreviousSheet = async () => {
  if (!hasPreviousSheet.value) return

  const previousSheet = allSheets.value[currentSheetIndex.value - 1]

  console.log('📄 导航到上一表格')

  // 🔥🔥 关键修复：将 excelFileName 改为 excelFile
  emit('navigate-sheet', {
    sheet: previousSheet,
    excelFile: previousSheet.excelFile  // 原来是 excelFileName
  })
}

const goToNextSheet = async () => {
  if (!hasNextSheet.value) return

  const nextSheet = allSheets.value[currentSheetIndex.value + 1]

  console.log('📄 导航到下一表格')

  // 🔥🔥 关键修复：将 excelFileName 改为 excelFile
  emit('navigate-sheet', {
    sheet: nextSheet,
    excelFile: nextSheet.excelFile  // 原来是 excelFileName
  })
}


// ============ 暴露给父组件的 hasUnsavedChanges ============
const emit = defineEmits([
  'toggle-flat-mode',
  'save-data',
  'restore-unsaved-data',
  'run-comprehensive-test',
  'cell-changed',
  'data-changed',
  'instance-ready',
  'unsaved-changes-updated',
  'navigate-sheet'
])


watch([() => props.excelData, () => props.flatData, () => props.showFlatMode], () => {
  nextTick(refreshHot)
}, { deep: true })

function refreshHot () {
  const viewer = originalViewer.value || flatViewer.value
  const hot = viewer?.getSafeHotInstance?.()
  hot && !hot.isDestroyed && hot.render()
}


// 当实际有未保存修改变化时，通知父组件
watch(enableSaveButtons, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    console.log('🔄 未保存修改状态变化:', { 旧值: oldVal, 新值: newVal })
    emit('unsaved-changes-updated', newVal)
  }
})


// 监听修改变化，强制重新渲染
watch(() => props.modifiedCellsCount, (newCount, oldCount) => {
  console.log('🔄 修改计数变化，强制重新渲染:', { 旧值: oldCount, 新值: newCount })
  forceRefreshKey.value++
  nextTick(() => {
    console.log('✅ 强制重新渲染完成')
  })
}, { immediate: true })

// 监听保存状态变化
watch(() => props.saveStatus, (newStatus, oldStatus) => {
  console.log('🔄 保存状态变化，强制重新渲染:', { 旧状态: oldStatus, 新状态: newStatus })
  forceRefreshKey.value++
}, { deep: true })

// 监听模式切换
watch(() => props.showFlatMode, (newMode, oldMode) => {
  console.log('🔄 扁平化模式变化，强制重新渲染:', { 旧模式: oldMode, 新模式: newMode })
  forceRefreshKey.value++
}, { immediate: true })


// 正确的写法：
watch(() => props.selectedSheet, (newSheet) => {  // ✅ 使用 props.selectedSheet
  console.log('🔍 ExcelContent: selectedSheet 变化', newSheet?.name)

  // 🔥 检查是否有扁平化数据
  setTimeout(() => {
    if (props.flatData && props.flatData.length > 0) {  // ✅ 使用 props.flatData
      // 有扁平化数据，确保显示扁平化模式
      if (!props.showFlatMode) {  // ✅ 使用 props.showFlatMode
        // 这里需要触发父组件切换模式
        emit('toggle-flat-mode')
        console.log('🔄 ExcelContent: 强制切换到扁平化模式')
      }
    }
  }, 200)
}, { deep: true })



// 🔥 只在数据加载时自动设置一次
watch(() => props.excelData, (newData) => {
  if (newData && newData.length > 0) {
    const isFlattenedData = checkIfFlattenedData(newData)

    console.log('🎯 初始化模式判断:', {
      数据特征: isFlattenedData ? '扁平化' : '原始',
      建议模式: isFlattenedData ? '扁平化' : '原始'
    })

    // 🔥 只在初始化时自动设置一次
    if (isFlattenedData !== props.showFlatMode) {
      console.log('🔄 初始化设置显示模式')
      emit('toggle-flat-mode')
    }
  }
}, { immediate: true })  // 🔥 只在第一次加载时执行

/* ===== 最小全局源：只告诉按钮“有没有” ===== */
const hasMod = computed(() => props.hasUnsavedChanges)   // 父组件给的 props
window.$hasMod = hasMod                                  // 挂到 window
onMounted(() => { window.$hasMod = hasMod })             // 确保挂载后可用

// ============ 暴露给父组件的实例与方法 ============
defineExpose({
  originalViewer,
  flatViewer,
  checkSaveButtons,
  tableData: computed(() => hotViewerRef.value?.tableData ?? []),
  flatData:  computed(() => []),
  debugExcelContent: {
    checkButtons: checkSaveButtons,
    getProps: () => ({
      hasUnsavedChanges: props.hasUnsavedChanges,
      selectedSheet: props.selectedSheet,
      selectedPdf: props.selectedPdf,
      selectedExcelFile: props.selectedExcelFile
    }),
    enableSaveButtons: () => enableSaveButtons.value
  }
})





</script>


<style scoped>

.section-header {
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  white-space: nowrap;
}

.header-actions {
  flex-shrink: 0;
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
  gap: 1px;
}

.save-buttons .el-button {
  border-radius: 0;
  padding: 6px 10px;
}

.save-buttons .el-button:first-child {
  border-top-left-radius: 4px;
  border-bottom-left-radius: 4px;
}

.save-buttons .el-button:last-child {
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

/* 保存状态栏样式 */
.save-status-bar {
  padding: 8px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.save-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
}

.change-count {
  color: #e6a23c;
  font-weight: 500;
}

.last-save {
  color: #909399;
  margin-left: auto;
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

/* 响应式调整 */
@media (max-width: 1200px) {
  .header-main {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .header-left {
    justify-content: space-between;
  }

  .action-row {
    justify-content: flex-start;
    gap: 6px;
  }

  .save-buttons .el-button {
    padding: 5px 8px;
    font-size: 12px;
  }
}

@media (max-width: 768px) {
  .action-row {
    flex-wrap: wrap;
  }

  .save-buttons {
    width: 100%;
    justify-content: stretch;
  }

  .save-buttons .el-button {
    flex: 1;
    text-align: center;
  }
}

.sub-bar {
  flex-shrink: 0;        /* 允许它自己收缩，但不要写 height:24px  */
  line-height: 24px;     /* 如果只想文字垂直居中，用 line-height 即可 */
  padding: 4px 16px;     /* 用 padding 撑出高度，而不是硬编码 height */
}





/* 在 ExcelContent.vue 的 style 部分，确保这样写 */

.excel-content-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;  /* 关键 */
  width: 100%;
}

/* 第二级：继续往下传 */
.excel-content {
  flex: 1 1 auto;
  min-height: 0;  /* 关键 */
  display: flex;
  flex-direction: column;
}

/* 第三级：Handsontable 真正占位 */
.handsontable-container {
  flex: 1 1 auto;
  min-height: 0;  /* 关键 */
  position: relative;
}

/* 确保 Handsontable 容器内部的 div 吃满 */
.handsontable-container > div {
  height: 100%;
  width: 100%;
}

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;   /* 左右分离 */
  gap: 16px;                        /* 主按钮与保存组间距 */
}

.save-buttons {
  margin-left: auto;                /* 保存组靠右 */
}

.cell-info-container {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 16px; /* 添加一些内边距 */
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.range-details {
  font-size: 12px;
  color: #666;
  margin-left: 4px;
}

.cell-txt {
  font-size: 13px;
  color: #606266;
}


.navigation-buttons {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-right: 12px;
}

.navigation-buttons .el-button {
  padding: 6px 8px;
  min-width: 60px;
}

.page-indicator {
  font-size: 12px;
  color: #606266;
  margin: 0 12px;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
  min-width: 120px;
  text-align: center;
}


</style>