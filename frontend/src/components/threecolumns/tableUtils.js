/**
 * 从双表头数据重建原始二维表格
 * @param {Array} dualHeaderData 双表头格式的数据
 * @returns {Array} 二维表格数据
 */
export const rebuildTwoDimensionalTable111 = (dualHeaderData) => {
  if (!dualHeaderData || dualHeaderData.length === 0) {
    console.error('❌ 数据为空，无法重建')
    return []
  }

  console.log('🔧 开始重建二维表格...')

  // 打印输入数据以便调试
  console.log('📥 输入数据格式检查:')
  dualHeaderData.forEach((row, idx) => {
    if (idx < 3) { // 只打印前3行
      console.log(`  行${idx}:`, {
        类型: row.__metadata ? '元数据' : row.__is_first_row ? '表头行' : row.__is_data_row ? '数据行' : '其他',
        行表头: row.__vertical_header,
        H_1: row.H_1,
        H_2: row.H_2
      })
    }
  })

  // 步骤1：查找元数据行
  const metadataRow = dualHeaderData.find(row => row?.__metadata)
  const metadata = metadataRow?.__metadata || {}

  const hasDualHeaders = metadata.has_dual_headers || false
  const horizontalHeaders = metadata.horizontal_headers || []
  const verticalHeaders = metadata.vertical_headers || []
  const topLeftCell = metadata.top_left_cell || ''

  console.log('📋 元数据信息:', {
    hasDualHeaders,
    左上角单元格: topLeftCell,
    横向表头: horizontalHeaders,
    纵向表头: verticalHeaders
  })

  // 步骤2：查找表头行和数据行
  const headerRow = dualHeaderData.find(row => row?.__is_first_row)
  const dataRows = dualHeaderData.filter(row => row?.__is_data_row)

  if (!headerRow) {
    console.error('❌ 未找到表头行')
    return []
  }

  console.log('📋 找到:', {
    表头行: !!headerRow,
    数据行数: dataRows.length
  })

  // 步骤3：重建二维表格
  const table = []

  if (hasDualHeaders) {
    // 情况1：双表头结构
    console.log('🔄 处理双表头结构...')

    // 第一行：左上角单元格 + 横向表头
    const firstRow = [topLeftCell || '']

    // 从headerRow获取横向表头值
    for (let i = 0; i < horizontalHeaders.length; i++) {
      const headerKey = `H_${i + 1}`
      const headerValue = headerRow[headerKey] !== undefined ? headerRow[headerKey] : horizontalHeaders[i] || ``
      firstRow.push(String(headerValue))
    }
    table.push(firstRow)

    console.log('📊 重建的表头行:', firstRow)

    // 数据行：纵向表头 + 数据
    dataRows.forEach((dataRow, rowIndex) => {
      const row = []

      // 纵向表头 - 直接使用__vertical_header
      const verticalHeader = dataRow.__vertical_header || ''
      row.push(String(verticalHeader))

      console.log(`📊 处理第${rowIndex+1}行，行表头: "${verticalHeader}"`)

      // 数据单元格
      for (let i = 0; i < horizontalHeaders.length; i++) {
        const headerKey = `H_${i + 1}`
        const cellValue = dataRow[headerKey] !== undefined ? dataRow[headerKey] : ''
        row.push(cellValue)
      }

      table.push(row)
    })
  }

  console.log('✅ 重建完成:', {
    总行数: table.length,
    总列数: table[0]?.length || 0,
    第一行: table[0],
    第一列前几个值: table.slice(1, 6).map(row => row[0])
  })

  // 检查是否有"列标记"行
  const columnMarkRowIndex = table.findIndex(row => row[0] && String(row[0]).includes('列标记'))
  if (columnMarkRowIndex >= 0) {
    console.log(`✅ 找到列标记行: 第${columnMarkRowIndex}行，内容: ${table[columnMarkRowIndex]}`)
  }

  // 检查是否有"行标记"列
  if (table.length > 0) {
    const firstRow = table[0]
    const rowMarkColumnIndex = firstRow.findIndex(cell => cell && String(cell).includes('行标记'))
    if (rowMarkColumnIndex >= 0) {
      console.log(`✅ 找到行标记列: 第${rowMarkColumnIndex}列，表头: "${firstRow[rowMarkColumnIndex]}"`)
    }
  }

  return table
}

/**
 * 从数据中提取表格信息
 */
