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

  /**
   * 选择Sheet并加载数据
   */
  const selectSheet = async (sheet, excelFileName, selectedPdf, selectedSheetRef,
                           selectedExcelFileRef, sheetStateManager, excelDataRef,
                           tableColumnsRef, flatDataRef, showFlatModeRef,
                           currentTableModeRef, loadExcelDataFn, loadAllClassDataFn) => {
    console.log('🔄 选择sheet:', {
      sheet名称: sheet.name,
      excel文件: excelFileName,
      当前PDF: selectedPdf?.id
    })

    // ============ 第1步：重置所有状态 ============
    // 1.1 更新UI状态
    selectedSheetRef.value = { ...sheet, excel_file: excelFileName }
    selectedExcelFileRef.value = excelFileName

    // 1.2 重置显示模式为原始表
    currentTableModeRef.value = 'original'
    window.currentTableMode = 'original'
    showFlatModeRef.value = false
    flatDataRef.value = []
    console.log('📊 显示模式已重置为原始表')

    // ============ 第2步：设置状态管理器上下文 ============
    if (!selectedPdf) {
      console.error('❌ 无法设置上下文：没有选中的PDF')
      ElMessage.error('请先选择PDF文件')
      return
    }

    // 2.1 设置状态管理器上下文
    sheetStateManager.setActiveContext(
      selectedPdf.id,
      excelFileName,
      sheet.name,
      'original'  // 新sheet总是从原始表开始
    )

    // 2.2 检查该sheet是否有历史修改记录（只做检查，不自动恢复）
    const sheetState = sheetStateManager.getActiveSheetState()
    if (sheetState) {
      const originalUnsaved = sheetState.stats.original.unsavedCount
      const flattenedUnsaved = sheetState.stats.flattened.unsavedCount

      if (originalUnsaved > 0 || flattenedUnsaved > 0) {
        console.log('📝 检测到历史修改记录:', {
          原始表未保存: originalUnsaved,
          扁平化表未保存: flattenedUnsaved
        })
        // 只在控制台提示，不自动恢复
      }
    }

    // ============ 第3步：处理PDF页面跳转 ============
    const pageNum = extractPageFromSheetName(sheet.name)
    if (pageNum) {
      console.log(`📄 从sheet名称提取到页码: ${pageNum}`)
      // PDF页面跳转会在数据加载完成后触发
    }

    // 0. 优先读本地草稿
    const draft = await loadDraftFromIndexedDB(selectedPdf.id, excelFileName, sheet.name, 'original')
    if (draft && draft.data) {
      console.log('✅ 使用本地草稿', new Date(draft.savedAt).toLocaleTimeString())
      // 直接渲染草稿数据
      excelDataRef.value = draft.data
      generateTableColumns(draft.data) // 你原来就有的函数
      sheetStateManager.setData('original', draft.data)
      ElMessage.success('已恢复本地草稿')
      loadingExcel.value = false
      return // ⚠️ 关键：提前结束，不再走下面 fetch
    }

    // ============ 第4步：加载表格数据 ============
    loadingExcel.value = true

    try {
      // 4.1 根据sheet类型加载数据
      if (sheet.name === '目录') {
        console.log('📁 加载目录数据...')
        await loadAllClassDataFn(excelFileName)

        // 保存目录数据到状态管理器
        if (excelDataRef.value.length > 0) {
          sheetStateManager.setData('original', excelDataRef.value)
          console.log(`✅ 目录数据已保存到状态管理器: ${excelDataRef.value.length}行`)
        }
      } else {
        console.log(`📊 加载普通sheet数据: ${sheet.name}`)
        await loadExcelDataFn(sheet.name, excelFileName)

        // excelData已在loadExcelData中更新并保存到状态管理器
      }

      // ============ 第5步：加载完成后处理 ============
      console.log('✅ 数据加载完成，开始后续处理...')

      // 5.1 检查状态管理器中的未保存修改
      const context = sheetStateManager.getActiveContext()
      if (context) {
        const unsavedModifications = sheetStateManager.getModifications(context.tableType)
          .filter(mod => !mod.saved)

        if (unsavedModifications.length > 0) {
          console.log('💡 检测到未保存修改，等待用户手动恢复:', {
            表类型: context.tableType,
            未保存数: unsavedModifications.length
          })

          // 可选：显示一个非模态提示
          setTimeout(() => {
            ElMessage.info({
              message: `检测到 ${unsavedModifications.length} 处未保存修改，可点击"恢复修改"按钮恢复`,
              duration: 5000,
              showClose: true
            })
          }, 1000)
        }
      }

      // 5.2 显示成功消息
      ElMessage.success(`已加载表格: ${sheet.name}`)

      // 5.3 如果有PDF页码，跳转
      if (pageNum && pageNum !== currentPage.value) {
        setTimeout(() => {
          currentPage.value = pageNum
          console.log(`🎯 PDF已跳转到第 ${pageNum} 页`)
          ElMessage.info(`PDF已跳转到第 ${pageNum} 页`)
        }, 300)
      }

    } catch (error) {
      console.error('❌ 加载表格数据失败:', error)
      ElMessage.error(`加载表格数据失败: ${error.message}`)

      // 重置数据
      excelDataRef.value = []
      tableColumnsRef.value = []
      flatDataRef.value = []

      // 重置状态管理器数据
      if (sheetStateManager.getActiveContext()?.sheetName === sheet.name) {
        sheetStateManager.setData('original', [])
        sheetStateManager.setData('flattened', [])
      }

    } finally {
      loadingExcel.value = false
      console.log('🏁 selectSheet 流程结束')
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