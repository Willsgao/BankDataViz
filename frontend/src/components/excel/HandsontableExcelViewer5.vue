<template>
  <div class="handsontable-excel-viewer" :class="{ 'edit-mode': isEditMode }">




    <!-- 功能操作栏（重新设计） -->
    <div class="action-toolbar" v-if="tableData.length > 0">

      <!-- 空白单元格操作组 → 单行 -->
        <div v-if="hasEmptyCells" class="action-group empty-cells-group oneline">
          <span class="group-title">
            <el-icon><View /></el-icon>
            空白单元格管理
          </span>
          <el-tag size="small" type="info" class="count-tag">
            {{ emptyCellsStats?.total || 0 }}个
          </el-tag>

          <!-- 按钮组 -->
          <el-button-group size="small" class="btn-grp">
            <el-button
              :type="showEmptyCellsHighlight ? 'primary' : ''"
              @click="toggleEmptyCellsHighlight"
            >
              <el-icon><View /></el-icon>
              {{ showEmptyCellsHighlight ? '隐藏高亮' : '高亮空格' }}
            </el-button>
            <el-button size="small" type="info" link @click="showEmptyCellsDetail">
              <el-icon><More /></el-icon>
            </el-button>
          </el-button-group>
        </div>

      <!-- 选中区域统计组 -->
      <div v-if="showStatsPanel" class="action-group selection-stats-group">
        <div class="group-header">
          <el-icon><DataAnalysis /></el-icon>
          <span class="group-title">选中区域统计</span>
          <el-tag
            size="small"
            :type="stats.selectionType === 'column' ? 'info' : 'success'"
          >
            {{ stats.selectionType === 'column' ? '整列' : '区域' }}
          </el-tag>
        </div>
        <div class="stats-content">
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-label">单元格数:</span>
              <span class="stat-value">{{ stats.rowCount }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">数值:</span>
              <span class="stat-value">{{ stats.numericCount }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">总和:</span>
              <span class="stat-value">{{ stats.sum }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">平均值:</span>
              <span class="stat-value">{{ stats.average }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">最大值:</span>
              <span class="stat-value">{{ stats.max }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">最小值:</span>
              <span class="stat-value">{{ stats.min }}</span>
            </div>
          </div>
          <el-button
            size="small"
            type="info"
            link
            @click="clearSelection"
            title="清除选择"
            class="clear-btn"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 当前单元格信息组 - 单行分块展示 -->
    <div v-if="showCellContent && selectedCell.position" class="action-group current-cell-group compact-single-row">
      <div class="group-header">
        <el-icon><Position /></el-icon>
        <span class="group-title">当前单元格</span>
      </div>

      <div class="single-row-content">
        <!-- 第一块：基本信息 -->
        <div class="info-block basic-info">
          <!-- 位置 -->
          <el-tag size="small" type="info" class="cell-position">
            <el-icon><Position /></el-icon>
            {{ selectedCell.position }}
          </el-tag>

          <!-- 类型 -->
          <el-tag
            size="small"
            :type="getCellTypeTag(selectedCell.type)"
            class="cell-type"
          >
            {{ selectedCell.type }}
          </el-tag>

          <!-- 修改状态 -->
          <el-tag
            v-if="selectedCell.isModified"
            size="small"
            type="danger"
            class="cell-modified"
          >
            <el-icon><Edit /></el-icon>
          </el-tag>
        </div>

        <!-- 分隔线 -->
        <div class="separator"></div>

        <!-- 第二块：内容 -->
        <div class="info-block cell-content-block">
          <div
            class="cell-content-display"
            :class="{
              'numeric-cell': selectedCell.isNumeric,
              'formula-cell': selectedCell.isFormula,
              'modified-cell': selectedCell.isModified,
              'invalid-number': selectedCell.isNumeric && !selectedCell.isValidNumber,
              'empty-cell': selectedCell.isEmpty
            }"
            :title="`${selectedCell.content || '[空]'} (${selectedCell.charCount}字符)`"
          >
            <span class="content-text">{{ selectedCell.content || '[空]' }}</span>
            <span v-if="selectedCell.charCount > 0" class="char-count">
              ({{ selectedCell.charCount }})
            </span>
          </div>
        </div>

        <!-- 分隔线 -->
        <div class="separator"></div>

        <!-- 第三块：状态信息 -->
        <div class="info-block status-info">
          <!-- 验证状态 -->
          <div v-if="selectedCell.isNumeric && selectedCell.numberValidationMsg"
               class="status-item validation-status"
               :class="selectedCell.isValidNumber ? 'valid' : 'invalid'">
            <el-icon v-if="selectedCell.isValidNumber"><Check /></el-icon>
            <el-icon v-else><Warning /></el-icon>
            <span class="status-text">{{ selectedCell.numberValidationMsg }}</span>
          </div>

          <!-- 日期类型 -->
          <div v-if="selectedCell.type === '日期'" class="status-item date-status">
            <el-icon><Calendar /></el-icon>
            <span class="status-text">日期</span>
          </div>

          <!-- 格式信息 -->
          <div v-if="selectedCell.format && selectedCell.format !== '文本'"
               class="status-item format-info">
            <el-icon><Document /></el-icon>
            <span class="status-text">{{ selectedCell.format }}</span>
          </div>

          <!-- 只读状态 -->
          <div v-if="selectedCell.isReadOnly" class="status-item readonly-status">
            <el-icon><Lock /></el-icon>
            <span class="status-text">只读</span>
          </div>
        </div>

        <!-- 分隔线 -->
        <div class="separator"></div>

        <!-- 第四块：操作按钮 -->
        <div class="info-block action-buttons" v-if="isEditMode && !selectedCell.isReadOnly">
          <el-button
            size="small"
            type="primary"
            link
            @click="copyCellContent"
            title="复制内容"
            class="action-btn"
          >
            <el-icon><CopyDocument /></el-icon>
          </el-button>
          <el-button
            size="small"
            type="warning"
            link
            @click="editCellInModal"
            title="编辑内容"
            class="action-btn"
          >
            <el-icon><Edit /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    </div>

    <!-- Handsontable 表格区域（保持不变） -->
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
        @after-init="onHotInit"

      />

      <div v-if="tableData.length === 0" class="empty-state">
        <el-empty description="暂无表格数据" />
      </div>

      <!-- 横向滚动提示 -->
      <div v-if="showScrollHint" class="horizontal-scroll-hint">
        ← → 可左右滚动查看完整表格
      </div>
    </div>
  </div>
</template>



<script setup>

import { registerLanguageDictionary, zhCN } from 'handsontable/i18n'
// 注册中文语言包
try {
  registerLanguageDictionary(zhCN)
  console.log('✅ 中文语言包已注册')
} catch (error) {
  console.warn('⚠️ 注册中文语言包失败，使用英文:', error.message)
}

import { watch, ref, computed, onMounted, onUnmounted, nextTick, defineEmits, defineProps } from 'vue'

import { HotTable } from '@handsontable/vue3'
import 'handsontable/dist/handsontable.full.css'
import {
  Download, Edit, Check, Warning, DataAnalysis, Close, More, Menu, Document,
  Grid, InfoFilled, Position, CopyDocument, Lock, Calendar, Finished, MagicStick, Bug
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 导入组合式函数
import useExcelTable from './useExcelTable.js'
import useExcelData from './useExcelData.js'
import useExcelEdit from './useExcelEdit.js'
import useExcelSelection from './useExcelSelection.js'
import Handsontable from 'handsontable'

// 导入工具函数
import {
  setupChineseLocalization,
  validateNumberFormat,
  isDateString,
  getCellTypeTag,
  formatNumber
} from './excel-utils.js'


// 实例一创建就暴露
const onHotInit = () => {
  const hot = hotTable.value?.hotInstance
  if (hot && !hot.isDestroyed) {
    window.__excelHotInstance = hot
    console.log('⚡ Handsontable 实例已立即暴露', hot)
  }
}

// ============ Props ============
const emit = defineEmits([
  'cell-changed',
  'data-changed',
  'edit-status-changed',
  'cell-change',
  'instance-ready'
])


// 2. 修改 handleCellChangeFromEdit 函数
const handleCellChangeFromEdit = (cellInfo) => {
  console.log('📤 收到单元格修改:', {
    行: cellInfo.row,
    列: cellInfo.col,
    旧值: cellInfo.oldValue,
    新值: cellInfo.newValue
  })

  // 发送原有事件（保持兼容）
  emit('cell-changed', {
    row: cellInfo.row,
    col: cellInfo.col,
    oldValue: cellInfo.oldValue,
    newValue: cellInfo.newValue,
    source: cellInfo.source,
    timestamp: cellInfo.timestamp,
    cellKey: cellInfo.cellKey
  })

  // 新增：发送给 sheetStateManager 的事件（关键！）
  emit('cell-change', {
    changes: [[cellInfo.row, cellInfo.col, cellInfo.oldValue, cellInfo.newValue]],
    sheetName: props.sheetName,
    pdfId: props.pdfId,
    excelFileName: props.excelFileName,
    source: cellInfo.source,
    timestamp: cellInfo.timestamp
  })

  // 发送数据变化汇总事件
  const hot = getSafeHotInstance()
  if (hot) {
    const allChanges = []
    modifiedCells.value.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      const value = hot.getDataAtCell(row, col)
      allChanges.push({ row, col, value, cellKey })
    })

    emit('data-changed', {
      totalChanges: modifiedCells.value.size,
      hasChanges: hasChanges.value,
      allChanges: allChanges,
      modifiedCellsCount: modifiedCells.value.size
    })
  }
}



// 3. 生成列宽
const colWidths = computed(() =>
  Array.from({ length: tableData.value[0]?.length || 0 }, (_, i) =>
    i === 0 ? 180 : 120
  )
)


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
  calculateHeight,
  getSafeHotInstance,
  isHotInstanceValid,
  setupEventListeners,
  safeSetTimeout,
  safeAsyncOperation,
  cleanup,
} = useExcelTable(props)


const showEmptyCellsHighlight = ref(false)
const emptyCellsHighlightEnabled = ref(false)

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

  // ============ 缺少这些导入 ============
  detectEmptyCells,  // 确保这个被导入
  hasEmptyCells,     // 确保这个被导入
  emptyCellsStats
// 确保这个被导入
} = useExcelData(props)

// 3. 修改 useExcelEdit 的初始化，传入回调
// 在 useExcelTable 导入后，添加一个增强版的 getSafeHotInstance
const getEnhancedHotInstance = () => {
  // 先尝试使用导入的 getSafeHotInstance
  const instance = getSafeHotInstance()

  if (instance) {
    // 验证实例是否有效
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

// 3. 修改 useExcelEdit 的初始化，传入回调
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
  // ============ 新增导入 ============
  checkInstanceHealth,
  refreshCache,
  clearCache,
  validateHotInstance,
  getHotInstance: getHotInstanceFromHook
} = useExcelEdit(getEnhancedHotInstance, handleCellChangeFromEdit)


// 选择统计
const {
  showStatsPanel,
  stats,
  currentSelection,
  calculateSelectionStats,
  clearSelection,
  setupColumnSelectionListener
} = useExcelSelection(getSafeHotInstance)


// 进入编辑模式后一次性标红所有历史修改
const markAllModifiedRed = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  const allModified = Array.from(modifiedCells.value) // modifiedCells 是 useExcelEdit 里的 Set
  const cellMeta = []

  allModified.forEach(key => {
    const [row, col] = key.split(',').map(Number)
    cellMeta.push({ row, col, className: 'cell-modified-red' })
  })

  hot.updateSettings({ cell: cellMeta }, false)
  hot.render()
}

// 组件自己的 toggleEditMode 函数
const toggleEditMode = () => {
  console.log('🔘 编辑按钮被点击')

  // 可选：先检查实例健康（如果函数存在）
  if (checkInstanceHealth) {
    try {
      const health = checkInstanceHealth()
      console.log('🔍 实例健康检查:', health)
    } catch (error) {
      console.warn('⚠️ 健康检查失败，但继续:', error)
    }
  } else {
    console.log('ℹ️ checkInstanceHealth 函数不存在，跳过检查')
  }

  // 调用 hook 中的 toggleEditMode
  toggleEditModeFromHook((message, type) => {
    console.log('回调:', message, type)

    // 显示消息
    if (message && type) {
      if (type === 'success') {
        ElMessage.success(message)
      } else if (type === 'info') {
        ElMessage.info(message)
      } else if (type === 'error') {
        ElMessage.error(message)
      } else if (type === 'warning') {
        ElMessage.warning(message)
      }
    }

    // 2. 一次性标红所有历史修改
    nextTick(() => markAllModifiedRed())

    // 切换后可选：验证实例（如果函数存在）
    if (checkInstanceHealth) {
      setTimeout(() => {
        try {
          const health = checkInstanceHealth()
          console.log('✅ 切换后实例健康检查:', health)
        } catch (error) {
          console.warn('⚠️ 切换后健康检查失败:', error)
        }
      }, 100)
    }


  })
}

// 保持 computedColumns 不变
const computedColumns = computed(() => {
  const baseColumns = columns.value
  if (!baseColumns || baseColumns.length === 0) {
    return []
  }

  return baseColumns.map((col, index) => ({
    ...col,
    readOnly: !isEditMode.value
  }))
})

const testCellStyles = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  // 测试：修改一个单元格
  hot.setDataAtCell(0, 0, '测试修改')
  ElMessage.success('测试修改已完成，检查单元格颜色')
}


