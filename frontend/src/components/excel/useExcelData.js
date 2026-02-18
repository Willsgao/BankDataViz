// frontend/src/components/excel/useExcelData.js
import { computed } from 'vue'

const convertObjectArrayToArray = (inputData) => {
  if (!inputData || !Array.isArray(inputData)) {
    console.log('📭 convertObjectArrayToArray: 输入为空或不是数组')
    return []
  }

  if (inputData.length === 0) {
    console.log('📭 convertObjectArrayToArray: 输入数组为空')
    return []
  }

  // 如果已经是数组数组，直接返回（但需要验证格式）
  if (Array.isArray(inputData[0])) {
    console.log('✅ convertObjectArrayToArray: 输入已经是数组数组格式')

    // 验证数组数组格式是否正确
    const isValidArrayArray = inputData.every(row => Array.isArray(row))
    if (isValidArrayArray) {
      return inputData
    } else {
      console.warn('⚠️ 数组数组格式验证失败，尝试修复')
    }
  }

  // 如果是对象数组，转换为数组数组
  if (typeof inputData[0] === 'object' && inputData[0] !== null) {

    try {
      const keys = Object.keys(inputData[0] || {})
      const result = []

      // 第一行是列名
      result.push(keys)

      // 后续行是数据
      inputData.forEach((obj, index) => {
        const row = keys.map(key => {
          const value = obj[key]
          // 统一处理空值
          if (value === null || value === undefined || value === '') {
            return ''
          }
          return String(value)
        })
        result.push(row)
      })

      return result
    } catch (error) {
      console.error('❌ convertObjectArrayToArray 转换失败:', error)
      return inputData // 出错时返回原数据
    }
  }

  console.warn('⚠️ convertObjectArrayToArray: 无法识别的数据格式，返回原数据')
  return inputData
}

