// frontend\src\components\excel\useExcelViewerHelpers.js
import { ElMessage } from 'element-plus'

// 样式修复相关辅助函数
export function fixCellStyles(hot, savedCells, unsavedCells, isEditMode) {
  if (!hot) return

  const cellConfig = []

  savedCells.forEach(cellKey => {
    const [row, col] = cellKey.split(',').map(Number)
    cellConfig.push({
      row: row,
      col: col,
      className: 'saved-modified-cell'
    })
  })

  if (isEditMode) {
    unsavedCells.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      cellConfig.push({
        row: row,
        col: col,
        className: 'unsaved-modified-cell'
      })
    })
  }

  hot.updateSettings({ cell: cellConfig }, false)
  hot.render()

  return cellConfig
}

// 单元格操作相关辅助函数
export function handleCellOperations(cellKey, operation, hot) {
  const [row, col] = cellKey.split(',').map(Number)

  switch (operation) {
    case 'copy':
      return copyCellContent(row, col, hot)
    case 'edit':
      return editCell(row, col, hot)
    case 'validate':
      return validateCell(row, col, hot)
    default:
      return { success: false, message: '未知操作' }
  }
}

function copyCellContent(row, col, hot) {
  try {
    const content = hot.getDataAtCell(row, col)
    navigator.clipboard.writeText(String(content))
    ElMessage.success('内容已复制')
    return { success: true, message: '复制成功' }
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败')
    return { success: false, message: '复制失败' }
  }
}

function editCell(row, col, hot) {
  // 实现编辑逻辑
  return { success: false, message: '编辑功能未实现' }
}

function validateCell(row, col, hot) {
  // 实现验证逻辑
  return { success: false, message: '验证功能未实现' }
}

// 工具函数
export function formatCellPosition(row, col) {
  if (row == null || col == null) return ''

  let columnName = ''
  let columnIndex = col

  while (columnIndex >= 0) {
    columnName = String.fromCharCode(65 + (columnIndex % 26)) + columnName
    columnIndex = Math.floor(columnIndex / 26) - 1
  }

  return `${columnName}${row + 1}`
}

export function debounce(func, wait) {
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

// 事件发射器辅助函数
export function emitCellChanges(emit, changes, props, source = 'user') {
  if (!changes || changes.length === 0) return

  changes.forEach(change => {
    emit('cell-changed', {
      ...change,
      sheetName: props.sheetName,
      pdfId: props.pdfId,
      excelFileName: props.excelFileName,
      source,
      timestamp: Date.now()
    })
  })

  // 发送汇总事件
  emit('data-changed', {
    totalChanges: changes.length,
    hasChanges: true,
    allChanges: changes,
    modifiedCellsCount: changes.length,
    timestamp: Date.now()
  })
}