// 语言相关
const currentLanguage = ref('zh-CN')
const langKey = ref('zh-CN-' + Date.now())

// ============ 单元格显示相关 ============

const showCellContent = ref(false)
const selectedCell = ref({
  row: null,
  col: null,
  position: '',
  content: '',
  type: '未知',
  charCount: 0,
  lineCount: 1,
  format: '',
  isModified: false,
  isReadOnly: false,
  isNumeric: false,
  isFormula: false,
  isValidNumber: false,
  numberValidationMsg: '',
  validationDetails: ''
})


// 检查空白单元格
const toggleEmptyCellsHighlight = () => {
  // 如果已经在高亮状态，则清除
  if (showEmptyCellsHighlight.value) {
    clearEmptyCellsHighlight()
    showEmptyCellsHighlight.value = false
    ElMessage.info('已隐藏空白单元格高亮')
  } else {
    // 否则应用高亮
    highlightEmptyCells()
    showEmptyCellsHighlight.value = true
    ElMessage.success('已高亮显示空白单元格')
  }
}



// 添加空白单元格详情显示方法
const showEmptyCellsDetail = () => {
  if (emptyCellsStats.value) {
    ElMessageBox.info({
      title: '空白单元格详情',
      message: `
        <div style="text-align: left; font-size: 13px;">
          <p><strong>总数:</strong> ${emptyCellsStats.value.total} 个</p>
          <p><strong>分布:</strong> ${emptyCellsStats.value.rowsWithEmptyCells}行, ${emptyCellsStats.value.colsWithEmptyCells}列</p>
          <p><strong>范围:</strong> 行${emptyCellsStats.value.minRow + 1}-${emptyCellsStats.value.maxRow + 1},
          列${emptyCellsStats.value.minCol + 1}-${emptyCellsStats.value.maxCol + 1}</p>
        </div>
      `,
      dangerouslyUseHTMLString: true,
      customClass: 'empty-cells-detail-modal'
    })
  }
}