export const extractTableInfoFromData = (dualHeaderData, tableData) => {
  const info = {
    pageNum: 1,
    defaultUnit: "",
    defaultCurrency: "人民币",
    reportPeriod: ""
  }

  // 尝试从表头提取信息
  if (tableData.length > 0 && tableData[0].length > 0) {
    const firstRow = tableData[0]

    // 检查是否包含单位信息
    const unitKeywords = ['万元', '亿元', '元', '%', '百分比']
    firstRow.forEach(cell => {
      const cellStr = String(cell)
      unitKeywords.forEach(keyword => {
        if (cellStr.includes(keyword)) {
          if (keyword === '%' || keyword === '百分比') {
            info.defaultUnit = "%"
          } else {
            info.defaultUnit = keyword
          }
        }
      })
    })

    // 检查是否包含报告期信息
    const periodPatterns = [
      /20\d{2}年/, /20\d{2}年度/, /20\d{2}年.*季度/,
      /第[一二三四1-4]季度/, /Q[1-4]/, /上半年/, /下半年/
    ]

    firstRow.forEach(cell => {
      const cellStr = String(cell)
      periodPatterns.forEach(pattern => {
        const match = cellStr.match(pattern)
        if (match) {
          info.reportPeriod = match[0]
        }
      })
    })
  }

  console.log('📋 提取的表格信息:', info)
  return info
}

/**
 * 将二维数组转换为Handsontable格式
 */
export const convertToHandsontableFormat = (twoDArray) => {
  if (!Array.isArray(twoDArray) || twoDArray.length === 0) {
    return []
  }

  // 第一行作为表头
  const headers = twoDArray[0]

  // 其余行作为数据
  return twoDArray.slice(1).map(row => {
    const obj = {}
    headers.forEach((header, index) => {
      obj[header] = row[index] || ''
    })
    return obj
  })
}

/**
 * 转换双表头数据为二维表格
 */
export const convertDualHeaderToTable = (dualHeaderData) => {
  if (!dualHeaderData || dualHeaderData.length === 0) {
    return []
  }

  console.log('🔄 转换双表头数据为二维表格')

  const metadata = dualHeaderData[0]?.__metadata || {}
  const horizontalHeaders = metadata.horizontal_headers || []
  const verticalHeaders = metadata.vertical_headers || []
  const topLeftCell = metadata.top_left_cell || ''

  console.log('📋 元数据:', {
    左上角: topLeftCell,
    横向表头数: horizontalHeaders.length,
    纵向表头数: verticalHeaders.length,
    总行数: dualHeaderData.length
  })

  // 查找表头行和数据行
  let headerRow = null
  const dataRows = []

  for (let i = 1; i < dualHeaderData.length; i++) { // 跳过元数据行
    const row = dualHeaderData[i]
    if (row?.__is_first_row) {
      headerRow = row
    } else if (row?.__is_data_row) {
      dataRows.push(row)
    }
  }

  if (!headerRow) {
    console.error('❌ 未找到表头行')
    return []
  }

  // 构建二维表格
  const table = []

  // 第一行：左上角 + 横向表头
  const firstRow = [topLeftCell]
  for (let i = 0; i < horizontalHeaders.length; i++) {
    const headerKey = `H_${i + 1}`
    const value = headerRow[headerKey] || horizontalHeaders[i] || ``
    firstRow.push(value)
  }
  table.push(firstRow)

  // 数据行：纵向表头 + 数据
  dataRows.forEach((dataRow, rowIndex) => {
    const row = []

    // 纵向表头
    const verticalHeader = dataRow.__vertical_header ||
                          verticalHeaders[rowIndex] ||
                          ``
    row.push(verticalHeader)

    // 数据单元格
    for (let i = 0; i < horizontalHeaders.length; i++) {
      const headerKey = `H_${i + 1}`
      const value = dataRow[headerKey] ?? ''
      row.push(value)
    }

    table.push(row)
  })

  console.log('✅ 双表头转换完成:', {
    总行数: table.length,
    总列数: table[0]?.length || 0,
    布局: `(1,1) = ${table[1]?.[1] || '空'}`
  })

  return table
}

/**
 * 从sheet名称提取页码
 */
export const extractPageFromSheetName = (sheetName) => {
  const pageMatch = sheetName.match(/P(\d+)_/)
  if (pageMatch && pageMatch[1]) {
    const pageNum = parseInt(pageMatch[1])
    if (pageNum > 0) {
      return pageNum
    }
  }
  return null
}


/**
 * 格式化时间显示
 */
