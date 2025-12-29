<template>
  <div class="handsontable-excel-viewer" :class="{ 'edit-mode': isEditMode }">
    <!-- 工具栏部分 -->
    <div class="excel-toolbar">
    <!-- 第一行：主要操作按钮和基本信息 -->
    <div class="toolbar-row toolbar-row-top">
      <div class="toolbar-left">
        <el-button-group size="small">
          <el-button @click="exportData" :disabled="!tableData.length">
            <el-icon><Download /></el-icon>
            导出数据
          </el-button>

          <!-- 编辑模式切换按钮 -->
          <el-button
            @click="toggleEditMode"
            :type="isEditMode ? 'success' : ''"
            :disabled="!tableData.length"
          >
            <el-icon><Edit /></el-icon>
            {{ isEditMode ? '退出编辑' : '进入编辑' }}
          </el-button>
        </el-button-group>
      </div>

      <div class="toolbar-right">
        <!-- 表头指示器 -->
        <div class="header-indicator" v-if="hasDualHeaders && tableInfo">
          <el-tag type="success" size="small">
            <el-icon><Grid /></el-icon>
            双表头表格
          </el-tag>
          <span class="indicator-text">
            结构: {{ tableInfo.横向表头 }}列 × {{ tableInfo.纵向表头 }}行
            <span v-if="tableInfo.左上角"> | 左上角: {{ tableInfo.左上角 }}</span>
          </span>
          <el-button
            size="small"
            type="info"
            link
            @click="verifyTableStructure"
            title="验证表格结构"
          >
            <el-icon><InfoFilled /></el-icon>
          </el-button>
        </div>

        <span class="data-info" v-if="tableData.length > 0">
          共 {{ tableData.length - 1 }} 行 {{ columns.length }} 列
        </span>
      </div>
    </div>

    <!-- 第二行：统计信息、空白单元格提示和状态 -->
    <div class="toolbar-row toolbar-row-bottom">
      <!-- 统计面板 -->
      <div v-if="showStatsPanel" class="stats-panel">
        <el-tag :type="stats.selectionType === 'column' ? 'info' : 'success'" size="small">
          <el-icon><DataAnalysis /></el-icon>
          {{ stats.selectionType === 'column' ? '整列统计' : '选中区域统计' }}
        </el-tag>
        <span class="stat-item">行数: {{ stats.rowCount }}</span>
        <span class="stat-item">数值: {{ stats.numericCount }}</span>
        <span class="stat-item">总和: {{ stats.sum }}</span>
        <span class="stat-item">平均值: {{ stats.average }}</span>
        <span class="stat-item">最大值: {{ stats.max }}</span>
        <span class="stat-item">最小值: {{ stats.min }}</span>
        <el-button
          v-if="stats.selectionType === 'selection'"
          size="small"
          type="primary"
          link
          @click="clearSelection"
          title="清除选择"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </div>

      <!-- 空白单元格指示器 -->
      <div v-if="hasEmptyCells" class="empty-cells-indicator">
        <el-tag type="info" size="small">
          <el-icon><InfoFilled /></el-icon>
          发现 {{ emptyCellsStats?.total || 0 }} 个空白单元格
        </el-tag>

        <el-button
          size="small"
          type="info"
          link
          @click="toggleEmptyCellsHighlight"
          :title="showEmptyCellsHighlight ? '隐藏空白单元格高亮' : '显示空白单元格高亮'"
        >
          <el-icon><View /></el-icon>
          {{ showEmptyCellsHighlight ? '隐藏' : '高亮' }}
        </el-button>

        <el-button
          v-if="isEditMode"
          size="small"
          type="warning"
          link
          @click="fillEmptyCellsWithZero"
          title="将所有空白单元格填充为0"
        >
          <el-icon><Edit /></el-icon>
          填充为0
        </el-button>
      </div>

      <!-- 选中单元格的空白提示 -->
      <div class="cell-empty" v-if="selectedCell.isEmpty && showCellContent">
        <el-tag size="small" type="info" title="此单元格为空">
          <el-icon><InfoFilled /></el-icon>
          空白单元格
        </el-tag>
      </div>

      <!-- 状态提示 -->
      <div class="status-indicators">
        <el-tag v-if="isEditMode" type="success" size="small">
          <el-icon><Edit /></el-icon>
          编辑模式
        </el-tag>
        <el-tag v-if="hasChanges" type="warning" size="small">
          <el-icon><Warning /></el-icon>
          有未保存的更改
        </el-tag>
        <span v-if="modifiedCellsCount > 0" class="modified-count">
          已修改 {{ modifiedCellsCount }} 个单元格
        </span>
      </div>

      <!-- 调试信息 -->
      <div v-if="true" class="debug-info">
        | 编辑模式: {{ isEditMode }} | 有更改: {{ hasChanges }} | 修改数: {{ modifiedCellsCount }} |
      </div>
    </div>
  </div>

    <!-- 单元格内容显示 -->
    <div class="cell-content-display" v-if="showCellContent && selectedCell.position">
      <div class="cell-info-bar">
        <div class="cell-position">
          <el-tag size="small" type="info">
            <el-icon><Position /></el-icon>
            {{ selectedCell.position }}
          </el-tag>
        </div>
        <div class="cell-type">
          <el-tag
            size="small"
            :type="getCellTypeTag(selectedCell.type)"
            :title="selectedCell.type + (selectedCell.format ? ' | ' + selectedCell.format : '')"
          >
            {{ selectedCell.type }}
            <span v-if="selectedCell.format" style="margin-left: 4px; font-size: 11px;">
              ({{ selectedCell.format }})
            </span>
          </el-tag>
        </div>

        <!-- 数字验证状态 -->
        <div class="cell-validation" v-if="selectedCell.isNumeric && selectedCell.numberValidationMsg">
          <el-tag
            size="small"
            :type="selectedCell.isValidNumber ? 'success' : 'danger'"
            :title="selectedCell.validationDetails || selectedCell.numberValidationMsg"
          >
            {{ selectedCell.numberValidationMsg }}
          </el-tag>
        </div>

        <!-- 日期类型提示 -->
        <div class="date-hint" v-if="selectedCell.type === '日期' && !selectedCell.isNumeric">
          <el-tag size="small" type="warning" :title="selectedCell.format || '日期类型'">
            <el-icon><Calendar /></el-icon>
            {{ selectedCell.format || '日期' }}
          </el-tag>
        </div>

        <!-- 修改状态 -->
        <div class="cell-modified" v-if="selectedCell.isModified">
          <el-tag size="small" type="danger" title="此单元格已被修改">
            <el-icon><Edit /></el-icon>
            已修改
          </el-tag>
        </div>
        <div class="cell-readonly" v-if="selectedCell.isReadOnly">
          <el-tag size="small" type="info" title="此单元格为只读">
            <el-icon><Lock /></el-icon>
            只读
          </el-tag>
        </div>
        <div class="cell-stats">
          <span class="stat-item" title="字符数">字符: {{ selectedCell.charCount }}</span>
          <span v-if="selectedCell.lineCount > 1" class="stat-item" title="行数">
            行数: {{ selectedCell.lineCount }}
          </span>
        </div>
      </div>

      <div class="cell-content-area">
        <div
          ref="cellContentDisplay"
          class="cell-content-text"
          :title="selectedCell.content"
          :class="{
            'numeric-cell': selectedCell.isNumeric,
            'formula-cell': selectedCell.isFormula,
            'modified-cell': selectedCell.isModified,
            'invalid-number': selectedCell.isNumeric && !selectedCell.isValidNumber
          }"
        >
          {{ selectedCell.content || '[空]' }}
        </div>
        <div class="cell-actions" v-if="isEditMode && !selectedCell.isReadOnly">
          <el-button
            size="small"
            type="primary"
            link
            @click="copyCellContent"
            title="复制内容"
          >
            <el-icon><CopyDocument /></el-icon>
          </el-button>
          <el-button
            size="small"
            type="warning"
            link
            @click="editCellInModal"
            title="编辑内容"
            v-if="selectedCell.position"
          >
            <el-icon><Edit /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- Handsontable 表格区域 -->
    <div class="excel-container" ref="excelContainer">
      <HotTable
        ref="hotTable"
        :data="tableData"
        :columns="computedColumns"
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
        @afterChange="onDataChange"
        @afterFilter="onFilter"
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