const highlightEmptyCells = () => {
  const hot = getSafeHotInstance()
  if (!hot || !hasEmptyCells.value) {
    console.warn('❌ 无法高亮空白单元格：实例无效或无空白单元格')
    return
  }

  console.log('🎨 开始高亮空白单元格...')

  try {
    const emptyCells = detectEmptyCells.value
    const cellConfig = []

    // 获取当前的单元格配置
    const currentCellConfig = hot.getSettings().cell || []

    // 创建新的配置，保留非空白样式
    const newCellConfig = currentCellConfig.filter(config =>
      !config.className || !config.className.includes('empty-cell')
    )

    // 为每个空白单元格添加样式
    emptyCells.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)

      // 确保行和列在有效范围内
      if (row < hot.countRows() && col < hot.countCols()) {
        newCellConfig.push({
          row: row,
          col: col,
          className: 'empty-cell highlighted'  // 添加 highlighted 类名
        })

        console.log(`➕ 高亮空白单元格: [${row},${col}]`)
      }
    })

    // 应用新的配置
    hot.updateSettings({
      cell: newCellConfig
    })

    // 强制重新渲染
    hot.render()
    emptyCellsHighlightEnabled.value = true

    console.log('✅ 空白单元格高亮已应用:', {
      空白单元格数: emptyCells.size,
      样式规则数: newCellConfig.length
    })

  } catch (error) {
    console.error('❌ 高亮空白单元格失败:', error)
  }
}


