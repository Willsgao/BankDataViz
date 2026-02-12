<template>
  <div class="excel-content-container">
    <!-- 第一行：标题 + 按钮（32 px） -->
    <div class="section-header">
      <div class="header-main">
        <div class="header-left">
          <h3>表格</h3>
          <div v-if="selectedSheet?.name" class="header-info">
            <el-tag type="primary">{{ selectedSheet?.name }}</el-tag>
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

    <!-- 🔥 新增：选中区域统计信息 -->
    <div v-if="selectionSumData.visible" class="selection-summary-bar">
      <div class="sum-info">
        <el-icon><DataAnalysis /></el-icon>
        <span class="sum-label">选中区域求和:</span>
        <span class="sum-value">{{ selectionSumData.total }}</span>
        <span class="sum-details">
          ({{ selectionSumData.numericCount }}/{{ selectionSumData.totalCells }} 个数值)
        </span>
        <span v-if="selectionSumData.numericCount > 1" class="sum-stats">
          平均值: {{ selectionSumData.average }} | 最大: {{ selectionSumData.max }} | 最小: {{ selectionSumData.min }}
        </span>
      </div>
      <el-button
        size="small"
        type="info"
        link
        @click="clearSelectionSum"
        title="清除求和显示"
      >
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

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
            :pdf-id="String(selectedPdf?.id)"
            :excel-file-name="selectedExcelFile"
            :flat-data="flatData"
            :enable-save-buttons="enableSaveButtons"
            :saving="saving"
            :key="`original-${selectedSheet?.name}-${excelData.length}`"
            @cell-changed="handleCellChanged"
            @data-changed="handleDataChanged"
            @cell-change="handleSheetCellChange"
            @instance-ready="handleInstanceReady"
            @edit-status-changed="handleEditStatusChanged"
            @global-flatten-complete="handleGlobalFlattenComplete"
            @save-data="triggerSave"
            @selection-sum-changed="handleSelectionSumChanged"
          />
        </div>

        <div v-show="showFlatMode">
          <HandsontableExcelViewer
            ref="flatViewer"
            :excel-data="flatData"
            :sheet-name="`扁平化_${selectedSheet?.name || ''}`"
            :pdf-id="String(selectedPdf?.id)"
            :excel-file-name="selectedExcelFile"
            :key="`flat-${selectedSheet?.name}-${flatData.length}`"
            :enable-save-buttons="enableSaveButtons"
            :saving="saving"
            @cell-changed="handleCellChanged"
            @data-changed="handleDataChanged"
            @cell-change="handleSheetCellChange"
            @instance-ready="handleInstanceReady"
            @edit-status-changed="handleEditStatusChanged"
            @global-flatten-complete="handleGlobalFlattenComplete"
            @save-data="triggerSave"
            @selection-sum-changed="handleSelectionSumChanged"
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
import { defineProps, defineEmits, ref, computed, watch, nextTick, onMounted, onUnmounted, inject } from 'vue'
import { ElMessage } from 'element-plus'
import { useSheetOperations  } from './useSheetOperations.js'

// 在setup函数开始处添加
const excelContentSearchState = inject('excelContentSearchState')
const sheetOperations = useSheetOperations()
const { handleSmartToggle, checkIfFlattenedData  } = sheetOperations

const performExcelContentSearch = inject('performExcelContentSearch')


/* ===== 模板变量 ===== */
const emptyCount = ref(0)
const stats = ref({
  rowCount: 0,
  numericCount: 0,
  sum: 0,
  average: 0,
  max: 0,
  min: 0
})

const currentCell = ref({
  position: '',
  content: '',
  type: '文本',
  isNumeric: false
})

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
  hasUnsavedChanges: {
    type: Boolean,
    default: false,
    required: false
  },
  isDev: {
    type: Boolean,
    default: false
  },
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

