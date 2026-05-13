<template>
  <div class="excel-content-container">
    <!-- 第一行：标题 + 按钮（32 px） -->
    <div class="section-header">
      <div class="header-main">
        <div class="header-left">
          <h3>表格</h3>
          <div
            v-if="selectedSheet?.name"
            class="header-info"
          >
            <el-tag type="primary">
              {{ selectedSheet?.name }}
            </el-tag>
          </div>
        </div>

        <div class="header-actions">
          <div class="action-row">
            <!-- 新增：导航按钮 -->
            <div class="navigation-buttons">
              <el-button
                size="small"
                :disabled="!hasPreviousSheet"
                title="上一页"
                @click="goToPreviousSheet"
              >
                <el-icon><ArrowLeft /></el-icon>
                上一页
              </el-button>

              <el-button
                size="small"
                :disabled="!hasNextSheet"
                title="下一页"
                @click="goToNextSheet"
              >
                下一页
                <el-icon><ArrowRight /></el-icon>
              </el-button>

              <!-- 新增：合并数据按钮 -->
              <el-button
                size="small"
                type="warning"
                :disabled="!canMergeData"
                title="将当前页数据合并到前一个_T_表"
                :loading="mergingData"
                @click="handleMergeData"
              >
                <el-icon><Connection /></el-icon>
                合并数据
              </el-button>

              <span
                v-if="currentPageInfo"
                class="page-indicator"
              >
                第{{ currentPageInfo.pageNumber }}页
                (表{{ currentPageInfo.currentTablePosition }}/{{ currentPageInfo.totalTablesInPage }})
              </span>
            </div>

            <!-- 主功能：大按钮 -->
            <el-button
              :key="`flat-button-${showFlatMode}`"
              type="primary"
              size="default"
              :disabled="!props.selectedSheet || excelData.length === 0"
              :loading="loadingFlat"
              @click="handleSmartToggle(
                props.selectedSheet,
                props.selectedPdf,
                props.selectedExcelFile,
                showFlatMode,
                excelData,
                flatData,
                () => $emit('toggle-flat-mode')
              )"
            >
              <el-icon><DataAnalysis /></el-icon>
              {{ showFlatMode ? '二维化' : '扁平化' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 🔥 新增：选中区域统计信息 -->
    <div
      v-if="selectionSumData.visible"
      class="selection-summary-bar"
    >
      <div class="sum-info">
        <el-icon><DataAnalysis /></el-icon>
        <span class="sum-label">选中区域求和:</span>
        <span class="sum-value">{{ selectionSumData.total }}</span>
        <span class="sum-details">
          ({{ selectionSumData.numericCount }}/{{ selectionSumData.totalCells }} 个数值)
        </span>
        <span
          v-if="selectionSumData.numericCount > 1"
          class="sum-stats"
        >
          平均值: {{ selectionSumData.average }} | 最大: {{ selectionSumData.max }} | 最小: {{ selectionSumData.min }}
        </span>
      </div>
      <el-button
        size="small"
        type="info"
        link
        title="清除求和显示"
        @click="clearSelectionSum"
      >
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

    <!-- 表格区域：自动撑满剩余高度 -->
    <div class="excel-content">
      <div
        v-if="!selectedSheet"
        class="placeholder"
      >
        <el-icon><Grid /></el-icon>
        <p>请选择表格查看内容</p>
      </div>
      <div
        v-else-if="loadingExcel"
        class="loading-state"
      >
        <el-icon class="is-loading">
          <Loading />
        </el-icon>
        加载表格数据中...
      </div>
      <div
        v-else-if="excelData.length === 0"
        class="empty-state"
      >
        <p>表格为空</p>
      </div>

      <!-- 表格显示 -->
      <div
        v-else
        class="handsontable-container"
      >
        <div v-show="!showFlatMode">
          <HandsontableExcelViewer
            ref="originalViewer"
            :key="`original-${selectedSheet?.name}-${excelData.length}`"
            :excel-data="excelData"
            :sheet-name="selectedSheet?.name || ''"
            :pdf-id="String(selectedPdf?.id)"
            :excel-file-name="selectedExcelFile"
            :flat-data="flatData"
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

        <div v-show="showFlatMode">
          <HandsontableExcelViewer
            ref="flatViewer"
            :key="`flat-${selectedSheet?.name}-${flatData.length}`"
            :excel-data="flatData"
            :sheet-name="`扁平化_${selectedSheet?.name || ''}`"
            :pdf-id="String(selectedPdf?.id)"
            :excel-file-name="selectedExcelFile"
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

        <div
          v-if="showFlatMode && flatData.length === 0 && loadingFlat"
          class="loading-state"
        >
          <el-icon class="is-loading">
            <Loading />
          </el-icon>
          正在扁平化数据...
        </div>

        <div
          v-if="showFlatMode && flatData.length === 0 && !loadingFlat"
          class="empty-state"
        >
          <el-icon><Grid /></el-icon>
          <p>暂无扁平化数据</p>
          <p class="tip">
            点击"数据扁平化"按钮生成数据
          </p>
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
import { ElMessage, ElMessageBox } from 'element-plus'
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

}

const handleInstanceReady = (instanceInfo) => {
  emit('instance-ready', instanceInfo)
}

const handleCellChanged = (cellInfo) => {
  emit('cell-changed', cellInfo)
}

const handleDataChanged = (changeInfo) => {
  emit('data-changed', changeInfo)
}

const handleEditStatusChanged = (status) => {
  console.log('🎛🎛️ [ExcelContent] 编辑状态变化:', status)
}

const handleGlobalFlattenComplete = (eventData) => {
  handleGlobalFlattenedData(eventData.flattenedData)
}


// 新增状态
const mergingData = ref(false)

const canMergeData = computed(() => {

  // 基本条件检查
  if (!props.selectedSheet || !props.selectedExcelFile) {
    console.log('❌ 未选择sheet或excel文件')
    return false
  }

  if (!hasPreviousSheet.value) {
    console.log('❌ 没有前一页')
    return false
  }

  const currentSheet = allSheets.value[currentSheetIndex.value]
  const previousSheet = allSheets.value[currentSheetIndex.value - 1]

  if (!currentSheet || !previousSheet) {
    console.log('❌ 无法获取当前或前一sheet')
    return false
  }

  console.log('✅ 基本条件满足，按钮可点击')
  return true
})



// 处理合并数据的函数
const handleMergeData = async () => {
  console.log('🎯🎯 开始合并数据流程 - 详细调试版 🎯🎯')
  console.log('=== 阶段1: 前置验证检查 ===')

  // 重新进行详细验证
  if (!hasPreviousSheet.value || !props.selectedSheet || !props.selectedExcelFile) {
    console.error('❌ 前置验证失败:')
    console.error('  - hasPreviousSheet:', hasPreviousSheet.value)
    console.error('  - selectedSheet:', props.selectedSheet)
    console.error('  - selectedExcelFile:', props.selectedExcelFile)
    ElMessage.warning('请先选择表格')
    return
  }

  console.log('✅ 前置验证通过')

  const currentSheet = allSheets.value[currentSheetIndex.value]
  const previousSheet = allSheets.value[currentSheetIndex.value - 1]

  console.log('=== 阶段2: Sheet信息检查 ===')

  if (!currentSheet || !previousSheet) {
    console.error('❌ 无法找到相关表格')
    ElMessage.warning('无法找到相关表格')
    return
  }

  const currentPageNum = extractPageNumber(currentSheet.name)
  const previousPageNum = extractPageNumber(previousSheet.name)

  console.log('=== 阶段3: 页号解析检查 ===')

  if (currentPageNum === null || previousPageNum === null) {
    console.error('❌ 无法解析页号')
    ElMessage.warning('无法解析页号')
    return
  }

  if (currentPageNum - previousPageNum !== 1) {
    console.error('❌ 页号不连续:', { currentPageNum, previousPageNum })
    ElMessage.warning(`页号不连续：当前页${currentPageNum}，前一页${previousPageNum}`)
    return
  }

  console.log('=== 阶段4: 格式验证检查 ===')

  if (!previousSheet.name.includes('_T_')) {
    console.error('❌ 前一页不是_T_结尾:', previousSheet.name)
    ElMessage.warning(`前一页"${previousSheet.name}"不是_T_结尾的表格`)
    return
  }

  // 添加当前sheet必须是_1_结尾的验证
  if (!currentSheet.name.includes('_1_')) {
    console.error('❌ 当前页不是_1_结尾:', currentSheet.name)
    ElMessage.warning(`当前表格"${currentSheet.name}"必须以"_1_"结尾才能合并`)
    return
  }

  // 🔥 修复1：简化弹窗内容，移除HTML格式
  console.log('=== 阶段5: 弹窗显示 ===')

  try {

    // 如果测试弹窗成功，显示真正的合并确认弹窗
    const confirmResult = await ElMessageBox.confirm(
      `确认将表格 "${currentSheet.name}" 的数据合并到 "${previousSheet.name}" 吗？\n\n⚠️ 注意：合并成功后，当前表格 "${currentSheet.name}" 将被删除，此操作不可撤销。`,
      '合并数据确认',
      {
        confirmButtonText: '确认合并',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false,  // 🔥 改为false
        showClose: true,
        closeOnClickModal: false,
        closeOnPressEscape: true
      }
    ).catch(error => {
      console.error('❌ 合并确认弹窗失败:', error)
      console.error('错误详情:', {
        消息: error.message,
        堆栈: error.stack,
        类型: typeof error,
        原始错误: error
      })
      return Promise.reject(error)
    })

    console.log('✅ 合并确认弹窗成功显示，用户点击确认')

  } catch (error) {
    console.error('❌❌ 弹窗处理失败，进入catch块:', error)
    console.error('错误对象详情:', {
      值: error,
      类型: typeof error,
      等于字符串cancel: error === 'cancel',
      等于数字: error === 2,
      等于false: error === false
    })

    if (error === 'cancel' || error === 2 || error === false) {
      console.log('🔍 弹窗被用户取消 (代码:', error, ')')
    } else if (error && error.message) {
      console.error('🔍 JavaScript错误:', error.message)
      console.error('错误堆栈:', error.stack)

      // 尝试使用浏览器原生confirm作为备选
      console.log('🔄 尝试使用原生confirm作为备选...')
      try {
        const nativeConfirm = confirm(`确认合并表格 "${currentSheet.name}" 到 "${previousSheet.name}" 吗？\n\n合并后当前表格将被删除。`)
        if (!nativeConfirm) {
          console.log('用户取消了操作（原生confirm）')
          return
        }
        console.log('✅ 用户确认（原生confirm），继续合并流程')
      } catch (nativeError) {
        console.error('❌ 备用确认框也失败:', nativeError)
        return
      }
    } else {
      console.error('🔍 未知错误类型:', error)
      return
    }
    return
  }

  // 如果所有验证通过，继续执行合并逻辑
  mergingData.value = true

  try {
    console.log('=== 阶段6: 准备请求数据 ===')
    // 🔥 修复2：确保pdfId正确处理
    const pdfId = props.selectedPdf?.id ? String(props.selectedPdf.id) : null
    console.log('  - pdfId:', pdfId)

    if (!pdfId) {
      console.error('❌ PDF信息不完整')
      throw new Error('PDF信息不完整，无法执行合并')
    }

    // 构建请求数据
    const mergeRequest = {
      sourceSheet: {
        name: currentSheet.name,
        excelFile: props.selectedExcelFile,
        pdfId: pdfId
      },
      targetSheet: {
        name: previousSheet.name,
        excelFile: props.selectedExcelFile,
        pdfId: pdfId
      },
      // 包含当前表格数据
      currentData: props.excelData || [],
      metadata: {
        isContinuousPages: true,
        currentPage: currentPageNum,
        previousPage: previousPageNum,
        deleteSourceSheet: true
      }
    }

    // 调用后端合并接口
    console.log('📡 调用后端API: /api/excel/merge-sheets')
    const response = await fetch('/api/excel/merge-sheets', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(mergeRequest)
    })

    // 检查响应状态
    console.log('📡 服务器响应状态:', response.status, response.statusText)

    if (!response.ok) {
      // 尝试获取详细的错误信息
      let errorData = {}
      try {
        errorData = await response.json()
        console.error('❌ 服务器返回错误:', errorData)
      } catch (parseError) {
        console.error('❌ 无法解析错误响应:', parseError)
      }

      // 用户友好的错误提示
      const userFriendlyMessages = {
        400: '请求格式错误，请检查数据格式',
        404: '目标表格不存在',
        500: '服务器内部错误，请稍后重试',
        403: '无权限执行此操作'
      }

      let errorMessage = errorData.error || userFriendlyMessages[response.status] || `合并失败: 服务器错误 (HTTP ${response.status})`

      // 解析具体的验证错误，提供用户友好的提示
      if (response.status === 400) {
        if (errorMessage.includes('缺少必要字段')) {
          errorMessage = '数据不完整，请刷新页面后重试'
        } else if (errorMessage.includes('必须包含"_1_"')) {
          errorMessage = '当前表格不是以"_1_"结尾，无法合并'
        } else if (errorMessage.includes('必须包含"_T_"')) {
          errorMessage = '前一页表格不是以"_T_"结尾，无法合并'
        } else if (errorMessage.includes('页号不连续')) {
          errorMessage = '表格页号不连续，无法合并'
        } else if (errorMessage.includes('列数不一致')) {
          errorMessage = '表格结构不一致，无法合并'
        } else if (errorMessage.includes('表头不匹配')) {
          errorMessage = '表格表头不一致，无法合并'
        } else if (errorMessage.includes('数据为空')) {
          errorMessage = '表格数据为空，无法合并'
        }
      }

      console.error('❌ 合并失败:', errorMessage, '技术详情:', errorData)
      throw new Error(errorMessage)
    }

    const result = await response.json()
    console.log('✅ 服务器返回结果:', result)

    if (result.success) {
      console.log('🎉 合并成功:', result)
      ElMessage.success({
        message: '数据合并成功，当前表格已删除',
        duration: 5000,
        showClose: true
      })

      // 合并成功后，刷新数据或跳转到前一页
      emit('navigate-sheet', {
        sheet: previousSheet,
        excelFile: props.selectedExcelFile
      })

      // 🔥 如果后端已删除当前sheet，可以通知父组件刷新sheet列表
      emit('sheet-deleted', {
        deletedSheet: currentSheet.name,
        targetSheet: previousSheet.name
      })

    } else {
      // 处理服务器返回的业务逻辑错误
      let errorMessage = result.error || '合并失败'
      console.error('❌ 服务器业务逻辑错误:', errorMessage)

      // 将技术错误转换为用户友好的提示
      if (errorMessage.includes('缺少必要字段')) {
        errorMessage = '数据不完整，请刷新页面后重试'
      } else if (errorMessage.includes('必须包含"_1_"')) {
        errorMessage = '当前表格不是以"_1_"结尾，无法合并'
      } else if (errorMessage.includes('必须包含"_T_"')) {
        errorMessage = '前一页表格不是以"_T_"结尾，无法合并'
      } else if (errorMessage.includes('页号不连续')) {
        errorMessage = '表格页号不连续，无法合并'
      } else if (errorMessage.includes('列数不一致')) {
        errorMessage = '表格结构不一致，无法合并'
      } else if (errorMessage.includes('表头不匹配')) {
        errorMessage = '表格表头不一致，无法合并'
      } else if (errorMessage.includes('数据为空')) {
        errorMessage = '表格数据为空，无法合并'
      } else if (errorMessage.includes('Excel文件不存在')) {
        errorMessage = '目标表格文件不存在，请检查文件路径'
      } else if (errorMessage.includes('获取目标sheet数据失败')) {
        errorMessage = '无法读取目标表格数据，请确认表格存在且可访问'
      } else if (errorMessage.includes('保存合并数据失败')) {
        errorMessage = '保存合并结果失败，请稍后重试'
      } else if (errorMessage.includes('删除当前sheet失败')) {
        errorMessage = '合并成功但删除当前表格失败，请手动清理'
      }

      console.error('❌ 合并失败:', errorMessage, '技术详情:', result)
      throw new Error(errorMessage)
    }

  } catch (error) {
    console.error('❌❌ 合并数据整体流程失败:', error)
    console.error('错误堆栈:', error.stack)

    // 用户友好的错误提示弹窗
    ElMessage.error({
      message: error.message || '合并数据失败，请稍后重试',
      duration: 5000,
      showClose: true,
      grouping: true,
      type: 'error',
      offset: 40
    })

  } finally {
    mergingData.value = false
  }
}