const clearEmptyCellsHighlight = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  try {
    const currentCellConfig = hot.getSettings().cell || []

    // 过滤掉空白单元格样式
    const filteredConfig = currentCellConfig.filter(config =>
      !config.className || !config.className.includes('empty-cell')
    )

    hot.updateSettings({
      cell: filteredConfig
    })

    hot.render()
    emptyCellsHighlightEnabled.value = false

    console.log('✅ 空白单元格高亮已清除')

  } catch (error) {
    console.error('❌ 清除空白单元格高亮失败:', error)
  }
}


// 计算单元格位置（直接从原文件复制）
const calculateCellPosition = (row, col) => {
  if (row === null || col === null) return ''

  let columnName = ''
  let columnIndex = col

  while (columnIndex >= 0) {
    columnName = String.fromCharCode(65 + (columnIndex % 26)) + columnName
    columnIndex = Math.floor(columnIndex / 26) - 1
  }

  const rowNumber = row + 1
  return `${columnName}${rowNumber}`
}

// 在 HandsontableExcelViewer.vue 的 methods 区域添加或修改
const setupCellSelectionListener = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    console.warn('❌ 表格实例无效，无法设置选择监听器')
    return
  }

  console.log('🔗 设置单元格选择监听器...')

  // 清除旧的监听器（如果有）
  try {
    hot.removeHook('afterSelection')
  } catch (e) {
    // 忽略错误
  }

  // 绑定新的选择监听器
  hot.addHook('afterSelection', (startRow, startCol, endRow, endCol, selectionLayerLevel) => {
    console.log('🎯 单元格选择事件触发:', {
      startRow, startCol, endRow, endCol,
      是否为单个单元格: startRow === endRow && startCol === endCol
    })

    // 如果是单个单元格选择
    if (startRow === endRow && startCol === endCol) {
      updateSelectedCellDisplay(startRow, startCol)
    } else {
      // 如果是区域选择，可以隐藏单元格显示区域
      showCellContent.value = false
    }
  })

  console.log('✅ 单元格选择监听器已配置')
}


// 在 HandsontableExcelViewer.vue 中替换现有的 setupCompleteSelectionListener 函数
const setupCompleteSelectionListener = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    console.warn('❌ 表格实例无效，无法设置选择监听器')
    return
  }

  // 清除旧的监听器（如果有）
  try {
    hot.removeHook('afterSelection')
  } catch (e) {
    // 忽略错误
  }

  // 设置新的选择监听器
  hot.addHook('afterSelection', (startRow, startCol, endRow, endCol, preventScrolling, selectionLayerLevel) => {

    // 单个单元格选择
    if (startRow === endRow && startCol === endCol) {
      // 显示单元格详细信息
      updateSelectedCellDisplay(startRow, startCol)
      showStatsPanel.value = false // 隐藏统计面板
      showCellContent.value = true // 显示单元格详情
    } else {
      // 区域选择：显示统计信息
      calculateSelectionStats(startRow, startCol, endRow, endCol)
      showCellContent.value = false // 隐藏单元格详情
      showStatsPanel.value = true // 显示统计面板
    }
  })

}


