import { reactive } from 'vue'  // 改为 reactive

/**
 * 选中区域求和计算
 * @param {Function} getHotInstance - 获取 Handsontable 实例的函数
 * @returns {Object} 选中区域求和相关状态和方法
 */
export const useSelectionSum = (getHotInstance) => {
  // 使用 reactive 代替 ref，直接修改属性而不是替换整个对象
  const selectionSum = reactive({
    visible: false,
    total: 0,
    numericCount: 0,
    totalCells: 0,
    average: 0,
    max: 0,
    min: 0,
    selectionRange: null
  })

  /**
   * 格式化数字，保留2位小数
   * @param {number} value - 数值
   * @returns {string} 格式化后的字符串
   */
  const formatNumber = (value) => {
    if (typeof value !== 'number' || isNaN(value)) return '0.00'
    return value.toFixed(2)
  }


  /**
   * 清除选中区域求和显示
   */
  const clearSelectionSum = () => {
    selectionSum.visible = false
    selectionSum.total = 0
    selectionSum.numericCount = 0
    selectionSum.totalCells = 0
    selectionSum.average = 0
    selectionSum.max = 0
    selectionSum.min = 0
    selectionSum.selectionRange = null
  }

  /**
   * 设置选中区域监听器
   */
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
        // 延迟计算，确保选中完成
        setTimeout(() => {
          calculateSelectionSum()
        }, 10)
      })

      // 监听取消选中事件
      hot.addHook('afterDeselect', () => {
        console.log('🔥 afterDeselect 事件被触发')
        selectionSum.visible = false
      })

      console.log('✅ 选中区域求和监听器已设置')
    } catch (error) {
      console.error('❌ 设置选中监听器失败:', error)
    }
  }


  /**
     * 计算选中区域的数值总和
     */
    const calculateSelectionSum = () => {
      const hot = getHotInstance()
      if (!hot) {
        console.log('⚠️ 表格实例未就绪，无法计算选中区域')
        return
      }

      try {
        const selected = hot.getSelected()
        if (!selected || selected.length === 0) {
          selectionSum.visible = false
          return
        }

        // 处理多区域选中情况，取第一个区域
        const [startRow, startCol, endRow, endCol] = selected[0]

        // 确保行列顺序正确
        const minRow = Math.min(startRow, endRow)
        const maxRow = Math.max(startRow, endRow)
        const minCol = Math.min(startCol, endCol)
        const maxCol = Math.max(startCol, endCol)

        let total = 0
        let numericCount = 0
        let totalCells = 0
        const numericValues = []

        // 遍历选中区域的所有单元格
        for (let row = minRow; row <= maxRow; row++) {
          for (let col = minCol; col <= maxCol; col++) {
            const cellData = hot.getDataAtCell(row, col)
            totalCells++

            // 检查是否为数值
            if (cellData !== null && cellData !== undefined && cellData !== '') {
              const numValue = parseFloat(cellData)
              if (!isNaN(numValue)) {
                total += numValue
                numericCount++
                numericValues.push(numValue)
              }
            }
          }
        }

        // 如果有数值单元格，更新显示状态
        if (numericCount > 0) {
          const average = total / numericCount
          const max = numericValues.length > 0 ? Math.max(...numericValues) : 0
          const min = numericValues.length > 0 ? Math.min(...numericValues) : 0

          // 直接修改 reactive 对象的属性
          selectionSum.visible = true
          selectionSum.total = formatNumber(total)
          selectionSum.numericCount = numericCount
          selectionSum.totalCells = totalCells
          selectionSum.average = formatNumber(average)
          selectionSum.max = formatNumber(max)
          selectionSum.min = formatNumber(min)
          selectionSum.selectionRange = {
            startRow: minRow,
            startCol: minCol,
            endRow: maxRow,
            endCol: maxCol
          }

          console.log('🎯🎯 选中区域统计:', {
            总单元格数: totalCells,
            数值单元格数: numericCount,
            求和: selectionSum.total,
            平均值: selectionSum.average,
            范围: selectionSum.selectionRange
          })

          // 🔥🔥🔥 关键添加：发射事件到父组件
          emitSelectionSumChanged(selectionSum)

        } else {
          selectionSum.visible = false
          console.log('📭📭 选中区域无有效数值')

          // 无有效数值时也发射事件
          emitSelectionSumChanged({ visible: false })
        }
      } catch (error) {
        console.error('❌❌ 计算选中区域求和失败:', error)
        selectionSum.visible = false
        emitSelectionSumChanged({ visible: false })
      }
    }

    /**
     * 🔥🔥🔥 新增：发射选中区域统计事件
     */
    const emitSelectionSumChanged = (sumData) => {
      // 方式1：通过自定义事件发射
      if (typeof window !== 'undefined') {
        const event = new CustomEvent('selection-sum-changed', {
          detail: { ...sumData } // 浅拷贝避免响应式问题
        })
        window.dispatchEvent(event)
        console.log('🚀 发射 selection-sum-changed 事件:', sumData)
      }

      // 方式2：通过全局变量发射（兼容方案）
      if (typeof window !== 'undefined' && window.$selectionSumEmitter) {
        window.$selectionSumEmitter(sumData)
      }
    }



  // 返回 reactive 对象，不需要 .value
  return {
    selectionSum,  // 直接返回 reactive 对象
    calculateSelectionSum,
    clearSelectionSum,
    setupSelectionSumListener
  }
}