export default function useExcelData(props) {

  // tableData 计算属性 - 修复版本
  const tableData = computed(() => {

  // 1. 检查数据是否存在
  if (!props.excelData) {
    console.log('📊📊 tableData: props.excelData 为 undefined')
    return []
  }

  if (!Array.isArray(props.excelData)) {
    console.warn('⚠️ tableData: props.excelData 不是数组', props.excelData)
    return []
  }

  if (props.excelData.length === 0) {
    console.log('📊📊 tableData: 数据长度为0')
    return []
  }


  const firstItem = props.excelData[0]

  // 2. 双表头逻辑
  if (firstItem?.__metadata?.has_dual_headers) {
    console.log('✅ 检测到双表头元数据（旧结构）')

    const metadata = firstItem.__metadata
    const dataRows = props.excelData.slice(1) // 跳过元数据

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
    firstRow.push(headerRowObj.__top_left_cell || '')

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

    // 🔥🔥🔥🔥 关键修复：应用格式转换
    const finalData = convertObjectArrayToArray(renderedTable)

    // 🔥🔥🔥🔥 强制验证和修复数据格式
    const validatedData = (() => {
      if (!finalData || !Array.isArray(finalData)) {
        console.error('❌❌ 数据为空或不是数组')
        return []
      }

      // 强制转换为数组数组
      if (Array.isArray(finalData[0])) {
        console.log('✅ 数据已经是数组数组格式')
        return finalData
      }

      // 如果是对象数组，强制转换
      if (typeof finalData[0] === 'object' && finalData[0] !== null) {
        console.warn('⚠️ 检测到对象数组，强制转换为数组数组')

        try {
          const keys = Object.keys(finalData[0] || {})
          const converted = [
            keys, // 第一行是表头
            ...finalData.map(obj => keys.map(key => obj[key] ?? ''))
          ]
          return converted
        } catch (error) {
          console.error('❌❌ 强制转换失败:', error)
          return finalData // 返回原数据
        }
      }

      console.error('❌❌ 无法识别的数据格式')
      return finalData
    })()
    const forceConverted = forceArrayArrayFormat(finalData)

    return forceConverted
  }

  // 3. 单表头逻辑
  let headers = []

  // 首先检查是否有 __orderedHeaders
  if (firstItem.__orderedHeaders && Array.isArray(firstItem.__orderedHeaders)) {
    headers = firstItem.__orderedHeaders
  } else {
    // 提取非 __ 开头的属性作为表头
    const allKeys = Object.keys(firstItem || {})
    headers = allKeys.filter(key => !key.startsWith('__'))
  }

  // 如果还是没有表头，创建默认表头
  if (!headers.length) {

    // 计算数据中的最大列数
    let maxColumns = 0
    for (const row of props.excelData) {
      if (row && typeof row === 'object') {
        const validKeys = Object.keys(row).filter(key => !key.startsWith('__'))
        maxColumns = Math.max(maxColumns, validKeys.length)
      }
    }

    headers = Array.from({ length: Math.max(maxColumns, 1) }, (_, i) => `列${i+1}`)
  }

  // 构建数据
  const result = props.excelData.map((row, rowIndex) => {
    return headers.map(header => {
      const value = row[header]
      // 处理可能的 null/undefined
      if (value === null || value === undefined || value === '') {
        return ''
      }
      // 确保返回字符串
      return String(value)
    })
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
  } else {
    console.warn('⚠️ 结果为空，不添加空白行列')
  }
  // ==================== 结束新增 ====================

  // 🔥🔥🔥🔥 关键修复：应用格式转换
  const finalData = convertObjectArrayToArray(result)


  // 🔥🔥🔥🔥 强制验证和修复数据格式
  const validatedData = (() => {
    if (!finalData || !Array.isArray(finalData)) {
      return []
    }

    // 强制转换为数组数组
    if (Array.isArray(finalData[0])) {
      return finalData
    }

    // 如果是对象数组，强制转换
    if (typeof finalData[0] === 'object' && finalData[0] !== null) {

      try {
        const keys = Object.keys(finalData[0] || {})
        const converted = [
          keys, // 第一行是表头
          ...finalData.map(obj => keys.map(key => obj[key] ?? ''))
        ]

        return converted
      } catch (error) {
        console.error('❌❌ 强制转换失败:', error)
        return finalData // 返回原数据
      }
    }

    console.error('❌❌ 无法识别的数据格式')
    return finalData
  })()

  const forceConverted = forceArrayArrayFormat(finalData)

  const finalDataToReturn = (() => {
      if (Array.isArray(forceConverted) && forceConverted.length > 0 && Array.isArray(forceConverted[0])) {
        return forceConverted;
      }

      if (Array.isArray(forceConverted) && forceConverted.length > 0 && typeof forceConverted[0] === 'object') {
        const keys = Object.keys(forceConverted[0] || {});
        return [
          keys,
          ...forceConverted.map(row => keys.map(key => String(row[key] || '')))
        ];
      }

      return forceConverted || [];
    })();

    return finalDataToReturn;
})


  // 在 useExcelData.js 中添加这个函数
  const forceArrayArrayFormat = (data) => {
      if (!data || !Array.isArray(data)) {
        console.log('❌ 数据无效:', { 数据存在: !!data, 是数组: Array.isArray(data) })
        return []
      }

      // 🔍 添加深度验证
      if (Array.isArray(data[0])) {
        const allRowsAreArrays = data.every(row => Array.isArray(row))

        return allRowsAreArrays ? data : []
      }

      // 对象数组转换
      if (typeof data[0] === 'object' && data[0] !== null) {
        console.warn('⚠️ 检测到对象数组，强制转换...')
        try {
          const keys = Object.keys(data[0] || {})
          const converted = [
            keys, // 表头行
            ...data.map(row => keys.map(key => String(row[key] ?? '')))
          ]

          return converted
        } catch (e) {
          console.error('❌ 转换失败:', e)
          return []
        }
      }

      console.warn('⚠️ 无法识别的数据格式')
      return []
    }

  // ============ 其他计算属性 ============
    /**
     * 智能判断表格类型
     * @param {Array} tableData - 表格数据（二维数组）
     * @returns {Object} 判断结果
     */
    const detectTableType = (data) => {
        if (!data || data.length === 0) {
            return {
                type: 'unknown',
                confidence: 0,
                reason: '空数据'
            };
        }

        // 1. 检查行标记（A列）
        const hasRowMarkers = checkRowMarkers(data);

        // 2. 检查列标记（首行）
        const hasColumnMarkers = checkColumnMarkers(data);

        // 3. 检查交叉结构
        const hasCrossStructure = checkCrossStructure(data);

        // 判断逻辑
        let result;
        if (hasRowMarkers && hasColumnMarkers && hasCrossStructure) {
            result = {
                type: 'flattened',
                confidence: 0.95,
                reason: '同时存在行标记和列标记，且具有交叉结构'
            };
        } else if (hasRowMarkers && hasColumnMarkers) {
            result = {
                type: 'flattened',
                confidence: 0.85,
                reason: '存在行标记和列标记'
            };
        } else if (hasRowMarkers) {
            result = {
                type: 'flattened',
                confidence: 0.75,
                reason: '存在行标记'
            };
        } else if (hasColumnMarkers) {
            result = {
                type: 'flattened',
                confidence: 0.70,
                reason: '存在列标记'
            };
        } else {
            result = {
                type: 'original',
                confidence: 0.90,
                reason: '无明显的行列标记，可能是原始表格'
            };
        }

        return result;
    };

    /**
     * 检查行标记（A列）
     */
    const checkRowMarkers = (data) => {
        if (!data || data.length < 2) return false;

        const firstColumn = data.map(row => row[0]).filter(val => val !== undefined && val !== '');
        if (firstColumn.length < 2) return false;

        // 行标记特征模式
        const rowMarkerPatterns = [
            /^\d+$/,           // 纯数字：1, 2, 3
            /^[A-Za-z]$/,      // 单个字母：A, B, C
            /^[A-Za-z]\d+$/,   // 字母+数字：A1, B2
            /^行\d+$/,         // 行1, 行2
            /^记录\d+$/,       // 记录1, 记录2
            /^#\d+$/,          // #1, #2
        ];

        let markerCount = 0;
        for (let i = 1; i < Math.min(firstColumn.length, 10); i++) {
            const value = String(firstColumn[i] || '').trim();
            if (rowMarkerPatterns.some(pattern => pattern.test(value))) {
                markerCount++;
            }
        }

        return markerCount >= 3; // 至少有3个行标记
    };

    /**
     * 检查列标记（首行）
     */
    const checkColumnMarkers = (data) => {
        if (!data || data.length === 0) return false;

        const firstRow = data[0];
        if (!firstRow || firstRow.length < 2) return false;

        // 列标记特征模式
        const columnMarkerPatterns = [
            /^[A-Za-z]$/,      // 单个字母
            /^[A-Za-z]\d+$/,   // 字母+数字
            /^列\d+$/,         // 列1, 列2
            /^字段\d+$/,       // 字段1, 字段2
            /^H_\d+$/,         // H_1, H_2
        ];

        let markerCount = 0;
        for (let j = 1; j < Math.min(firstRow.length, 10); j++) {
            const value = String(firstRow[j] || '').trim();
            if (columnMarkerPatterns.some(pattern => pattern.test(value))) {
                markerCount++;
            }
        }

        return markerCount >= 3; // 至少有3个列标记
    };

    /**
     * 检查交叉结构
     */
    const checkCrossStructure = (data) => {
        if (!data || data.length < 3) return false;

        let dataCellCount = 0;
        const sampleRows = Math.min(data.length, 10);
        const sampleCols = Math.min(data[0].length, 10);

        for (let i = 1; i < sampleRows; i++) {
            for (let j = 1; j < sampleCols; j++) {
                if (data[i] && data[i][j] &&
                    String(data[i][j]).trim() !== '') {
                    dataCellCount++;
                }
            }
        }

        return dataCellCount >= 5; // 至少有5个数据交叉点
    };


    // 🔥🔥🔥 修改：切换数值高亮显示
    const toggleNumericCellsHighlight = () => {
      showNumericCellsHighlight.value = !showNumericCellsHighlight.value

      if (showNumericCellsHighlight.value) {
        // 检测数值单元格
        const numericData = detectNumericCells()
        hasNumericCells.value = numericData.hasNumericCells
        numericCellsStats.value = getNumericStats()

        // 高亮显示数值单元格
        highlightNumericCells()

        ElMessage.success(`发现 ${numericData.totalNumericCells} 个数值单元格`)
      } else {
        // 清除高亮
        clearNumericCellsHighlight()
      }
    }

    // 🔥🔥🔥 新增：高亮数值单元格
    const highlightNumericCells = () => {
      const hot = getSafeHotInstance()
      if (!hot || hot.isDestroyed) return

      const { numericCells } = detectNumericCells()
      const cellConfig = numericCells.map(cell => ({
        row: cell.row,
        col: cell.col,
        className: 'numeric-cell-highlight'
      }))

      if (cellConfig.length > 0) {
        hot.updateSettings({ cell: cellConfig }, false)
        hot.render()
        console.log('✅ 数值单元格高亮已应用')
      }
    }

    // 🔥🔥🔥 新增：清除数值单元格高亮
    const clearNumericCellsHighlight = () => {
      const hot = getSafeHotInstance()
      if (!hot || hot.isDestroyed) return

      // 清除所有 numeric-cell-highlight 类
      const currentCellConfig = hot.getSettings().cell || []
      const filteredCellConfig = currentCellConfig.filter(cell =>
        cell.className !== 'numeric-cell-highlight'
      )

      hot.updateSettings({ cell: filteredCellConfig }, false)
      hot.render()
    }


    // 计算属性：当前表格类型
    const tableType = computed(() => {
        return detectTableType(tableData.value);
    });

    // 计算属性：是否应该显示扁平化模式
    const shouldShowFlatMode = computed(() => {
        return tableType.value.confidence >= 0.7 && tableType.value.type === 'flattened';
    });

    // 计算属性：智能提示信息
    const smartTip = computed(() => {
        const detection = tableType.value;
        if (detection.confidence >= 0.7) {
            return {
                title: `检测到${detection.type === 'flattened' ? '扁平化' : '原始'}表格结构`,
                description: detection.reason,
                type: detection.type,
                confidence: detection.confidence
            };
        }
        return null;
    });


  // 双表头检测
  const hasDualHeaders = computed(() => {
    return props.excelData?.[0]?.__metadata?.has_dual_headers || false
  })

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
    if (!tableData.value || tableData.value.length === 0) return []

    const headers = tableData.value[0] || []

    // 🔥 判断是否有"项目0"列（检查第一列的表头）
    const hasProjectZero = headers[0] === '项目0'

    if (hasProjectZero) {
        // 原始数据：有"项目0"和"项目"两列
        return [
            // 第 0 列："项目0"
            {
                data: 0,
                title: '项目0',
                width: 100,
                className: 'project-zero-column',
                readOnly: true
            },
            // 第 1 列："项目"
            {
                data: 1,
                title: '项目',
                width: 180,
                className: 'vertical-header-column',
                readOnly: false
            },
            // 其余列从第2列开始
            ...headers.slice(2).map((h, i) => ({
                data: i + 2,
                type: 'text',
                title: h || `列${i + 3}`,
                width: 150,
                readOnly: true
            }))
        ]
    } else {
        // 扁平化后数据：只有"项目"一列（原来的两列已合并）
        return [
            // 第 0 列："项目"（纵向表头）
            {
                data: 0,
                title: headers[0] || '项目',  // 使用实际表头
                width: 180,
                className: 'vertical-header-column',
                readOnly: false
            },
            // 其余列从第1列开始
            ...headers.slice(1).map((h, i) => ({
                data: i + 1,
                type: 'text',
                title: h || `列${i + 2}`,
                width: 150,
                readOnly: true
            }))
        ]
    }
})


  // 验证表格结构
  const verifyTableStructure = () => {
    if (!hasDualHeaders.value || !tableData.value.length) return
  }


  // 🔥🔥🔥 修改：增强的导出数据函数