// 更新选中单元格显示（增强空白单元格检测）
const updateSelectedCellDisplay = (row, col) => {

  // 新增：立即拦截非法坐标
  if (
    row == null ||
    col == null ||
    row < 0 ||
    col < 0 ||
    !Number.isInteger(row) ||
    !Number.isInteger(col)
  ) {
    console.warn('🚫 非法单元格坐标', { row, col });
    return;
  }

  const hot = getSafeHotInstance()
  if (!hot) {
    showCellContent.value = false
    return
  }

  // 检查是否为有效的选择
    if (row === null || col === null) {
      console.warn('⚠️ 无效的单元格坐标')
      showCellContent.value = false
      return
    }



  try {
    const content = hot.getDataAtCell(row, col)
    const cellMeta = hot.getCellMeta(row, col)

    const contentStr = content !== null && content !== undefined ? String(content) : ''
    const charCount = contentStr.length
    const lineCount = contentStr.split('\n').length

    // ============ 增强空白单元格检测 ============
    const isEmpty = (value) => {
      // 1. 基本空值检测
      if (value === null || value === undefined) {
        return true
      }

      // 2. 字符串类型检测
      if (typeof value === 'string') {
        const trimmed = value.trim()

        // 空字符串
        if (trimmed === '') {
          return true
        }

        // 各种空值表示
        const emptyPatterns = [
          'null', 'NULL', 'Null',
          'nan', 'NaN', 'NAN', 'Nan',
          'none', 'None', 'NONE',
          'n/a', 'N/A', 'na', 'NA',
          '空', '空白', '空缺', '缺省',
          'undefined', 'Undefined', 'UNDEFINED',
          ' ', '\t', '\n', '\r' // 纯空白字符
        ]

        // 检查是否匹配空值模式
        if (emptyPatterns.includes(trimmed.toLowerCase())) {
          return true
        }

        // 检查是否全是空白字符
        if (/^\s+$/.test(trimmed)) {
          return true
        }

        // 检查是否包含特定占位符
        const placeholderPatterns = [
          '--', '---', '____', '####', '****',
          'null', 'NULL', 'nan', 'NaN'
        ]

        if (placeholderPatterns.includes(trimmed)) {
          return true
        }
      }

      // 3. 数字类型特殊检测
      if (typeof value === 'number') {
        // NaN 被认为是空值
        if (isNaN(value)) {
          return true
        }
        // 某些情况下，0可能被视为空值（根据业务需求）
        // 如果需要，可以添加：if (value === 0) return true
      }

      return false
    }

    // 判断是否为空单元格
    const isActuallyEmpty = isEmpty(content)
    // ============ 空白检测结束 ============

    // 判断单元格类型
    let cellType = '未知'
    let dataFormat = '文本'
    let isNumeric = false
    let isFormula = false
    let isValidNumber = false
    let numberValidationMsg = ''
    let validationDetails = ''

    // 如果是空值，需要确定具体的空值类型
    let emptyType = ''
    let emptyReason = ''

    if (isActuallyEmpty) {
      cellType = '空值'

      // 确定空值类型
      if (content === null) {
        emptyType = 'null'
        emptyReason = '原生 null 值'
      } else if (content === undefined) {
        emptyType = 'undefined'
        emptyReason = '未定义'
      } else if (typeof content === 'string') {
        const trimmed = content.trim()
        if (trimmed === '') {
          emptyType = 'empty_string'
          emptyReason = '空字符串'
        } else if (['null', 'NULL', 'Null'].includes(trimmed)) {
          emptyType = 'null_string'
          emptyReason = '文本 null'
        } else if (['nan', 'NaN', 'NAN', 'Nan'].includes(trimmed)) {
          emptyType = 'nan_string'
          emptyReason = '文本 NaN'
        } else if (['none', 'None', 'NONE'].includes(trimmed)) {
          emptyType = 'none_string'
          emptyReason = '文本 None'
        } else if (['n/a', 'N/A', 'na', 'NA'].includes(trimmed)) {
          emptyType = 'na_string'
          emptyReason = '文本 N/A'
        } else if (/^\s+$/.test(trimmed)) {
          emptyType = 'whitespace'
          emptyReason = '纯空白字符'
        } else {
          emptyType = 'other_empty'
          emptyReason = `其他空值: "${trimmed}"`
        }
      } else if (typeof content === 'number' && isNaN(content)) {
        emptyType = 'nan_number'
        emptyReason = '数字 NaN'
      }

      dataFormat = emptyReason

    } else if (typeof content === 'string') {
      const trimmed = content.trim()

      if (trimmed.startsWith('=')) {
        cellType = '公式'
        isFormula = true
        dataFormat = '计算'
      } else if (trimmed === 'TRUE' || trimmed === 'FALSE' || trimmed === 'true' || trimmed === 'false') {
        cellType = '布尔'
        dataFormat = '逻辑'
      } else if (isDateString(trimmed)) {
        cellType = '日期'
        dataFormat = '日期'
      } else {
        const numericValue = parseFloat(trimmed)
        const isNumericString = !isNaN(numericValue) && isFinite(numericValue)

        if (isNumericString) {
          if (/^\d{4}$/.test(trimmed) && trimmed >= '1900' && trimmed <= '2100') {
            cellType = '日期'
            dataFormat = '年份'
          } else if (/^\d{8}$/.test(trimmed)) {
            // 检查是否是有效日期
            const year = parseInt(trimmed.substring(0, 4), 10)
            const month = parseInt(trimmed.substring(4, 6), 10)
            const day = parseInt(trimmed.substring(6, 8), 10)
            if (year >= 1900 && year <= 2100 && month >= 1 && month <= 12 && day >= 1 && day <= 31) {
              cellType = '日期'
              dataFormat = '日期数字'
            } else {
              cellType = '数字'
              dataFormat = '数值'
            }
          } else {
            cellType = '数字'
            dataFormat = '数值'
            isNumeric = true
            const validationResult = validateNumberFormat(trimmed)
            isValidNumber = validationResult.isValid
            numberValidationMsg = validationResult.message
            validationDetails = validationResult.details || ''
          }
        } else {
          cellType = '文本'
        }
      }
    } else if (typeof content === 'number' && !isNaN(content) && isFinite(content)) {
      if (content >= 1900 && content <= 2100 && content % 1 === 0) {
        cellType = '日期'
        dataFormat = '年份'
      } else {
        cellType = '数字'
        dataFormat = '数值'
        isNumeric = true
        isValidNumber = true
        numberValidationMsg = '✅ 格式正确'
        validationDetails = '原生数字类型'
      }
    } else if (content instanceof Date) {
      cellType = '日期'
      dataFormat = '日期对象'
    }

    const cellKey = `${row},${col}`
    const isModified = modifiedCells.value.has(cellKey)
    const formatInfo = cellMeta?.format || ''
    const isReadOnly = cellMeta?.readOnly || false

    // 构建选中单元格对象
    selectedCell.value = {
      row,
      col,
      position: calculateCellPosition(row, col),
      content: contentStr,
      type: cellType,
      charCount,
      lineCount,
      format: formatInfo,
      isModified,
      isReadOnly,
      isNumeric,
      isFormula,
      isValidNumber,
      numberValidationMsg,
      validationDetails,

      // 新增空白单元格相关属性
      isEmpty: isActuallyEmpty,
      emptyType: emptyType,
      emptyReason: emptyReason,
      // isEmptyFromDetection: detectEmptyCells.value?.has(cellKey) || false,
      isEmptyFromDetection: detectEmptyCells.value ? detectEmptyCells.value.has(cellKey) : false,

      // 原始值（用于调试）
      rawValue: content,
      rawType: typeof content,

      inDualHeader: hasDualHeaders.value,
      ...(hasDualHeaders.value && {
        headerInfo: {
          isTopLeft: row === 0 && col === 0,
          isHorizontalHeader: row === 0 && col > 0,
          isVerticalHeader: row > 0 && col === 0
        }
      })
    }

    showCellContent.value = true

    nextTick(() => {
      const contentDisplay = document.querySelector('.cell-content-display')
      if (contentDisplay) {
        contentDisplay.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
    })

  } catch (error) {
    console.warn('⚠️ 获取单元格内容失败:', error)
    showCellContent.value = false
  }
}


// 复制单元格内容（直接从原文件复制）
const copyCellContent = () => {
  if (selectedCell.value.content) {
    navigator.clipboard.writeText(selectedCell.value.content)
      .then(() => {
        ElMessage.success('内容已复制到剪贴板')
      })
      .catch(err => {
        console.error('复制失败:', err)
        ElMessage.error('复制失败')
      })
  }
}

// 编辑单元格（直接从原文件复制）
const editCellInModal = () => {
  // 实现单元格编辑逻辑
  ElMessage.info('编辑单元格功能')
}

// ============ 事件处理 ============
const onFilter = (conditions) => {
  console.log('筛选条件:', conditions)
}


// 包装的保存更改
const saveChanges = () => {
  saveChangesInternal(async (modifiedData, totalChanges) => {
    // 调用后台API保存数据
    const response = await fetch('/api/save-excel-data', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        pdf_id: props.pdfId,
        excel_file: props.excelFileName,
        sheet_name: props.sheetName,
        modified_cells: modifiedData,
        total_changes: totalChanges
      })
    })

    if (!response.ok) {
      throw new Error(`保存失败: ${response.status}`)
    }

    const result = await response.json()
  })
}


