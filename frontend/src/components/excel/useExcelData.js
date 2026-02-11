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

  console.log('🔍 convertObjectArrayToArray 输入检查:', {
    输入类型: typeof inputData[0],
    是数组数组: Array.isArray(inputData[0]),
    是对象: typeof inputData[0] === 'object',
    第一行样本: inputData[0]
  })

  // 如果已经是数组数组，直接返回（但需要验证格式）
  if (Array.isArray(inputData[0])) {
    console.log('✅ convertObjectArrayToArray: 输入已经是数组数组格式')

    // 验证数组数组格式是否正确
    const isValidArrayArray = inputData.every(row => Array.isArray(row))
    if (isValidArrayArray) {
      console.log('✅ 数组数组格式验证通过')
      return inputData
    } else {
      console.warn('⚠️ 数组数组格式验证失败，尝试修复')
    }
  }

  // 如果是对象数组，转换为数组数组
  if (typeof inputData[0] === 'object' && inputData[0] !== null) {
    console.log('🔄 convertObjectArrayToArray: 将对象数组转换为数组数组')

    try {
      const keys = Object.keys(inputData[0] || {})
      const result = []

      // 第一行是列名
      result.push(keys)
      console.log('📋 提取的列名:', keys)

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

      console.log('✅ convertObjectArrayToArray: 转换完成', {
        原数据行数: inputData.length,
        转换后行数: result.length,
        列数: keys.length,
        转换后格式: Array.isArray(result[0]) ? '数组数组' : '其他'
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
  console.log('🔄🔄 tableData computed 触发')

  console.log('=== 🔥 tableData 计算属性开始 ===')

  // 添加诊断代码
  console.log('1. props.excelData 类型:', typeof props.excelData)
  console.log('2. props.excelData 是数组:', Array.isArray(props.excelData))
  if (props.excelData && Array.isArray(props.excelData)) {
    console.log('3. props.excelData[0] 类型:', typeof props.excelData[0])
    console.log('4. props.excelData[0] 是数组:', Array.isArray(props.excelData[0]))
    console.log('5. props.excelData[0] 样本:', props.excelData[0])
  }

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

  console.log('📊📊 接收到的原始数据:', {
    长度: props.excelData.length,
    第一个元素类型: typeof props.excelData[0],
    第一个元素: props.excelData[0],
    第一个元素的键: Object.keys(props.excelData[0] || {})
  })

  const firstItem = props.excelData[0]

  // 2. 双表头逻辑
  if (firstItem?.__metadata?.has_dual_headers) {
    console.log('✅ 检测到双表头元数据（旧结构）')

    const metadata = firstItem.__metadata
    const dataRows = props.excelData.slice(1) // 跳过元数据

    console.log('📋📋 元数据详情:', {
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
    console.log('📊📊 第一行构建完成:', firstRow)

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

    console.log('✅ 双表头数据转换检查:', {
      转换前类型: Array.isArray(renderedTable[0]) ? '数组数组' : '对象数组',
      转换后类型: Array.isArray(finalData[0]) ? '数组数组' : '对象数组',
      转换前形状: `${renderedTable.length}行 × ${renderedTable[0]?.length || 0}列`,
      转换后形状: `${finalData.length}行 × ${finalData[0]?.length || 0}列`
    })

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
          console.log('✅ 强制转换完成:', { 行数: converted.length, 列数: keys.length })
          return converted
        } catch (error) {
          console.error('❌❌ 强制转换失败:', error)
          return finalData // 返回原数据
        }
      }

      console.error('❌❌ 无法识别的数据格式')
      return finalData
    })()

    console.log('🎯🎯 双表头最终数据格式验证:', {
      格式: Array.isArray(validatedData[0]) ? '数组数组 ✅' : '对象数组 ❌❌',
      行数: validatedData.length,
      列数: validatedData[0]?.length || 0,
      支持列操作: Array.isArray(validatedData[0]) ? '是' : '否'
    })

    // 🔥🔥🔥🔥🔥 最终诊断
    console.group('🔍🔍🔍 最终数据诊断')
    console.log('1. 数据格式检查:', {
      数据存在: !!validatedData,
      是数组: Array.isArray(validatedData),
      长度: validatedData?.length || 0,
      第一行存在: !!validatedData?.[0],
      第一行类型: typeof validatedData?.[0],
      是数组数组: Array.isArray(validatedData?.[0]),
      是对象: typeof validatedData?.[0] === 'object',
      第一行样本: validatedData?.[0]
    })

    // 强制转换验证
    // 在调用 forceArrayArrayFormat 的地方添加诊断
console.log('🔥 调用 forceArrayArrayFormat 前:')
console.log('- 输入数据:', finalData)
console.log('- 输入数据[0] 类型:', typeof finalData?.[0])
console.log('- 是数组数组:', Array.isArray(finalData?.[0]))

const forceConverted = forceArrayArrayFormat(finalData)

console.log('🔥 调用 forceArrayArrayFormat 后:')
console.log('- 输出数据[0] 类型:', typeof forceConverted?.[0])
console.log('- 是数组数组:', Array.isArray(forceConverted?.[0]))
console.log('- 转换结果:', forceConverted)
    console.log('2. 强制转换验证:', {
      转换成功: Array.isArray(forceConverted?.[0]),
      格式: Array.isArray(forceConverted?.[0]) ? '数组数组 ✅' : '对象数组 ❌',
      行数: forceConverted.length,
      列数: forceConverted[0]?.length || 0
    })
    console.groupEnd()

    return forceConverted
  }

  // 3. 单表头逻辑
  console.log('📊📊 单表头模式')

  // 获取表头
  let headers = []

  // 首先检查是否有 __orderedHeaders
  if (firstItem.__orderedHeaders && Array.isArray(firstItem.__orderedHeaders)) {
    headers = firstItem.__orderedHeaders
    console.log('📊📊 使用 __orderedHeaders:', headers)
  } else {
    // 提取非 __ 开头的属性作为表头
    const allKeys = Object.keys(firstItem || {})
    headers = allKeys.filter(key => !key.startsWith('__'))
  }

  // 如果还是没有表头，创建默认表头
  if (!headers.length) {
    console.warn('⚠️ 未找到表头，使用默认表头')

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

  console.log('✅ 单表头数据转换检查:', {
    转换前类型: Array.isArray(result[0]) ? '数组数组' : '对象数组',
    转换后类型: Array.isArray(finalData[0]) ? '数组数组' : '对象数组',
    转换前形状: `${result.length}行 × ${result[0]?.length || 0}列`,
    转换后形状: `${finalData.length}行 × ${finalData[0]?.length || 0}列`
  })

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
        console.log('✅ 强制转换完成:', { 行数: converted.length, 列数: keys.length })
        return converted
      } catch (error) {
        console.error('❌❌ 强制转换失败:', error)
        return finalData // 返回原数据
      }
    }

    console.error('❌❌ 无法识别的数据格式')
    return finalData
  })()

  console.log('🎯🎯 单表头最终数据格式验证:', {
    格式: Array.isArray(validatedData[0]) ? '数组数组 ✅' : '对象数组 ❌❌',
    行数: validatedData.length,
    列数: validatedData[0]?.length || 0,
    支持列操作: Array.isArray(validatedData[0]) ? '是' : '否'
  })

  // 🔥🔥🔥🔥🔥 最终诊断
  console.group('🔍🔍🔍 最终数据诊断')
  console.log('1. 数据格式检查:', {
    数据存在: !!validatedData,
    是数组: Array.isArray(validatedData),
    长度: validatedData?.length || 0,
    第一行存在: !!validatedData?.[0],
    第一行类型: typeof validatedData?.[0],
    是数组数组: Array.isArray(validatedData?.[0]),
    是对象: typeof validatedData?.[0] === 'object',
    第一行样本: validatedData?.[0]
  })

  // 强制转换验证
  // 在调用 forceArrayArrayFormat 的地方添加诊断
