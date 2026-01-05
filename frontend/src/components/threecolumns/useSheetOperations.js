               import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import excelDataCache from '@/utils/excelDataCache'
import { extractPageFromSheetName } from './tableUtils'
import { loadDraftFromIndexedDB } from '@/utils/draftDB'

/**
 * Sheet操作管理组合函数
 */
export function useSheetOperations(generateTableColumns) {
  // 状态
  const loadingSheets = ref(false)
  const loadingExcel = ref(false)
  const loadingFlat = ref(false)
  const currentPage = ref(1)
  const totalPages = ref(0)


  // 检查扁平化缓存的辅助函数
    const checkFlattenedCache = (pdfId, excelFile, sheetName) => {
      if (!pdfId || !excelFile || !sheetName) {
        return false
      }
      try {
        // 从缓存系统中检查
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
  loadAllClassDataFn
) => {
      console.log('🔄 选择sheet:', {
        sheet名称: sheet.name,
        excel文件: excelFileName,
        当前PDF: selectedPdf?.id,
        currentTableModeRef存在: !!currentTableModeRef
      })

      // 🔥🔥🔥 关键修复1：添加安全检查
      if (!selectedSheetRef || !selectedExcelFileRef || !sheetStateManager) {
        console.error('❌❌❌ 关键参数缺失:', {
          selectedSheetRef: !!selectedSheetRef,
          selectedExcelFileRef: !!selectedExcelFileRef,
          sheetStateManager: !!sheetStateManager,
          currentTableModeRef: !!currentTableModeRef
        })
        throw new Error('函数参数不完整，无法选择表格')
      }

      // 🔥🔥🔥 关键修复2：检查PDF参数
      if (!selectedPdf) {
        console.error('❌❌❌ selectedPdf 参数为 undefined 或 null')
        ElMessage.error('PDF参数缺失，请先选择PDF文件')
        return { success: false, error: 'PDF参数缺失' }
      }

      try {
        /* ---------- 1. 重置状态 ---------- */
        console.log('🔄 开始重置状态...')

        selectedSheetRef.value = { ...sheet, excel_file: excelFileName }
        selectedExcelFileRef.value = excelFileName

        // 🔥 安全设置 currentTableModeRef
        if (currentTableModeRef && typeof currentTableModeRef.value !== 'undefined') {
          //currentTableModeRef.value = 'original'
          console.log('✅ currentTableModeRef 设置为: original')
        } else {
          console.warn('⚠️ currentTableModeRef 不可用，跳过设置')
        }

        // 🔥 安全设置 window.currentTableMode
        if (typeof window !== 'undefined') {
          window.currentTableMode = 'original'
          console.log('✅ window.currentTableMode 设置为: original')
        }


        console.log('✅ 状态重置完成')

        /* ---------- 2. 状态管理器上下文 ---------- */
        console.log('🔄 设置状态管理器上下文...')
        sheetStateManager.setActiveContext(
          selectedPdf.id,
          excelFileName,
          sheet.name,
          'original'
        )
        console.log('✅ 上下文设置完成')

        /* ---------- 3. 优先读本地草稿 ---------- */
        const draftKey = `excel_draft_${selectedPdf.id}_${excelFileName}_${sheet.name}_original`
        const draftRaw = localStorage.getItem(draftKey)

        if (draftRaw) {
          try {
            const draft = JSON.parse(draftRaw)
            if (draft.data && Array.isArray(draft.data)) {
              console.log('📦 发现本地草稿', new Date(draft.timestamp).toLocaleTimeString())

              // 直接用草稿数据
              excelDataRef.value = draft.data
              tableColumnsRef.value = generateTableColumns(draft.data)
              sheetStateManager.setData('original', draft.data)

              // 把修改记录还原（可选）
              if (draft.modifications?.length) {
                draft.modifications.forEach(m =>
                  sheetStateManager.recordCellChange(m.row, m.col, m.oldValue, m.newValue, 'original')
                )
              }

              ElMessage.success('已恢复本地草稿')
              console.log('✅ 草稿恢复完成')
              return { success: true, source: 'draft' } // ⚠️ 提前结束，不再请求接口
            }
          } catch (e) {
            console.warn('⚠️ 草稿解析失败，回退到接口', e)
          }
        }

        /* ---------- 4. 无草稿 → 正常加载 ---------- */
        console.log('🔄 无草稿，开始正常加载数据...')
        loadingExcel.value = true

        try {
          if (sheet.name === '目录') {
              console.log('📁 加载目录数据...')
              await loadAllClassDataFn(excelFileName)
            } else {
              console.log('📊 加载普通表格数据...')

              // 🔥 先检查是否有扁平化缓存
              const hasFlattenedCache = window.excelDataCache?.hasFlattenedData?.(selectedPdf.id, excelFileName, sheet.name)
              console.log(`📊 扁平化缓存检查: ${hasFlattenedCache ? '有' : '无'}`)


              if (hasFlattenedCache) {
                  // 有缓存，加载扁平化数据
                  console.log('🎯 加载扁平化数据')
                  await loadExcelDataFn(sheet.name, excelFileName, 'flattened')

                  // 设置扁平化模式
                  if (currentTableModeRef && typeof currentTableModeRef.value !== 'undefined') {
                    currentTableModeRef.value = 'flattened'
                  }

                  // 立即激活扁平化模式
                  showFlatModeRef.value = true
                  console.log('✅ 立即激活扁平化模式（有缓存）')

                } else {
                  // 无缓存，但尝试加载扁平化数据
                  console.log('🎯 尝试加载扁平化数据')
                  await loadExcelDataFn(sheet.name, excelFileName, 'flattened')

                  // 检查是否成功加载到扁平化数据
                  if (flatDataRef.value && flatDataRef.value.length > 0) {
                    // 成功加载到扁平化数据
                    if (currentTableModeRef && typeof currentTableModeRef.value !== 'undefined') {
                      currentTableModeRef.value = 'flattened'
                    }
                    showFlatModeRef.value = true
                    console.log('✅ 成功加载扁平化数据，激活扁平化模式')
                  } else {
                    // 没有扁平化数据，加载原始数据
                    console.log('🔄 无扁平化数据，加载原始数据')
                    await loadExcelDataFn(sheet.name, excelFileName, 'original')

                    if (currentTableModeRef && typeof currentTableModeRef.value !== 'undefined') {
                      currentTableModeRef.value = 'original'
                    }
                    showFlatModeRef.value = false
                    console.log('✅ 设置为原始模式')
                  }
                }



            }

          // 此时 excelDataRef 已被 loadExcelDataFn 填充
          sheetStateManager.setData('original', excelDataRef.value)
          // 🔥 根据当前模式设置数据

          console.log('✅ 数据加载完成，数据长度:', excelDataRef.value?.length || 0)

        } catch (err) {
          console.error('❌ 加载失败', err)
          ElMessage.error(err.message)
          excelDataRef.value = []
          throw err // 重新抛出错误

        } finally {
          loadingExcel.value = false
        }

        console.log('✅✅✅ selectSheet 完成')

        // 🔥🔥🔥 关键修复：检查是否有扁平化数据并激活扁平化模式
        setTimeout(() => {
          if (flatDataRef.value && flatDataRef.value.length > 0) {
            // 有扁平化数据，激活扁平化模式
            showFlatModeRef.value = true
            console.log('🔄 自动激活扁平化模式（检测到扁平化数据）')
          } else {
            // 没有扁平化数据，使用原始模式
            showFlatModeRef.value = false
            console.log('🔄 设置为原始模式')
          }
        }, 100)


        return { success: true, source: 'api' }

      } catch (error) {
        console.error('❌❌❌ selectSheet 执行失败:', error)
        // 确保在出错时清理状态
        excelDataRef.value = []
        tableColumnsRef.value = []
        flatDataRef.value = []
        showFlatModeRef.value = false

        throw error // 重新抛出错误
      }
    }



  /**
   * 切换扁平化模式
   */
  const toggleFlatMode = async (selectedSheet, selectedPdf, selectedExcelFile,
                               sheetStateManager, excelDataCache, getCachedFlattenedDataFn,
                               convertToFlatDataFn, showFlatModeRef, flatDataRef,
                               currentTableModeRef, excelDataRef, tableColumnsRef, loadExcelDataFn) => {
    if (!selectedSheet || !selectedPdf) {
      ElMessage.warning('请先选择表格')
      return
    }

    // 更新模式状态
    if (showFlatModeRef.value) {
      // 切换到原始模式
      currentTableModeRef.value = 'original'
      window.currentTableMode = 'original'

      // 更新状态管理器上下文
      sheetStateManager.setActiveContext(
        selectedPdf.id,
        selectedExcelFile,
        selectedSheet.name,
        'original'
      )

      await switchToOriginalMode(selectedPdf.id, selectedExcelFile, selectedSheet.name,
                                excelDataCache, excelDataRef, tableColumnsRef,
                                showFlatModeRef, loadExcelDataFn)
    } else {
      // 切换到扁平化模式
      currentTableModeRef.value = 'flat'
      window.currentTableMode = 'flat'

      // 更新状态管理器上下文
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

    console.log('🔄 表格模式切换:', {
      新模式: currentTableModeRef.value,
      显示扁平化: showFlatModeRef.value
    })
  }

  /**
   * 切换到原始模式
   */
  const switchToOriginalMode = async (pdfId, excelFile, sheetName, excelDataCache,
                                     excelDataRef, tableColumnsRef, showFlatModeRef,
                                     loadExcelDataFn) => {
    console.log('🔄 切换到原始模式')

    // 从缓存获取原始数据
    const originalData = excelDataCache.getOriginalData(pdfId, excelFile, sheetName)

    if (!originalData || originalData.length === 0) {
      console.warn('原始数据缓存为空，重新加载')
      // 重新加载数据
      await loadExcelDataFn(sheetName, excelFile)
      return
    }

    // 显示原始数据
    excelDataRef.value = originalData
    // 注意：这里需要generateTableColumns函数，可能需要传入或重构
    showFlatModeRef.value = false

    ElMessage.success('已切换回原始表格模式')
  }

  /**
   * 加载Excel sheets列表
   */
  const loadExcelSheets = async (pdfId, getApiUrl, excelFilesRef, loadingSheetsRef,
                                selectSheetFn) => {
    console.log('开始加载Excel sheets，PDF ID:', pdfId)
    loadingSheetsRef.value = true
    excelFilesRef.value = []

    try {
      const response = await fetch(getApiUrl(`/excel-sheets/${pdfId}`))
      console.log('Excel sheets API响应状态:', response.status)

      if (response.ok) {
        const data = await response.json()
        console.log('Excel sheets API返回数据:', data)
        excelFilesRef.value = data.excel_files || []
        console.log('解析后的Excel文件列表:', excelFilesRef.value)

        // 如果有sheet，默认选中第一个文件的第一个sheet
        if (excelFilesRef.value.length > 0 && excelFilesRef.value[0].sheets.length > 0) {
          const firstFile = excelFilesRef.value[0]
          const firstSheet = firstFile.sheets[0]
          console.log('默认选中第一个sheet:', firstSheet, '来自文件:', firstFile.excel_file)
          await selectSheetFn(firstSheet, firstFile.excel_file)
        } else {
          console.log('没有找到Excel sheets或sheets为空')
          ElMessage.info('该PDF没有对应的表格数据')
        }
      } else {
        console.log('Excel sheets API请求失败，状态码:', response.status)
        const errorText = await response.text()
        console.log('错误响应:', errorText)
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

  /**
   * 加载所有班级数据（目录特殊处理）
   */
  const loadAllClassData = async (excelFileName, selectedPdf, getApiUrl,
                                 excelDataRef, tableColumnsRef) => {
    if (!selectedPdf) return

    try {
      const pdfId = selectedPdf.id
      // 首先获取目录信息
      const directoryResponse = await fetch(getApiUrl(`/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/目录`))

      if (!directoryResponse.ok) {
        throw new Error('无法加载目录数据')
      }

      const directoryData = await directoryResponse.json()

      // 从目录中获取所有班级sheet名称
      const classSheets = directoryData.rows.map(row => ({
        sheetName: row.sheet_name,
        tableName: row.table_name
      })).filter(item => item.sheetName && item.sheetName !== '目录')

      console.log('发现班级sheets:', classSheets)

      // 并行加载所有班级数据
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

      // 设置合并后的数据（用于显示）
      excelDataRef.value = mergeClassDataForDisplay(allClassData)
      // 注意：需要generateDirectoryTableColumns函数，可能需要传入或重构

      // 保存所有班级数据用于分析
      window.allClassData = allClassData

      ElMessage.success(`已加载 ${allClassData.length} 个班级的数据`)

    } catch (error) {
      console.error('加载所有班级数据失败:', error)
      throw error
    }
  }

  /**
   * 合并班级数据用于显示
   */
  const mergeClassDataForDisplay = (allClassData) => {
    return allClassData.map(classData => ({
      班级名称: classData.className,
      表格类型: classData.tableName,
      数据条数: classData.totalRows,
      平均总分: calculateClassAverageScore(classData.data)
    }))
  }

  /**
   * 计算班级平均分
   */
  const calculateClassAverageScore = (classData) => {
    const scores = classData.map(row => parseInt(row.总分 || row['总分'] || 0)).filter(score => !isNaN(score))
    if (scores.length === 0) return 0
    return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
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
    calculateClassAverageScore
  }
}