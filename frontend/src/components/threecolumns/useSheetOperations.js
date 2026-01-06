import { ref, computed } from 'vue'
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


   const handleSmartToggle = async (
      selectedSheet,
      selectedPdf,
      selectedExcelFile,
      showFlatModeRef,
      excelDataRef,
      flatDataRef,
      toggleFlatModeFn
    ) => {
      if (!selectedSheet || !selectedPdf) {
        ElMessage.warning('请先选择表格')
        return
      }

      try {
        console.log('🔄 用户手动切换模式...')

        // 1. 先手动切换（用户点击）
        await toggleFlatModeFn()

        // 2. 等待新数据加载完成
        setTimeout(() => {
          // 3. 获取切换后的数据
          const currentData = showFlatModeRef.value ? flatDataRef.value : excelDataRef.value

          if (currentData && currentData.length > 0) {
            console.log('🔍 切换后检查数据真实状态...')

            // 4. 判断数据的真实状态
            const isFlattenedData = checkIfFlattenedData(currentData)
            console.log('📊 数据真实状态判断:', {
              数据特征: isFlattenedData ? '扁平化数据' : '原始数据',
              当前按钮状态: showFlatModeRef.value ? '二维化' : '扁平化',
              应该的按钮状态: isFlattenedData ? '二维化' : '扁平化'
            })

            // 5. 如果状态不一致，自动纠正
            if (isFlattenedData !== showFlatModeRef.value) {
              console.log('🔄 状态不一致，自动纠正按钮状态')
              toggleFlatModeFn() // 再次切换，纠正到正确状态
            } else {
              console.log('✅ 状态一致，保持当前按钮状态')
            }
          }
        }, 500) // 等待数据加载
      } catch (error) {
        console.error('❌ 智能切换失败:', error)
        toggleFlatModeFn() // 出错时回退
      }
    }


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


  // 🔥🔥🔥 新增：智能判断相关函数
  /**
   * 智能判断表格类型
   */
  const detectTableType = (tableData) => {
      if (!tableData || tableData.length === 0) {
          return {
              type: 'unknown',
              confidence: 0,
              reason: '空数据'
          };
      }

      console.log('🔍🔍 开始智能判断表格类型...');

      // 1. 检查行标记（A列）
      const hasRowMarkers = checkRowMarkers(tableData);
      console.log('   - 行标记检测:', hasRowMarkers);

      // 2. 检查列标记（首行）
      const hasColumnMarkers = checkColumnMarkers(tableData);
      console.log('   - 列标记检测:', hasColumnMarkers);

      // 3. 检查交叉结构
      const hasCrossStructure = checkCrossStructure(tableData);
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



    // 🔥🔥🔥 修正：根据第一行表头文本判断按钮文本
    const getButtonText = computed(() => {
      if (!props.excelData || props.excelData.length === 0) {
        return '扁平化' // 默认文本
      }

      // 分析数据特征
      const isFlattenedData = checkIfFlattenedData(props.excelData)

      console.log('🎯 按钮文本判断:', {
        数据行数: props.excelData.length,
        数据特征: isFlattenedData ? '扁平化数据' : '原始数据',
        按钮文本: isFlattenedData ? '二维化' : '扁平化'
      })

      // 如果数据是扁平化特征，按钮显示"二维化"；否则显示"扁平化"
      return isFlattenedData ? '二维化' : '扁平化'
    })


    const checkIfFlattenedData = (data) => {
        if (!data || data.length === 0) return false

        try {
            console.log('🔍 检查数据是否为扁平化格式...')

            const firstRow = data[0] || {}
            console.log('📊 第一行数据:', firstRow)

            // 🔥🔥🔥 修复：直接检查第一行内容
            const rowText = JSON.stringify(firstRow).toLowerCase()
            console.log('📊 第一行文本:', rowText)

            // 🔥🔥🔥 扁平化数据特征：包含"银行名"、"币种"等字段
            const flattenedColumnPatterns = ['银行名', '币种', '数值', '单位']
            const hasFlattenedColumns = flattenedColumnPatterns.some(pattern =>
                rowText.includes(pattern.toLowerCase())
            )

            console.log('📊 扁平化列名检测:', {
                检测字段: flattenedColumnPatterns,
                检测结果: hasFlattenedColumns
            })

            // 🔥🔥🔥 关键修复：返回正确的布尔值
            return hasFlattenedColumns

        } catch (error) {
            console.error('❌ 数据检测失败:', error)
            return false
        }
    }

    const autoSetTableMode = (tableData, sheetName, showFlatModeRef, currentTableModeRef) => {
        if (!tableData || tableData.length === 0) return

        console.log('🔍 智能设置显示模式...')

        // 🔥🔥🔥 修复调用逻辑
        const isFlattenedData = checkIfFlattenedData(tableData)

        console.log('🎯 正确判断:', {
            数据特征: isFlattenedData ? '扁平化数据' : '原始数据',
            应该显示: isFlattenedData ? '二维化' : '扁平化',  // ✅ 修复逻辑
            当前显示: showFlatModeRef.value ? '二维化' : '扁平化'
        })

        // 🔥🔥🔥 修复：扁平化数据应该显示"二维化"按钮
        if (isFlattenedData !== showFlatModeRef.value) {
            console.log('🔄 纠正按钮状态')
            showFlatModeRef.value = isFlattenedData  // ✅ 正确逻辑
        } else {
            console.log('✅ 按钮状态正确，无需纠正')
        }
    }


  /**
   * 智能切换显示模式（带提示）
   */
  const smartToggleTableMode = (selectedSheet, selectedPdf, selectedExcelFile,
                               sheetStateManager, excelDataCache, getCachedFlattenedDataFn,
                               convertToFlatDataFn, showFlatModeRef, flatDataRef,
                               currentTableModeRef, excelDataRef, tableColumnsRef, loadExcelDataFn) => {
      if (!selectedSheet || !selectedPdf) {
          ElMessage.warning('请先选择表格');
          return;
      }

      // 获取当前数据
      const currentData = showFlatModeRef.value ? flatDataRef.value : excelDataRef.value;
      const detection = detectTableType(currentData);

      // 显示智能建议
      if (detection.confidence >= 0.7) {
          ElMessage.info({
              message: `当前数据更适合${detection.type === 'flattened' ? '扁平化' : '原始'}显示`,
              description: `系统建议: ${detection.reason}`,
              duration: 2000
          });
      }

      // 调用原有的切换逻辑
      return toggleFlatMode(selectedSheet, selectedPdf, selectedExcelFile,
                          sheetStateManager, excelDataCache, getCachedFlattenedDataFn,
                          convertToFlatDataFn, showFlatModeRef, flatDataRef,
                          currentTableModeRef, excelDataRef, tableColumnsRef, loadExcelDataFn);
  };

  // 🔥🔥🔥 修改现有的 selectSheet 函数，集成智能判断
  const originalSelectSheet = selectSheet;



  const selectSheetWithSmartDetection = async (...args) => {
    console.log('🎯 带智能判断的Sheet选择...')

    // 调用原有逻辑
    const result = await originalSelectSheet(...args)

    // 从参数中提取需要的引用
    const [sheet, excelFileName, selectedPdf, selectedSheetRef, selectedExcelFileRef,
           sheetStateManager, excelDataRef, tableColumnsRef, flatDataRef,
           showFlatModeRef, currentTableModeRef] = args

    // 🔥🔥🔥 关键修复：检查原始数据，而不是扁平化数据
    if (result.success && excelDataRef.value && excelDataRef.value.length > 0) {
        console.log('🎯 Sheet选择完成，开始智能判断显示模式...')

        // 延迟执行，确保UI已更新
        setTimeout(() => {
            // 🔥🔥🔥 修复调用逻辑
            const isFlattenedData = checkIfFlattenedData(excelDataRef.value)

            console.log('🎯 正确判断:', {
                数据特征: isFlattenedData ? '扁平化数据' : '原始数据',
                应该显示: isFlattenedData ? '二维化' : '扁平化',  // ✅ 修复逻辑
                当前显示: showFlatModeRef.value ? '二维化' : '扁平化'
            })

            // 🔥🔥🔥 修复：扁平化数据应该显示"二维化"按钮
            if (isFlattenedData !== showFlatModeRef.value) {
                console.log('🔄 纠正按钮状态')
                showFlatModeRef.value = isFlattenedData  // ✅ 正确逻辑
            } else {
                console.log('✅ 按钮状态正确，无需纠正')
            }
        }, 200)
    }

    return result
}


  return {
    // 状态
    loadingSheets,
    loadingExcel,
    loadingFlat,
    currentPage,
    totalPages,
    // 方法
    selectSheet: selectSheetWithSmartDetection,
    toggleFlatMode,
    switchToOriginalMode,
    loadExcelSheets,
    loadAllClassData,
    mergeClassDataForDisplay,
    calculateClassAverageScore,
    detectTableType,
    smartToggleTableMode,
    checkRowMarkers,
    checkColumnMarkers,
    checkCrossStructure,
    checkIfFlattenedData,
    getButtonText,
    handleSmartToggle

  }
}