// 在 HandsontableExcelViewer.vue 的 script 部分添加
const debugCellStyles = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    console.log('❌ 表格实例无效')
    return
  }

  console.log('=== 单元格样式调试 ===')

  // 检查已应用的样式
  const cellConfig = hot.getSettings().cell || []
  console.log('📋 当前cell配置:', cellConfig.length, '条规则')

  // 检查DOM中的样式
  const unsavedInDOM = hot.rootElement.querySelectorAll('.unsaved-modified-cell')
  const savedInDOM = hot.rootElement.querySelectorAll('.saved-modified-cell')

}


// 修复已保存单元格样式
const forceFixSavedCellsStyles = () => {
  console.log('🔧 强制修复已保存单元格样式...')

  const hot = getSafeHotInstance()
  if (!hot) return

  try {
    // 创建一个新的 cell 配置数组
    const cellConfig = []

    // 1. 先添加已保存单元格
    savedCells.value.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      cellConfig.push({
        row: row,
        col: col,
        className: 'saved-modified-cell'
      })
    })

    // 2. 再添加未保存单元格（如果有的话且是编辑模式）
    if (isEditMode.value) {
      unsavedCells.value.forEach(cellKey => {
        const [row, col] = cellKey.split(',').map(Number)
        cellConfig.push({
          row: row,
          col: col,
          className: 'unsaved-modified-cell'
        })
      })
    }

    // 3. 应用配置
    hot.updateSettings({
      cell: cellConfig
    }, false)

    // 4. 强制重新渲染
    hot.render()

    // 5. 使用 cells 渲染器作为备份
    hot.updateSettings({
      cells: function(row, col, prop) {
        const cellKey = `${row},${col}`
        const base = {}

        if (savedCells.value.has(cellKey)) {
          base.className = 'saved-modified-cell'
        }

        if (isEditMode.value && unsavedCells.value.has(cellKey)) {
          base.className = base.className ?
            `${base.className} unsaved-modified-cell` :
            'unsaved-modified-cell'
        }

        return base
      }
    })

    hot.render()

    console.log('✅ 已保存单元格样式修复完成')

    // 验证
    setTimeout(() => {
      const savedInDOM = hot.rootElement.querySelectorAll('.saved-modified-cell')
      console.log('✅ 修复后验证:', {
        DOM中已保存单元格: savedInDOM.length,
        预期数量: savedCells.value.size
      })
    }, 300)

  } catch (error) {
    console.error('❌ 修复已保存单元格样式失败:', error)
  }
}

// 批量标记多个单元格
const markMultipleCellsAsSaved = (cells) => {
  console.log('📦 markMultipleCellsAsSaved 被调用:', cells?.length || 0)

  if (!cells || !Array.isArray(cells)) {
    console.warn('❌ 参数无效')
    return { success: false, message: '参数无效' }
  }

  const savedCellKeys = []

  cells.forEach(cell => {
    if (cell.row !== undefined && cell.col !== undefined) {
      savedCellKeys.push(`${cell.row},${cell.col}`)
    } else if (typeof cell === 'string' && cell.includes(',')) {
      savedCellKeys.push(cell)
    }
  })

  return markSavedCells(savedCellKeys)
}

// 清除所有已保存标记
const clearSavedMarks = () => {
  console.log('🧹 清除所有已保存标记...')

  savedCells.value.clear()

  const hot = getSafeHotInstance()
  if (hot) {
    try {
      const currentCellConfig = hot.getSettings().cell || []
      const filteredConfig = currentCellConfig.filter(config => {
        const className = config.className || ''
        return !className.includes('saved-modified-cell')
      })

      hot.updateSettings({
        cell: filteredConfig
      }, false)

      hot.render()

      console.log('✅ 所有已保存标记已清除')
    } catch (error) {
      console.warn('⚠️ 清除已保存标记失败:', error)
    }
  }

  return { success: true, message: '已保存标记已清除' }
}