// 增强版的页号提取函数
const extractPageNumber = (sheetName) => {
  if (!sheetName) return null

  // 尝试多种格式匹配
  const patterns = [
    /P(\d+)_/,           // P025_
    /P(\d+)-/,           // P025-
    /[Pp](\d+)_/,        // p025_
    /[Pp](\d+)-/,        // p025-
  ]

  for (const pattern of patterns) {
    const match = sheetName.match(pattern)
    if (match) {
      return parseInt(match[1])
    }
  }

  return null
}



// 🔥 新增：仅保存到本地草稿的函数（如果不存在则添加）
const saveToLocalDraftOnly = (tableType) => {
  if (!selectedPdf.value || !selectedSheet.value) {
    console.warn('❌ 保存本地草稿失败：缺少PDF或Sheet信息');
    return;
  }

  try {
    console.log('💾 开始保存到本地草稿，表类型:', tableType);

    const draftKey = ExcelKey.getDraftKey(
      selectedPdf.value.id,
      selectedExcelFile.value,
      selectedSheet.value.name,
      tableType
    );

    const hot = getActiveHotInstance();
    if (hot && !hot.isDestroyed) {
      const fullData = hot.getSourceData() || [];
      const modifications = Array.from(window.unsavedCells?.[tableType] || []);

      const draft = {
        fullData,
        modifications,
        savedAt: Date.now(),
        tableType,
        backendSaved: false,
        rowRemovals: window.unsavedRowRemovals?.[tableType] || 0
      };

      localStorage.setItem(draftKey, JSON.stringify(draft));
      console.log('✅ 已保存到本地草稿:', {
        键: draftKey,
        数据行数: fullData.length,
        修改数: modifications.length,
        删除行数: draft.rowRemovals
      });
    } else {
      console.warn('⚠️ 无法获取表格实例，跳过本地草稿保存');
    }
  } catch (error) {
    console.error('❌❌ 保存到本地草稿失败:', error);
  }
};


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

  }
}