import { watch, ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { HotTable } from '@handsontable/vue3'
import 'handsontable/dist/handsontable.full.css'
import {
  Download, Edit, Check, Warning, DataAnalysis, Close,
  Grid, InfoFilled, Position, CopyDocument, Lock, Calendar
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

// ============ Props ============
const props = defineProps({
  excelData: {
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

// 编辑模式
const {
  isEditMode,
  hasChanges,
  saving,
  modifiedCellsCount,
  modifiedCells,
  toggleEditMode: toggleEditModeInternal,
  saveChanges: saveChangesInternal,
  onDataChange,
  updateTableReadOnly,
  resetChanges,
  collectModifiedData,
  updateModifiedCellsStyle
} = useExcelEdit(getSafeHotInstance)

// 选择统计
const {
  showStatsPanel,
  stats,
  currentSelection,
  calculateSelectionStats,
  clearSelection,
  setupColumnSelectionListener
} = useExcelSelection(getSafeHotInstance)

// ============ 计算属性 ============

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


const fillEmptyCellsWithZero = () => {
  const hot = getSafeHotInstance()
  if (!hot || !hasEmptyCells.value) return

  ElMessageBox.confirm(
    `确定要将所有 ${emptyCellsStats?.total || 0} 个空白单元格填充为 0 吗？`,
    '填充空白单元格',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    const emptyCells = detectEmptyCells.value
    const changes = []

    emptyCells.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      changes.push([row, col, '', '0'])
    })

    // 批量更新单元格
    hot.setDataAtCell(changes)

    // 清除高亮
    clearEmptyCellsHighlight()

    ElMessage.success(`已填充 ${emptyCells.size} 个空白单元格为 0`)

  }).catch(() => {
    console.log('用户取消填充操作')
  })
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


// 统一的选择监听器（处理单个单元格和区域选择）
const setupCompleteSelectionListener = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    console.warn('❌ 表格实例无效，无法设置选择监听器')
    return
  }

  console.log('🔗 设置完整选择监听器...')

  // 清除旧的监听器（如果有）
  try {
    hot.removeHook('afterSelection')
  } catch (e) {
    // 忽略错误
  }

  // 设置新的选择监听器
  hot.addHook('afterSelection', (startRow, startCol, endRow, endCol, preventScrolling, selectionLayerLevel) => {
    console.log('🎯 选择事件触发:', {
      startRow, startCol, endRow, endCol,
      是否为单个单元格: startRow === endRow && startCol === endCol,
      选择类型: startCol === endCol ? '单列' : '区域',
      选择大小: `${Math.abs(endRow - startRow) + 1}行 × ${Math.abs(endCol - startCol) + 1}列`
    })

    // 单个单元格选择
    if (startRow === endRow && startCol === endCol) {
      // 显示单元格详细信息
      updateSelectedCellDisplay(startRow, startCol)
      showStatsPanel.value = false // 隐藏统计面板
    } else {
      // 区域选择：显示统计信息
      calculateSelectionStats(startRow, startCol, endRow, endCol)
      showCellContent.value = false // 隐藏单元格详情
    }
  })

  // 监听数据变化（包括筛选）来更新统计
  hot.addHook('afterFilter', () => {
    console.log('🔍 筛选条件变化')
    if (currentSelection.value) {
      const { startRow, startCol, endRow, endCol } = currentSelection.value
      // 如果当前选择是区域，更新统计
      if (!(startRow === endRow && startCol === endCol)) {
        calculateSelectionStats(startRow, startCol, endRow, endCol)
      }
    }
  })

  console.log('✅ 完整选择监听器已配置')
}


// 更新选中单元格显示（增强空白单元格检测）
const updateSelectedCellDisplay = (row, col) => {
  const hot = getSafeHotInstance()
  if (!hot) {
    showCellContent.value = false
    return
  }

  console.log('🔍 更新选中单元格显示:', { row, col })

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
      isEmptyFromDetection: detectEmptyCells.value?.has(cellKey) || false,

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

    console.log('🔍 选中单元格详情:', {
      位置: selectedCell.value.position,
      内容: `"${selectedCell.value.content}"`,
      类型: selectedCell.value.type,
      原始类型: selectedCell.value.rawType,
      是否空白: selectedCell.value.isEmpty,
      空白类型: selectedCell.value.emptyType,
      空白原因: selectedCell.value.emptyReason,
      是否修改: selectedCell.value.isModified,
      是否只读: selectedCell.value.isReadOnly,
      是否数字: selectedCell.value.isNumeric,
      是否公式: selectedCell.value.isFormula
    })

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

// 包装的编辑模式切换
const toggleEditMode = () => {
  toggleEditModeInternal((message, type) => {
    if (type === 'success') {
      ElMessage.success(message)
    }
  })
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
    console.log('✅ 保存成功:', result)
  })
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



onMounted(() => {
  // 设置全局回调
  window.__onDataChange = (changes, source) => {
    if (onDataChange) {
      console.log('🎯 通过全局回调触发 onDataChange')
      onDataChange(changes, source)
    }
  }

  // 强制初始化事件监听
  setTimeout(() => {
    if (setupEventListeners) {
      setupEventListeners()
    }
  }, 500)
})

onUnmounted(() => {
  console.log('🔧 开始清理组件资源...')
  cleanup()

  // 清理全局实例
  if (window.excelViewerInstance) {
    delete window.excelViewerInstance
    console.log('✅ 全局实例已清理')
  }

  // 安全销毁 Handsontable 实例
  if (hotTable.value?.hotInstance && !hotTable.value.hotInstance.isDestroyed) {
    try {
      console.log('🔧 正在销毁 Handsontable 实例...')
      hotTable.value.hotInstance.destroy()
      console.log('✅ Handsontable 实例已安全销毁')
    } catch (error) {
      console.log('ℹ️ 清理 Handsontable 实例:', error.message)
    }
  }

  console.log('✅ 组件资源清理完成')
})

// ============ 暴露方法 ============
defineExpose({
  exportData,
  verifyTableStructure,
  clearSelection,
  getSafeHotInstance
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

.excel-toolbar {
  flex-shrink: 0;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 60px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.data-info {
  font-size: 12px;
  color: #606266;
}

.empty-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
}

/* ====================
   关键修复：恢复滚动功能
   ==================== */
.excel-container {
  flex: 1;
  min-height: 0;
  overflow: auto; /* 确保可以滚动 */
  position: relative;
  border: 1px solid #e0e0e0;
  background: white;
}

/* 给表格容器添加padding，避免内容被遮挡 */
.excel-container {
  padding-top: 1px !important; /* 微小padding避免边界问题 */
}


/* 确保 Handsontable 正常显示 */
:deep(.handsontable .wtHolder) {
  overflow: auto !important;
}

:deep(.handsontable) {
  position: relative;
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

.status-indicators {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modified-count {
  font-size: 12px;
  color: #e6a23c;
  font-weight: 500;
}

/* 确保表头文本可见 */
:deep(.ht_clone_top th) {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
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

.stats-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 12px;
  background: #f0f9ff;
  border: 1px solid #e1f5fe;
  border-radius: 6px;
  margin-right: 16px;
}

.stat-item {
  font-size: 12px;
  color: #1890ff;
  font-weight: 500;
}

.stat-item:not(:last-child)::after {
  content: "|";
  margin-left: 8px;
  color: #d9d9d9;
}

/* 确保统计面板在移动端也能正常显示 */
@media (max-width: 768px) {
  .stats-panel {
    flex-wrap: wrap;
    gap: 8px;
  }

  .stat-item::after {
    content: none !important;
  }
}

.stats-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 12px;
  background: #f0f9ff;
  border: 1px solid #e1f5fe;
  border-radius: 6px;
  margin-right: 16px;
  max-width: 600px;
  overflow: hidden;
}

.stat-item {
  font-size: 12px;
  color: #1890ff;
  font-weight: 500;
  white-space: nowrap;
}

.stat-item:not(:last-child)::after {
  content: "|";
  margin-left: 8px;
  color: #d9d9d9;
}

/* 选中区域统计的特殊样式 */
.stats-panel .el-tag[type="success"] {
  background: #f6ffed;
  border-color: #b7eb8f;
  color: #52c41a;
}

/* 清除选择按钮 */
.stats-panel .el-button {
  margin-left: 4px;
  padding: 0 4px;
}

/* 确保统计面板在移动端也能正常显示 */
@media (max-width: 768px) {
  .stats-panel {
    flex-wrap: wrap;
    gap: 8px;
    max-width: 300px;
  }

  .stat-item::after {
    content: none !important;
  }

  .stat-item {
    font-size: 11px;
  }
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

.header-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: #f0f9ff;
  border-radius: 4px;
  margin-left: 12px;
}

.indicator-text {
  font-size: 12px;
  color: #1890ff;
  font-weight: 500;
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


/* 在 <style scoped> 部分添加或检查 */
.cell-info-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;  /* 确保多行时正确换行 */
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.cell-content-area {
  padding: 12px;
}

.cell-content-text {
  min-height: 24px;
  padding: 8px;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  white-space: pre-wrap;  /* 保持换行 */
  word-break: break-word;  /* 长单词换行 */
}

/* 不同类型单元格的特殊样式 */
.cell-content-text.numeric-cell {
  font-family: 'Consolas', monospace;
  text-align: right;
}

.cell-content-text.formula-cell {
  font-style: italic;
  color: #409eff;
}

.cell-content-text.modified-cell {
  background-color: #fff2f0;
  border-color: #ffccc7;
}


/* 新增验证状态样式 */
.cell-info-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  min-height: 44px;
}

.cell-validation .el-tag {
  font-weight: bold;
  cursor: help;
  min-width: 100px;
  text-align: center;
}

/* 验证状态颜色 */
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

/* 无效数字的特殊样式 */
.cell-content-text.invalid-number {
  background-color: #fff2f0 !important;
  border-color: #ffccc7 !important;
  color: #ff4d4f;
}

/* 内容区域样式 */
.cell-content-area {
  padding: 12px;
  background: white;
}

.cell-content-text {
  min-height: 24px;
  padding: 8px;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.cell-content-text.numeric-cell {
  text-align: right;
  font-family: 'Consolas', 'Monaco', monospace;
}

.cell-content-text.formula-cell {
  font-style: italic;
  color: #1677ff;
  background-color: #f0f6ff;
}

.cell-content-text.modified-cell {
  background-color: #fff7e6;
  border-color: #ffd591;
}

/* 统计信息样式 */
.cell-stats {
  margin-left: auto;
  display: flex;
  gap: 12px;
}

.stat-item {
  font-size: 12px;
  color: #666;
  padding: 2px 6px;
  background: #f0f0f0;
  border-radius: 3px;
  cursor: default;
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

/* 内容区域样式优化 */
.cell-content-text[data-type="date"] {
  color: #fa8c16;
  background-color: #fff7e6;
  border-color: #ffd591;
}

.cell-content-text[data-type="year"] {
  color: #d48806;
  font-weight: 500;
}


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


/* 修改单元格的样式 */
:deep(.handsontable td.modified-cell) {
  background-color: #fff2e8 !important;
  border: 2px solid #ff7a45 !important;
  position: relative;
}

/* 修改标记小圆点 */
:deep(.handsontable td.modified-cell::after) {
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

/* 在 <style scoped> 部分确保有以下样式 */
:deep(.handsontable td.modified-cell) {
  background-color: #fff2e8 !important;
  border: 2px solid #ff7a45 !important;
  position: relative;
}

:deep(.handsontable td.modified-cell::after) {
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

/* 在 HandsontableExcelViewer.vue 的 <style scoped> 部分添加 */
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
:deep(.edit-mode .handsontable td.empty-cell) {
  background-color: #e6f7ff !important;
  border: 2px dotted #1890ff !important;
}

/* 编辑模式下的单元格样式 */
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

/* 修改单元格的样式 */
:deep(.handsontable td.modified-cell) {
  background-color: #fff2e8 !important;
  border: 2px solid #ff7a45 !important;
  position: relative;
}

/* 修改标记小圆点 */
:deep(.handsontable td.modified-cell::after) {
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

/* 修改单元格的样式 */
:deep(.handsontable td.modified-cell) {
  background-color: #fff2e8 !important;
  border: 2px solid #ff7a45 !important;
  position: relative;
}

/* 修改标记小圆点 */
:deep(.handsontable td.modified-cell::after) {
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

</style>