// 获取当前已保存单元格状态
const getSavedCellsState = () => {
  return {
    savedCells: Array.from(savedCells.value),
    unsavedCells: Array.from(unsavedCells.value),
    modifiedCells: Array.from(modifiedCells.value),
    count: {
      saved: savedCells.value.size,
      unsaved: unsavedCells.value.size,
      total: modifiedCells.value.size
    }
  }
}

// 调试方法
const debugSavedCells = () => {
  console.log('=== 已保存单元格调试信息 ===')

  const state = getSavedCellsState()
  console.log('📊 保存状态:', state.count)

  console.log('📋 已保存单元格详情:')
  state.savedCells.forEach((cellKey, index) => {
    console.log(`  ${index + 1}. ${cellKey}`)
  })

  const hot = getSafeHotInstance()
  if (hot) {
    const savedInDOM = hot.rootElement.querySelectorAll('.saved-modified-cell')
    console.log('🎯 DOM中的已保存单元格:', savedInDOM.length)

    // 检查样式是否应用
    state.savedCells.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      const cell = hot.getCell(row, col)
      if (cell) {
        const hasClass = cell.classList.contains('saved-modified-cell')
        console.log(`  [${row},${col}] - DOM类名: "${cell.className}"`, hasClass ? '✅' : '❌')
      }
    })
  }

  console.log('=== 调试结束 ===')
}


// 实际的表格高度计算
const actualTableHeight = computed(() => {
  if (!tableData.value || tableData.value.length === 0) {
    return 200
  }
  return tableHeight.value
})


const forceFixStyles = () => {
  console.log('🚀 强制修复所有样式')

  // 重新应用修改单元格样式
  const hot = getSafeHotInstance()
  if (hot) {
    // 先清除所有样式
    hot.updateSettings({
      cell: []
    }, false)

    // 重新渲染
    hot.render()

    // 延迟重新应用样式
    setTimeout(() => {
      // 这里应该调用 useExcelEdit.js 中的函数
      // 但我们已经在上面导入了 updateModifiedCellsStyle
      updateModifiedCellsStyle() // 现在这个函数应该可用了

      if (showEmptyCellsHighlight.value) {
        highlightEmptyCells()
      }

      console.log('✅ 强制修复完成')
    }, 200)
  }
}


// 在 HandsontableExcelViewer.vue 的 setup 函数中添加
const verifyTableInstance = () => {
  const hot = getSafeHotInstance()
  if (hot) {

    // 确保编辑模式与表格状态一致
    if (isEditMode.value && hot.getSettings().readOnly) {
      console.warn('⚠️ 表格状态不一致，正在修复...')
      hot.updateSettings({ readOnly: false }, false)
      hot.render()
    }

  } else {
    console.warn('❌ 表格实例验证失败')
  }
}


// 监听 tableData 变化
watch(() => tableData.value, () => {
  console
.log('📊 表格数据变化，重新检测空白单元格')

  // 延迟执行，确保表格已渲染
  nextTick(() => {
    if (showEmptyCellsHighlight.value) {
      highlightEmptyCells()
    }
  })
}, { deep: true })



// 在 HandsontableExcelViewer.vue 中添加监控函数
const monitorEditMode = () => {
  setInterval(() => {
    const hot = getSafeHotInstance()
    if (hot && isEditMode.value) {
      // 确保表格不在只读状态
      if (hot.getSettings().readOnly) {
        console.warn('⚠️ 检测到表格意外变为只读，正在修复...')
        hot.updateSettings({ readOnly: false }, false)
      }
    }
  }, 1000) // 每秒检查一次
}


// 监听 modifiedCells 的变化
watch(modifiedCells, (newCells, oldCells) => {
  console.log('🔄 [HandsontableExcelViewer] modifiedCells 发生变化:', {
    新数量: newCells.size,
    旧数量: oldCells?.size || 0,
    是否有增长: newCells.size > (oldCells?.size || 0),
    是否在编辑模式: isEditMode.value
  })


  // 2. 通知父组件修改状态（新增功能）
  if (newCells.size === 0) {
    // 如果没有修改了，发送清零事件
    emit('data-changed', {
      totalChanges: 0,
      hasChanges: false,
      modifiedCellsCount: 0
    })
    return
  }

  // 3. 获取表格实例来获取单元格值
  const hot = getSafeHotInstance()
  if (!hot) {
    console.warn('❌ 表格实例无效，无法获取单元格值')
    return
  }

  // 4. 收集所有修改的详细信息
  const allChanges = []

  // 找出新增的修改（用于 cell-changed 事件）
  const newKeys = oldCells ? [] : Array.from(newCells.keys())
  if (oldCells) {
    newCells.forEach(key => {
      if (!oldCells.has(key)) {
        newKeys.push(key)
      }
    })
  }

  // 遍历所有修改的单元格
  newCells.forEach(cellKey => {
    const [row, col] = cellKey.split(',').map(Number)
    try {
      const newValue = hot.getDataAtCell(row, col)

      allChanges.push({
        row,
        col,
        newValue,
        cellKey,
        timestamp: Date.now()
      })

      // 如果是新增的修改，发送单个事件
      if (newKeys.includes(cellKey)) {
        emit('cell-changed', {
          row,
          col,
          oldValue: null, // 旧值未知，但父组件可以处理
          newValue: newValue,
          source: 'watch-modifiedCells',
          timestamp: Date.now(),
          isEditMode: isEditMode.value
        })
      }
    } catch (error) {
      console.warn(`⚠️ 无法获取单元格 [${row},${col}] 的值:`, error)
    }
  })

  // 5. 发送汇总事件
  emit('data-changed', {
    totalChanges: newCells.size,
    hasChanges: true,
    allChanges: allChanges,
    modifiedCellsCount: newCells.size,
    isEditMode: isEditMode.value
  })

  console.log('📤 [HandsontableExcelViewer] 已发送修改事件:', {
    事件总数: 1 + newKeys.length, // 1个汇总事件 + 多个单个事件
    汇总事件: { totalChanges: newCells.size },
    单个事件数: newKeys.length
  })
}, { deep: true })