const handleGlobalFlattenedData = (flattenedData) => {
  try {

    if (Array.isArray(flattenedData) && flattenedData.length > 0) {
      // ✅ 正确方式：通过emit通知父组件更新
      emit('update-flat-data', flattenedData)

    }

    if (!props.showFlatMode) {
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

    ElMessage.success('草稿已保存')
  } catch (e) {
    console.error('草稿失败', e)
    ElMessage.error('草稿保存失败')
  } finally {
    savingDraft.value = false
  }
}

/* ===== 计算属性 ===== */
const enableSaveButtons0000 = computed(() => {
  const result = props.selectedSheet && props.actualHasUnsavedChanges
  return result
})

const enableSaveButtons = computed(() => {
  // 原有逻辑：检查是否有选中的Sheet和实际未保存更改
  const result = props.selectedSheet && props.actualHasUnsavedChanges

  // 🔥 修复：通过组件自身的props获取表格类型
  const tableType = props.showFlatMode ? 'flattened' : 'original';

  // 🔥 修复：增加对"删除行"未保存状态的检查
  const hasUnsavedRemovals = typeof window !== 'undefined'
    ? (window.unsavedRowRemovals?.[tableType] || 0) > 0
    : false;

  // 调试日志
  console.log('💾 保存按钮状态检查:', {
    选中Sheet: !!props.selectedSheet,
    实际未保存更改: props.actualHasUnsavedChanges,
    表格类型: tableType,
    删除行记录: window.unsavedRowRemovals?.[tableType] || 0,
    有未保存删除行: hasUnsavedRemovals,
    基础结果: result,
    最终结果: result || hasUnsavedRemovals
  })

  return result || hasUnsavedRemovals
})


// 应该修改为：
const allSheets = computed(() => {

  if (!props.sortedSheets) {
    console.warn('⚠️ sortedSheets为null/undefined')
    return []
  }

  if (!Array.isArray(props.sortedSheets)) {
    console.warn('⚠️ sortedSheets不是数组:', props.sortedSheets)
    return []
  }

  return props.sortedSheets
})


const currentSheetIndex = computed(() => {
  console.log('🔍 currentSheetIndex计算属性执行:')

  if (!props.selectedSheet || !props.selectedExcelFile) {
    return -1
  }

  if (!allSheets.value || allSheets.value.length === 0) {
    console.log('❌ allSheets为空，返回-1')
    return -1
  }

  const index = allSheets.value.findIndex(sheet => {
    // 尝试多种可能的属性名
    const sheetExcelFile = sheet.excelFile || sheet.excel_file || ''
    const match = sheet.name === props.selectedSheet.name &&
                 sheetExcelFile === props.selectedExcelFile

    return match
  })

  return index
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

  if (dataChangeTimer.value) {
    clearTimeout(dataChangeTimer.value)
  }

  if (newData && newData.length > 0) {
    isDataLoaded.value = true
    tableDataVersion.value++

    dataChangeTimer.value = setTimeout(() => {
      forceRefreshHandsontable()
    }, 300)
  } else {
    isDataLoaded.value = false
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

    // 🔥🔥 保存当前 undo 历史栈，避免刷新后丢失
    let undoStack = []
    let redoStack = []
    // 保存自定义撤销/重做栈
    let customUndoStack = []
    let customRedoStack = []
    try {
      if (hotInstance.undoRedo) {
        undoStack = hotInstance.undoRedo.undoStack ? [...hotInstance.undoRedo.undoStack] : []
        redoStack = hotInstance.undoRedo.redoStack ? [...hotInstance.undoRedo.redoStack] : []
        console.log('💾 保存 undo 历史:', undoStack.length, 'redo 历史:', redoStack.length)
      }
      // 保存自定义撤销栈（从 window 获取）
      try {
        customUndoStack = window.customUndoStack || []
        customRedoStack = window.customRedoStack || []
        console.log('💾 保存自定义 undo 历史:', customUndoStack.length, 'redo 历史:', customRedoStack.length, '从window获取')
      } catch (e) {
        console.warn('⚠️ 获取自定义 undo 栈失败:', e)
      }
    } catch (e) {
      console.warn('⚠️ 保存 undo 历史失败:', e)
    }

    hotInstance.render()
    hotInstance.updateSettings({}, false)

    // 🔥 只有数据真正变化时才 loadData，避免不必要的刷新
    // 但如果是在填充操作后，临时跳过刷新
    if (window.skipForceRefresh) {
      console.log('⏭️ 跳过强制刷新（填充操作中）')
      return
    }

    const currentData = hotInstance.getSourceData ? hotInstance.getSourceData() : []
    const newData = props.excelData || []
    
    // 简单比较：如果行数或第一行不同，才重新加载
    const needsReload = currentData.length !== newData.length || 
      (currentData.length > 0 && newData.length > 0 && 
       JSON.stringify(currentData[0]) !== JSON.stringify(newData[0]))
    
    if (needsReload && props.excelData && props.excelData.length > 0) {
      console.log('🔄 数据变化，执行 loadData...')
      hotInstance.loadData(props.excelData)
    } else {
      console.log('⏭️ 数据无变化，跳过 loadData')
    }

    // 🔥🔥 恢复 undo 历史栈
    try {
      if (hotInstance.undoRedo && (undoStack.length > 0 || redoStack.length > 0)) {
        hotInstance.undoRedo.undoStack = undoStack
        hotInstance.undoRedo.redoStack = redoStack
        console.log('✅ 恢复 undo 历史:', undoStack.length, 'redo 历史:', redoStack.length)
      }
      // 恢复自定义撤销栈（设置到 window）
      if (customUndoStack.length > 0 || customRedoStack.length > 0) {
        window.customUndoStack = customUndoStack
        window.customRedoStack = customRedoStack
        console.log('✅ 恢复自定义 undo 历史:', customUndoStack.length, 'redo 历史:', customRedoStack.length, '设置到window')
      }
    } catch (e) {
      console.warn('⚠️ 恢复 undo 历史失败:', e)
    }

    console.log('✅ 表格强制刷新完成')

    // ==================== 🔥 关键新增：刷新后重新添加删除行监听器 ====================
    setTimeout(() => {
      console.log('🔧 表格刷新完成，等待300ms后重新设置删除行监听器...')

      // 重新获取当前活跃的表格实例
      const currentViewer = props.showFlatMode ? flatViewer.value : originalViewer.value
      if (!currentViewer) {
        console.warn('⚠️ 刷新后无法获取表格查看器')
        return
      }

      const refreshedInstance = currentViewer.getSafeHotInstance?.()
      if (!refreshedInstance || refreshedInstance.isDestroyed) {
        console.warn('⚠️ 刷新后无法获取表格实例')
        return
      }

      console.log('🔧 开始重新添加删除行监听器，实例GUID:', refreshedInstance.guid)

      // 检查当前是否有监听器（使用 hasHook）
      console.log('🔍 检查当前监听器状态:')
      if (typeof refreshedInstance.hasHook === 'function') {
        const hasExistingHook = refreshedInstance.hasHook('afterRemoveRow')
        console.log('   - hasHook("afterRemoveRow"):', hasExistingHook)
        console.log('   - 实例GUID:', refreshedInstance.guid)

        // 如果已有监听器，先移除旧的
        if (hasExistingHook) {
          console.log('🗑️ 移除旧的监听器...')
          if (typeof refreshedInstance.removeHook === 'function') {
            refreshedInstance.removeHook('afterRemoveRow')
            console.log('✅ 旧监听器已移除')
          }
        }
      } else {
        console.log('⚠️ 无法检查监听器状态，hasHook 方法不存在')
      }

      // 添加新的删除行监听器
      refreshedInstance.addHook('afterRemoveRow', (index, amount, physicalRows, source) => {
        console.log('🔥🔥🔥 刷新后监听器触发: 检测到删除行操作', {
          index,
          amount,
          source,
          时间戳: Date.now(),
          实例GUID: refreshedInstance.guid
        })

        // 创建数据变更信息
        const changeInfo = {
          isEditMode: true,
          hasChanges: true,
          operation: 'removeRows',
          details: {
            startIndex: index,
            removedCount: amount,
            source: source,
            refreshType: 'forceRefresh',
            instanceGuid: refreshedInstance.guid
          },
          allChanges: []
        }

        // 发射数据变更事件
        emit('data-changed', changeInfo)

        // 发射编辑状态变更事件
        emit('edit-status-changed', {
          hasChanges: true,
          operation: 'rowRemovalAfterRefresh',
          affectedRows: amount
        })

        console.log('✅ 删除行操作已通过刷新后监听器处理')
      })

      // 验证监听器是否成功添加（使用 hasHook）
      console.log('✅ 刷新后监听器设置完成:')
      if (typeof refreshedInstance.hasHook === 'function') {
        const hasNewHook = refreshedInstance.hasHook('afterRemoveRow')
        console.log('   - hasHook("afterRemoveRow"):', hasNewHook)
        console.log('   - 实例GUID:', refreshedInstance.guid)
        console.log('   - 设置成功:', hasNewHook)
      } else {
        console.log('⚠️ 无法验证监听器，hasHook 方法不存在')
        console.log('   但监听器已尝试添加，实例GUID:', refreshedInstance.guid)
      }
    }, 300) // 延迟300ms，确保表格渲染完成
    // ==================== 🔥 关键新增结束 ====================

  } catch (error) {
    console.error('❌❌ 表格刷新失败:', error)
    retryCount = 0 // 🔥 出错时也重置计数器
  }
}


const forceRefreshHandsontable00000 = () => {
  console.log('🔄🔄 开始强制刷新Handsontable...')

  try {
    const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value

    if (!viewer) {
      console.log('⏳⏳⏳ 表格视图未就绪，稍后重试...')

      // 🔥 关键修复：先检查再增加
      if (retryCount >= MAX_RETRY_COUNT) {
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

    hotInstance.render()
    hotInstance.updateSettings({}, false)

    if (props.excelData && props.excelData.length > 0) {
      hotInstance.loadData(props.excelData)
    }

    console.log('✅ 表格强制刷新完成')

    // 🔥🔥 关键新增：刷新后重新添加删除行监听器
    console.log('⏳ 表格刷新完成，等待300ms后重新设置监听器...')
    setTimeout(() => {
      console.log('🔄 开始重新设置删除行监听器')

      // 重新获取实例，确保是当前活跃的实例
      const refreshedInstance = viewer.getSafeHotInstance?.()
      if (!refreshedInstance || refreshedInstance.isDestroyed) {
        console.warn('⚠️ 表格实例在刷新后被销毁，无法设置监听器')
        return
      }

      // 检查是否需要重新设置监听器
      const existingHooks = refreshedInstance.getHooks('afterRemoveRow')
      console.log('🔍 检查当前监听器状态:', {
        已有监听器数量: existingHooks?.length || 0,
        实例GUID: refreshedInstance.guid
      })

      // 如果已有监听器，先移除旧的
      if (existingHooks && existingHooks.length > 0) {
        console.log('🗑️ 移除旧的监听器...')
        refreshedInstance.removeHook('afterRemoveRow')
      }

      // 添加新的删除行监听器
      refreshedInstance.addHook('afterRemoveRow', (index, amount, physicalRows, source) => {
        console.log('🔥🔥🔥 表格刷新后监听器触发: 删除行操作', {
          index,
          amount,
          source,
          timestamp: Date.now()
        })

        // 创建数据变更信息
        const changeInfo = {
          isEditMode: true,
          hasChanges: true,
          operation: 'removeRows',
          details: {
            startIndex: index,
            removedCount: amount,
            source: source,
            refreshType: 'forceRefresh',
            instanceGuid: refreshedInstance.guid
          },
          allChanges: []
        }

        // 发射数据变更事件
        emit('data-changed', changeInfo)

        // 发射编辑状态变更事件
        emit('edit-status-changed', {
          hasChanges: true,
          operation: 'rowRemovalAfterRefresh',
          affectedRows: amount
        })

        console.log('✅ 删除行操作已通过刷新后监听器处理')
      })

      // 验证监听器是否成功添加
      const newHooks = refreshedInstance.getHooks('afterRemoveRow')
      console.log('✅ 刷新后监听器设置完成:', {
        新监听器数量: newHooks?.length || 0,
        设置成功: (newHooks?.length || 0) > 0,
        实例GUID: refreshedInstance.guid
      })
    }, 300) // 延迟300ms，确保表格渲染完成

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
  isDataLoaded: () => isDataLoaded.value
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

  if (props.selectedSheet) {
    setTimeout(() => {
      console.log('🔄🔄 强制更新保存按钮状态')
    }, 50)
  }
}, { immediate: true })


// 在ExcelContent.vue的watch中添加
watch(() => props.excelData, (newData, oldData) => {

  if (newData && newData.length > 0) {

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

  const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value
  if (!viewer) {
    setTimeout(forceRefreshTables, 100)
    return
  }

  const hotInstance = viewer.getSafeHotInstance?.()
  if (hotInstance && !hotInstance.isDestroyed) {
    hotInstance.render()
  }
}


// 在 ExcelContent.vue 中添加搜索路由函数
const routeSearchToCorrectViewer = (keyword) => {

  // 优先使用当前显示模式的组件
  const targetViewer = showFlatMode.value ? flatViewer.value : originalViewer.value

  if (targetViewer && targetViewer.performSearch) {
    targetViewer.performSearch(keyword)
  } else {
    console.error('❌ 目标组件不可用')
  }
}


const checkSaveButtons = () => {
  const noSheet = !props.selectedSheet
  const noChanges = !enableSaveButtons.value
  const shouldDisable = noSheet || noChanges

  setTimeout(() => {
    const saveButtons = document.querySelectorAll('.save-buttons .el-button')
    saveButtons.forEach((btn, idx) => {

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
    highlightCurrentSheetContent(currentSearchKeyword)
  }
}

// 增强事件处理函数
const handleExcelSearchEvent = (event) => {
  const { keyword } = event.detail

  // 立即执行，不延迟
  highlightCurrentSheetContent(keyword)
}

// 在 ExcelContent.vue 的 watch 中添加
watch(() => props.excelData, (newData, oldData) => {

  if (newData && newData.length > 0) {

    // 立即检查子组件状态
    nextTick(() => {
      const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value
      if (viewer) {
        console.log('🔍 子组件状态检查:', {
          组件类型: props.showFlatMode ? '扁平化' : '原始'
        })
      }
    })
  }
}, { deep: true, immediate: true })


// 在canMergeData计算属性后面添加调试代码
watch(() => canMergeData.value, (canMerge) => {
  console.group('🔍 合并数据按钮状态分析')

  if (hasPreviousSheet.value && props.selectedSheet) {
    const currentSheet = allSheets.value[currentSheetIndex.value]
    const previousSheet = allSheets.value[currentSheetIndex.value - 1]

    if (currentSheet && previousSheet) {
      const currentPageNum = extractPageNumber(currentSheet.name)
      const previousPageNum = extractPageNumber(previousSheet.name)
    }
  }
  console.groupEnd()
}, { immediate: true })

// 在 ExcelContent.vue 的 onMounted 中添加
onMounted(() => {

  // 监听选中区域统计事件
  const handleSelectionSum = (event) => {
    selectionSumData.value = event.detail
  }

  window.addEventListener('selection-sum-changed', handleSelectionSum)

  // 清理事件监听
  onUnmounted(() => {
    window.removeEventListener('selection-sum-changed', handleSelectionSum)
  })
})

// 在组件挂载后设置全局搜索函数
onMounted(() => {
  if (performExcelContentSearch) {
    // 设置全局函数供 App.vue 调用
    window.performExcelSearch = performExcelContentSearch
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


/* 合并确认弹窗样式 */
.merge-confirm-dialog .el-message-box__content {
  line-height: 1.6;
}

.merge-confirm-dialog .el-message-box__content ul {
  margin: 8px 0;
  padding-left: 20px;
}

.merge-confirm-dialog .el-message-box__content li {
  margin-bottom: 4px;
}

.merge-confirm-dialog .el-message-box__content b {
  color: #409eff;
}

.merge-confirm-dialog .el-message-box__btns {
  margin-top: 20px;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

</style>