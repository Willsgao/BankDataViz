// src/composables/excel/useSelectionSum.js
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

export const useSelectionSum = (getHotInstance) => {
  // 选中区域统计状态
  const selectionSum = ref({
    visible: false,
    total: 0,
    numericCount: 0,
    totalCells: 0,
    average: 0,
    max: 0,
    min: 0,
    selectionRange: null
  })

  // 检查是否为有效数值
  const isValidNumber = (value) => {
    if (value === null || value === undefined || value === '') {
      return false
    }

    // 转换为数字
    const num = parseFloat(value)

    // 检查是否为有效数字且不是NaN
    if (isNaN(num)) {
      return false
    }

    // 检查是否为有限数字（排除Infinity）
    if (!isFinite(num)) {
      return false
    }

    return true
  }

  // 格式化数字显示
  const formatNumber = (num) => {
    if (num === 0) return '0'

    // 大数字使用千分位分隔符
    if (Math.abs(num) >= 10000) {
      return num.toLocaleString('zh-CN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    }

    // 小数字保留适当小数位
    if (Math.abs(num) < 0.01) {
      return num.toFixed(6)
    } else if (Math.abs(num) < 1) {
      return num.toFixed(4)
    } else {
      return num.toLocaleString('zh-CN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    }
  }

  // 计算选中区域的统计信息
  const calculateSelectionSum = () => {
    const hot = getHotInstance()
    if (!hot || hot.isDestroyed) {
      selectionSum.value.visible = false
      return
    }

    try {
      const selection = hot.getSelected()
      if (!selection || selection.length === 0) {
        selectionSum.value.visible = false
        return
      }

      let total = 0
      let numericCount = 0
      const numericValues = []
      let totalCells = 0
      let selectionRange = null

      // 遍历所有选中的区域
      selection.forEach(([startRow, startCol, endRow, endCol]) => {
        const rowStart = Math.min(startRow, endRow)
        const rowEnd = Math.max(startRow, endRow)
        const colStart = Math.min(startCol, endCol)
        const colEnd = Math.max(startCol, endCol)

        // 记录选择范围
        if (!selectionRange) {
          selectionRange = {
            startRow: rowStart,
            startCol: colStart,
            endRow: rowEnd,
            endCol: colEnd
          }
        }

        // 遍历选中区域的所有单元格
        for (let row = rowStart; row <= rowEnd; row++) {
          for (let col = colStart; col <= colEnd; col++) {
            totalCells++

            try {
              const cellValue = hot.getDataAtCell(row, col)

              // 检查是否为有效数值
              if (isValidNumber(cellValue)) {
                const numValue = parseFloat(cellValue)
                total += numValue
                numericCount++
                numericValues.push(numValue)
              }
            } catch (error) {
              console.warn('获取单元格数据失败:', error)
            }
          }
        }
      })

      if (numericCount > 0) {
        const average = total / numericCount
        const max = numericValues.length > 0 ? Math.max(...numericValues) : 0
        const min = numericValues.length > 0 ? Math.min(...numericValues) : 0

        selectionSum.value = {
          visible: true,
          total: formatNumber(total),
          numericCount,
          totalCells,
          average: formatNumber(average),
          max: formatNumber(max),
          min: formatNumber(min),
          selectionRange
        }

        console.log('🎯 选中区域统计:', {
          总单元格数: totalCells,
          数值单元格数: numericCount,
          求和: selectionSum.value.total,
          平均值: selectionSum.value.average,
          范围: selectionRange
        })
      } else {
        selectionSum.value.visible = false
        console.log('📭 选中区域无有效数值')
      }

    } catch (error) {
      console.error('❌ 计算选中区域求和失败:', error)
      selectionSum.value.visible = false
    }
  }

  // 清除求和显示
  const clearSelectionSum = () => {
    selectionSum.value.visible = false
  }

  // 设置选中监听器
  const setupSelectionSumListener = () => {
      const hot = getHotInstance()
      console.log('🔍 setupSelectionSumListener 被调用, hot实例:', hot) // 添加这行

      if (!hot) {
        console.warn('⚠️ 表格实例未就绪，无法设置选中监听器')
        return
      }

      try {
        // 监听选中变化事件
        hot.addHook('afterSelection', (row, column, row2, column2) => {
          console.log('🔥 afterSelection 事件被触发:', {row, column, row2, column2}) // 添加这行
          // 延迟计算，确保选中完成
          setTimeout(() => {
            calculateSelectionSum()
          }, 10)
        })

        // 监听取消选中事件
        hot.addHook('afterDeselect', () => {
          console.log('🔥 afterDeselect 事件被触发') // 添加这行
          selectionSum.value.visible = false
        })

        console.log('✅ 选中区域求和监听器已设置')
      } catch (error) {
        console.error('❌ 设置选中监听器失败:', error)
      }
    }

  return {
    selectionSum,
    calculateSelectionSum,
    clearSelectionSum,
    setupSelectionSumListener
  }
}