export const formatTime = (timestamp) => {
  if (!timestamp) return '从未保存'
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * 标准化change格式
 */
export const normalizeChange = (change) => {
  console.log('🔄 normalizeChange 输入:', change)

  // 如果已经是标准格式
  if (change && change.row !== undefined && change.col !== undefined && change.newValue !== undefined) {
    console.log('✅ 已为标准格式')
    return change
  }

  // 数组格式 [row, col, old, new]
  if (Array.isArray(change) && change.length >= 4) {
    console.log('✅ 检测到数组格式')
    return {
      row: change[0],
      col: change[1],
      oldValue: change[2],
      newValue: change[3]
    }
  }

  // 检测常见键名
  const possibleKeys = {
    row: ['row', 'rowIndex', 'r', '_row', 'Row', 'rowIndex', 'row_index'],
    col: ['col', 'colIndex', 'c', '_col', 'column', 'Column', 'colIndex', 'col_index'],
    newValue: ['newValue', 'new', 'value', 'val', '_value', 'Value', 'new_value']
  }

  const normalized = {}

  // 查找row
  for (const key of possibleKeys.row) {
    if (change[key] !== undefined) {
      normalized.row = change[key]
      console.log(`🔍 找到row键: ${key} = ${change[key]}`)
      break
    }
  }

  // 查找col
  for (const key of possibleKeys.col) {
    if (change[key] !== undefined) {
      normalized.col = change[key]
      console.log(`🔍 找到col键: ${key} = ${change[key]}`)
      break
    }
  }

  // 查找newValue
  for (const key of possibleKeys.newValue) {
    if (change[key] !== undefined) {
      normalized.newValue = change[key]
      console.log(`🔍 找到newValue键: ${key} = ${change[key]}`)
      break
    }
  }

  // 如果还没有找到，尝试其他方式
  if (normalized.row === undefined && change[0] !== undefined) {
    normalized.row = change[0]
  }

  if (normalized.col === undefined && change[1] !== undefined) {
    normalized.col = change[1]
  }

  if (normalized.newValue === undefined && change[3] !== undefined) {
    normalized.newValue = change[3]
  }

  console.log('🔄 标准化结果:', normalized)
  return normalized
}


export const rebuildTwoDimensionalTable222 = (inputData) => {
  if (!inputData || inputData.length === 0) {
    console.error('❌❌❌ 数据为空，无法重建')
    return []
  }

  console.log('🔧🔧🔧 开始重建二维表格...')
  console.log('📊📊📊 输入数据信息:', {
    总行数: inputData.length,
    第一行类型: typeof inputData[0],
    是否为数组: Array.isArray(inputData[0]),
    第一行样本: inputData[0],
    第一行列数: inputData[0]?.length || 0
  })

  // 🔥 关键修复：不进行任何过滤，直接返回原始数据
  console.log('🎯🎯🎯 策略：保留所有原始数据，不进行过滤')

  // 🔥 情况1：数据已经是二维数组
  if (Array.isArray(inputData[0])) {
    console.log('✅✅✅ 数据是二维数组，直接返回所有数据')

    // 打印完整数据信息以便调试
    console.log('📋📋📋 完整数据统计:')
    inputData.forEach((row, index) => {
      if (index < 5) { // 只打印前5行
        console.log(`  行${index}:`, {
          长度: row.length,
          内容: row,
          第一列值: row[0],
          第二列值: row[1]
        })
      }
    })

    console.log('📊📊📊 数据维度:', {
      总行数: inputData.length,
      总列数: inputData[0]?.length || 0,
      数据总量: inputData.length * (inputData[0]?.length || 0)
    })

    return inputData
  }

  // 🔥 情况2：数据是对象数组（双表头结构）
  if (typeof inputData[0] === 'object' && !Array.isArray(inputData[0])) {
    console.log('🔄🔄🔄 数据是对象数组，转换为二维数组（保留所有数据）')

    const twoDArray = []

    // 第一步：提取所有可能的键（列）
    const allKeys = new Set()
    inputData.forEach(row => {
      if (typeof row === 'object') {
        Object.keys(row).forEach(key => {
          if (!key.startsWith('__')) { // 保留元数据字段
            allKeys.add(key)
          }
        })
      }
    })

    const keys = Array.from(allKeys)
    console.log('📋📋📋 发现列:', keys)

    // 第二步：添加表头行
    twoDArray.push(keys)

    // 第三步：添加所有数据行
    inputData.forEach((row, index) => {
      const dataRow = keys.map(key => row[key] !== undefined ? row[key] : '')
      twoDArray.push(dataRow)

      if (index < 3) {
        console.log(`  数据行${index}:`, dataRow)
      }
    })

    console.log('✅✅✅ 转换完成:', {
      原数据行数: inputData.length,
      转换后行数: twoDArray.length,
      列数: keys.length
    })

    return twoDArray
  }

  // 🔥 情况3：其他格式，尝试保守转换
  console.log('🔄🔄🔄 未知格式，尝试保守转换')

  try {
    // 如果是单个数组，包装成二维数组
    if (Array.isArray(inputData) && !Array.isArray(inputData[0])) {
      return [inputData]
    }

    // 其他情况直接包装
    return [].concat(inputData)
  } catch (error) {
    console.error('❌❌❌ 格式转换失败:', error)
    return []
  }
}


export const rebuildTwoDimensionalTable = (inputData) => {
  if (!inputData || inputData.length === 0) {
    console.log('⚠️ 输入数据为空')
    return []
  }

  console.log('🔧 开始重建二维表格...')
  console.log('输入数据:', inputData)
  console.log('输入类型:', typeof inputData)
  console.log('输入长度:', inputData.length)
  console.log('第一个元素:', inputData[0])
  console.log('第一个元素类型:', typeof inputData[0])

  // 情况1：已经是二维数组
  if (Array.isArray(inputData) && Array.isArray(inputData[0])) {
    console.log('✅ 输入已经是二维数组，直接返回')
    return inputData
  }

  // 情况2：对象数组
  if (Array.isArray(inputData) && typeof inputData[0] === 'object' && !Array.isArray(inputData[0])) {
    console.log('🔄 对象数组转换为二维数组')

    try {
      const twoDArray = []
      const allKeys = new Set()

      // 收集所有可能的键
      inputData.forEach(item => {
        if (item && typeof item === 'object') {
          Object.keys(item).forEach(key => {
            allKeys.add(key)
          })
        }
      })

      const keys = Array.from(allKeys)
      console.log('🔍 发现列:', keys)

      // 添加表头行
      twoDArray.push(keys)

      // 添加数据行
      inputData.forEach(item => {
        const row = keys.map(key => item[key] !== undefined ? item[key] : '')
        twoDArray.push(row)
      })

      console.log('✅ 转换完成:', {
        行数: twoDArray.length,
        列数: twoDArray[0]?.length || 0
      })

      return twoDArray

    } catch (error) {
      console.error('❌ 对象数组转换失败:', error)
      return []
    }
  }

  // 情况3：一维数组
  if (Array.isArray(inputData) && !Array.isArray(inputData[0])) {
    console.log('🔄 一维数组转换为二维数组')
    return [inputData]
  }

  // 情况4：未知格式
  console.error('❌ 无法识别的输入格式:', typeof inputData)
  return []
}


// 🔥 新增：单表头结构处理函数
const rebuildSingleHeaderTable = (singleHeaderData) => {
  console.log('🔄🔄🔄 开始处理单表头结构...')

  if (!singleHeaderData || singleHeaderData.length === 0) {
    console.error('❌❌❌ 单表头数据为空')
    return []
  }

  // 🔥 查找表头行和数据行
  const headerRow = singleHeaderData.find(row => row?.__is_first_row)
  const dataRows = singleHeaderData.filter(row => row?.__is_data_row)

  if (!headerRow) {
    console.error('❌❌❌ 未找到表头行')
    return []
  }

  console.log('📋📋📋 单表头结构:', {
    表头行: !!headerRow,
    数据行数: dataRows.length
  })

  // 🔥 应用您的过滤条件
  console.log('🎯🎯🎯 应用过滤条件到单表头数据:')
  const filteredDataRows = dataRows.filter(dataRow => {
    // 条件1：行标记为0的要过滤
    if (dataRow.__row_mark === 0) {
      console.log('⏭️⏭️⏭️ 过滤行标记为0的行')
      return false
    }

    // 条件2：第一列为空的要过滤
    const firstColValue = dataRow.H_1
    if (firstColValue === null ||
        firstColValue === undefined ||
        firstColValue === '' ||
        String(firstColValue).toLowerCase() === 'nan' ||
        String(firstColValue).toLowerCase() === 'null') {
      console.log('⏭️⏭️⏭️ 过滤第一列为空的行:', firstColValue)
      return false
    }

    return true
  })

  console.log('✅✅✅ 单表头过滤完成:', {
    原数据行数: dataRows.length,
    过滤后行数: filteredDataRows.length
  })

  if (filteredDataRows.length === 0) {
    console.error('❌❌❌ 过滤后数据为空')
    return []
  }

  // 🔥 重建单表头结构的二维表格
  const table = []

  // 提取表头
  const headers = []
  let colIndex = 1
  while (`H_${colIndex}` in headerRow) {
    headers.push(headerRow[`H_${colIndex}`] || `列${colIndex}`)
    colIndex++
  }

  if (headers.length === 0) {
    console.error('❌❌❌ 未找到表头列')
    return []
  }

  table.push(headers)
  console.log('📊📊📊 表头行:', headers)

  // 添加数据行
  filteredDataRows.forEach((dataRow, rowIndex) => {
    const row = []
    for (let i = 0; i < headers.length; i++) {
      const headerKey = `H_${i + 1}`
      row.push(dataRow[headerKey] !== undefined ? dataRow[headerKey] : '')
    }
    table.push(row)
  })

  console.log('✅✅✅ 单表头重建完成:', {
    总行数: table.length,
    总列数: table[0]?.length || 0,
    样本: table.slice(0, Math.min(3, table.length))
  })

  return table
}


