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
        // 监听选中变化事件 - 修复参数传递
        hot.addHook('afterSelection', (row, column, row2, column2) => {
          console.log('🔥 afterSelection 事件被触发:', {row, column, row2, column2})

          // 🔥 修复：直接传递参数，而不是从 hot.getSelected() 获取
          const selection = {
            row: row,
            column: column,
            row2: row2,
            column2: column2
          }

          // 延迟计算，确保选中完成
          setTimeout(() => {
            calculateSelectionSum(selection)
          }, 10)
        })

        // 监听取消选中事件
        hot.addHook('afterDeselect', () => {
          console.log('🔥 afterDeselect 事件被触发')
          selectionSum.visible = false
          emitSelectionSumChanged({ visible: false })
        })

        console.log('✅ 选中区域求和监听器已设置')
      } catch (error) {
        console.error('❌❌ 设置选中监听器失败:', error)
      }
    }


  /**
     * 计算选中区域的数值总和
     */
     const calculateSelectionSum = (selection) => {
      const hot = getHotInstance();
      if (!hot) return;

      const { row: startRow, column: startCol, row2: endRow, column2: endCol } = selection;

      let total = 0;
      const numericValues = [];
      let totalCells = 0;
      let maxVal = -Infinity;
      let minVal = Infinity;

      for (let r = startRow; r <= endRow; r++) {
        for (let c = startCol; c <= endCol; c++) {
          totalCells++;
          const cellValue = hot.getDataAtCell(r, c);

          // 🔥 关键修复：同时处理千分位和括号负数
          let numValue = 0;
          if (cellValue !== null && cellValue !== undefined && cellValue !== '') {
            // 处理字符串类型的数字
            if (typeof cellValue === 'string') {
              // 1. 检查是否用括号表示负数，如 (123) 或 (1,234.56)
              const isNegativeInParentheses = cellValue.startsWith('(') && cellValue.endsWith(')');

              // 2. 移除所有非数字字符（保留小数点、负号和括号用于判断）
              let cleanedValue = cellValue;

              if (isNegativeInParentheses) {
                // 如果是括号负数，移除括号并在前面加负号
                cleanedValue = '-' + cellValue.replace(/[()]/g, '');
              }

              // 3. 移除千分位逗号和其他非数字字符（保留小数点、负号）
              cleanedValue = cleanedValue.replace(/[^\d.-]/g, '');

              // 4. 解析数字
              numValue = parseFloat(cleanedValue) || 0;

            } else if (typeof cellValue === 'number') {
              // 直接使用数字类型
              numValue = cellValue;
            }
          }

          // 只处理有效的数字（排除 NaN 和 0）
          if (!isNaN(numValue) && numValue !== 0) {
            numericValues.push(numValue);
            total += numValue;
            maxVal = Math.max(maxVal, numValue);
            minVal = Math.min(minVal, numValue);

            console.log('🔢 解析单元格值:', {
              原始值: cellValue,
              解析后: numValue,
              位置: `R${r+1}C${c+1}`
            });
          }
        }
      }

      const numericCount = numericValues.length;
      const avg = numericCount > 0 ? total / numericCount : 0;

      // 更新统计结果
      selectionSum.value = {
        visible: numericCount > 0,
        total: formatNumber(total),
        numericCount,
        totalCells,
        average: formatNumber(avg),
        max: formatNumber(maxVal === -Infinity ? 0 : maxVal),
        min: formatNumber(minVal === Infinity ? 0 : minVal),
        range: { startRow, startCol, endRow, endCol }
      };

      console.log('🎯 最终统计结果:', selectionSum.value);
      emitSelectionSumChanged(selectionSum.value);
    };

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