// frontend/src/components/excel/useExcelViewerLogic.js
import * as ExcelKey from '@/utils/excelKeyUtils.js'
import { watch, ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import Handsontable from 'handsontable'
import { isDateString, validateNumberFormat } from './excel-utils.js'
import { useSelectionSum } from './useSelectionSum.js'

export default function useExcelViewerLogic(
  props,
  {
    // 从组合式函数传入
    hotTable,
    getSafeHotInstance,
    isEditMode,
    hasChanges,
    modifiedCells,
    modifiedCellsCount,
    savedCells,
    unsavedCells,
    tableData,
    hasDualHeaders,
    tableInfo,
    columns,
    hasEmptyCells,
    detectEmptyCells,
    emptyCellsStats,
    showStatsPanel,
    stats,
    calculateSelectionStats,
    clearSelection,
    updateTableReadOnly,
    markSavedCells,
    toggleEditModeFromHook,
    cleanup,
    onDataChange
  },
  emit
) {
  // 状态
  const showEmptyCellsHighlight = ref(false)
  const emptyCellsHighlightEnabled = ref(false)
  const showCellContent = ref(false)
  const selectedCell = ref({
    row: null,
    col: null,
    position: '',
    content: '',
    type: '未知',
    charCount: 0,
    lineCount: 1,
    format: '',
    isModified: false,
    isReadOnly: false,
    isNumeric: false,
    isFormula: false,
    isValidNumber: false,
    numberValidationMsg: '',
    validationDetails: ''
  })

  // 🔥🔥 新增：集成多单元格求和功能
  const {
    selectionSum,
    calculateSelectionSum,
    clearSelectionSum,
    setupSelectionSumListener
  } = useSelectionSum(getSafeHotInstance)

  // 计算属性
  const colWidths = computed(() =>
    Array.from({ length: tableData.value[0]?.length || 0 }, (_, i) =>
      i === 0 ? 180 : 120
    )
  )

  const computedColumns000000 = computed(() => {
      const baseColumns = columns.value;

      // 获取当前数据列数
      const dataColCount = tableData.value[0]?.length || 0;

      // 如果没有配置或列数不匹配，基于数据生成配置
      if (!baseColumns || baseColumns.length === 0) {
        return Array.from({ length: dataColCount }, (_, index) => ({
          data: index,
          readOnly: !isEditMode.value,
          title: String.fromCharCode(65 + index), // A, B, C...
          filter: true // 🔥 添加筛选配置
        }));
      }

      // ✅ 关键：如果配置列数 < 数据列数，补充新列配置
      if (baseColumns.length < dataColCount) {
        const newColumns = [...baseColumns];
        for (let i = baseColumns.length; i < dataColCount; i++) {
          newColumns.push({
            i,
            readOnly: !isEditMode.value,
            title: `列${i + 1}`,  // 新列默认名称
            filter: true // 🔥 添加筛选配置
          });
        }
        return newColumns.map((col, index) => ({
          ...col,
          index,  // 确保 data 索引正确
          readOnly: !isEditMode.value,
          filter: true // 🔥 添加筛选配置
        }));
      }

      // 如果配置列数 > 数据列数，截断（但保留名称供后续使用）
      if (baseColumns.length > dataColCount) {
        return baseColumns.slice(0, dataColCount).map((col, index) => ({
          ...col,
          data: index,
          readOnly: !isEditMode.value,
          filter: true // 🔥 添加筛选配置
        }));
      }

      // 正常情况：列数匹配
      return baseColumns.map((col, index) => ({
        ...col,
        data: index,
        readOnly: !isEditMode.value,
        filter: true // 🔥 添加筛选配置
      }));
    });

  const computedColumns1111111 = computed(() => {
      const baseColumns = columns.value;
      const dataColCount = tableData.value[0]?.length || 0;

      if (!baseColumns || baseColumns.length === 0) {
        return Array.from({ length: dataColCount }, (_, index) => ({
          data: index,
          readOnly: !isEditMode.value,
          title: String.fromCharCode(65 + index),
          filter: {
            condition: 'contains', // 明确指定筛选条件
            placeholder: '筛选...'
          }
        }));
      }

      // 确保筛选配置不被覆盖
      return baseColumns.map((col, index) => ({
        ...col,
        data: index,
        readOnly: !isEditMode.value,
        filter: col.filter !== undefined ? col.filter : { // 保留原有配置或使用默认
          condition: 'contains',
          placeholder: '筛选...'
        }
      }));
    });

   // 替换现有的 computedColumns 计算属性
    const computedColumns = computed(() => {

      const baseColumns = columns.value;
      const dataColCount = tableData.value[0]?.length || 0;

      // 如果没有配置或列数不匹配，基于数据生成配置
      if (!baseColumns || baseColumns.length === 0) {
        const newColumns = Array.from({ length: dataColCount }, (_, index) => ({
          data: index,
          readOnly: !isEditMode.value,
          title: String.fromCharCode(65 + index), // A, B, C...
          filter: true // ✅ 关键修改：使用布尔值启用筛选
        }))

        return newColumns
      }

      // 如果配置列数 < 数据列数，补充新列配置
      if (baseColumns.length < dataColCount) {
        const newColumns = [...baseColumns];
        for (let i = baseColumns.length; i < dataColCount; i++) {
          newColumns.push({
            data: i,
            readOnly: !isEditMode.value,
            title: `列${i + 1}`,
            filter: true // ✅ 关键修改：使用布尔值
          });
        }
        return newColumns;
      }

      // 如果配置列数 > 数据列数，截断
      if (baseColumns.length > dataColCount) {
        return baseColumns.slice(0, dataColCount).map((col, index) => ({
          ...col,
          data: index,
          readOnly: !isEditMode.value,
          filter: col.filter !== undefined ? col.filter : true // ✅ 关键修改：保留原有或使用默认
        }));
      }

      // 正常情况：列数匹配
      const finalColumns = baseColumns.map((col, index) => ({
        ...col,
        data: index,
        readOnly: !isEditMode.value,
        filter: col.filter !== undefined ? col.filter : true // ✅ 关键修改：保留原有或使用默认
      }))

      return finalColumns
    })


  // 处理单元格修改的函数
  const handleCellChangeFromEdit = (cellInfo) => {
    console.log('📤📤 收到单元格修改:', {
      行: cellInfo.row,
      列: cellInfo.col,
      旧值: cellInfo.oldValue,
      新值: cellInfo.newValue
    })

    // 发送原有事件（保持兼容）
    emit('cell-changed', {
      row: cellInfo.row,
      col: cellInfo.col,
      oldValue: cellInfo.oldValue,
      newValue: cellInfo.newValue,
      source: cellInfo.source,
      timestamp: cellInfo.timestamp,
      cellKey: cellInfo.cellKey
    })

    // 新增：发送给 sheetStateManager 的事件
    emit('cell-change', {
      changes: [[cellInfo.row, cellInfo.col, cellInfo.oldValue, cellInfo.newValue]],
      sheetName: props.sheetName,
      pdfId: props.pdfId,
      excelFileName: props.excelFileName,
      source: cellInfo.source,
      timestamp: cellInfo.timestamp
    })

    // 发送数据变化汇总事件
    const hot = getSafeHotInstance()
    if (hot) {
      const allChanges = []
      modifiedCells.value.forEach(cellKey => {
        const [row, col] = cellKey.split(',').map(Number)
        const value = hot.getDataAtCell(row, col)
        allChanges.push({ row, col, value, cellKey })
      })

      emit('data-changed', {
        totalChanges: modifiedCells.value.size,
        hasChanges: hasChanges.value,
        allChanges: allChanges,
        modifiedCellsCount: modifiedCells.value.size
      })
    }
  }

  // 编辑模式相关
  const toggleEditMode = () => {
    console.log('🔘🔘 编辑按钮被点击')

    toggleEditModeFromHook((message, type) => {
      console.log('回调:', message, type)

      // 显示消息
      if (message && type) {
        if (type === 'success') {
          ElMessage.success(message)
        } else if (type === 'info') {
          ElMessage.info(message)
        } else if (type === 'error') {
          ElMessage.error(message)
        } else if (type === 'warning') {
          ElMessage.warning(message)
        }
      }

      // 2. 一次性标红所有历史修改
      nextTick(() => markAllModifiedRed())
    })
  }

  const markAllModifiedRed = () => {
    const hot = getSafeHotInstance()
    if (!hot) return

    const allModified = Array.from(modifiedCells.value)
    const cellMeta = []

    allModified.forEach(key => {
      const [row, col] = key.split(',').map(Number)
      cellMeta.push({ row, col, className: 'cell-modified-red' })
    })

    hot.updateSettings({ cell: cellMeta }, false)
    hot.render()
  }

  // 高亮空白单元格
  const highlightEmptyCells = () => {
    console.log('🟡🟡🟡 执行高亮空单元格')
    const hot = getSafeHotInstance()
    if (!hot) {
      console.error('❌❌ 无法获取表格实例')
      return false
    }

    try {
      const data = tableData.value
      if (!data || data.length === 0) {
        console.log('📭📭 表格数据为空')
        ElMessage.warning('表格数据为空')
        return false
      }

      // 计算有效数据区域
      let maxDataRow = -1
      let maxDataCol = -1

      // 找到最后一个有数据的行和列
      for (let row = 0; row < data.length; row++) {
        for (let col = 0; col < (data[row]?.length || 0); col++) {
          const value = data[row][col]
          const hasValue = value !== null &&
                          value !== undefined &&
                          value !== '' &&
                          !(typeof value === 'string' && value.trim() === '') &&
                          !(typeof value === 'number' && isNaN(value))

          if (hasValue) {
            maxDataRow = Math.max(maxDataRow, row)
            maxDataCol = Math.max(maxDataCol, col)
          }
        }
      }

      console.log(`📊📊 有效数据区域: 行0-${maxDataRow}, 列0-${maxDataCol}`)

      // 如果没有有效数据
      if (maxDataRow === -1 || maxDataCol === -1) {
        console.log('📭📭 没有发现有效数据')
        ElMessage.info('表格中没有有效数据')
        return false
      }

      let emptyCount = 0
      // 只在有效数据区域内检查空单元格
      for (let row = 0; row <= maxDataRow; row++) {
        for (let col = 0; col <= maxDataCol; col++) {
          // 确保行和列在数据范围内
          if (row >= data.length || col >= (data[row]?.length || 0)) {
            continue
          }

          const value = data[row][col]
          const isEmpty = value === null ||
                         value === undefined ||
                         (typeof value === 'string' && value.trim() === '') ||
                         (typeof value === 'number' && isNaN(value))

          if (isEmpty) {
            console.log(`📍 发现空单元格: [${row},${col}]`, { value, type: typeof value })
            hot.setCellMeta(row, col, 'className', 'empty-cell-highlight')
            emptyCount++
          }
        }
      }

      hot.render()
      console.log(`✅ 高亮完成: ${emptyCount} 个空单元格 (有效区域: ${maxDataRow + 1}行 × ${maxDataCol + 1}列)`)

      // 验证高亮是否应用成功
      setTimeout(() => {
        const highlightedCells = hot.rootElement.querySelectorAll('.empty-cell-highlight')
        console.log(`🎯🎯 DOM中高亮的单元格数量: ${highlightedCells.length}`)
      }, 100)

      if (emptyCount === 0) {
        ElMessage.info('有效数据区域内未发现空白单元格')
        return false
      }

      ElMessage.success(`高亮显示 ${emptyCount} 个空白单元格`)
      return true
    } catch (error) {
      console.error('❌❌ 高亮空单元格失败:', error)
      ElMessage.error('高亮失败')
      return false
    }
  }

  // 清除空白单元格高亮
  const clearEmptyCellsHighlight = () => {
    console.log('🟡🟡🟡 执行清除高亮')
    const hot = getSafeHotInstance()
    if (!hot) return

    try {
      const data = tableData.value
      if (!data || data.length === 0) return

      for (let row = 0; row < data.length; row++) {
        for (let col = 0; col < (data[row]?.length || 0); col++) {
          hot.setCellMeta(row, col, 'className', '')
        }
      }

      hot.render()
      console.log('✅ 高亮清除完成')
    } catch (error) {
      console.error('❌❌ 清除高亮失败:', error)
    }
  }

  // 空白单元格处理
  const toggleEmptyCellsHighlight = () => {
    console.log('🔘🔘 点击高亮空格按钮', {
      当前高亮状态: showEmptyCellsHighlight.value,
      是否有空单元格: hasEmptyCells.value
    })

    if (showEmptyCellsHighlight.value) {
      // 清除高亮
      clearEmptyCellsHighlight()
      showEmptyCellsHighlight.value = false
      ElMessage.info('已隐藏空白单元格高亮')
    } else {
      // 应用高亮
      const hasEmpties = highlightEmptyCells()
      if (hasEmpties) {
        showEmptyCellsHighlight.value = true
        ElMessage.success('已高亮显示空白单元格')
      } else {
        // 如果没有空单元格，保持关闭状态
        showEmptyCellsHighlight.value = false
      }
    }
  }

  const showEmptyCellsDetail = () => {
    if (emptyCellsStats.value) {
      ElMessageBox.info({
        title: '空白单元格详情',
        message: `
          <div style="text-align: left; font-size: 13px;">
            <p><strong>总数:</strong> ${emptyCellsStats.value.total} 个</p>
            <p><strong>分布:</strong> ${emptyCellsStats.value.rowsWithEmptyCells}行, ${emptyCellsStats.value.colsWithEmptyCells}列</p>
            <p><strong>范围:</strong> 行${emptyCellsStats.value.minRow + 1}-${emptyCellsStats.value.maxRow + 1},
            列${emptyCellsStats.value.minCol + 1}-${emptyCellsStats.value.maxCol + 1}</p>
          </div>
        `,
        dangerouslyUseHTMLString: true,
        customClass: 'empty-cells-detail-modal'
      })
    }
  }

  // 单元格选择和显示
  const calculateCellPosition = (row, col) => {
    if (row === null || col === null) return ''

    let columnName = ''
    let columnIndex = col

    while (columnIndex >= 0) {
      columnName = String.fromCharCode(65 + (columnIndex % 26)) + columnName
      columnIndex = Math.floor(columnIndex / 26) - 1
    }

    const rowNumber = row + 1
    return `${columnName}${rowNumber}`
  }

  const setupCompleteSelectionListener = () => {
    const hot = getSafeHotInstance()
    if (!hot) {
      console.warn('❌❌ 表格实例无效，无法设置选择监听器')
      return
    }

    // 清除旧的监听器
    try {
      hot.removeHook('afterSelection')
    } catch (e) {
      // 忽略错误
    }

    // 设置新的选择监听器
    hot.addHook('afterSelection', (startRow, startCol, endRow, endCol, preventScrolling, selectionLayerLevel) => {
      // 单个单元格选择
      if (startRow === endRow && startCol === endCol) {
        updateSelectedCellDisplay(startRow, startCol)
        showStatsPanel.value = false // 隐藏统计面板
        showCellContent.value = true // 显示单元格详情
      } else {
        // 区域选择：显示统计信息
        calculateSelectionStats(startRow, startCol, endRow, endCol)
        showCellContent.value = false // 隐藏单元格详情
        showStatsPanel.value = true // 显示统计面板

        // 🔥🔥 新增：触发多单元格求和计算
        nextTick(() => {
          calculateSelectionSum()
        })
      }
    })
  }

  const updateSelectedCellDisplay = (row, col) => {
    // 立即拦截非法坐标
    if (
      row == null ||
      col == null ||
      row < 0 ||
      col < 0 ||
      !Number.isInteger(row) ||
      !Number.isInteger(col)
    ) {
      console.warn('🚫🚫 非法单元格坐标', { row, col });
      return;
    }

    const hot = getSafeHotInstance()
    if (!hot) {
      showCellContent.value = false
      return
    }

    // 检查是否为有效的选择
    if (row === null || col === null) {
      console.warn('⚠️ 无效的单元格坐标')
      showCellContent.value = false
      return
    }

    try {
      const content = hot.getDataAtCell(row, col)
      const cellMeta = hot.getCellMeta(row, col)

      const contentStr = content !== null && content !== undefined ? String(content) : ''
      const charCount = contentStr.length
      const lineCount = contentStr.split('\n').length

      // 增强空白单元格检测
      const isEmpty = (value) => {
        if (value === null || value === undefined) {
          return true
        }

        if (typeof value === 'string') {
          const trimmed = value.trim()

          if (trimmed === '') {
            return true
          }

          const emptyPatterns = [
            'null', 'NULL', 'Null',
            'nan', 'NaN', 'NAN', 'Nan',
            'none', 'None', 'NONE',
            'n/a', 'N/A', 'na', 'NA',
            '空', '空白', '空缺', '缺省',
            'undefined', 'Undefined', 'UNDEFINED',
            ' ', '\t', '\n', '\r'
          ]

          if (emptyPatterns.includes(trimmed.toLowerCase())) {
            return true
          }

          if (/^\s+$/.test(trimmed)) {
            return true
          }

          const placeholderPatterns = [
            '--', '---', '____', '####', '****',
            'null', 'NULL', 'nan', 'NaN'
          ]

          if (placeholderPatterns.includes(trimmed)) {
            return true
          }
        }

        if (typeof value === 'number') {
          if (isNaN(value)) {
            return true
          }
        }

        return false
      }

      const isActuallyEmpty = isEmpty(content)

      // 判断单元格类型
      let cellType = '未知'
      let dataFormat = '文本'
      let isNumeric = false
      let isFormula = false
      let isValidNumber = false
      let numberValidationMsg = ''
      let validationDetails = ''

      // 如果是空值，需要确定具体的空值类型
      let emptyType = ''
      let emptyReason = ''

      if (isActuallyEmpty) {
        cellType = '空值'

        if (content === null) {
          emptyType = 'null'
          emptyReason = '原生 null 值'
        } else if (content === undefined) {
          emptyType = 'undefined'
          emptyReason = '未定义'
        } else if (typeof content === 'string') {
          const trimmed = content.trim()
          if (trimmed === '') {
            emptyType = 'empty_string'
            emptyReason = '空字符串'
          } else if (['null', 'NULL', 'Null'].includes(trimmed)) {
            emptyType = 'null_string'
            emptyReason = '文本 null'
          } else if (['nan', 'NaN', 'NAN', 'Nan'].includes(trimmed)) {
            emptyType = 'nan_string'
            emptyReason = '文本 NaN'
          } else if (['none', 'None', 'NONE'].includes(trimmed)) {
            emptyType = 'none_string'
            emptyReason = '文本 None'
          } else if (['n/a', 'N/A', 'na', 'NA'].includes(trimmed)) {
            emptyType = 'na_string'
            emptyReason = '文本 N/A'
          } else if (/^\s+$/.test(trimmed)) {
            emptyType = 'whitespace'
            emptyReason = '纯空白字符'
          } else {
            emptyType = 'other_empty'
            emptyReason = `其他空值: "${trimmed}"`
          }
        } else if (typeof content === 'number' && isNaN(content)) {
          emptyType = 'nan_number'
          emptyReason = '数字 NaN'
        }

        dataFormat = emptyReason
      } else if (typeof content === 'string') {
        const trimmed = content.trim()

        if (trimmed.startsWith('=')) {
          cellType = '公式'
          isFormula = true
          dataFormat = '计算'
        } else if (trimmed === 'TRUE' || trimmed === 'FALSE' || trimmed === 'true' || trimmed === 'false') {
          cellType = '布尔'
          dataFormat = '逻辑'
        } else if (isDateString(trimmed)) {
          cellType = '日期'
          dataFormat = '日期'
        } else {
          const numericValue = parseFloat(trimmed)
          const isNumericString = !isNaN(numericValue) && isFinite(numericValue)

          if (isNumericString) {
            if (/^\d{4}$/.test(trimmed) && trimmed >= '1900' && trimmed <= '2100') {
              cellType = '日期'
              dataFormat = '年份'
            } else if (/^\d{8}$/.test(trimmed)) {
              const year = parseInt(trimmed.substring(0, 4), 10)
              const month = parseInt(trimmed.substring(4, 6), 10)
              const day = parseInt(trimmed.substring(6, 8), 10)
              if (year >= 1900 && year <= 2100 && month >= 1 && month <= 12 && day >= 1 && day <= 31) {
                cellType = '日期'
                dataFormat = '日期数字'
              } else {
                cellType = '数字'
                dataFormat = '数值'
              }
            } else {
              cellType = '数字'
              dataFormat = '数值'
              isNumeric = true
              const validationResult = validateNumberFormat(trimmed)
              isValidNumber = validationResult.isValid
              numberValidationMsg = validationResult.message
              validationDetails = validationResult.details || ''
            }
          } else {
            cellType = '文本'
          }
        }
      } else if (typeof content === 'number' && !isNaN(content) && isFinite(content)) {
        if (content >= 1900 && content <= 2100 && content % 1 === 0) {
          cellType = '日期'
          dataFormat = '年份'
        } else {
          cellType = '数字'
          dataFormat = '数值'
          isNumeric = true
          isValidNumber = true
          numberValidationMsg = '✅ 格式正确'
          validationDetails = '原生数字类型'
        }
      } else if (content instanceof Date) {
        cellType = '日期'
        dataFormat = '日期对象'
      }

      const cellKey = `${row},${col}`
      const isModified = modifiedCells.value.has(cellKey)
      const formatInfo = cellMeta?.format || ''
      const isReadOnly = cellMeta?.readOnly || false

      // 构建选中单元格对象
      selectedCell.value = {
        row,
        col,
        position: calculateCellPosition(row, col),
        content: contentStr,
        type: cellType,
        charCount,
        lineCount,
        format: formatInfo,
        isModified,
        isReadOnly,
        isNumeric,
        isFormula,
        isValidNumber,
        numberValidationMsg,
        validationDetails,
        isEmpty: isActuallyEmpty,
        emptyType: emptyType,
        emptyReason: emptyReason,
        isEmptyFromDetection: detectEmptyCells.value ? detectEmptyCells.value.has(cellKey) : false,
        rawValue: content,
        rawType: typeof content,
        inDualHeader: hasDualHeaders.value,
        ...(hasDualHeaders.value && {
          headerInfo: {
            isTopLeft: row === 0 && col === 0,
            isHorizontalHeader: row === 0 && col > 0,
            isVerticalHeader: row > 0 && col === 0
          }
        })
      }

      showCellContent.value = true

      nextTick(() => {
        const contentDisplay = document.querySelector('.cell-content-display')
        if (contentDisplay) {
          contentDisplay.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }
      })

    } catch (error) {
      console.warn('⚠️ 获取单元格内容失败:', error)
      showCellContent.value = false
    }
  }

  const restoreModifiedCellsStyle = () => {
    const hot = getSafeHotInstance()
    if (!hot || hot.isDestroyed) return

    const tableType = window.currentTableType || 'original'
    const unsaved = window.unsavedCells?.[tableType] || new Set()
    const history = historyCells.value          // 来自 useExcelEdit 的永久历史池

    const cellMeta = []

    /* -------- 唯一需要改的地方 ↓ ------- */
    // 1. 未保存（深红+红点）
    unsaved.forEach(key => {
      // key 已经是「pdf_excel_sheet_type_row,col」完整格式，直接解析即可
      const parsed = ExcelKey.parseCellKey(key)   // ⬅⬅⬅️ 用工具解析
      if (!parsed) return
      const { row, col } = parsed
      if (Number.isInteger(row) && Number.isInteger(col) && row >= 0 && col >= 0) {
        cellMeta.push({ row, col, className: 'unsaved-modified-cell' })
      }
    })

    // 2. 历史已保存（浅红，无点）
    history.forEach(key => {
      if (unsaved.has(key)) return               // 避免重复
      const parsed = ExcelKey.parseCellKey(key)  // ⬅⬅⬅️ 同样用工具解析
      if (!parsed) return
      const { row, col } = parsed
      if (Number.isInteger(row) && Number.isInteger(col) && row >= 0 && col >= 0) {
        cellMeta.push({ row, col, className: 'history-modified-cell' })
      }
    })
    /* -------- 改动结束 ↑ ------------- */

    if (cellMeta.length) {
      hot.updateSettings({ cell: cellMeta }, false)
      hot.render()
      console.log(`✅ 恢复标记完成：未保存${unsaved.size} 历史${history.size}`)
    }
  }

  const copyCellContent = () => {
    if (selectedCell.value.content) {
      navigator.clipboard.writeText(selectedCell.value.content)
        .then(() => {
          ElMessage.success('内容已复制到剪贴板')
        })
        .catch(err => {
          console.error('复制失败:', err)
          ElMessage.error('复制失败')
        })
    }
  }

  const editCellInModal = () => {
    ElMessage.info('编辑单元格功能')
  }

  // 事件处理
  const onFilter = (conditions) => {
    console.log('筛选条件:', conditions)
  }

  // 样式修复方法
  const debugCellStyles = () => {
    const hot = getSafeHotInstance()
    if (!hot) {
      console.log('❌❌ 表格实例无效')
      return
    }

    console.log('=== 单元格样式调试 ===')
    const cellConfig = hot.getSettings().cell || []
    console.log('📋📋 当前cell配置:', cellConfig.length, '条规则')
  }

  const forceFixSavedCellsStyles = () => {
    console.log('🔧🔧 强制修复已保存单元格样式...')

    const hot = getSafeHotInstance()
    if (!hot) return

    try {
      const cellConfig = []

      savedCells.value.forEach(cellKey => {
        const [row, col] = cellKey.split(',').map(Number)
        cellConfig.push({
          row: row,
          col: col,
          className: 'saved-modified-cell'
        })
      })

      if (isEditMode.value) {
        unsavedCells.value.forEach(cellKey => {
          const [row, col] = cellKey.split(',').map(Number)
          cellConfig.push({
            row: row,
            col: col,
            className: 'unsaved-modified-cell'
          })
        })
      }

      hot.updateSettings({
        cell: cellConfig
      }, false)

      hot.render()

      hot.updateSettings({
        cells: function(row, col, prop) {
          const cellKey = `${row},${col}`
          const base = {}

          if (savedCells.value.has(cellKey)) {
            base.className = 'saved-modified-cell'
          }

          if (isEditMode.value && unsavedCells.value.has(cellKey)) {
            base.className = base.className ?
              `${base.className} unsaved-modified-cell` :
              'unsaved-modified-cell'
          }

          return base
        }
      })

      hot.render()

      console.log('✅ 已保存单元格样式修复完成')

      setTimeout(() => {
        const savedInDOM = hot.rootElement.querySelectorAll('.saved-modified-cell')
        console.log('✅ 修复后验证:', {
          DOM中已保存单元格: savedInDOM.length,
          预期数量: savedCells.value.size
        })
      }, 300)

    } catch (error) {
      console.error('❌❌ 修复已保存单元格样式失败:', error)
    }
  }

  const markMultipleCellsAsSaved = (cells) => {
    console.log('📦📦 markMultipleCellsAsSaved 被调用:', cells?.length || 0)

    if (!cells || !Array.isArray(cells)) {
      console.warn('❌❌ 参数无效')
      return { success: false, message: '参数无效' }
    }

    const savedCellKeys = []

    cells.forEach(cell => {
      if (cell.row !== undefined && cell.col !== undefined) {
        savedCellKeys.push(`${cell.row},${cell.col}`)
      } else if (typeof cell === 'string' && cell.includes(',')) {
        savedCellKeys.push(cell)
      }
    })

    return markSavedCells(savedCellKeys)
  }

  const clearSavedMarks = () => {
    console.log('🧹🧹 清除所有已保存标记...')

    savedCells.value.clear()

    const hot = getSafeHotInstance()
    if (hot) {
      try {
        const currentCellConfig = hot.getSettings().cell || []
        const filteredConfig = currentCellConfig.filter(config => {
          const className = config.className || ''
          return !className.includes('saved-modified-cell')
        })

        hot.updateSettings({
          cell: filteredConfig
        }, false)

        hot.render()

        console.log('✅ 所有已保存标记已清除')
      } catch (error) {
        console.warn('⚠️ 清除已保存标记失败:', error)
      }
    }

    return { success: true, message: '已保存标记已清除' }
  }

  const getSavedCellsState = () => {
    return {
      savedCells: Array.from(savedCells.value),
      unsavedCells: Array.from(unsavedCells.value),
      modifiedCells: Array.from(modifiedCells.value),
      count: {
        saved: savedCells.value.size,
        unsaved: unsavedCells.value.size,
        total: modifiedCells.value.size
      }
    }
  }

  const debugSavedCells = () => {
    console.log('=== 已保存单元格调试信息 ===')

    const state = getSavedCellsState()
    console.log('📊📊 保存状态:', state.count)

    console.log('📋📋 已保存单元格详情:')
    state.savedCells.forEach((cellKey, index) => {
      console.log(`  ${index + 1}. ${cellKey}`)
    })

    const hot = getSafeHotInstance()
    if (hot) {
      const savedInDOM = hot.rootElement.querySelectorAll('.saved-modified-cell')
      console.log('🎯🎯 DOM中的已保存单元格:', savedInDOM.length)
    }

    console.log('=== 调试结束 ===')
  }

  const forceFixStyles = () => {
    console.log('🚀🚀 强制修复所有样式')

    const hot = getSafeHotInstance()
    if (hot) {
      hot.updateSettings({
        cell: []
      }, false)

      hot.render()

      setTimeout(() => {
        if (showEmptyCellsHighlight.value) {
          highlightEmptyCells()
        }

        console.log('✅ 强制修复完成')
      }, 200)
    }
  }

  const verifyTableInstance = () => {
    const hot = getSafeHotInstance()
    if (hot) {
      if (isEditMode.value && hot.getSettings().readOnly) {
        console.warn('⚠️ 表格状态不一致，正在修复...')
        hot.updateSettings({ readOnly: false }, false)
        hot.render()
      }
    } else {
      console.warn('❌❌ 表格实例验证失败')
    }
  }

  const monitorEditMode = () => {
    setInterval(() => {
      const hot = getSafeHotInstance()
      if (hot && isEditMode.value) {
        if (hot.getSettings().readOnly) {
          console.warn('⚠️ 检测到表格意外变为只读，正在修复...')
          hot.updateSettings({ readOnly: false }, false)
        }
      }
    }, 1000)
  }

  const getHotInstanceWithRetry = (maxRetries = 3, delay = 100) => {
    return new Promise((resolve) => {
      const tryGetInstance = (retryCount = 0) => {
        const hot = hotTable.value?.hotInstance

        if (hot && !hot.isDestroyed) {
          resolve(hot)
          return
        }

        if (retryCount < maxRetries) {
          setTimeout(() => tryGetInstance(retryCount + 1), delay)
        } else {
          console.warn(`❌❌ 获取实例失败，达到最大重试次数 ${maxRetries}`)
          resolve(null)
        }
      }
      tryGetInstance()
    })
  }

  const tryExpose = () => {
    const hot = hotTable.value?.hotInstance
    if (hot && !hot.isDestroyed) {
      window.__excelHotInstance = hot

      if (!hot._afterChangeBound) {
        hot._afterChangeBound = true
        hot.addHook('afterChange', onDataChange)
      }
    } else {
      setTimeout(tryExpose, 200)
    }
  }

  const restoreCellStates = (states) => {
    if (states.savedCells) {
      savedCells.value = new Set(states.savedCells)
    }
    if (states.unsavedCells) {
      unsavedCells.value = new Set(states.unsavedCells)
    }
    if (states.modifiedCells) {
      modifiedCells.value = new Set(states.modifiedCells)
    }

    forceFixSavedCellsStyles()

    return {
      success: true,
      message: '单元格状态已恢复'
    }
  }

  const onCellClick = (row, col) => {
    if (row < 0 || col < 0) {
      console.log('🟡🟡🟡 点击了列头或行头，跳过单元格显示');
      return; // 不处理列头/行头点击
    }

    updateSelectedCellDisplay(row, col)
    showCellContent.value = true
  }

  const setupCellClickListener = () => {
    const hot = getSafeHotInstance()
    if (!hot) return

    hot.removeHook('afterOnCellMouseDown')
    hot.addHook('afterOnCellMouseDown', (event, coords) => {
      if (event.button === 0) {
        onCellClick(coords.row, coords.col)
      }
    })
  }

  // 🔥🔥 新增：初始化求和监听器
  const initSelectionSumListener = () => {
    nextTick(() => {
      setTimeout(() => {
        try {
          setupSelectionSumListener()
        } catch (error) {
          console.error('❌ 设置选中求和监听器失败:', error)
        }
      }, 200)
    })
  }

  // 🔥🔥 修改：增强的清理函数
  const enhancedCleanup = () => {

    // 原有的清理逻辑
    if (typeof cleanup === 'function') {
      cleanup()
    }

    // 🔥🔥 新增：清理求和显示
    clearSelectionSum()

  }

  // 初始化
  onMounted(() => {
    nextTick(() => {
      tryExpose()

      const hot = getSafeHotInstance()
      if (hot) {
        setupCellClickListener()
        // 🔥🔥 新增：初始化求和监听器
        initSelectionSumListener()
      } else {
        setTimeout(() => {
          setupCellClickListener()
          initSelectionSumListener()
        }, 300)
      }
    })
  })

  onUnmounted(() => {
    enhancedCleanup()

    if (window.excelViewerInstance) {
      delete window.excelViewerInstance
    }

    if (hotTable.value?.hotInstance && !hotTable.value.hotInstance.isDestroyed) {
      try {
        hotTable.value.hotInstance.destroy()
      } catch (error) {
        console.log('ℹℹ️ 清理 Handsontable 实例:', error.message)
      }
    }
  })

  // 监听器
  watch(() => tableData.value, () => {
    console.log('📊📊 表格数据变化，重新检测空白单元格')
    nextTick(() => {
      if (showEmptyCellsHighlight.value) {
        highlightEmptyCells()
      }
    })
  }, { deep: true })

  watch(modifiedCells, (newCells, oldCells) => {
    console.log('🔄🔄 [HandsontableExcelViewer] modifiedCells 发生变化:', {
      新数量: newCells.size,
      旧数量: oldCells?.size || 0,
      是否有增长: newCells.size > (oldCells?.size || 0),
      是否在编辑模式: isEditMode.value
    })

    if (newCells.size === 0) {
      emit('data-changed', {
        totalChanges: 0,
        hasChanges: false,
        modifiedCellsCount: 0
      })
      return
    }

    const hot = getSafeHotInstance()
    if (!hot) {
      console.warn('❌❌ 表格实例无效，无法获取单元格值')
      return
    }

    const allChanges = []
    const newKeys = oldCells ? [] : Array.from(newCells.keys())
    if (oldCells) {
      newCells.forEach(key => {
        if (!oldCells.has(key)) {
          newKeys.push(key)
        }
      })
    }

    newCells.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      try {
        const newValue = hot.getDataAtCell(row, col)

        allChanges.push({
          row,
          col,
          newValue,
          cellKey,
          timestamp: Date.now()
        })

        if (newKeys.includes(cellKey)) {
          emit('cell-changed', {
            row,
            col,
            oldValue: null,
            newValue: newValue,
            source: 'watch-modifiedCells',
            timestamp: Date.now(),
            isEditMode: isEditMode.value
          })
        }
      } catch (error) {
        console.warn(`⚠️ 无法获取单元格 [${row},${col}] 的值:`, error)
      }
    })

    emit('data-changed', {
      totalChanges: newCells.size,
      hasChanges: true,
      allChanges: allChanges,
      modifiedCellsCount: newCells.size,
      isEditMode: isEditMode.value
    })

    console.log('📤📤 [HandsontableExcelViewer] 已发送修改事件:', {
      事件总数: 1 + newKeys.length,
      汇总事件: { totalChanges: newCells.size },
      单个事件数: newKeys.length
    })
  }, { deep: true })

  watch(hasChanges, (newValue, oldValue) => {
    console.log('📊📊 [HandsontableExcelViewer] hasChanges 变化:', {
      旧值: oldValue,
      新值: newValue
    })

    emit('edit-status-changed', {
      isEditMode: isEditMode.value,
      hasChanges: newValue,
      modifiedCellsCount: modifiedCellsCount.value,
      timestamp: Date.now()
    })
  })

  watch(isEditMode, (newValue, oldValue) => {
    console.log('🎛🎛️ [HandsontableExcelViewer] 编辑模式变化:', {
      旧模式: oldValue,
      新模式: newValue
    })

    emit('edit-status-changed', {
      isEditMode: newValue,
      hasChanges: hasChanges.value,
      modifiedCellsCount: modifiedCellsCount.value,
      timestamp: Date.now()
    })
  })

  return {
    // 状态
    showEmptyCellsHighlight,
    emptyCellsHighlightEnabled,
    showCellContent,
    selectedCell,

    // 🔥🔥 新增：求和功能状态
    selectionSum,
    calculateSelectionSum,
    clearSelectionSum,

    // 计算属性
    colWidths,
    computedColumns,

    // 方法
    handleCellChangeFromEdit,
    toggleEditMode,
    toggleEmptyCellsHighlight,
    showEmptyCellsDetail,
    setupCompleteSelectionListener,
    updateSelectedCellDisplay,
    copyCellContent,
    editCellInModal,
    onFilter,
    debugCellStyles,
    forceFixSavedCellsStyles,
    markMultipleCellsAsSaved,
    clearSavedMarks,
    getSavedCellsState,
    debugSavedCells,
    forceFixStyles,
    verifyTableInstance,
    monitorEditMode,
    getHotInstanceWithRetry,
    restoreCellStates,
    setupCellClickListener,

    // 暴露的方法
    exposedMethods: {
      exportData: () => {},
      verifyTableStructure: () => {},
      clearSelection,
      getSafeHotInstance,
      markSavedCells,
      markMultipleCellsAsSaved,
      forceFixSavedCellsStyles,
      clearSavedMarks,
      getSavedCellsState,
      debugSavedCells,
      restoreCellStates,
      toggleEditMode,
      forceFixStyles,
      restoreModifiedCellsStyle,
      // 🔥🔥 新增：求和功能方法
      calculateSelectionSum,
      clearSelectionSum
    }
  }
}