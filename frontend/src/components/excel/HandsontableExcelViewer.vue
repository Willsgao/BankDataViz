<template>
  <div class="handsontable-excel-viewer" :class="{ 'edit-mode': isEditMode }">
    <!-- 第一行：主控栏（最简科学） -->
    <div class="main-toolbar">
      <div class="toolbar-section left-section">
        <el-button type="primary" size="small" :disabled="!tableData.length" @click="exportData">
          <el-icon><Download /></el-icon>导出
        </el-button>

        <el-button
          v-if="hasEmptyCells"
          :type="showEmptyCellsHighlight ? 'primary' : ''"
          size="small"
          @click="toggleEmptyCellsHighlight"
        >
          <el-icon><View /></el-icon>{{ showEmptyCellsHighlight ? '隐藏空格' : '高亮空格' }}
        </el-button>

        <el-button
          :type="isEditMode ? 'danger' : 'warning'"
          size="small"
          :disabled="!tableData.length"
          @click="toggleEditMode"
        >
          <el-icon><Edit /></el-icon>{{ isEditMode ? '退出' : '编辑' }}
        </el-button>



      </div>

      <div class="toolbar-section center-section" v-if="tableData.length > 0">
        <el-tag size="small" type="info" class="data-summary">
          <el-icon><Grid /></el-icon>
          {{ tableData.length - 1 }}行 × {{ columns.length }}列
        </el-tag>

        <el-divider
          v-if="hasDualHeaders && tableInfo"
          direction="vertical"
          style="margin: 0 8px;"
        />

        <div v-if="hasDualHeaders && tableInfo" class="dual-header-info">
          <el-tag type="success" size="small">
            <el-icon><Menu /></el-icon>双表头
          </el-tag>
          <span class="structure-info">
            {{ tableInfo.横向表头 }}列 × {{ tableInfo.纵向表头 }}行
          </span>
        </div>
      </div>

      <div class="toolbar-section right-section">
        <!-- 将整体扁平化按钮移动到这里 -->
        <el-button
          type="primary"
          size="small"
          :disabled="!globalFlattenEnabled"
          @click="handleGlobalFlatten"
          :loading="globalFlattenLoading"
          class="global-flatten-btn"
        >
          <el-icon><DataBoard /></el-icon>
          整体扁平化
        </el-button>


        <el-tooltip
          v-if="isEditMode"
          :content="`编辑模式${hasChanges ? ` (已修改 ${modifiedCellsCount} 个单元格)` : ''}`"
          placement="bottom"
        >
          <el-tag
            :type="hasChanges ? 'warning' : 'success'"
            size="small"
            class="status-tag"
          >
            <el-icon><Edit /></el-icon>
            {{ hasChanges ? `已修改(${modifiedCellsCount})` : '编辑中' }}
          </el-tag>
        </el-tooltip>
      </div>
    </div>

    <!-- 第二行：功能操作栏（合并当前单元格完整信息，选中才显） -->
    <div class="action-toolbar compact-line" v-if="tableData.length > 0 && (showStatsPanel || selectedCell.position)">
      <!-- 左侧：选中统计（原有） -->
      <div v-if="showStatsPanel" class="action-group selection-stats-group">
        <div class="group-header">
          <el-icon><DataAnalysis /></el-icon>
          <span class="group-title">选中区域统计</span>
          <el-tag size="small" :type="stats.selectionType === 'column' ? 'info' : 'success'">
            {{ stats.selectionType === 'column' ? '整列' : '区域' }}
          </el-tag>
        </div>
        <div class="stats-content">
          <div class="stats-grid">
            <div class="stat-item"><span class="stat-label">单元格数:</span><span class="stat-value">{{ stats.rowCount }}</span></div>
            <div class="stat-item"><span class="stat-label">数值:</span><span class="stat-value">{{ stats.numericCount }}</span></div>
            <div class="stat-item"><span class="stat-label">总和:</span><span class="stat-value">{{ stats.sum }}</span></div>
            <div class="stat-item"><span class="stat-label">平均值:</span><span class="stat-value">{{ stats.average }}</span></div>
            <div class="stat-item"><span class="stat-label">最大值:</span><span class="stat-value">{{ stats.max }}</span></div>
            <div class="stat-item"><span class="stat-label">最小值:</span><span class="stat-value">{{ stats.min }}</span></div>
          </div>
          <el-button size="small" type="info" link @click="clearSelection" title="清除选择" class="clear-btn"><el-icon><Close /></el-icon></el-button>
        </div>
      </div>

      <!-- 右侧：当前单元格完整信息（合并进来，不省略） -->
      <div v-if="selectedCell.position" class="action-group current-cell-inline">
        <el-tag size="small" type="info" style="white-space: normal; line-height: 1.4;">
          <el-icon><Position /></el-icon>
          <span class="cell-pos">{{ selectedCell.position }}</span> |
          <span class="cell-type">{{ selectedCell.type }}</span> |
          <span class="cell-content">{{ selectedCell.content || '[空]' }}</span>
          <span v-if="selectedCell.isModified" style="color: #f56c6c;">（已修改）</span>
        </el-tag>
      </div>
    </div>

    <!-- 表格区域（完全不动） -->
    <div class="excel-container" ref="excelContainer">
      <HotTable
        ref="hotTable"
        :data="tableData"
        :columns="computedColumns"
        :colWidths="colWidths"
        :colHeaders="true"
        :rowHeaders="true"
        :width="'100%'"
        :height="tableHeight"
        licenseKey="non-commercial-and-evaluation"
        :language="currentLanguage"
        :filters="true"
        :dropdownMenu="true"
        :contextMenu="true"
        :manualColumnResize="true"
        :manualRowResize="true"
        :wordWrap="false"
        :columnSorting="true"
        :multiColumnSorting="false"
        :autoRowSize="false"
        :autoColumnSize="false"
        :renderAllRows="false"
        :fixedRowsTop="fixedRowsTop"
        :fixedColumnsLeft="fixedColumnsLeft"
        :key="langKey"
        @afterFilter="onFilter"
        @after-change="onDataChange"
        @after-init="onHotInit"
      />

      <div v-if="tableData.length === 0" class="empty-state">
        <el-empty description="暂无表格数据" />
      </div>

      <div v-if="showScrollHint" class="horizontal-scroll-hint">
        ← → 可左右滚动查看完整表格
      </div>
    </div>
  </div>