const emit = defineEmits([
  'toggle-flat-mode',
  'save-data',
  'restore-unsaved-data',
  'run-comprehensive-test',
  'cell-changed',
  'data-changed',
  'instance-ready',
  'unsaved-changes-updated',
  'navigate-sheet',
  'update-flat-data'
])

/* ===== 组件引用和状态 ===== */
const originalViewer = ref(null)
const flatViewer = ref(null)
const localUnsavedChanges = ref(0)
const savingDraft = ref(false)
const savingFinal = ref(false)
const forceRefreshKey = ref(0)

// 🔥🔥 修复：只定义一次响应式变量
const tableDataVersion = ref(0)
const isDataLoaded = ref(false)
const dataChangeTimer = ref(null)
let retryCount = 0
const MAX_RETRY_COUNT = 3

/* ===== 事件处理函数 ===== */
const handleCellSelected = (cell) => {
  console.log('🔍🔍🔍🔍 收到选择事件:', cell)

  if (cell.isRange && cell.range) {
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

const handleInstanceReady = (instanceInfo) => {
  console.log('📡📡 ExcelContent: 收到实例就绪事件', instanceInfo)
  emit('instance-ready', instanceInfo)
}

const handleCellChanged = (cellInfo) => {
  console.log('📝📝 [ExcelContent] 单元格修改:', cellInfo)
  emit('cell-changed', cellInfo)
}

const handleDataChanged = (changeInfo) => {
  console.log('📊📊 [ExcelContent] 数据修改汇总:', changeInfo)
  emit('data-changed', changeInfo)
}

const handleEditStatusChanged = (status) => {
  console.log('🎛🎛️ [ExcelContent] 编辑状态变化:', status)
}

const handleGlobalFlattenComplete = (eventData) => {
  console.log('📥📥 ExcelContent: 接收整体扁平化数据', eventData)
  handleGlobalFlattenedData(eventData.flattenedData)
}


// 选中区域合计数据
const selectionSumData = ref({
  visible: false,
  total: 0,
  numericCount: 0,
  totalCells: 0,
  average: 0,
  max: 0,
  min: 0
})

// 处理选中区域合计变化
const handleSelectionSumChanged = (data) => {
  selectionSumData.value = data
}


// 在 ExcelContent.vue 的 script 中添加
const clearSelectionSum = () => {
  console.log('🗑️ 清除选中区域求和显示')
  selectionSumData.value = {
    visible: true,
    total: 0,
    numericCount: 0,
    totalCells: 0,
    average: 0,
    max: 0,
    min: 0
  }
}


const highlightCurrentSheetContent = (keyword) => {
  console.log('🔍 ExcelContent 执行搜索高亮:', keyword)

  // 根据当前显示模式选择正确的组件引用
  const targetViewer = props.showFlatMode ? flatViewer.value : originalViewer.value

  // 修复：使用正确的组件引用
  if (targetViewer && typeof targetViewer.highlightCurrentSheetContent === 'function') {
    targetViewer.highlightCurrentSheetContent(keyword)
  } else {
    console.warn('⚠️ 无法执行搜索：Handsontable 实例不可用', {
      当前模式: props.showFlatMode ? '扁平化' : '原始',
      组件存在: !!targetViewer,
      搜索方法存在: targetViewer?.highlightCurrentSheetContent ? '是' : '否'
    })
  }
}


const handleGlobalFlattenedData = (flattenedData) => {
  try {
    console.log('🔄🔄 处理整体扁平化数据', {
      数据行数: flattenedData.length,
      第一行样本: flattenedData[0]
    })

    if (Array.isArray(flattenedData) && flattenedData.length > 0) {

      // ✅ 正确方式：通过emit通知父组件更新
      emit('update-flat-data', flattenedData)

      console.log('✅ 已通知父组件更新扁平化数据', {
        新数据行数: flattenedData.length
      })
    }

    if (!props.showFlatMode) {
      console.log('🔄🔄 自动切换到扁平化模式')
      emit('toggle-flat-mode')
    }

    nextTick(() => {
      if (flatViewer.value) {
        const hotInstance = flatViewer.value.getSafeHotInstance?.()
        if (hotInstance && !hotInstance.isDestroyed) {
          hotInstance.render()
          console.log('✅ 表格已刷新显示')
        }
      }
    })

  } catch (error) {
    console.error('❌❌ 处理整体扁平化数据失败:', error)
    ElMessage.error('处理扁平化数据失败')
  }
}

const handleGlobalFlattenedData0000 = (flattenedData) => {
  try {
    console.log('🔄🔄 处理整体扁平化数据', {
      数据行数: flattenedData.length,
      第一行样本: flattenedData[0]
    })

    if (Array.isArray(flattenedData) && flattenedData.length > 0) {
      props.flatData.length = 0
      flattenedData.forEach(row => {
        props.flatData.push(row)
      })

      console.log('✅ 扁平化数据已更新', {
        新数据行数: props.flatData.length
      })
    }

    if (!props.showFlatMode) {
      console.log('🔄🔄 自动切换到扁平化模式')
      emit('toggle-flat-mode')
    }

    nextTick(() => {
      if (flatViewer.value) {
        const hotInstance = flatViewer.value.getSafeHotInstance?.()
        if (hotInstance && !hotInstance.isDestroyed) {
          hotInstance.render()
          console.log('✅ 表格已刷新显示')
        }
      }
    })

  } catch (error) {
    console.error('❌❌ 处理整体扁平化数据失败:', error)
    ElMessage.error('处理扁平化数据失败')
  }
}

/* ===== 保存相关函数 ===== */
const triggerSave = () => {
  console.log('💾💾 ExcelContent: 保存按钮点击')
  emit('save-data')
}

const handleSaveDraft = async () => {
  savingDraft.value = true
  try {
    const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value
    const key = ExcelKey.getDraftKey(props.selectedPdf.id,
        props.selectedExcelFile,
        props.selectedSheet.name,
        props.showFlatMode ? 'flattened' : 'original')

    const draft = {
      data: viewer.tableData,
      modifications: Array.from(window.unsavedCells?.[props.showFlatMode ? 'flattened' : 'original'] || []),
      savedAt: Date.now()
    }
    localStorage.setItem(key, JSON.stringify(draft))

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

/* ===== 计算属性 ===== */
const enableSaveButtons = computed(() => {
  const result = props.selectedSheet && props.actualHasUnsavedChanges
  console.log('✅ enableSaveButtons 结果:', result)
  return result
})

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

/* ===== 导航函数 ===== */
const goToPreviousSheet = async () => {
  if (!hasPreviousSheet.value) return

  const previousSheet = allSheets.value[currentSheetIndex.value - 1]
  console.log('📄📄 导航到上一表格')

  emit('navigate-sheet', {
    sheet: previousSheet,
    excelFile: previousSheet.excelFile
  })
}

const goToNextSheet = async () => {
  if (!hasNextSheet.value) return

  const nextSheet = allSheets.value[currentSheetIndex.value + 1]
  console.log('📄📄 导航到下一表格')

  emit('navigate-sheet', {
    sheet: nextSheet,
    excelFile: nextSheet.excelFile
  })
}

/* ===== 核心修复：数据监听和刷新逻辑 ===== */
// 在第一个 watch 中添加调试
watch(() => props.excelData, (newData, oldData) => {
  console.log('📊📊 ExcelContent: excelData 变化', {
    新数据长度: newData?.length,
    旧数据长度: oldData?.length,
    时间: new Date().toLocaleTimeString(),
    当前sheet: props.selectedSheet?.name,
    数据样本: newData?.slice(0, 2) // 查看前两行数据
  })

  if (dataChangeTimer.value) {
    clearTimeout(dataChangeTimer.value)
  }

  if (newData && newData.length > 0) {
    isDataLoaded.value = true
    tableDataVersion.value++
    console.log('✅ 数据就绪，准备刷新表格')

    dataChangeTimer.value = setTimeout(() => {
      forceRefreshHandsontable()
    }, 300)
  } else {
    isDataLoaded.value = false
    console.log('📭📭 数据为空，不进行刷新')
  }
}, { deep: true, immediate: true })

// 🔥🔥 修复：只定义一次 watch
watch(() => props.selectedSheet, (newSheet, oldSheet) => {
  if (newSheet?.name !== oldSheet?.name) {
    isDataLoaded.value = false
    tableDataVersion.value = 0
  }
})


// 🔥🔥 修复：只定义一次函数
const forceRefreshHandsontable = () => {
  console.log('🔄🔄 开始强制刷新Handsontable...')

  try {
    const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value

    if (!viewer) {
      console.log('⏳⏳⏳ 表格视图未就绪，稍后重试...')

      // 🔥 关键修复：先检查再增加
      if (retryCount >= MAX_RETRY_COUNT) {
        console.log('⏹️⏹️ 达到最大重试次数，停止重试')
        retryCount = 0 // 重置计数器
        return
      }

      retryCount++ // 增加重试计数

      setTimeout(() => {
        console.log(`🔄🔄 第${retryCount}次重试...`)
        forceRefreshHandsontable()
      }, 500)
      return
    }

    // 🔥 成功获取viewer时重置计数器
    retryCount = 0

    const hotInstance = viewer.getSafeHotInstance?.()
    if (!hotInstance) {
      console.error('❌❌ 无法获取Handsontable实例')
      return
    }

    if (hotInstance.isDestroyed) {
      console.error('❌❌ Handsontable实例已销毁')
      return
    }

    console.log('✅ 获取到Handsontable实例，开始刷新...')
    hotInstance.render()
    hotInstance.updateSettings({}, false)

    if (props.excelData && props.excelData.length > 0) {
      hotInstance.loadData(props.excelData)
    }

    console.log('✅ 表格强制刷新完成')

  } catch (error) {
    console.error('❌❌ 表格刷新失败:', error)
    retryCount = 0 // 🔥 出错时也重置计数器
  }
}


/* ===== 生命周期 ===== */
onMounted(() => {
  retryCount = 0
  if (typeof window !== 'undefined') {
    window.$hasMod = computed(() => props.hasUnsavedChanges)
  }
})

onUnmounted(() => {
  if (dataChangeTimer.value) {
    clearTimeout(dataChangeTimer.value)
  }
  console.log('🧹🧹 ExcelContent 组件卸载，清理资源')
})

/* ===== 暴露给父组件 ===== */
defineExpose({
  originalViewer,
  flatViewer,
  forceRefreshTable: forceRefreshHandsontable,
  getDataVersion: () => tableDataVersion.value,
  isDataLoaded: () => isDataLoaded.value,
  // highlightCurrentSheetContent
})

// 保留原有的其他函数和逻辑
const handleSmartToggleWrapper = () => {
  handleSmartToggle(
    props.selectedSheet,
    props.selectedPdf,
    props.selectedExcelFile,
    props.showFlatMode,
    props.excelData,
    props.flatData,
    () => emit('toggle-flat-mode')
  )
}

const canSaveFinal = computed(() =>
  !savingFinal.value && (window.unsavedCells?.size > 0 || sheetStateManager.hasUnsavedChanges(props.showFlatMode ? 'flattened' : 'original'))
)

const handleSheetCellChange = (changeData) => {
  console.log('📦📦 [ExcelContent] 收到单元格修改:', changeData)

  if (!sheetStateManager) {
    console.warn('⚠️ sheetStateManager 未初始化')
    return
  }

  const tableType = props.showFlatMode ? 'flattened' : 'original'

  if (props.selectedSheet && props.selectedPdf && props.selectedExcelFile) {
    sheetStateManager.setActiveContext(
      props.selectedPdf.id,
      props.selectedExcelFile,
      props.selectedSheet.name,
      tableType
    )
  }

  changeData.changes.forEach(([row, col, oldValue, newValue]) => {
    try {
      const success = sheetStateManager.recordCellChange(
        row,
        col,
        oldValue,
        newValue,
        tableType
      )

      const cellKey = ExcelKey.getCellKey(
        props.selectedPdf.id,
        props.selectedExcelFile,
        props.selectedSheet.name,
        tableType,
        row,
        col
      )
      if (!window.unsavedCells) {
        window.unsavedCells = { original: new Set(), flattened: new Set() }
      }
      window.unsavedCells[tableType].add(cellKey)

    } catch (error) {
      console.error('❌❌ 记录修改失败:', error)
    }
  })

  emit('unsaved-changes-updated', true)
}

// 其他辅助函数
const updateLocalUnsavedChanges = () => {
  if (window.sheetStateManager) {
    localUnsavedChanges.value = window.sheetStateManager.getUnsavedChangesCount()
  }
}

const debugSaveButtonState = computed(() => {
  return !props.selectedSheet || !props.hasUnsavedChanges
})

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

onMounted(() => {
  console.log('🚀🚀 ExcelContent mounted, 检查按钮初始状态')
  checkButtonDOMState()
})

watch(() => props.hasUnsavedChanges, () => {
  console.log('🔄🔄 hasUnsavedChanges 变化，重新检查按钮')
  checkButtonDOMState()
})

watch(() => props.selectedSheet, () => {
  console.log('🔄🔄 selectedSheet 变化，重新检查按钮')
  checkButtonDOMState()
})

watch(() => props.showFlatMode, (newMode, oldMode) => {
  console.log('🔄🔄 ExcelContent: 扁平化模式变化', {
    旧模式: oldMode,
    新模式: newMode,
    当前sheet: props.selectedSheet?.name
  })

  if (props.selectedSheet) {
    setTimeout(() => {
      console.log('🔄🔄 强制更新保存按钮状态')
    }, 50)
  }
}, { immediate: true })


// 在ExcelContent.vue的watch中添加
watch(() => props.excelData, (newData, oldData) => {
  console.log('📊 ExcelContent: excelData变化', {
    新数据长度: newData?.length,
    旧数据长度: oldData?.length,
    时间: new Date().toLocaleTimeString(),
    当前sheet: props.selectedSheet?.name
  })

  if (newData && newData.length > 0) {
    console.log('✅ 数据已就绪，准备刷新表格')

    // 强制刷新Handsontable
    setTimeout(() => {
      forceRefreshHandsontable()
    }, 300)
  } else {
    console.log('📭 数据为空，等待数据加载')
  }
}, { deep: true, immediate: true })

// 强制刷新表格显示
const forceRefreshTables = () => {
  console.log('🔄 强制刷新表格显示')

  const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value
  if (!viewer) {
    console.log('⏳ 表格视图未就绪，稍后重试')
    setTimeout(forceRefreshTables, 100)
    return
  }

  const hotInstance = viewer.getSafeHotInstance?.()
  if (hotInstance && !hotInstance.isDestroyed) {
    hotInstance.render()
    console.log('✅ 表格已刷新显示')
  }
}


// 在 ExcelContent.vue 中添加搜索路由函数
const routeSearchToCorrectViewer = (keyword) => {
  console.log('🔄 路由搜索请求到正确的组件:', keyword)

  // 优先使用当前显示模式的组件
  const targetViewer = showFlatMode.value ? flatViewer.value : originalViewer.value

  if (targetViewer && targetViewer.performSearch) {
    console.log('✅ 路由到正确组件:', showFlatMode.value ? '扁平化' : '原始')
    targetViewer.performSearch(keyword)
  } else {
    console.error('❌ 目标组件不可用')
  }
}


const checkSaveButtons = () => {
  console.group('🔍🔍 ExcelContent 保存按钮状态检查')
  const noSheet = !props.selectedSheet
  const noChanges = !enableSaveButtons.value
  const shouldDisable = noSheet || noChanges
  console.log('   - 按钮应该禁用?', shouldDisable)

  setTimeout(() => {
    const saveButtons = document.querySelectorAll('.save-buttons .el-button')
    saveButtons.forEach((btn, idx) => {
      console.log(`   按钮${idx + 1}:`, {
        文本: btn.textContent,
        是否禁用: btn.disabled,
        类名: btn.className
      })
    })
  }, 100)

  console.groupEnd()
  return enableSaveButtons.value
}

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


// 在 ExcelContent.vue 中添加对全局搜索状态的监听
onMounted(() => {
  console.log('🚀 ExcelContent 组件挂载，开始监听搜索状态')

  // 监听搜索事件
  window.addEventListener('excel-content-search', handleExcelSearchEvent)

  // 主动检查当前的搜索状态并立即应用
  checkAndApplyCurrentSearch()
})

// 检查并应用当前搜索状态
const checkAndApplyCurrentSearch = () => {
  // 获取全局的搜索状态（假设存储在 window 或通过 provide/inject）
  const currentSearchKeyword = window.excelContentSearchState?.keyword ||
                               excelContentSearchState?.keyword

  if (currentSearchKeyword && currentSearchKeyword.trim()) {
    console.log('🔍 发现现有搜索关键词，立即应用:', currentSearchKeyword)
    highlightCurrentSheetContent(currentSearchKeyword)
  }
}

// 增强事件处理函数
const handleExcelSearchEvent = (event) => {
  const { keyword } = event.detail
  console.log('📥 ExcelContent 收到搜索事件，立即执行高亮:', keyword)

  // 立即执行，不延迟
  highlightCurrentSheetContent(keyword)
}

// 在 ExcelContent.vue 的 watch 中添加
watch(() => props.excelData, (newData, oldData) => {
  console.log('📊📊 ExcelContent 数据变化:', {
    新数据长度: newData?.length,
    旧数据长度: oldData?.length,
    当前sheet: props.selectedSheet?.name,
    时间: new Date().toLocaleTimeString()
  })

  if (newData && newData.length > 0) {
    console.log('✅ 数据已就绪，准备传递给子组件')

    // 立即检查子组件状态
    nextTick(() => {
      const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value
      if (viewer) {
        console.log('🔍 子组件状态检查:', {
          组件类型: props.showFlatMode ? '扁平化' : '原始',
          组件存在: !!viewer,
          props数据长度: viewer.props?.excelData?.length
        })
      }
    })
  }
}, { deep: true, immediate: true })

// 在 ExcelContent.vue 的 onMounted 中添加
onMounted(() => {
  console.log('🚀 ExcelContent 组件挂载，开始监听统计事件')

  // 监听选中区域统计事件
  const handleSelectionSum = (event) => {
    console.log('📥 ExcelContent 收到统计事件:', event.detail)
    selectionSumData.value = event.detail
  }

  window.addEventListener('selection-sum-changed', handleSelectionSum)

  // 清理事件监听
  onUnmounted(() => {
    window.removeEventListener('selection-sum-changed', handleSelectionSum)
    console.log('🧹 ExcelContent 清理统计事件监听')
  })
})


// 在组件挂载后设置全局搜索函数
onMounted(() => {
  if (performExcelContentSearch) {
    // 设置全局函数供 App.vue 调用
    window.performExcelSearch = performExcelContentSearch
    console.log('✅ 全局搜索函数已设置')
  }
})

// 在组件卸载时清理
onUnmounted(() => {
  delete window.performExcelSearch
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


.selection-summary-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.selection-summary-bar .summary-label {
  font-weight: 600;
  margin-right: 8px;
}

.selection-summary-bar .summary-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.selection-summary-bar .sum-value {
  font-size: 18px;
  font-weight: bold;
  color: #ffd700;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.selection-summary-bar .summary-stats {
  margin-left: auto;
  padding-left: 16px;
  border-left: 1px solid rgba(255,255,255,0.3);
  font-size: 13px;
  opacity: 0.95;
}


</style>