console.log('🔥 调用 forceArrayArrayFormat 前:')
console.log('- 输入数据:', finalData)
console.log('- 输入数据[0] 类型:', typeof finalData?.[0])
console.log('- 是数组数组:', Array.isArray(finalData?.[0]))

const forceConverted = forceArrayArrayFormat(finalData)

console.log('🔥 调用 forceArrayArrayFormat 后:')
console.log('- 输出数据[0] 类型:', typeof forceConverted?.[0])
console.log('- 是数组数组:', Array.isArray(forceConverted?.[0]))
console.log('- 转换结果:', forceConverted)

  console.log('2. 强制转换验证:', {
    转换成功: Array.isArray(forceConverted?.[0]),
    格式: Array.isArray(forceConverted?.[0]) ? '数组数组 ✅' : '对象数组 ❌',
    行数: forceConverted.length,
    列数: forceConverted[0]?.length || 0
  })
  console.groupEnd()

  const finalDataToReturn = (() => {
      if (Array.isArray(forceConverted) && forceConverted.length > 0 && Array.isArray(forceConverted[0])) {
        return forceConverted;
      }

      if (Array.isArray(forceConverted) && forceConverted.length > 0 && typeof forceConverted[0] === 'object') {
        console.log('🔥 强制转换对象数组为数组数组');
        const keys = Object.keys(forceConverted[0] || {});
        return [
          keys,
          ...forceConverted.map(row => keys.map(key => String(row[key] || '')))
        ];
      }

      return forceConverted || [];
    })();

    console.log('✅ 最终数据格式:', Array.isArray(finalDataToReturn[0]) ? '数组数组' : '对象数组');
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
        console.log('✅ 数据验证:', {
          是数组数组: true,
          所有行都是数组: allRowsAreArrays,
          行数: data.length,
          列数: data[0]?.length || 0
        })
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
          console.log('✅ 转换结果:', {
            行数: converted.length,
            列数: keys.length,
            第一行样本: converted[0]
          })
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

        console.log('🔍🔍 开始智能判断表格类型...');

        // 1. 检查行标记（A列）
        const hasRowMarkers = checkRowMarkers(data);
        console.log('   - 行标记检测:', hasRowMarkers);

        // 2. 检查列标记（首行）
        const hasColumnMarkers = checkColumnMarkers(data);
        console.log('   - 列标记检测:', hasColumnMarkers);

        // 3. 检查交叉结构
        const hasCrossStructure = checkCrossStructure(data);
        console.log('   - 交叉结构检测:', hasCrossStructure);

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

        console.log('✅ 智能判断完成:', result);
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


    // 在 HandsontableExcelViewer.vue 中修改
    // 🔥🔥🔥 修改：将空格相关状态改为数值相关状态
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
      console.log('✅ 数值单元格高亮已清除')
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

  console.log('📊📊 数值单元格统计:', {
    总数: numericCells.length,
    样本: numericCells.slice(0, 5)
  })

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
    exportData,

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