</template>


<script setup>
import { registerLanguageDictionary, zhCN } from 'handsontable/i18n'
import { ref, computed, defineEmits, defineProps, nextTick, onMounted, onUnmounted, defineExpose } from 'vue'

import { HotTable } from '@handsontable/vue3'
import 'handsontable/dist/handsontable.full.min.css'  // 使用最新样式
import {
  Download, Edit, View, Grid, Menu, DataAnalysis,
  Close, Position, DataBoard
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'


// 导入组合式函数
import useExcelTable from './useExcelTable.js'
import useExcelData from './useExcelData.js'
import useExcelEdit from './useExcelEdit.js'
import useExcelSelection from './useExcelSelection.js'
import useExcelViewerLogic from './useExcelViewerLogic.js'
import useExcelViewerExpose from './useExcelViewerExpose.js'

// 注册中文语言包
try {
  registerLanguageDictionary(zhCN)
  console.log('✅ 中文语言包已注册')
} catch (error) {
  console.warn('⚠️ 注册中文语言包失败，使用英文:', error.message)
}

// 在现有的响应式变量后添加新变量
const globalFlattenLoading = ref(false)

// 添加计算属性：判断是否启用整体扁平化按钮
const globalFlattenEnabled = computed(() => {
  return props.pdfId && props.excelFileName && props.sheetName && tableData.value.length > 0
})


// 前端调用时，需要将pdf_id放在URL路径中
const handleGlobalFlatten = async () => {
  if (!props.pdfId) {
    ElMessage.warning('请先选择PDF文件')
    return
  }

  globalFlattenLoading.value = true

  try {
    console.log('🔄 开始整体扁平化处理', {
      pdfId: props.pdfId,
      excelFileName: props.excelFileName,
      sheetName: props.sheetName
    })

    // 构建请求数据（注意：pdf_id现在放在URL路径中）
    const requestData = {
      excel_file: props.excelFileName,
      sheet_name: props.sheetName,
      request_timestamp: Date.now()
    }

    // 🔥 修正：pdf_id放在URL路径中
    const response = await fetch(`/api/excel/global-flatten/${props.pdfId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData)
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const result = await response.json()
    console.log('📥 整体扁平化API返回:', result)

    if (result.success && result.data) {
      // 发射事件给父组件处理数据
      emit('global-flatten-complete', {
        flattenedData: result.data,
        pdfId: result.pdf_id,  // 使用返回的pdf_id确认
        excelFile: props.excelFileName,
        sheetName: props.sheetName,
        fileInfo: result.file_info,
        processingInfo: {
          originalRows: result.original_rows,
          flattenedRows: result.flattened_rows
        }
      })

      ElMessage.success(`整体扁平化完成，生成 ${result.data.length} 行数据`)
    } else {
      throw new Error(result.error || '整体扁平化处理失败')
    }

  } catch (error) {
    console.error('❌ 整体扁平化失败:', error)
    ElMessage.error(`整体扁平化失败: ${error.message}`)
  } finally {
    globalFlattenLoading.value = false
  }
}


// ============ 核心：Handsontable 实例控制器 ============
class HotInstanceController {
  constructor() {
    this.instance = null
    this.ready = false
    this.waiters = []
    this.initPromise = null
    this.timeout = 5000
  }

  setInstance(hot) {
    if (!hot || hot.isDestroyed) return

    this.instance = hot
    this.ready = true

    // 解决所有等待者
    this.resolveWaiters()

    console.log('🎯 HotInstanceController: 实例已设置', {
      行数: hot.countRows?.(),
      列数: hot.countCols?.()
    })
  }

  waitForReady(timeout = 5000) {
    if (this.ready && this.instance && !this.instance.isDestroyed) {
      return Promise.resolve(this.instance)
    }

    return new Promise((resolve, reject) => {
      const waiterId = Date.now() + Math.random()
      this.waiters.push({ id: waiterId, resolve, reject })

      const timer = setTimeout(() => {
        const index = this.waiters.findIndex(w => w.id === waiterId)
        if (index > -1) {
          this.waiters.splice(index, 1)
          reject(new Error(`Handsontable 实例 ${timeout}ms 内未就绪`))
        }
      }, timeout)

      // 为第一个等待者启动健康检查
      if (this.waiters.length === 1 && !this.initPromise) {
        this.startHealthCheck()
      }
    })
  }

  startHealthCheck() {
    this.initPromise = new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (this.ready && this.instance && !this.instance.isDestroyed) {
          clearInterval(checkInterval)
          resolve(this.instance)
          this.resolveWaiters()
        }
      }, 100)

      // 超时停止检查
      setTimeout(() => {
        clearInterval(checkInterval)
        if (!this.ready) {
          console.warn('⚠️ Handsontable 健康检查超时')
        }
      }, this.timeout)
    })
  }

  resolveWaiters() {
    while (this.waiters.length > 0) {
      const waiter = this.waiters.shift()
      if (waiter.resolve) {
        try {
          waiter.resolve(this.instance)
        } catch (err) {
          console.error('解析等待者失败:', err)
        }
      }
    }
  }

  getInstance() {
    return this.instance
  }

  isReady() {
    return this.ready && this.instance && !this.instance.isDestroyed
  }

  destroy() {
    this.ready = false
    this.waiters = []
    this.initPromise = null
    if (this.instance && !this.instance.isDestroyed) {
      this.instance.destroy()
    }
    this.instance = null
  }
}

// 创建全局控制器
const hotController = new HotInstanceController()
const hotInstanceRef = ref(null)

// ============ Props & Emits ============
const emit = defineEmits([
  'cell-changed',
  'data-changed',
  'edit-status-changed',
  'cell-change',
  'instance-ready',
  'global-flatten-complete'
])

const props = defineProps({
  excelData: {
    type: Array,
    default: () => []
  },
  flatData: {
    type: Array,
    default: () => []
  },
  sheetName: String,
  pdfId: String,
  excelFileName: String
})

// ============ 组合式函数初始化 ============

// 表格实例管理
const {
  hotTable,
  excelContainer,
  tableHeight,
  showScrollHint,
  getSafeHotInstance,
  setupEventListeners,
  cleanup,
} = useExcelTable(props)

// 语言相关
const currentLanguage = ref('zh-CN')
const langKey = ref('zh-CN-' + Date.now())

// 优化的实例获取函数
const getHotInstanceDirect = () => {
  try {
    // 优先级1：通过控制器获取
    if (hotController.isReady()) {
      return hotController.getInstance()
    }

    // 优先级2：通过组件ref获取
    if (hotTable.value && hotTable.value.hotInstance) {
      const instance = hotTable.value.hotInstance
      if (!instance.isDestroyed) {
        hotController.setInstance(instance)
        return instance
      }
    }

    // 优先级3：从DOM获取
    const hotElement = excelContainer.value?.querySelector?.('.handsontable')
    if (hotElement && hotElement.hotInstance) {
      const instance = hotElement.hotInstance
      if (!instance.isDestroyed) {
        hotController.setInstance(instance)
        return instance
      }
    }

    // 优先级4：全局变量
    if (window.__excelHotInstance && !window.__excelHotInstance.isDestroyed) {
      hotController.setInstance(window.__excelHotInstance)
      return window.__excelHotInstance
    }

    return null
  } catch (error) {
    console.warn('直接获取 Handsontable 实例失败:', error)
    return null
  }
}

// 修改 onHotInit 函数
// HandsontableExcelViewer.vue - 修改 onHotInit 函数
const onHotInit = () => {
  setTimeout(() => {
    const hot = getHotInstanceDirect()
    if (hot) {
      hotInstanceRef.value = hot
      hotController.setInstance(hot)
      window.__excelHotInstance = hot

      console.log('⚡ Handsontable 实例已立即暴露', {
        行数: hot.countRows(),
        列数: hot.countCols(),
        实例ID: hot.guid,
        时间戳: Date.now()
      })

      // 🔥 关键修改：发射强化版的就绪事件
      emit('instance-ready', {
        instance: hot,
        guid: hot.guid,
        pdfId: props.pdfId,
        excelFileName: props.excelFileName,
        sheetName: props.sheetName,
        tableType: props.excelData === props.flatData ? 'flattened' : 'original',
        timestamp: Date.now()
      })

      // 原有的恢复红色标记
      nextTick(() => restoreModifiedCellsStyle())
    }
  }, 0)
}

// 获取增强版实例（兼容原有逻辑）
const getEnhancedHotInstance = () => {
  const instance = getSafeHotInstance()
  if (instance) {
    try {
      if (instance.isDestroyed) {
        console.warn('⚠️ 表格实例已销毁')
        return null
      }
      const settings = instance.getSettings()
      if (!settings) {
        console.warn('⚠️ 无法获取表格设置')
        return null
      }
      return instance
    } catch (error) {
      console.warn('⚠️ 验证表格实例失败:', error)
      return null
    }
  }
  return null
}

// 数据处理
const {
  tableData,
  hasDualHeaders,
  tableInfo,
  fixedRowsTop,
  fixedColumnsLeft,
  columns,
  verifyTableStructure,
  exportData,
  detectEmptyCells,
  hasEmptyCells,
  emptyCellsStats
} = useExcelData(props)

// 编辑功能
const {
  isEditMode,
  hasChanges,
  saving,
  modifiedCellsCount,
  modifiedCells,
  saveChanges: saveChangesInternal,
  onDataChange,
  updateTableReadOnly,
  resetChanges,
  savedCells,
  unsavedCells,
  collectModifiedData,
  updateModifiedCellsStyle,
  markSavedCells,
  toggleEditMode: toggleEditModeFromHook,
  checkInstanceHealth,
  refreshCache,
  clearCache,
  validateHotInstance,
  getHotInstance: getHotInstanceFromHook
} = useExcelEdit(getEnhancedHotInstance)

// 选择统计
const {
  showStatsPanel,
  stats,
  currentSelection,
  calculateSelectionStats,
  clearSelection,
  setupColumnSelectionListener
} = useExcelSelection(getSafeHotInstance)

// 主要逻辑
const logic = useExcelViewerLogic(
  props,
  {
    hotTable,
    getSafeHotInstance,
    isEditMode,
    hasChanges,
    modifiedCells,
    modifiedCellsCount,
    savedCells,
    unsavedCells,
    tableData,
    hasDualHeaders,
    tableInfo,
    columns,
    hasEmptyCells,
    detectEmptyCells,
    emptyCellsStats,
    showStatsPanel,
    stats,
    calculateSelectionStats,
    clearSelection,
    updateTableReadOnly,
    markSavedCells,
    toggleEditModeFromHook,
    highlightEmptyCells: () => {},
    clearEmptyCellsHighlight: () => {},
    cleanup,
    onDataChange
  },
  emit
)

// 添加这3个关键方法
defineExpose({
  waitForInstanceReady: (timeout = 5000) => hotController.waitForReady(timeout),
  getHotInstance: () => hotController.getInstance(),
  isInstanceReady: () => hotController.isReady(),
})

// 保留原有的 useExcelViewerExpose 调用（不要删除）
useExcelViewerExpose({
  exportData,
  tableData,
  verifyTableStructure,
  clearSelection,
  getSafeHotInstance,
  markSavedCells: logic.markSavedCells,
  markMultipleCellsAsSaved: logic.markMultipleCellsAsSaved,
  forceFixSavedCellsStyles: logic.forceFixSavedCellsStyles,
  clearSavedMarks: logic.clearSavedMarks,
  getSavedCellsState: logic.getSavedCellsState,
  debugSavedCells: logic.debugSavedCells,
  restoreCellStates: logic.restoreCellStates,
  toggleEditMode: logic.toggleEditMode,
  forceFixStyles: logic.forceFixStyles,
})


// 模板中使用的属性和方法
const {
  showEmptyCellsHighlight,
  selectedCell,
  colWidths,
  computedColumns,
  toggleEmptyCellsHighlight,
  toggleEditMode,
  onFilter
} = logic

// 组件销毁时清理
onUnmounted(() => {
  hotController.destroy()
  if (window.__excelHotInstance === hotInstanceRef.value) {
    window.__excelHotInstance = null
  }
})
</script>



<style scoped>
/* 恢复正常的表头样式，移除所有 sticky 定位 */
.handsontable-excel-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
}

/* ====================
   重新设计的主要工具栏
   ==================== */
.main-toolbar {
  flex-shrink: 0;
  padding: 8px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 52px;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 左侧区域 */
.left-section {
  flex: 1;
}

.primary-actions {
  margin-right: 12px;
}

.table-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.data-summary {
  background: #f0f9ff;
  border-color: #e1f5fe;
  color: #1890ff;
}

.dual-header-info {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  background: #f6ffed;
  border-radius: 4px;
  border: 1px solid #b7eb8f;
}

.structure-info {
  font-size: 12px;
  color: #52c41a;
  font-weight: 500;
}

/* 右侧区域 */
.global-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-tag {
  cursor: default;
  transition: all 0.2s;
  min-width: 60px;
  text-align: center;
}

.status-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* ====================
   功能操作栏
   ==================== */
.action-toolbar {
  flex-shrink: 0;
  padding: 8px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

/* 操作组通用样式 */
.action-group {
  background: white;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 8px 12px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #f0f0f0;
}

.group-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.group-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 空白单元格组 */
.empty-cells-group {
  border-left: 3px solid #1890ff;
}

/* 选中区域统计组 */
.selection-stats-group {
  border-left: 3px solid #52c41a;
}

.stats-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  flex: 1;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 8px;
  background: #f0f9ff;
  border-radius: 4px;
  border: 1px solid #e1f5fe;
  min-width: 120px;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

.stat-value {
  font-size: 12px;
  font-weight: 500;
  color: #1890ff;
}

.clear-btn {
  margin-left: 12px;
}

/* 当前单元格组 */
.current-cell-group {
  border-left: 3px solid #fa8c16;
  padding: 10px 12px;
}

.cell-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cell-info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cell-preview-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cell-preview {
  flex: 1;
  padding: 6px 10px;
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: #333;
  white-space: pre-wrap;
  word-break: break-all;
  min-height: 28px;
  max-height: 56px;
  overflow-y: auto;
}

.cell-details-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.format-text {
  margin-left: 2px;
  font-size: 11px;
  opacity: 0.8;
}

.cell-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #888;
}

.meta-item .el-icon {
  font-size: 12px;
}

/* 单元格预览样式继承（保持不变） */
.cell-preview.numeric-cell {
  text-align: right;
  font-family: 'Consolas', 'Monaco', monospace;
}

.cell-preview.formula-cell {
  font-style: italic;
  color: #1677ff;
  background-color: #f0f6ff;
}

.cell-preview.modified-cell {
  background-color: #fff7e6;
  border-color: #ffd591;
}

.cell-preview.invalid-number {
  background-color: #fff2f0 !important;
  border-color: #ffccc7 !important;
  color: #ff4d4f;
}

.cell-preview.empty-cell {
  background-color: #f0f9ff;
  border: 1px dashed #1890ff;
  color: #666;
}

/* ====================
   表格容器区域（撑满 + 防遮挡）
   ==================== */
.excel-container {
  flex: 1 1 auto;              /* 关键：占满剩余高度 */
  min-height: 0;               /* 防止 flex 子项被内容撑爆 */
  overflow: auto;              /* 内容多时滚动 */
  position: relative;
  border: 1px solid #e0e0e0;
  background: white;
  padding-top: 1px;            /* 微小内距，避免边框被遮挡 */
  height: 100%;
}

/* ====================
   以下为原有样式，保持不变
   ==================== */

/* 确保 Handsontable 正常显示 */
:deep(.handsontable .wtHolder) {
  overflow: auto !important;
}

:deep(.handsontable) {
  height: 100%;          /* 让 Handsontable 内部也吃满 */
}

/* ====================
   表头固定修复（不破坏滚动）
   ==================== */
/* 关键：不要修改表头的position，让Handsontable自己管理 */
:deep(.ht_clone_top) {
  z-index: 999 !important;
  overflow: visible !important;
}

/* 确保表头容器正常 */
:deep(.ht_clone_top .wtHolder) {
  overflow: hidden !important;
}

/* 主表格区域保持滚动 */
:deep(.ht_master .wtHolder) {
  overflow: auto !important;
  width: 100% !important;
}

/* 隐藏左侧表头的滚动条 */
:deep(.ht_clone_left::-webkit-scrollbar) {
  display: none !important;
}

/* ====================
   其他样式保持不变
   ==================== */
:deep(.modified-cell) {
  background-color: #ffebee !important;
  border: 1px solid #f44336 !important;
}

.horizontal-scroll-hint {
  position: absolute;
  bottom: 5px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 100;
  animation: fadeInOut 2s ease-in-out;
}

@keyframes fadeInOut {
  0%, 100% { opacity: 0; }
  50% { opacity: 1; }
}

/* 双表头特殊样式 */
:deep(.vertical-header-column) {
  background-color: #f6ffed !important;
  font-weight: 600 !important;
  min-width: 120px !important;
}

/* 确保固定表头样式正确 */
:deep(.ht_clone_top) {
  z-index: 100 !important;
}

:deep(.ht_clone_left) {
  -ms-overflow-style: none !important;  /* IE and Edge */
  scrollbar-width: none !important;     /* Firefox */
}

:deep(.ht_clone_top th) {
  background-color: #f0f9ff !important;
  border-bottom: 2px solid #409eff !important;
}

/* 确保左侧表头与主表格对齐 */
:deep(.ht_clone_left table) {
  height: 100% !important;
}

:deep(.ht_clone_top th:first-child) {
  background: linear-gradient(135deg, #f0f9ff 50%, #f6ffed 50%) !important;
  border-right: 2px solid #409eff !important;
  border-bottom: 2px solid #52c41a !important;
}

:deep(.ht_clone_left td) {
  background-color: #f6ffed !important;
  border-right: 2px solid #52c41a !important;
}

/* ====================
   新增：防止表头被拉上去的特殊修复
   ==================== */
/* 防止表头行高变化 */
:deep(.ht_clone_top th) {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
  height: 20px !important; /* 减小高度 */
  min-height: 20px !important;
  line-height: 20px !important;
  box-sizing: border-box !important;
}

/* 确保表头背景不透明 */
:deep(.ht_clone_top) {
  background-color: #f8f9fa !important;
}

/* ====================
   验证状态样式（保持不变）
   ==================== */
.cell-validation .el-tag {
  font-weight: bold;
  cursor: help;
  min-width: 100px;
  text-align: center;
}

.cell-validation .el-tag.el-tag--success {
  background-color: #f6ffed;
  border-color: #b7eb8f;
  color: #52c41a;
}

.cell-validation .el-tag.el-tag--danger {
  background-color: #fff2f0;
  border-color: #ffccc7;
  color: #ff4d4f;
}

.cell-validation .el-tag.el-tag--warning {
  background-color: #fff7e6;
  border-color: #ffd591;
  color: #fa8c16;
}

/* 日期类型样式 */
.date-hint .el-tag {
  background-color: #fff7e6;
  border-color: #ffd591;
  color: #fa8c16;
}

.date-hint .el-tag .el-icon {
  margin-right: 2px;
}

/* ====================
   单元格样式控制（全部保持不变）
   ==================== */
/* 最简单：通过父级类名控制 */
.edit-mode :deep(.handsontable .htCore td:not([readonly])) {
  background-color: #f9f9f9 !important;
  border: 1px solid #d9d9d9 !important;
}

/* 在保存时给修改过的单元格添加类 */
.edit-mode :deep(.handsontable .htCore td.modified) {
  background-color: #fff2e8 !important;
  border: 1px solid #ff7a45 !important;
}


/* 编辑模式下的单元格悬停效果 */
:deep(.handsontable .htCore td:not(.modified-cell):hover) {
  background-color: #f0f6ff !important;
  border-color: #1890ff !important;
}

/* 修改单元格的悬停效果 */
:deep(.handsontable .htCore td.modified-cell:hover) {
  background-color: #ffe7d9 !important;
  border-color: #ff7a45 !important;
  box-shadow: 0 0 0 1px #ff7a45;
}

/* 选中修改单元格时的样式 */
:deep(.handsontable .htCore td.modified-cell.current) {
  background-color: #ffd8bf !important;
  border-color: #ff7a45 !important;
}

/* 空白单元格样式 */
:deep(.handsontable td.empty-cell) {
  background-color: #f0f9ff !important;
  border: 2px dashed #1890ff !important;
  position: relative;
}

:deep(.handsontable td.empty-cell::after) {
  content: '空';
  position: absolute;
  top: 1px;
  right: 1px;
  font-size: 9px;
  color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
  padding: 0 2px;
  border-radius: 2px;
  opacity: 0.7;
}

/* 编辑模式下空白单元格样式 */
.edit-mode :deep(.handsontable td.empty-cell) {
  background-color: #e6f7ff !important;
  border: 2px dotted #1890ff !important;
}

/* ====================
   响应式设计
   ==================== */
@media (max-width: 1024px) {
  .main-toolbar {
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 12px;
  }

  .table-info {
    flex-wrap: wrap;
    gap: 8px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stat-item {
    min-width: 140px;
  }
}

@media (max-width: 768px) {
  .action-toolbar {
    padding: 8px 12px;
    max-height: 400px;
  }

  .action-group {
    padding: 8px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .stats-content {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .clear-btn {
    margin-left: 0;
    align-self: flex-end;
  }

  .cell-info-row,
  .cell-details-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .cell-meta {
    margin-left: 0;
    flex-wrap: wrap;
  }

  .cell-preview-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .cell-actions {
    align-self: flex-end;
  }
}

@media (max-width: 480px) {
  .main-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .toolbar-section {
    justify-content: space-between;
    width: 100%;
  }

  .primary-actions {
    width: 100%;
    justify-content: center;
  }

  .global-status {
    justify-content: center;
    width: 100%;
  }

  .group-header {
    flex-wrap: wrap;
    gap: 4px;
  }
}


/* ====================
   单行分块展示样式
   ==================== */
.current-cell-group.compact-single-row {
  border-left: 3px solid #fa8c16;
  padding: 6px 12px;
  min-height: 40px;
}

.compact-single-row .group-header {
  margin-bottom: 4px;
  padding-bottom: 4px;
  border-bottom: 1px solid #f0f0f0;
}

.compact-single-row .group-title {
  font-size: 12px;
  color: #666;
}

.single-row-content {
  display: flex;
  align-items: center;
  gap: 0;
  height: 32px;
}

/* 信息块通用样式 */
.info-block {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 8px;
  height: 100%;
}

/* 分隔线 */
.separator {
  width: 1px;
  height: 20px;
  background: #e0e0e0;
  margin: 0 4px;
}

/* 第一块：基本信息 */
.basic-info {
  min-width: 120px;
}

.basic-info .el-tag {
  height: 22px;
  line-height: 20px;
  padding: 0 6px;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.basic-info .cell-position {
  background: #f5f5f5;
  border-color: #d9d9d9;
  color: #666;
  min-width: 50px;
  justify-content: center;
}

.basic-info .cell-type {
  min-width: 40px;
  justify-content: center;
}

.basic-info .cell-modified {
  width: 22px;
  min-width: 22px;
  justify-content: center;
  padding: 0;
}

.basic-info .cell-modified .el-icon {
  font-size: 12px;
}

/* 第二块：内容显示 */
.cell-content-block {
  flex: 1;
  min-width: 120px;
  max-width: 250px;
}

.cell-content-display {
  flex: 1;
  padding: 4px 8px;
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 3px;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  color: #333;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
  cursor: default;
}

.content-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.char-count {
  font-size: 10px;
  color: #888;
  margin-left: 4px;
  flex-shrink: 0;
}

/* 单元格内容样式变体 */
.cell-content-display.numeric-cell {
  text-align: right;
  font-family: 'Consolas', 'Monaco', monospace;
}

.cell-content-display.formula-cell {
  font-style: italic;
  color: #1677ff;
  background-color: #f0f6ff;
}

.cell-content-display.modified-cell {
  background-color: #fff7e6;
  border-color: #ffd591;
}

.cell-content-display.invalid-number {
  background-color: #fff2f0 !important;
  border-color: #ffccc7 !important;
  color: #ff4d4f;
}

.cell-content-display.empty-cell {
  background-color: #f0f9ff;
  border: 1px dashed #1890ff;
  color: #666;
}

/* 第三块：状态信息 */
.status-info {
  min-width: 160px;
  max-width: 200px;
  flex-wrap: wrap;
  gap: 4px;
}

.status-item {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  padding: 1px 4px;
  border-radius: 3px;
  height: 18px;
}

.status-item .el-icon {
  font-size: 10px;
}

.status-item .status-text {
  white-space: nowrap;
}

/* 验证状态 */
.validation-status.valid {
  background-color: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.validation-status.invalid {
  background-color: #fff2f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

/* 日期状态 */
.date-status {
  background-color: #fff7e6;
  color: #fa8c16;
  border: 1px solid #ffd591;
}

/* 格式信息 */
.format-info {
  background-color: #f0f9ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
}

/* 只读状态 */
.readonly-status {
  background-color: #f5f5f5;
  color: #666;
  border: 1px solid #d9d9d9;
}

/* 第四块：操作按钮 */
.action-buttons {
  min-width: 60px;
  justify-content: flex-end;
}

.action-buttons .action-btn {
  padding: 4px;
  height: 24px;
  width: 24px;
  min-width: 24px;
}

.action-buttons .action-btn .el-icon {
  font-size: 14px;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .single-row-content {
    height: auto;
    flex-wrap: wrap;
    gap: 8px;
  }

  .separator {
    display: none;
  }

  .info-block {
    padding: 4px 0;
  }

  .basic-info {
    order: 1;
    flex: 1;
  }

  .cell-content-block {
    order: 3;
    flex: 2;
    min-width: 100%;
    max-width: 100%;
  }

  .status-info {
    order: 2;
    flex: 1;
    justify-content: flex-end;
    min-width: auto;
    max-width: none;
  }

  .action-buttons {
    order: 4;
    flex: 0;
    min-width: auto;
  }
}

@media (max-width: 768px) {
  .compact-single-row {
    padding: 4px 8px;
  }

  .cell-content-display {
    font-size: 11px;
    padding: 3px 6px;
    height: 22px;
  }

  .basic-info .el-tag {
    height: 20px;
    line-height: 18px;
    padding: 0 4px;
    font-size: 10px;
  }

  .status-item {
    font-size: 10px;
  }
}


/* 在 HandsontableExcelViewer.vue 的 style 部分添加，确保在最后面 */
/* 使用最高优先级的选择器 */
.handsontable-excel-viewer :deep(.handsontable td.modified-cell),
.handsontable-excel-viewer :deep(.handsontable .htCore td.modified-cell),
.handsontable-excel-viewer :deep(.handsontable .htCore tbody tr td.modified-cell),
.handsontable-excel-viewer :deep(.handsontable .htCore thead tr th.modified-cell) {
  background-color: #ffd8d2 !important;
  border: 1px solid #ff7875 !important;
  position: relative;
  z-index: 10;
}

/* 修改标记小圆点 */
.handsontable-excel-viewer :deep(.handsontable td.modified-cell::after),
.handsontable-excel-viewer :deep(.handsontable .htCore td.modified-cell::after) {
  content: '';
  position: absolute;
  top: 3px;
  right: 3px;
  width: 6px;
  height: 6px;
  background-color: #ff4d4f;
  border-radius: 50%;
  z-index: 100;
}






/* 修改标记小圆点 */
.handsontable-excel-viewer :deep(.handsontable td.modified-cell::after) {
  content: '';
  position: absolute;
  top: 3px;
  right: 3px;
  width: 6px;
  height: 6px;
  background-color: #ff4d4f;
  border-radius: 50%;
  z-index: 100;
  display: block !important;
}



/* 确保编辑模式下的样式正确应用 */
.edit-mode :deep(.handsontable .htCore td:not([readonly])) {
  background-color: #f9f9f9 !important;
  border: 1px solid #d9d9d9 !important;
}

/* 编辑模式下单元格可编辑 */
.edit-mode :deep(.handsontable .htCore td) {
  cursor: cell !important;
}

/* 非编辑模式下单元格不可编辑 */
:not(.edit-mode) :deep(.handsontable .htCore td) {
  cursor: default !important;
}


/* ===== 方案 A：只要改过就永久红色 ===== */
/* 🔥 强制红色背景 - 最高优先级样式 */
:deep(.unsaved-modified-cell),
:deep(.htCore .unsaved-modified-cell),
:deep(.htCore td.unsaved-modified-cell),
:deep(.handsontable .htCore td.unsaved-modified-cell),
:deep(.handsontable .htCore tbody tr td.unsaved-modified-cell) {
  background-color: #ffd8d2 !important;
  background: #ffd8d2 !important;
  border: 2px solid #ff7875 !important;
  border-color: #ff7875 !important;
  box-shadow: inset 0 0 0 1px #ff7875 !important;
}

/* 红色圆点 */
:deep(.unsaved-modified-cell)::after,
:deep(.htCore td.unsaved-modified-cell)::after {
  content: '' !important;
  position: absolute !important;
  top: 3px !important;
  right: 3px !important;
  width: 6px !important;
  height: 6px !important;
  background-color: #ff4d4f !important;
  border-radius: 50% !important;
  z-index: 1000 !important;
}


/* 1. 让整个三栏布局吃满视口高度 */
.three-column-layout {
  height: 100vh;
  display: flex;          /* 你原来就有这条的话可省略 */
}

/* 2. 右侧放表格的那一列再纵向 flex */
.right-column {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.main-toolbar {
  display: flex;
  justify-content: space-between;   /* 左中右分离 */
  align-items: center;
  gap: 16px;                        /* 区间距 */
}

.current-cell-full {
  margin-left: 8px;
  max-width: 320px;          /* 限制最大宽度，防止溢出 */
  word-break: break-all;     /* 长内容自动换行 */
  line-height: 1.4;
}


.main-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 6px;
}

.current-cell-bar {
  padding: 6px 12px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 8px;
}

.cell-pos,
.cell-type,
.cell-content {
  font-weight: 500;
  margin-right: 4px;
}

/* 未保存：深红+红点 */
:deep(.unsaved-modified-cell){
  background-color: #ffd8d2 !important;
  border: 1px solid #ff7875 !important;
  position: relative;
}
:deep(.unsaved-modified-cell::after){
  content: '';
  position: absolute;
  top: 2px; right: 2px;
  width: 6px; height: 6px;
  background: #ff4d4f;
  border-radius: 50%;
}

/* 历史已保存：浅红，无红点 */
:deep(.history-modified-cell){
  background-color: #ffe7e6 !important;
  border: 1px solid #ffb7b3 !important;
}


/* 放在 HandsontableExcelViewer.vue 的 <style scoped> 最末尾 */
:deep(.handsontable td.unsaved-modified-cell) {
  background-color: #ffd8d2 !important;
  border: 1px solid #ff7875 !important;
}
:deep(.handsontable td.history-modified-cell) {
  background-color: #ffe7e6 !important;
  border: 1px solid #ffb7b3 !important;
}

/* 放在 <style scoped> 最末尾，权重要最高 */
:deep(.handsontable td.unsaved-modified-cell) {
  background-color: #ffd8d2 !important;
  border: 1px solid #ff7875 !important;
  position: relative;
}
:deep(.handsontable td.unsaved-modified-cell::after) {
  content: '';
  position: absolute;
  top: 2px;
  right: 2px;
  width: 6px;
  height: 6px;
  background: #ff4d4f;
  border-radius: 50%;
}
:deep(.handsontable td.history-modified-cell) {
  background-color: #ffe7e6 !important;
  border: 1px solid #ffb7b3 !important;
}

/* 修改操作按钮组的样式 - 靠右对齐 */
.operation-buttons-group.right-aligned {
  margin-left: auto; /* 关键：靠右对齐 */
  border-left: 3px solid #1890ff; /* 蓝色边框 */
  padding: 6px 12px;
}

.operation-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap; /* 防止换行 */
}

/* 整体扁平化按钮特殊样式 */
.global-flatten-btn {
  background-color: #1890ff;
  border-color: #1890ff;
  color: white;
  font-weight: 600;
}

.global-flatten-btn:hover {
  background-color: #40a9ff;
  border-color: #40a9ff;
}

.global-flatten-btn:disabled {
  background-color: #a0d0ff;
  border-color: #a0d0ff;
  color: #e6f7ff;
}

/* 确保操作按钮组在右侧 */
.action-toolbar.compact-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

/* 左侧统计信息自适应 */
.selection-stats-group {
  flex: 1;
  min-width: 0; /* 防止溢出 */
}

/* 中间单元格信息自适应 */
.current-cell-inline {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: center;
}

/* 右侧操作按钮组固定宽度 */
.operation-buttons-group {
  flex-shrink: 0; /* 防止收缩 */
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .operation-buttons {
    gap: 6px;
  }

  .operation-buttons .el-button {
    font-size: 12px;
    padding: 6px 8px;
  }
}

@media (max-width: 1024px) {
  .action-toolbar.compact-line {
    flex-wrap: wrap;
    gap: 12px;
  }

  .operation-buttons-group.right-aligned {
    margin-left: 0;
    width: 100%;
    justify-content: flex-end;
  }

  .operation-buttons {
    justify-content: flex-end;
  }
}

@media (max-width: 768px) {
  .action-toolbar.compact-line {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .operation-buttons-group.right-aligned {
    width: 100%;
    border-left: none;
    border-top: 3px solid #1890ff;
    padding: 8px 0;
  }

  .operation-buttons {
    justify-content: space-around;
    flex-wrap: wrap;
  }

  .operation-buttons .el-button {
    flex: 1;
    min-width: 120px;
    margin: 2px;
  }
}

@media (max-width: 480px) {
  .operation-buttons {
    flex-direction: column;
    gap: 6px;
  }

  .operation-buttons .el-button {
    width: 100%;
    min-width: auto;
  }
}

/* 确保按钮排列合理 */
.main-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.left-section {
  justify-content: flex-start;
  flex: 1;
}

.center-section {
  justify-content: center;
  flex: 1;
}

.right-section {
  justify-content: flex-end;
  flex: 1;
}

/* 整体扁平化按钮样式 */
.global-flatten-btn {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border-color: #1890ff;
  color: white;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.3);
}

.global-flatten-btn:hover {
  background: linear-gradient(135deg, #40a9ff 0%, #1890ff 100%);
  border-color: #40a9ff;
}

.global-flatten-btn:disabled {
  background: #d9d9d9;
  border-color: #d9d9d9;
  color: #8c8c8c;
  box-shadow: none;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .main-toolbar {
    flex-direction: column;
    gap: 8px;
    align-items: stretch;
  }

  .toolbar-section {
    justify-content: center;
    width: 100%;
  }
}

</style>



