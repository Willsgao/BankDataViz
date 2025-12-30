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
            <!-- 主功能：大按钮 -->
            <el-button
              type="primary"
              size="default"
              :disabled="!props.selectedSheet || excelData.length === 0"
              @click="$emit('toggle-flat-mode')"
              :loading="loadingFlat"
            >
              <el-icon><DataAnalysis /></el-icon>
              {{ showFlatMode ? '二维化' : '扁平化' }}
            </el-button>

            <!-- 保存组：缩小 + 靠右 -->
            <el-button-group size="small" class="save-buttons">
              <el-button
                type="warning"
                :disabled="!(props.selectedSheet && props.hasUnsavedChanges)"
                @click="props.selectedSheet && props.hasUnsavedChanges && $emit('save-data', 'draft')"
              >
                存草稿
              </el-button>
              <el-button
                type="success"
                :disabled="!(props.selectedSheet && props.hasUnsavedChanges)"
                @click="props.selectedSheet && props.hasUnsavedChanges && $emit('save-data', 'final')"
              >
                存后台
              </el-button>
            </el-button-group>

          </div>
        </div>

      </div>
    </div>

    <!-- 第二行：统计 + 保存状态（24 px） -->
    <div class="sub-bar">
      <!-- 空白单元格 -->
      <el-tag v-if="emptyCount" size="small" type="info">
        空白 {{ emptyCount }}
      </el-tag>

      <!-- 选中区域统计 -->
      <el-tag v-if="stats.rowCount" size="small">
        选中 {{ stats.rowCount }} 单元格
        <template v-if="stats.numericCount">
          总和 {{ stats.sum }} 平均 {{ stats.average }}
        </template>
      </el-tag>

      <!-- 保存状态（合并进来） -->
      <SaveStatus
        :selected-sheet="selectedSheet"
        :status="saveStatus"
        :modified-cells-count="modifiedCellsCount"
        :last-save-time="lastSaveTime"
      />
    </div>

    <!-- 当前单元格信息（有值才显示） -->
    <template v-if="currentCell.position">
      <el-tag size="small">{{ currentCell.position }}</el-tag>
      <el-tag size="small" type="info">{{ currentCell.type }}</el-tag>
      <span class="cell-txt">{{ currentCell.content }}</span>
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
            @edit-status-changed="handleEditStatusChanged"
          />
        </div>

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
            @cell-change="handleSheetCellChange"
            @edit-status-changed="handleEditStatusChanged"
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
import sheetStateManager from '@/utils/SheetStateManager.js'

import HandsontableExcelViewer from '@/components/excel/HandsontableExcelViewer.vue'
import {
  DataAnalysis, Document, Check, Refresh, Timer, Grid, Loading
} from '@element-plus/icons-vue'
import { defineProps, defineEmits, ref, computed, watch, nextTick, onMounted   } from 'vue'

import { ElMessage } from 'element-plus'

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
const handleCellSelected = (cell) => {
  currentCell.value = cell
}



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
  }
})

// ============ 新增状态 ============
const originalViewer = ref(null)
const flatViewer = ref(null)
const localUnsavedChanges = ref(0)


const savingDraft = ref(false)
const savingFinal = ref(false)

/* 存后台可点条件：有未保存且不在保存中 */
const canSaveFinal = computed(() =>
  !savingFinal.value && (window.unsavedCells?.size > 0 || sheetStateManager.hasUnsavedChanges(props.showFlatMode ? 'flattened' : 'original'))
)

/* 存草稿：纯前端，永远可点 */
async function handleSaveDraft() {
  savingDraft.value = true
  try {
    // 1. 取当前数据
    const viewer = props.showFlatMode ? flatViewer.value : originalViewer.value
    const key = `draft_${props.selectedPdf.id}_${props.selectedExcelFile}_${props.selectedSheet.name}_${props.showFlatMode ? 'flat' : 'orig'}`

    // 2. 写 localStorage（确保字符串化）
    const draft = {
      data: viewer.tableData,
      modifications: Array.from(window.unsavedCells || []),
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
    window.unsavedCells.clear()
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


// 在 ExcelContent.vue 中检查
const enableSaveButtons = computed(() => {
  console.log('🎯 enableSaveButtons 被计算')
  const result = !!props.selectedSheet && !!props.hasUnsavedChanges

  return result
})


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

      console.log(`📝 记录修改结果:`, {
        成功: success,
        单元格: `[${row},${col}]`,
        旧值: oldValue,
        新值: newValue,
        表类型: tableType
      })
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


// ExcelContent.vue - 确保调试函数正确暴露

// 调试函数
const checkSaveButtons = () => {
  console.group('🔍 ExcelContent 保存按钮状态检查')

  console.log('1. 来自父组件的参数:')
  console.log('   - hasUnsavedChanges:', props.hasUnsavedChanges)
  console.log('   - selectedSheet:', props.selectedSheet?.name)
  console.log('   - selectedPdf:', props.selectedPdf?.id)
  console.log('   - selectedExcelFile:', props.selectedExcelFile)

  console.log('2. 计算属性结果:')
  console.log('   - enableSaveButtons:', enableSaveButtons.value)

  console.log('3. 按钮禁用条件:')
  const noSheet = !props.selectedSheet
  const noChanges = !enableSaveButtons.value
  const shouldDisable = noSheet || noChanges
  console.log('   - 没有选中的sheet:', noSheet)
  console.log('   - 没有未保存修改:', noChanges)
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


// ============ 暴露给父组件的 hasUnsavedChanges ============
// 我们需要向上传递实际的状态
const emit = defineEmits([
  'toggle-flat-mode',
  'save-data',
  'restore-unsaved-data',
  'run-comprehensive-test',
  'cell-changed',
  'data-changed',
  'unsaved-changes-updated'  // 新增
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

</style>