const exportData = (format = 'csv') => {
  if (!tableData.value.length) {
    console.warn('⚠️ 没有数据可导出')
    return
  }

  try {
    console.log('💾💾💾💾 开始导出数据，格式:', format)

    if (format === 'csv') {
      exportToCSVWithBOM()
    } else {
      exportToExcel()
    }

  } catch (error) {
    console.error('❌❌ 导出数据失败:', error)
    // 显示错误消息
    if (window.__showMessage) {
      window.__showMessage('导出数据失败: ' + error.message, 'error')
    }
  }
}



// 🔥 前端Excel导出函数（解决Office乱码问题）- 保持原函数名
const exportToExcel = async () => {
  try {

    // 检查数据
    if (!tableData.value || tableData.value.length === 0) {
      throw new Error('没有数据可导出')
    }

    // 动态导入xlsx库
    let XLSX
    try {
      XLSX = await import('xlsx')
      console.log('✅ xlsx库加载成功')
    } catch (error) {
      console.error('❌ xlsx库加载失败:', error)
      throw new Error('Excel生成库加载失败，请检查xlsx安装')
    }

    // 准备数据（与CSV导出完全一致）
    const data = tableData.value.map(row =>
      row.map(cell => {
        if (cell === null || cell === undefined || cell === '') {
          return ''
        }
        return String(cell)
      })
    )

    // 创建工作表
    const worksheet = XLSX.utils.aoa_to_sheet(data)

    // 创建工作簿
    const workbook = XLSX.utils.book_new()
    const sheetName = props.sheetName || 'Sheet1'
    XLSX.utils.book_append_sheet(workbook, worksheet, sheetName)

    // 生成Excel二进制数据
    const excelBuffer = XLSX.write(workbook, {
      bookType: 'xlsx',
      type: 'array',
      bookSST: false  // 简化文件，不启用字符串共享
    })

    // 创建Blob并下载
    const blob = new Blob([excelBuffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    // 生成文件名
    const timestamp = new Date().toLocaleDateString('zh-CN').replace(/\//g, '')
    const fileName = `${props.sheetName || '表格数据'}_${timestamp}.xlsx`
    link.download = fileName

    // 触发下载
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    // 清理URL
    setTimeout(() => URL.revokeObjectURL(url), 100)

    // 显示成功消息
    if (typeof ElMessage !== 'undefined') {
      ElMessage.success('Excel文件导出成功（解决Office乱码）')
    }

    return {
      success: true,
      message: 'Excel文件导出成功',
      fileName: fileName,
      fileSize: blob.size,
      format: 'xlsx',
      generatedBy: 'frontend'
    }

  } catch (error) {
    console.error('❌❌ 前端Excel导出失败:', error)

    // 显示错误消息
    if (typeof ElMessage !== 'undefined') {
      ElMessage.error(`Excel导出失败: ${error.message}`)
    }

    throw error
  }
}

// 🔥 智能导出函数保持不变
const smartExport = async (format = 'excel') => {
  console.log('🎯🎯 智能导出被调用，格式:', format)

  try {
    // 检查数据
    if (!tableData.value || tableData.value.length === 0) {
      throw new Error('没有数据可导出')
    }

    let result

    if (format === 'csv') {
      // CSV导出（保持原有逻辑）
      console.log('📊 使用CSV格式导出')
      result = await exportToCSVWithBOM()
    } else {
      // Excel导出（使用新的前端生成方案）
      console.log('📊 使用Excel格式导出（解决Office乱码）')
      result = await exportToExcel()  // 🔥 保持原函数名
    }

    return result

  } catch (error) {
    console.error('❌❌ 导出失败:', error)
    throw error
  }
}

    /**
     * 检测数值单元格
     */
    const detectNumericCells = () => {
      if (!tableData.value || tableData.value.length === 0) {
        return { hasNumericCells: false, totalNumericCells: 0, numericCells: [] }
      }

      console.log('🔍🔍 开始检测数值单元格...')
      const numericCells = []

      // 遍历所有单元格
      for (let row = 0; row < tableData.value.length; row++) {
        if (!tableData.value[row]) continue

        for (let col = 0; col < tableData.value[row].length; col++) {
          const cellValue = tableData.value[row][col]

          if (isValidNumericValue(cellValue)) {
            numericCells.push({
              row,
              col,
              value: cellValue,
              formattedValue: formatNumericValue(cellValue)
            })
          }
        }
      }

      return {
        hasNumericCells: numericCells.length > 0,
        totalNumericCells: numericCells.length,
        numericCells
      }
    }

    /**
     * 验证是否为有效的数值
     */
    const isValidNumericValue = (value) => {
      if (value === null || value === undefined || value === '') {
        return false
      }

      // 字符串类型处理
      if (typeof value === 'string') {
        const trimmed = value.trim()

        // 空字符串
        if (trimmed === '') return false

        // 排除常见的非数值文本
        const nonNumericPatterns = [
          'null', 'NULL', 'Null',
          'nan', 'NaN', 'NAN', 'Nan',
          'none', 'None', 'NONE',
          'n/a', 'N/A', 'na', 'NA',
          '空', '空白', '空缺', '缺省',
          'undefined', 'Undefined', 'UNDEFINED'
        ]

        if (nonNumericPatterns.includes(trimmed.toLowerCase())) {
          return false
        }

        // 尝试转换为数字
        const num = Number(trimmed)
        return !isNaN(num) && isFinite(num)
      }

      // 数字类型
      if (typeof value === 'number') {
        return !isNaN(value) && isFinite(value)
      }

      return false
    }

    /**
     * 获取数值统计信息
     */
    const getNumericStats = () => {
      const { numericCells } = detectNumericCells()

      if (numericCells.length === 0) {
        return {
          count: 0,
          sum: 0,
          average: 0,
          max: 0,
          min: 0
        }
      }

      const values = numericCells.map(cell => {
        const num = typeof cell.value === 'string' ?
                    Number(cell.value.trim()) : cell.value
        return num
      }).filter(num => !isNaN(num) && isFinite(num))

      if (values.length === 0) {
        return {
          count: 0,
          sum: 0,
          average: 0,
          max: 0,
          min: 0
        }
      }

      const sum = values.reduce((acc, val) => acc + val, 0)
      const average = sum / values.length
      const max = Math.max(...values)
      const min = Math.min(...values)

      return {
        count: values.length,
        sum: formatNumericValue(sum),
        average: formatNumericValue(average),
        max: formatNumericValue(max),
        min: formatNumericValue(min)
      }
    }

    /**
     * 格式化数值
     */
    const formatNumericValue = (value) => {
      if (typeof value !== 'number' || isNaN(value) || !isFinite(value)) {
        return value
      }

      // 如果是整数，直接返回
      if (Number.isInteger(value)) {
        return value.toString()
      }

      // 浮点数保留2位小数
      return value.toFixed(2)
    }



        // 🔥🔥🔥 完整版：导出带BOM头的CSV文件
    const exportToCSVWithBOM = () => {
      console.log('📤📤 生成带BOM头的CSV文件...')

      try {
        // 1. 验证数据
        if (!tableData.value || tableData.value.length === 0) {
          throw new Error('没有数据可导出')
        }

        // 2. 生成CSV内容
        const csvContent = generateCSVContent()
        if (!csvContent) {
          throw new Error('生成CSV内容失败')
        }

        // 3. 🔥🔥🔥 关键：添加UTF-8 BOM头
        const BOM = '\uFEFF' // UTF-8 BOM字符
        const csvWithBOM = BOM + csvContent

        // 5. 创建Blob，指定UTF-8编码
        const blob = new Blob([csvWithBOM], {
          type: 'text/csv;charset=utf-8;'
        })

        // 6. 创建下载链接
        const link = document.createElement('a')
        const url = URL.createObjectURL(blob)

        link.setAttribute('href', url)

        // 7. 生成文件名
        const timestamp = new Date().toLocaleDateString('zh-CN').replace(/\//g, '')
        const fileName = `${props.sheetName || '表格数据'}_${timestamp}.csv`
        link.setAttribute('download', fileName)
        link.style.visibility = 'hidden'

        // 8. 触发下载
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)

        // 9. 清理URL
        setTimeout(() => {
          URL.revokeObjectURL(url)
        }, 100)

        // 10. 显示成功消息
        if (window.__showMessage) {
          window.__showMessage('CSV文件导出成功', 'success')
        }

        // 11. 🔥🔥🔥 返回导出结果用于验证
        return {
          success: true,
          fileName: fileName,
          fileSize: blob.size,
          hasBOM: csvWithBOM.charCodeAt(0) === 65279,
          bomHex: 'EF BB BF',
          downloadUrl: url,
          timestamp: Date.now()
        }

      } catch (error) {
        console.error('❌❌ CSV导出失败:', error)

        // 显示错误消息
        if (window.__showMessage) {
          window.__showMessage('CSV导出失败: ' + error.message, 'error')
        }

        // 🔥🔥🔥 返回错误结果
        return {
          success: false,
          error: error.message,
          timestamp: Date.now()
        }
      }
    }

    // 🔥🔥🔥 辅助函数：生成CSV内容（处理特殊字符）
    const generateCSVContent = () => {
      if (!tableData.value || tableData.value.length === 0) {
        console.warn('⚠️ 没有数据可生成CSV')
        return ''
      }

      try {
        const csvRows = []

        // 处理每一行数据
        tableData.value.forEach((row, rowIndex) => {
          const formattedRow = row.map((cell, colIndex) => {
            return formatCSVValue(cell, rowIndex, colIndex)
          })
          csvRows.push(formattedRow.join(','))
        })

        const csvContent = csvRows.join('\n')

        return csvContent

      } catch (error) {
        console.error('❌❌ 生成CSV内容失败:', error)
        throw error
      }
    }

    // 🔥🔥🔥 辅助函数：格式化CSV单元格值
    const formatCSVValue = (value, rowIndex, colIndex) => {
      // 处理空值
      if (value === null || value === undefined || value === '') {
        return ''
      }

      const strValue = String(value)

      // 检查是否需要引号包裹（包含逗号、换行、引号等特殊字符）
      const needsQuotes = /[",\n\r]/.test(strValue) || strValue.trim() !== strValue

      if (needsQuotes) {
        // 转义引号：将 " 替换为 ""
        const escapedValue = strValue.replace(/"/g, '""')
        return `"${escapedValue}"`
      }

      return strValue
    }

    // 🔥🔥🔥 新增：快速验证函数（在控制台运行）
    const verifyCSVExport = async () => {
      console.log('🧪🧪 开始验证CSV导出功能...')

      try {
        // 创建测试数据
        const testData = [
          ['姓名', '年龄', '城市', '备注'],
          ['张三', '25', '北京', '正常数据'],
          ['李四', '30', '上海', '包含,逗号'],
          ['王五', '28', '广州', '包含"引号"测试'],
          ['赵六', '35', '深圳', '包含\n换行符']
        ]

        // 临时替换数据
        const originalData = tableData.value
        tableData.value = testData

        const result = await exportToCSVWithBOM()

        // 恢复原数据
        tableData.value = originalData

        if (result.success) {
          console.log('✅✅ 验证通过！文件包含BOM头，应该兼容Office和WPS')
        } else {
          console.error('❌❌ 验证失败:', result.error)
        }

        return result

      } catch (error) {
        console.error('❌❌ 验证过程出错:', error)
        return {
          success: false,
          error: error.message
        }
      }
    }

    // 🔥🔥🔥 暴露验证函数到全局（开发环境使用）
    if (process.env.NODE_ENV === 'development') {
      window.verifyCSVExport = verifyCSVExport
      console.log('🔧🔧 CSV验证函数已暴露: window.verifyCSVExport()')
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
    exportData,
    smartExport,          // 🔥🔥🔥 新增：智能导出函数
    exportToCSVWithBOM,   // 🔥🔥🔥 新增：带BOM的CSV导出
    exportToExcel,        // 🔥🔥🔥 新增：Excel导出
    verifyCSVExport,      // 🔥🔥🔥 新增：验证函数

    // 新增智能判断相关导出
    detectTableType,
    tableType,
    shouldShowFlatMode,
    smartTip,
    checkRowMarkers,
    checkColumnMarkers,
    checkCrossStructure,

    // 🔥🔥🔥 修改：将空格相关改为数值相关
  detectNumericCells,           // 替换 detectEmptyCells
  isValidNumericValue,          // 新增
  getNumericStats,             // 新增
  formatNumericValue,          // 新增
  hasNumericCells: computed(() => detectNumericCells().hasNumericCells), // 替换 hasEmptyCells
  numericCellsStats: getNumericStats(), // 替换 emptyCellsStats
  }
}