// frontend/src/components/excel/useExcelSelection.js
import { ref } from 'vue'
import { formatNumber } from './excel-utils.js'

export default function useExcelSelection(getSafeHotInstance) {
  // ============ 状态 ============
  const showStatsPanel = ref(false)
  const stats = ref({
    selectionType: '',
    rowCount: 0,
    numericCount: 0,
    sum: 0,
    average: 0,
    max: 0,
    min: 0,
    selectionRange: null
  })

  const currentSelection = ref(null)

  // ============ 核心方法 ============

  // 计算选择统计（直接从原文件复制完整逻辑）
  const calculateSelectionStats = (startRow, startCol, endRow, endCol) => {
    const hot = getSafeHotInstance()
    if (!hot) return

    console.log('📊 开始计算选择统计:', { startRow, startCol, endRow, endCol })

    // 规范化选择区域
    const normalizedStartRow = Math.min(startRow, endRow)
    const normalizedEndRow = Math.max(startRow, endRow)
    const normalizedStartCol = Math.min(startCol, endCol)
    const normalizedEndCol = Math.max(startCol, endCol)

    console.log('📐 规范化后的选择区域:', {
      normalizedStartRow, normalizedEndRow, normalizedStartCol, normalizedEndCol,
      行数: normalizedEndRow - normalizedStartRow + 1,
      列数: normalizedEndCol - normalizedStartCol + 1
    })

    // 判断选择类型
    let selectionType = ''
    let selectedData = []

    if (normalizedStartCol === normalizedEndCol && normalizedEndRow - normalizedStartRow >= 0) {
      // 单列选择
      selectionType = 'column'
      selectedData = getFilteredColumnData(normalizedStartCol)
      console.log('🎯 识别为单列选择')
    } else if (normalizedStartRow === normalizedEndRow && normalizedStartCol === normalizedEndCol) {
      // 单个单元格选择，不显示统计
      console.log('🎯 单个单元格选择，隐藏统计面板')
      showStatsPanel.value = false
      currentSelection.value = null
      return
    } else {
      // 区域选择
      selectionType = 'selection'
      selectedData = getSelectedAreaData(normalizedStartRow, normalizedStartCol, normalizedEndRow, normalizedEndCol)
      console.log('🎯 识别为区域选择', {
        选择单元格数量: selectedData.length,
        区域: `${normalizedEndRow - normalizedStartRow + 1}行 × ${normalizedEndCol - normalizedStartCol + 1}列`
      })
    }

    // 保存当前选择信息
    currentSelection.value = {
      startRow: normalizedStartRow,
      startCol: normalizedStartCol,
      endRow: normalizedEndRow,
      endCol: normalizedEndCol,
      type: selectionType
    }

    console.log('💾 保存选择信息:', currentSelection.value)

    // 更新统计信息
    updateStatistics(selectedData, selectionType)
    showStatsPanel.value = true
  }

  // 清除选择（直接从原文件复制完整逻辑）
  const clearSelection = () => {
    const hot = getSafeHotInstance()
    if (hot) {
      hot.deselectCell()
      showStatsPanel.value = false
      currentSelection.value = null
    }
  }

  // ============ 辅助方法 ============

  // 获取选中区域数据（直接从原文件复制完整逻辑）
  const getSelectedAreaData = (startRow, startCol, endRow, endCol) => {
    const hot = getSafeHotInstance()
    if (!hot) return []

    try {
      const data = hot.getData()
      const selectedData = []

      console.log('📋 获取选中区域数据:', {
        数据总行数: data.length,
        选择区域: `${startRow}-${endRow}行, ${startCol}-${endCol}列`
      })

      // 遍历选中区域的所有单元格
      for (let row = startRow; row <= endRow; row++) {
        for (let col = startCol; col <= endCol; col++) {
          // 确保不超出数据范围
          if (row < data.length && col < (data[row]?.length || 0)) {
            const value = data[row][col]
            selectedData.push(value)
          }
        }
      }

      console.log('✅ 获取到选中数据:', {
        总单元格数: selectedData.length,
        样本数据: selectedData.slice(0, 5)
      })

      return selectedData
    } catch (error) {
      console.error('❌ 获取选中区域数据失败:', error)
      return []
    }
  }

  // 获取筛选后的列数据（直接从原文件复制完整逻辑）
  const getFilteredColumnData = (columnIndex) => {
    const hot = getSafeHotInstance()
    if (!hot) return []

    try {
      const data = hot.getData()
      const columnData = []

      // 跳过表头行（如果有）
      const startRow = hot.getSettings().colHeaders ? 1 : 0

      for (let row = startRow; row < data.length; row++) {
        if (columnIndex < data[row].length) {
          const value = data[row][columnIndex]
          columnData.push(value)
        }
      }

      return columnData
    } catch (error) {
      console.error('获取列数据失败:', error)
      return []
    }
  }

  // 更新统计信息（直接从原文件复制完整逻辑）
  const updateStatistics = (data, selectionType) => {
    if (!data || data.length === 0) {
      resetStatistics(selectionType)
      return
    }

    // 过滤出数值类型的数据
    const numericData = data
      .map(value => {
        if (value === null || value === undefined || value === '') return null
        const num = Number(value)
        return isNaN(num) ? null : num
      })
      .filter(value => value !== null)

    const totalCount = data.length
    const numericCount = numericData.length

    if (numericCount === 0) {
      resetStatistics(selectionType)
      stats.value.rowCount = totalCount
      stats.value.numericCount = 0
      return
    }

    const sum = numericData.reduce((acc, val) => acc + val, 0)
    const average = sum / numericCount
    const max = Math.max(...numericData)
    const min = Math.min(...numericData)

    stats.value = {
      selectionType: selectionType,
      rowCount: totalCount,
      numericCount: numericCount,
      sum: formatNumber(sum),
      average: formatNumber(average),
      max: formatNumber(max),
      min: formatNumber(min),
      selectionRange: currentSelection.value
    }
  }

  // 重置统计信息（直接从原文件复制完整逻辑）
  const resetStatistics = (selectionType = '') => {
    stats.value = {
      selectionType: selectionType,
      rowCount: 0,
      numericCount: 0,
      sum: 0,
      average: 0,
      max: 0,
      min: 0,
      selectionRange: null
    }
  }

  // 设置列选择监听器（直接从原文件复制完整逻辑）
  const setupColumnSelectionListener = () => {
    const hot = getSafeHotInstance()
    if (!hot) return

    // 监听选择变化事件
    hot.addHook('afterSelection', (startRow, startCol, endRow, endCol, preventScrolling, selectionLayerLevel) => {
      console.log('🎯 选择事件触发:', {
        startRow, startCol, endRow, endCol,
        选择类型: startCol === endCol ? '单列' : '区域',
        选择大小: `${Math.abs(endRow - startRow) + 1}行 × ${Math.abs(endCol - startCol) + 1}列`
      })

      calculateSelectionStats(startRow, startCol, endRow, endCol)
    })

    // 监听数据变化（包括筛选）来更新统计
    hot.addHook('afterFilter', () => {
      console.log('🔍 筛选条件变化')
      if (currentSelection.value) {
        const { startRow, startCol, endRow, endCol } = currentSelection.value
        calculateSelectionStats(startRow, startCol, endRow, endCol)
      }
    })

    console.log('✅ 选择监听器已配置')
  }

  return {
    // refs
    showStatsPanel,
    stats,
    currentSelection,

    // methods
    calculateSelectionStats,
    clearSelection,
    setupColumnSelectionListener,

    // 辅助方法（暴露给外部使用）
    getSelectedAreaData,
    getFilteredColumnData,
    updateStatistics,
    resetStatistics
  }
}