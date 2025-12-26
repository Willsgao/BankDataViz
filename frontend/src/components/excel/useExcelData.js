// frontend/src/components/excel/useExcelData.js
import { computed } from 'vue'

export default function useExcelData(props) {
  // ============ 计算属性 ============

  // tableData 计算属性（保持与原文件完全一致）
  const tableData = computed(() => {
    if (!props.excelData || props.excelData.length === 0) {
      console.log('📊 tableData: 数据为空或长度为0')
      return []
    }

    console.log('📊 接收到的原始数据:', {
      长度: props.excelData.length,
      第一个元素类型: typeof props.excelData[0],
      第一个元素: props.excelData[0]
    })

    const firstItem = props.excelData[0]

    // 检查是否有双表头元数据（旧结构）
    if (firstItem?.__metadata?.has_dual_headers) {
      console.log('✅ 检测到双表头元数据（旧结构）')

      const metadata = firstItem.__metadata
      const dataRows = props.excelData.slice(1) // 跳过元数据

      console.log('📋 元数据详情:', {
        左上角: metadata.top_left_cell,
        横向表头数: metadata.horizontal_headers?.length,
        纵向表头数: metadata.vertical_headers?.length,
        数据行数: dataRows.length
      })

      // 关键修复：重新设计渲染逻辑
      const renderedTable = []

      // 1. 找到第一行数据（包含横向表头）
      const headerRowObj = dataRows.find(row => row?.__is_first_row)
      if (!headerRowObj) {
        console.warn('⚠️ 未找到第一行（横向表头）数据')
        return []
      }

      // 2. 构建第一行：左上角 + 横向表头
      const firstRow = []

      // 左上角单元格
      firstRow.push(headerRowObj.__top_left_cell || metadata.top_left_cell || '')

      // 横向表头（按顺序 H_1, H_2, H_3...）
      const horizontalCount = metadata.horizontal_headers?.length || 0
      for (let i = 1; i <= horizontalCount; i++) {
        const key = `H_${i}`
        const value = headerRowObj[key] ||
                     metadata.horizontal_headers?.[i-1] ||
                     ``
        firstRow.push(value || '')
      }

      renderedTable.push(firstRow)
      console.log('📊 第一行构建完成:', firstRow)

      // 3. 构建数据行：纵向表头 + 数据
      const dataRowsOnly = dataRows.filter(row => row?.__is_data_row)
      const verticalCount = metadata.vertical_headers?.length || 0

      dataRowsOnly.forEach((rowData, rowIndex) => {
        const row = []

        // 纵向表头
        const verticalHeader = rowData.__vertical_header ||
                              metadata.vertical_headers?.[rowIndex] ||
                              ``
        row.push(verticalHeader || '')

        // 数据单元格
        for (let i = 1; i <= horizontalCount; i++) {
          const key = `H_${i}`
          const value = rowData[key] ?? ''
          row.push(value)
        }

        renderedTable.push(row)

        // 调试输出前3行
        if (rowIndex < 3) {
          console.log(`📊 第 ${rowIndex + 2} 行:`, row.slice(0, 4))
        }
      })

      console.log('✅ 表格构建完成（旧结构）:', {
        总行数: renderedTable.length,
        总列数: renderedTable[0]?.length || 0,
        示例: renderedTable.slice(0, 3).map(row => row.slice(0, 4))
      })

      // ==================== 新增：添加空白行和列 ====================
      // 在数据后面添加6行空白
      for (let i = 0; i < 6; i++) {
        const blankRow = new Array(renderedTable[0]?.length || 0).fill('')
        renderedTable.push(blankRow)
      }

      // 在每行后面添加2列空白
      renderedTable.forEach(row => {
        for (let i = 0; i < 2; i++) {
          row.push('')
        }
      })
      // ==================== 结束新增 ====================

      console.log('✅ 添加空白行列后:', {
        最终行数: renderedTable.length,
        最终列数: renderedTable[0]?.length || 0
      })

      return renderedTable
    }

    // ============ 单表头逻辑 ============
    console.log('📊 单表头模式')

    // 获取表头
    let headers = []
    if (firstItem.__orderedHeaders) {
      headers = firstItem.__orderedHeaders
    } else {
      // 提取非 __ 开头的属性作为表头
      headers = Object.keys(firstItem || {}).filter(key => !key.startsWith('__'))
    }

    if (!headers.length) {
      console.warn('⚠️ 未找到表头')
      return []
    }

    // 构建数据
    const result = props.excelData.map(row => {
      return headers.map(header => {
        const value = row[header]
        // 处理可能的 null/undefined
        return value !== null && value !== undefined ? String(value) : ''
      })
    })

    console.log('📊 单表头构建完成:', {
      行数: result.length,
      列数: result[0]?.length || 0,
      表头: headers,
      第一行数据: result[0]
    })

    // ==================== 新增：单表头模式也添加空白行和列 ====================
    if (result.length > 0 && result[0].length > 0) {
      // 在数据后面添加3行空白
      for (let i = 0; i < 3; i++) {
        const blankRow = new Array(result[0].length).fill('')
        result.push(blankRow)
      }

      // 在每行后面添加3列空白
      result.forEach(row => {
        for (let i = 0; i < 3; i++) {
          row.push('')
        }
      })

      console.log('✅ 添加空白行列后:', {
        最终行数: result.length,
        最终列数: result[0]?.length || 0
      })
    }
    // ==================== 结束新增 ====================

    return result
  })

  // ============ 其他计算属性 ============

  // 双表头检测
  const hasDualHeaders = computed(() => {
    return props.excelData?.[0]?.__metadata?.has_dual_headers || false
  })


  // 在 useExcelData.js 的 return 前添加以下函数

  // 检测空白单元格
  const detectEmptyCells = computed(() => {
      if (!tableData.value || tableData.value.length === 0) {
        return new Set()
      }

      console.log('🔍 开始检测空白单元格...')
      const emptyCells = new Set()

      // 获取数据区域的大小（排除我们添加的空白行和空白列）
      const dataAreaRows = tableData.value.length - 6 // 减去我们添加的6行空白
      const dataAreaCols = tableData.value[0]?.length - 2 || 0 // 减去我们添加的2列空白

      console.log('📊 数据区域大小:', {
        数据行数: dataAreaRows,
        数据列数: dataAreaCols,
        总行数: tableData.value.length,
        总列数: tableData.value[0]?.length || 0
      })

      // 定义空值检测函数
      const isEmptyValue = (value) => {
        // 基本空值
        if (value === null || value === undefined) {
          return true
        }

        // 字符串类型
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
            'undefined', 'Undefined', 'UNDEFINED'
          ]

          // 检查是否匹配空值模式
          if (emptyPatterns.includes(trimmed.toLowerCase())) {
            return true
          }

          // 检查是否全是空白字符
          if (/^\s+$/.test(trimmed)) {
            return true
          }
        }

        // 数字类型：NaN
        if (typeof value === 'number' && isNaN(value)) {
          return true
        }

        return false
      }

      // 遍历数据区域（不包括我们添加的空白部分）
      for (let row = 0; row < dataAreaRows; row++) {
        if (row >= tableData.value.length) break

        for (let col = 0; col < dataAreaCols; col++) {
          if (col >= tableData.value[row].length) break

          const cellValue = tableData.value[row][col]

          if (isEmptyValue(cellValue)) {
            emptyCells.add(`${row},${col}`)
          }
        }
      }

      console.log('📊 空白单元格统计:', {
        总数: emptyCells.size,
        样本: Array.from(emptyCells).slice(0, 10).map(key => {
          const [r, c] = key.split(',').map(Number)
          return { row: r, col: c, value: tableData.value[r]?.[c] }
        })
      })

      return emptyCells
    })

  // 检测是否有空白单元格
  const hasEmptyCells = computed(() => {
    return detectEmptyCells.value.size > 0
  })

  // 获取空白单元格统计
  const emptyCellsStats = computed(() => {
  const emptyCells = detectEmptyCells.value
  if (emptyCells.size === 0) return null

  let minRow = Infinity
  let maxRow = -Infinity
  let minCol = Infinity
  let maxCol = -Infinity

  emptyCells.forEach(cellKey => {
    const [row, col] = cellKey.split(',').map(Number)
    minRow = Math.min(minRow, row)
    maxRow = Math.max(maxRow, row)
    minCol = Math.min(minCol, col)
    maxCol = Math.max(maxCol, col)
  })

  return {
    total: emptyCells.size,
    minRow,
    maxRow,
    minCol,
    maxCol,
    rowsWithEmptyCells: new Set(Array.from(emptyCells).map(key => key.split(',')[0])).size,
    colsWithEmptyCells: new Set(Array.from(emptyCells).map(key => key.split(',')[1])).size
  }
})

  // 表格信息
  const tableInfo = computed(() => {
    if (!hasDualHeaders.value) return null

    const metadata = props.excelData[0]?.__metadata || {}
    return {
      左上角: metadata.top_left_cell || '空',
      横向表头: metadata.horizontal_headers?.length || 0,
      纵向表头: metadata.vertical_headers?.length || 0,
      数据区域: `${metadata.vertical_headers?.length || 0}行 × ${metadata.horizontal_headers?.length || 0}列`
    }
  })

  // 固定行数
  const fixedRowsTop = computed(() => {
    const firstItem = props.excelData?.[0]
    return firstItem?.__metadata?.has_dual_headers ? 1 : 0
  })

  // 固定列数
  const fixedColumnsLeft = computed(() => {
    const firstItem = props.excelData?.[0]
    return firstItem?.__metadata?.has_dual_headers ? 1 : 0
  })

  // 列配置 - 重要：这里需要传入 isEditMode
  const columns = computed(() => {
    if (!tableData.value || tableData.value.length === 0) {
      return []
    }

    const headers = tableData.value[0] || []
    console.log('🎯 生成列配置:', {
      列数: headers.length,
      表头样本: headers.slice(0, 3)
    })

    return headers.map((header, index) => ({
      data: index,
      type: 'text',
      width: 150,
      // readOnly 需要在主组件中动态设置
      readOnly: true, // 默认值，在主组件中会覆盖
      title: header || (index === 0 ? '' : `列${index}`),
      // 第一列特殊样式
      ...(index === 0 && {
        className: 'vertical-header-column',
        renderer: function(instance, td, row, col, prop, value) {
          // 这里需要 Handsontable 实例，稍后在主组件中处理
          if (window.Handsontable && window.Handsontable.renderers) {
            window.Handsontable.renderers.TextRenderer.apply(this, arguments)
            td.style.background = '#f6ffed'
            td.style.fontWeight = '600'
          }
        }
      })
    }))
  })

  // ============ 方法 ============

  // 验证表格结构
  const verifyTableStructure = () => {
    if (!hasDualHeaders.value || !tableData.value.length) return

    console.log('🔍 验证表格结构:')
    console.log('1. 表格维度:', {
      总行数: tableData.value.length,
      总列数: tableData.value[0].length,
      固定行数: fixedRowsTop.value,
      固定列数: fixedColumnsLeft.value
    })

    console.log('2. 左上角单元格:', tableData.value[0][0])
    console.log('3. 横向表头行:', tableData.value[0].slice(1, 4))
    console.log('4. 纵向表头列:', tableData.value.slice(1, 4).map(row => row[0]))
    console.log('5. 数据区域起始:', `(1,1) = ${tableData.value[1]?.[1]}`)
  }

  // 导出数据
  const exportData = () => {
    if (!tableData.value.length) return

    try {
      const headers = tableData.value[0]
      const csvContent = [
        headers.join(','),
        ...tableData.value.slice(1).map(row => row.join(','))
      ].join('\n')

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)

      link.setAttribute('href', url)
      link.setAttribute('download', `${props.sheetName || 'data'}.csv`)
      link.style.visibility = 'hidden'

      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      // 消息提示通过回调或事件触发
      if (window.__showMessage) {
        window.__showMessage('数据导出成功', 'success')
      }
    } catch (error) {
      console.error('导出数据失败:', error)
      if (window.__showMessage) {
        window.__showMessage('导出数据失败', 'error')
      }
    }
  }

  return {
    // computed
    tableData,
    hasDualHeaders,
    tableInfo,
    fixedRowsTop,
    fixedColumnsLeft,
    columns,

    // 新增的空白单元格相关
    detectEmptyCells,
    hasEmptyCells,
    emptyCellsStats,

    // methods
    verifyTableStructure,
    exportData
  }
}