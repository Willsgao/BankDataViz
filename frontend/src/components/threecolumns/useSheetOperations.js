import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import excelDataCache from '@/utils/excelDataCache'
import { extractPageFromSheetName } from './tableUtils'
import { loadDraftFromIndexedDB } from '@/utils/draftDB'

/**
 * Sheet操作管理组合函数
 */
export function useSheetOperations() {
  // 状态
  const loadingSheets = ref(false)
  const loadingExcel = ref(false)
  const loadingFlat = ref(false)
  const currentPage = ref(1)
  const totalPages = ref(0)

  // 工具函数：生成表格列
  const generateTableColumns = (data) => {
    if (!data || data.length === 0) return []
    const firstRow = data[0]
    if (!firstRow) return []

    if (Array.isArray(firstRow)) {
      // 如果是数组格式
      return firstRow.map((_, index) => ({
        key: `column_${index}`,
        title: `列${index + 1}`,
        dataIndex: index
      }))
    } else if (typeof firstRow === 'object') {
      // 如果是对象格式
      return Object.keys(firstRow).map(key => ({
        key,
        title: key,
        dataIndex: key
      }))
    }

    return []
  }


  // 智能切换处理 - 完整修复版
const handleSmartToggle = async (
    selectedSheet,
    selectedPdf,
    selectedExcelFile,
    showFlatMode,
    excelDataRef,
    flatDataRef,
    toggleFlatModeFn
) => {
    if (!selectedSheet || !selectedPdf) {
        ElMessage.warning('请先选择表格')
        return
    }

    try {
        console.log('🔄🔄 用户手动切换模式...')

        // 🔥🔥🔥 关键修复：检查是否为扁平化文件并确保数据加载
        const isFlattenedFile = selectedExcelFile && /flattened_/i.test(selectedExcelFile)

        if (isFlattenedFile) {

            // 🔥 关键：确保 flatData 有数据
            if (flatDataRef.value.length === 0) {

                if (excelDataRef.value && excelDataRef.value.length > 0) {
                    // 深拷贝 excelData 到 flatData
                    flatDataRef.value = JSON.parse(JSON.stringify(excelDataRef.value))
                } else {
                    console.warn('⚠️ excelData 为空，无法复制数据')
                    ElMessage.warning('表格数据为空，无法切换模式')
                    return
                }
            } else {
                console.log('✅ flatData 已有数据，长度:', flatDataRef.value.length)
            }
        }

        // 执行模式切换
        await toggleFlatModeFn()

        // 延迟检查数据状态（可选）
        setTimeout(() => {
            const currentData = showFlatMode ? flatDataRef.value : excelDataRef.value

            if (currentData && currentData.length > 0) {
                const isFlattenedData = checkIfFlattenedData(currentData)

            }
        }, 300)

    } catch (error) {
        console.error('❌❌ 智能切换失败:', error)
        ElMessage.error('切换模式失败')
    }
}


  // 智能切换处理
  const handleSmartToggle11111 = async (
      selectedSheet,
      selectedPdf,
      selectedExcelFile,
      showFlatMode,      // ← 改名更清晰：这不是 ref，是布尔值
      excelDataRef,
      flatDataRef,
      toggleFlatModeFn
    ) => {
      if (!selectedSheet || !selectedPdf) {
        ElMessage.warning('请先选择表格')
        return
      }

      try {
        console.log('🔄🔄 用户手动切换模式...')
        await toggleFlatModeFn()

        setTimeout(() => {
          // 修复：直接使用 showFlatMode（布尔值），不加 .value
          const currentData = showFlatMode ? flatDataRef.value : excelDataRef.value

          if (currentData && currentData.length > 0) {
            const isFlattenedData = checkIfFlattenedData(currentData)

          }
        }, 500)
      } catch (error) {
        console.error('❌❌ 智能切换失败:', error)
      }
    }


  // 检查扁平化缓存
  const checkFlattenedCache = (pdfId, excelFile, sheetName) => {
    if (!pdfId || !excelFile || !sheetName) {
      return false
    }
    try {
      if (window.excelDataCache && typeof window.excelDataCache.getFlattenedData === 'function') {
        const cache = window.excelDataCache.getFlattenedData(pdfId, excelFile, sheetName)
        return !!(cache && cache.length > 0)
      }
      return false
    } catch (error) {
      console.warn('检查扁平化缓存失败:', error)
      return false
    }
  }


  // 切换扁平化模式
  const toggleFlatMode = async (
    selectedSheet,
    selectedPdf,
    selectedExcelFile,
    sheetStateManager,
    excelDataCache,
    getCachedFlattenedDataFn,
    convertToFlatDataFn,
    showFlatModeRef,
    flatDataRef,
    currentTableModeRef,
    excelDataRef,
    tableColumnsRef,
    loadExcelDataFn
  ) => {
    if (!selectedSheet || !selectedPdf) {
      ElMessage.warning('请先选择表格')
      return
    }

    if (showFlatModeRef.value) {
      currentTableModeRef.value = 'original'
      window.currentTableMode = 'original'

      sheetStateManager.setActiveContext(
        selectedPdf.id,
        selectedExcelFile,
        selectedSheet.name,
        'original'
      )

      await switchToOriginalMode(
        selectedPdf.id,
        selectedExcelFile,
        selectedSheet.name,
        excelDataCache,
        excelDataRef,
        tableColumnsRef,
        showFlatModeRef,
        loadExcelDataFn
      )
    } else {
      currentTableModeRef.value = 'flat'
      window.currentTableMode = 'flat'

      sheetStateManager.setActiveContext(
        selectedPdf.id,
        selectedExcelFile,
        selectedSheet.name,
        'flattened'
      )

      const cachedData = await getCachedFlattenedDataFn()
      if (cachedData && cachedData.length > 0) {
        flatDataRef.value = cachedData
        showFlatModeRef.value = true
        ElMessage.success('已切换到扁平化模式')
      } else {
        await convertToFlatDataFn()
      }
    }

    console.log('🔄🔄 表格模式切换:', {
      新模式: currentTableModeRef.value,
      显示扁平化: showFlatModeRef.value
    })
  }

  // 切换到原始模式
  const switchToOriginalMode = async (
    pdfId,
    excelFile,
    sheetName,
    excelDataCache,
    excelDataRef,
    tableColumnsRef,
    showFlatModeRef,
    loadExcelDataFn
  ) => {
    console.log('🔄🔄 切换到原始模式')
    const originalData = excelDataCache.getOriginalData(pdfId, excelFile, sheetName)

    if (!originalData || originalData.length === 0) {
      console.warn('原始数据缓存为空，重新加载')
      await loadExcelDataFn(sheetName, excelFile)
      return
    }

    excelDataRef.value = originalData
    showFlatModeRef.value = false
    ElMessage.success('已切换回原始表格模式')
  }


  // 替换 useSheetOperations.js 中的整个 selectSheet 函数
    const selectSheet = async (
      sheet,
      excelFileName,
      selectedPdf,
      selectedSheetRef,
      selectedExcelFileRef,
      sheetStateManager,
      excelDataRef,
      tableColumnsRef,
      flatDataRef,
      showFlatModeRef,
      currentTableModeRef,
      loadExcelDataFn,
      loadAllClassDataFn,
      loadingExcelRef,
      excelDataCache,
      dataManager
    ) => {

      // 参数验证
      if (!selectedSheetRef || !selectedExcelFileRef || !sheetStateManager) {
        console.error('❌❌❌❌❌❌❌❌ 关键参数缺失')
        throw new Error('函数参数不完整，无法选择表格')
      }

      if (!selectedPdf) {
        console.error('❌❌❌❌❌❌❌❌ selectedPdf参数为undefined或null')
        ElMessage.error('PDF参数缺失，请先选择PDF文件')
        return { success: false, error: 'PDF参数缺失' }
      }

      try {
        // 1. 重置状态
        console.log('🔄🔄🔄🔄🔄🔄🔄🔄 开始重置状态...')
        selectedSheetRef.value = { ...sheet, excel_file: excelFileName }
        selectedExcelFileRef.value = excelFileName

        if (currentTableModeRef && typeof currentTableModeRef.value !== 'undefined') {
          currentTableModeRef.value = 'original'
        }

        if (typeof window !== 'undefined') {
          window.currentTableMode = 'original'
        }

        // 2. 状态管理器上下文
        console.log('🔄🔄🔄🔄🔄🔄🔄🔄 设置状态管理器上下文...')
        sheetStateManager.setActiveContext(
          selectedPdf.id,
          excelFileName,
          sheet.name,
          'original'
        )

        // 3. 清除缓存
        const pdfId = selectedPdf.id

        if (excelDataCache && excelDataCache.deleteOriginalData) {
          excelDataCache.deleteOriginalData(pdfId, excelFileName, sheet.name)
        }
        if (excelDataCache && excelDataCache.deleteFlattenedData) {
          excelDataCache.deleteFlattenedData(pdfId, excelFileName, sheet.name)
        }

        const cacheKey = `${pdfId}_${excelFileName}_${sheet.name}`
        if (window.sheetDataCache) {
          delete window.sheetDataCache[cacheKey]
        }

        if (dataManager && dataManager.indexedDBManager) {
          try {
            await dataManager.indexedDBManager.deleteOriginalCache(pdfId, excelFileName, sheet.name)
            await dataManager.indexedDBManager.deleteFlattenedCache(pdfId, excelFileName, sheet.name)
          } catch (error) {
            console.warn('⚠️ 清除IndexedDB缓存失败:', error)
          }
        }

        // 4. 加载数据
        if (loadingExcelRef) {
          loadingExcelRef.value = true
        }

        try {
          if (sheet.name === '目录') {
            await loadAllClassDataFn(excelFileName)
          } else {
            const loadResult = await loadExcelDataFn(sheet.name, excelFileName, true)

            if (!loadResult.success) {
              throw new Error(loadResult.error || '加载数据失败')
            }

          }

          sheetStateManager.setData('original', excelDataRef.value)
        } finally {
          if (loadingExcelRef) {
            loadingExcelRef.value = false
          }
        }

        // 强制设置为原始模式
        showFlatModeRef.value = false
        if (currentTableModeRef) {
          currentTableModeRef.value = 'original'
        }
        if (typeof window !== 'undefined') {
          window.currentTableMode = 'original'
        }

        // 🔥🔥 关键：清空扁平化数据，避免后续误判
        if (flatDataRef && typeof flatDataRef.value !== 'undefined') {
          flatDataRef.value = []
        }

        return { success: true, source: 'api' }

      } catch (error) {
        console.error('❌❌❌❌❌❌❌❌ selectSheet 执行失败:', error)
        excelDataRef.value = []
        tableColumnsRef.value = []
        flatDataRef.value = []
        showFlatModeRef.value = false

        // 出错时也要确保状态正确
        if (currentTableModeRef) {
          currentTableModeRef.value = 'original'
        }
        if (typeof window !== 'undefined') {
          window.currentTableMode = 'original'
        }

        if (loadingExcelRef) {
          loadingExcelRef.value = false
        }

        ElMessage.error(`选择表格失败: ${error.message}`)
        return { success: false, error: error.message }
      }
    }

  // 加载Excel sheets列表
  const loadExcelSheets = async (
    pdfId,
    getApiUrl,
    excelFilesRef,
    loadingSheetsRef,
    selectSheetFn
  ) => {
    loadingSheetsRef.value = true
    excelFilesRef.value = []

    try {
      const response = await fetch(getApiUrl(`/excel-sheets/${pdfId}`))

      if (response.ok) {
        const data = await response.json()
        excelFilesRef.value = data.excel_files || []

        if (excelFilesRef.value.length > 0 && excelFilesRef.value[0].sheets.length > 0) {
          const firstFile = excelFilesRef.value[0]
          const firstSheet = firstFile.sheets[0]
          await selectSheetFn(firstSheet, firstFile.excel_file)
        } else {
          ElMessage.info('该PDF没有对应的表格数据')
        }
      } else {
        const errorText = await response.text()
        excelFilesRef.value = []
        ElMessage.warning('该PDF没有对应的Excel文件')
      }
    } catch (error) {
      console.error('加载Excel sheet列表失败:', error)
      excelFilesRef.value = []
      ElMessage.error('加载表格列表失败')
    } finally {
      loadingSheetsRef.value = false
    }
  }

  // 加载所有班级数据
  const loadAllClassData = async (
    excelFileName,
    selectedPdf,
    getApiUrl,
    excelDataRef,
    tableColumnsRef
  ) => {
    if (!selectedPdf) return

    try {
      const pdfId = selectedPdf.id
      const directoryResponse = await fetch(getApiUrl(`/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/目录`))

      if (!directoryResponse.ok) {
        throw new Error('无法加载目录数据')
      }

      const directoryData = await directoryResponse.json()
      const classSheets = directoryData.rows.map(row => ({
        sheetName: row.sheet_name,
        tableName: row.table_name
      })).filter(item => item.sheetName && item.sheetName !== '目录')

      const classDataPromises = classSheets.map(async (classItem) => {
        try {
          const response = await fetch(getApiUrl(`/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/${encodeURIComponent(classItem.sheetName)}`))
          if (response.ok) {
            const data = await response.json()
            return {
              className: classItem.sheetName,
              tableName: classItem.tableName,
              data: data.rows,
              totalRows: data.total_rows
            }
          }
        } catch (error) {
          console.error(`加载班级 ${classItem.sheetName} 数据失败:`, error)
          return null
        }
      })

      const allClassData = (await Promise.all(classDataPromises)).filter(Boolean)
      excelDataRef.value = mergeClassDataForDisplay(allClassData)
      window.allClassData = allClassData

      ElMessage.success(`已加载 ${allClassData.length} 个班级的数据`)
    } catch (error) {
      console.error('加载所有班级数据失败:', error)
      throw error
    }
  }

  // 合并班级数据用于显示
  const mergeClassDataForDisplay = (allClassData) => {
    return allClassData.map(classData => ({
      班级名称: classData.className,
      表格类型: classData.tableName,
      数据条数: classData.totalRows,
      平均总分: calculateClassAverageScore(classData.data)
    }))
  }

  // 计算班级平均分
  const calculateClassAverageScore = (classData) => {
    const scores = classData.map(row => parseInt(row.总分 || row['总分'] || 0)).filter(score => !isNaN(score))
    if (scores.length === 0) return 0
    return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
  }

  // 检查数据是否为扁平化格式
  const checkIfFlattenedData = (data) => {
    if (!data || data.length === 0) return false
    try {
      const firstRow = data[0] || {}
      const rowText = JSON.stringify(firstRow).toLowerCase()
      const flattenedColumnPatterns = ['银行名', '币种', '数值', '单位']
      const hasFlattenedColumns = flattenedColumnPatterns.some(pattern =>
        rowText.includes(pattern.toLowerCase())
      )
      return hasFlattenedColumns
    } catch (error) {
      console.error('数据检测失败:', error)
      return false
    }
  }

  // 获取按钮文本
  const getButtonText = (excelData) => {
    if (!excelData || excelData.length === 0) {
      return '扁平化'
    }
    const isFlattenedData = checkIfFlattenedData(excelData)

    return isFlattenedData ? '二维化' : '扁平化'
  }

  // 智能设置表格模式
  const autoSetTableMode = (tableData, sheetName, showFlatModeRef, currentTableModeRef) => {
    if (!tableData || tableData.length === 0) return

    const isFlattenedData = checkIfFlattenedData(tableData)

    if (isFlattenedData !== showFlatModeRef.value) {
      showFlatModeRef.value = isFlattenedData
    } else {
      console.log('✅ 按钮状态正确，无需纠正')
    }
  }

  return {
    // 状态
    loadingSheets,
    loadingExcel,
    loadingFlat,
    currentPage,
    totalPages,

    // 方法
    selectSheet,
    toggleFlatMode,
    switchToOriginalMode,
    loadExcelSheets,
    loadAllClassData,
    mergeClassDataForDisplay,
    calculateClassAverageScore,
    checkIfFlattenedData,
    getButtonText,
    handleSmartToggle,
    generateTableColumns,
    autoSetTableMode,
    checkFlattenedCache
  }
}