// 6. 监听 hasChanges 的变化，发送编辑状态事件
watch(hasChanges, (newValue, oldValue) => {
  console.log('📊 [HandsontableExcelViewer] hasChanges 变化:', {
    旧值: oldValue,
    新值: newValue
  })

  emit('edit-status-changed', {
    isEditMode: isEditMode.value,
    hasChanges: newValue,
    modifiedCellsCount: modifiedCellsCount.value,
    timestamp: Date.now()
  })
})

// 7. 监听 isEditMode 的变化
watch(isEditMode, (newValue, oldValue) => {
  console.log('🎛️ [HandsontableExcelViewer] 编辑模式变化:', {
    旧模式: oldValue,
    新模式: newValue
  })

  emit('edit-status-changed', {
    isEditMode: newValue,
    hasChanges: hasChanges.value,
    modifiedCellsCount: modifiedCellsCount.value,
    timestamp: Date.now()
  })
})

onUnmounted(() => {

  cleanup()

  // 清理全局实例
  if (window.excelViewerInstance) {
    delete window.excelViewerInstance
  }

  // 安全销毁 Handsontable 实例
  if (hotTable.value?.hotInstance && !hotTable.value.hotInstance.isDestroyed) {
    try {
      hotTable.value.hotInstance.destroy()
    } catch (error) {
      console.log('ℹ️ 清理 Handsontable 实例:', error.message)
    }
  }

})


// 在 HandsontableExcelViewer.vue 中添加
const getHotInstanceWithRetry = (maxRetries = 3, delay = 100) => {
  return new Promise((resolve) => {
    const tryGetInstance = (retryCount = 0) => {
      const instance = getEnhancedHotInstance()

      if (instance) {
        resolve(instance)
        return
      }

      if (retryCount < maxRetries) {
        setTimeout(() => tryGetInstance(retryCount + 1), delay)
      } else {
        console.warn(`❌ 获取实例失败，达到最大重试次数 ${maxRetries}`)
        resolve(null)
      }
    }
    tryGetInstance()

  })
}


const tryExpose = () => {
  const hot = hotTable.value?.hotInstance;
  if (hot && !hot.isDestroyed) {
    window.__excelHotInstance = hot;
    console.log('⚡ Handsontable 实例已主动暴露', hot);

    // ✅ 1. 补绑 afterChange（已有）
    if (!hot._afterChangeBound) {
      hot._afterChangeBound = true;
      hot.addHook('afterChange', onDataChange);
      console.log('✅ afterChange 已永久补绑');
    }

  } else {
    setTimeout(tryExpose, 200);
  }
};


const restoreCellStates = (states) => {

  if (states.savedCells) {
    savedCells.value = new Set(states.savedCells)
  }
  if (states.unsavedCells) {
    unsavedCells.value = new Set(states.unsavedCells)
  }
  if (states.modifiedCells) {
    modifiedCells.value = new Set(states.modifiedCells)
  }

  // 更新样式
  forceFixSavedCellsStyles()

  return {
    success: true,
    message: '单元格状态已恢复'
  }
}

// ============ 暴露方法 ============
defineExpose({
  exportData,
  tableData,
  verifyTableStructure,
  clearSelection,
  getSafeHotInstance,

  // 新增的保存相关方法
  markSavedCells,
  markMultipleCellsAsSaved,
  forceFixSavedCellsStyles,
  clearSavedMarks,
  getSavedCellsState,
  debugSavedCells,
  restoreCellStates,

  // 新增：编辑和实例管理方法
  toggleEditMode,
  saveChanges: saveChangesInternal,
  checkInstanceHealth: checkInstanceHealth || (() => ({ healthy: false, reason: '未定义' })),
  refreshCache: refreshCache || (() => ({ success: false, message: '未定义' })),
  validateHotInstance: validateHotInstance || (() => false),

  // 原有方法
  forceFixStyles
})


onMounted(() => {
  nextTick(() => {
    // 原有代码 …
    tryExpose();        // ← 确保执行
  });
});


/* ===== 1. 确保点击单元格时触发 ===== */
const onCellClick = (row, col) => {
  // 单点即显示
  updateSelectedCellDisplay(row, col)
  showCellContent.value = true
}

/* ===== 2. 在 Handsontable 初始化后绑事件 ===== */
const setupCellClickListener = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  // 清除旧监听，防止重复
  hot.removeHook('afterOnCellMouseDown')
  hot.addHook('afterOnCellMouseDown', (event, coords) => {
    // 只响应左键单击
    if (event.button === 0) {
      onCellClick(coords.row, coords.col)
    }
  })
}

/* ===== 3. 在表格 ready 后调用一次 ===== */
onMounted(() => {
  nextTick(() => {
    // 等待渲染完成
    const hot = getSafeHotInstance()
    if (hot) {
      setupCellClickListener()
    } else {
      // 如果还未 ready，0.3s 后再试
      setTimeout(() => setupCellClickListener(), 300)
    }
  })
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

</style>



