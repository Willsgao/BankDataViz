import { reactive } from 'vue'

/**
 * 选中区域求和计算
 * @param {Function} getHotInstance - 获取 Handsontable 实例的函数
 * @returns {Object} 选中区域求和相关状态和方法
 */
export const useSelectionSum = (getHotInstance) => {
  const selectionSum = reactive({
    visible: true,
    total: 0,
    numericCount: 0,
    totalCells: 0,
    average: 0,
    max: 0,
    min: 0,
    selectionRange: null
  })

  const formatNumber = (value) => {
    if (typeof value !== 'number' || isNaN(value)) return '0.00'
    const parts = value.toFixed(2).split('.')
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    return parts.join('.')
  }

  const clearSelectionSum = () => {
    selectionSum.visible = true
    selectionSum.total = 0
    selectionSum.numericCount = 0
    selectionSum.totalCells = 0
    selectionSum.average = 0
    selectionSum.max = 0
    selectionSum.min = 0
    selectionSum.selectionRange = null
  }

  /**
   * 🔥🔥🔥 修复：获取所有选区（支持Ctrl多选）
   */
  const getAllSelections = () => {
    const hot = getHotInstance()
    if (!hot) return []

    try {
      const selections = hot.getSelected() || []
      console.log('🎯 获取所有选区:', selections.length, '个选区')
      return selections
    } catch (error) {
      console.error('❌ 获取选区失败:', error)
      return []
    }
  }

  /**
   * 🔥🔥🔥 修复：解析单元格数值
   */
  const parseCellValue = (cellValue) => {
    if (cellValue === null || cellValue === undefined || cellValue === '') {
      return 0
    }

    let numValue = 0

    if (typeof cellValue === 'string') {
      const isNegativeInParentheses = cellValue.startsWith('(') && cellValue.endsWith(')')

      let cleanedValue = cellValue
      if (isNegativeInParentheses) {
        cleanedValue = '-' + cellValue.replace(/[()]/g, '')
      }

      cleanedValue = cleanedValue.replace(/[^\d.-]/g, '')
      numValue = parseFloat(cleanedValue) || 0

    } else if (typeof cellValue === 'number') {
      numValue = cellValue
    }

    return numValue
  }

  /**
   * 🔥🔥🔥 修复：计算选中区域的数值总和（支持Ctrl多选）
   */
  const calculateSelectionSum = (selection) => {
    const hot = getHotInstance()
    if (!hot) return

    // 🔥🔥🔥 修复：正确获取所有选区
    const allSelections = getAllSelections()

    if (allSelections.length === 0) {
      clearSelectionSum()
      emitSelectionSumChanged(selectionSum)
      return
    }

    let total = 0
    const numericValues = []
    let totalCells = 0
    let maxVal = -Infinity
    let minVal = Infinity

    console.log('🔍 开始计算选区求和，选区数量:', allSelections.length)

    // 🔥🔥🔥 修复：正确遍历选区
    allSelections.forEach((sel, index) => {
      // 🔥🔥🔥 关键修复：确保选区坐标有效
      const startRow = Math.min(sel[0], sel[2])
      const startCol = Math.min(sel[1], sel[3])
      const endRow = Math.max(sel[0], sel[2])
      const endCol = Math.max(sel[1], sel[3])

      console.log(`📊 计算选区 ${index + 1}: R${startRow+1}C${startCol+1} 到 R${endRow+1}C${endCol+1}`)

      // 计算当前选区的数值
      for (let r = startRow; r <= endRow; r++) {
        for (let c = startCol; c <= endCol; c++) {
          totalCells++
          const cellValue = hot.getDataAtCell(r, c)
          const numValue = parseCellValue(cellValue)

          if (!isNaN(numValue) && numValue !== 0) {
            numericValues.push(numValue)
            total += numValue
            maxVal = Math.max(maxVal, numValue)
            minVal = Math.min(minVal, numValue)
          }
        }
      }
    })

    const numericCount = numericValues.length
    const avg = numericCount > 0 ? total / numericCount : 0

    // 更新统计结果
    selectionSum.visible = true
    selectionSum.total = total
    selectionSum.numericCount = numericCount
    selectionSum.totalCells = totalCells
    selectionSum.average = avg
    selectionSum.max = maxVal === -Infinity ? 0 : maxVal
    selectionSum.min = minVal === Infinity ? 0 : minVal
    selectionSum.selectionRange = allSelections[0]

    console.log('🎯 最终统计结果:', {
      选区数量: allSelections.length,
      单元格总数: totalCells,
      数值单元格: numericCount,
      总和: formatNumber(total)
    })

    emitSelectionSumChanged({
      visible: selectionSum.visible,
      total: formatNumber(selectionSum.total),
      numericCount: selectionSum.numericCount,
      totalCells: selectionSum.totalCells,
      average: formatNumber(selectionSum.average),
      max: formatNumber(selectionSum.max),
      min: formatNumber(selectionSum.min),
      range: selectionSum.selectionRange
    })
  }

  const setupSelectionSumListener = () => {
    const hot = getHotInstance()
    if (!hot) {
      console.warn('⚠️ 表格实例未就绪，无法设置选中监听器')
      return
    }

    try {
      // 监听选中变化事件
      hot.addHook('afterSelection', (row, column, row2, column2) => {
        console.log('🔥 afterSelection 事件被触发:', {row, column, row2, column2})

        setTimeout(() => {
          calculateSelectionSum({ row, column, row2, column2 })
        }, 10)
      })

      // 监听取消选中事件
      hot.addHook('afterDeselect', () => {
        console.log('🔥 afterDeselect 事件被触发')

        const remainingSelections = getAllSelections()
        if (remainingSelections.length > 0) {
          calculateSelectionSum(remainingSelections[0])
        } else {
          clearSelectionSum()
          emitSelectionSumChanged({
            visible: true,
            total: 0,
            numericCount: 0,
            totalCells: 0,
            average: 0,
            max: 0,
            min: 0
          })
        }
      })

      console.log('✅ 选中区域求和监听器已设置')
    } catch (error) {
      console.error('❌ 设置选中监听器失败:', error)
    }
  }

  const emitSelectionSumChanged = (sumData) => {
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('selection-sum-changed', {
        detail: { ...sumData }
      })
      window.dispatchEvent(event)
    }
  }

  const getFormattedValues = () => {
    return {
      total: formatNumber(selectionSum.total),
      average: formatNumber(selectionSum.average),
      max: formatNumber(selectionSum.max),
      min: formatNumber(selectionSum.min)
    }
  }

  return {
    selectionSum,
    calculateSelectionSum,
    clearSelectionSum,
    setupSelectionSumListener,
    getFormattedValues,
    formatNumber
  }
}