import { ref, computed, inject } from 'vue'
import { ElMessage } from 'element-plus'
import { getApiUrl, getBackendUrl } from '@/utils/config'


/**
 * 三列页面主逻辑组合函数
 */
export function useThreeColumnPage() {
  // 注入的搜索数据
  const searchResults = inject('searchResults', ref([]))
  const isSearching = inject('isSearching', ref(false))

  // 主要状态
  const selectedPdf = ref(null)
  const pdfUrl = ref('')
  const downloadLoading = ref(false)
  const isMiddleCollapsed = ref(false)
  const showFlatMode = ref(true)
  const flatData = ref([])
  const sheetList = ref([])
  const excelFiles = ref([])
  const selectedSheet = ref(null)
  const selectedExcelFile = ref('')
  const excelData = ref([])
  const tableColumns = ref([])
  const currentTableMode = ref('original')
  const hasGlobalChanges = ref(false)
  const globalModifiedCount = ref(0)

  // 计算属性
  const filteredPdfCount = computed(() => searchResults?.value?.length || 0)  // ✅ 安全访问
  const tableCount = computed(() => {
    return excelFiles.value.reduce((total, file) => total + file.sheets.length, 0)
  })
  const hasChanges = computed(() => {
    return globalModifiedCount.value > 0
  })

  /**
   * 选择PDF文件
   */
  const selectPdf = async (pdf) => {
    console.log('选中PDF:', pdf)
    selectedPdf.value = pdf
    selectedSheet.value = null
    excelFiles.value = []
    excelData.value = []
    tableColumns.value = []

    try {
      // 获取PDF文件的URL
      //let fileId = pdf.id
      let fileId = pdf.disk_name || pdf.id
      if (!fileId) {
        // 如果没有ID，尝试通过文件名查找
        console.log('PDF没有ID，尝试通过文件名查找:', pdf.name)
        const fileResponse = await fetch(getApiUrl(`/search-pdf?keyword=${encodeURIComponent(pdf.name)}`))

        if (fileResponse.ok) {
          const fileData = await fileResponse.json()
          // const matchedFile = fileData.files.find(f => f.name === pdf.name)
          const matchedFile = fileData.files.find(f => f.name === pdf.name || f.disk_name === pdf.disk_name)
          if (matchedFile && matchedFile.id) {
            fileId = matchedFile.id
            console.log('通过文件名找到ID:', fileId)
          }
        }
      }

      if (fileId) {
        // 通过文件ID获取PDF内容
        pdfUrl.value = getBackendUrl(`/api/file-by-id/${fileId}`)
        console.log('设置PDF预览URL:', pdfUrl.value)

        ElMessage.success(`已加载PDF: ${pdf.name}`)
        return { success: true, fileId }
      } else {
        // 备用方案：通过文件名获取
        console.log('使用文件名作为备用方案:', pdf.name)
        pdfUrl.value = `/api/file/${encodeURIComponent(pdf.name)}`
        console.log('设置备用PDF预览URL:', pdfUrl.value)

        ElMessage.success(`已加载PDF: ${pdf.name}`)
        return { success: true }
      }
    } catch (error) {
      console.error('加载PDF失败:', error)
      ElMessage.error('加载PDF失败')
      return { success: false, error }
    }
  }



  // 在 useThreeColumnPage.js 中添加
  const loadFromAPI111 = async (fileId, excelFileName, sheetName) => {
      try {
        console.log('🌐🌐 调用API加载数据:', { fileId, excelFileName, sheetName });

        const encodedExcelFile = encodeURIComponent(excelFileName);
        const encodedSheetName = encodeURIComponent(sheetName);

        const response = await fetch(
          `/api/excel-data/${fileId}/${encodedExcelFile}/${encodedSheetName}`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();

        console.log('📊📊 API返回数据:', {
          状态: result.success,
          总行数: result.total_rows,
          总列数: result.total_columns,
          数据行数: result.rows?.length || 0
        });

        if (!result.rows || result.rows.length === 0) {
          console.warn('⚠️ API返回空数据');
          return {
            success: false,
            error: 'API返回空数据',
            data: [],
            totalRows: 0,
            totalColumns: 0
          };
        }

        return {
          success: true,
          data: result.rows,
          totalRows: result.total_rows,
          totalColumns: result.total_columns
        };

      } catch (error) {
        console.error('❌❌ 从API加载数据失败:', error);
        return {
          success: false,
          error: error.message,
          data: [],
          totalRows: 0,
          totalColumns: 0
        };
      }
    };


   const loadFromAPI = async (fileId, excelFileName, sheetName) => {
      try {
        console.log('🌐🌐 调用API加载数据:', { fileId, excelFileName, sheetName })

        const apiUrl = `/api/excel-data/${encodeURIComponent(fileId)}/${encodeURIComponent(excelFileName)}/${encodeURIComponent(sheetName)}`
        console.log('🔗 API URL:', apiUrl)

        const response = await fetch(apiUrl)
        console.log('📡 API响应状态:', response.status)

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const result = await response.json()
        console.log('📥 API返回数据:', {
          success: result.success,
          data类型: typeof result.data,
          data是数组: Array.isArray(result.data),
          data长度: Array.isArray(result.data) ? result.data.length : '非数组',
          rows: result.rows,
          cols: result.cols
        })

        // 🔥🔥🔥 关键修复：确保返回的数据结构正确
        if (!result.success) {
          return {
            success: false,
            error: result.error || 'API调用失败',
            data: []
          }
        }

        // 确保data是数组
        if (!Array.isArray(result.data)) {
          console.warn('⚠️ API返回的data不是数组，强制转换为空数组')
          result.data = []
        }

        return result

      } catch (error) {
        console.error('❌❌ 从API加载数据失败:', error)
        return {
          success: false,
          error: error.message,
          data: []  // 确保返回数组
        }
      }
    }

  /**
   * 加载Excel数据
   */
   const loadExcelData111 = async (sheetName, excelFileName) => {

   const currentPdf = selectedPdf.value;
  const pdfId = currentPdf?.disk_name || currentPdf?.id;
  const tableType = showFlatMode.value ? 'flattened' : 'original';

  console.log('🔍🔍🔍🔍🔍🔍 开始加载Excel数据流程 🔍🔍🔍🔍🔍🔍');
  console.log('📋 输入参数:', { pdfId, sheetName, excelFileName, tableType });

  try {
    // 🎯 阶段1: 检查缓存
    console.log('🔄 阶段1: 检查缓存');
    let cachedData = null;
    if (tableType === 'original') {
      cachedData = excelDataCache.getOriginalData(pdfId, excelFileName, sheetName);
      console.log('📦 检查原始数据缓存:', {
        是否存在: !!cachedData,
        数据长度: cachedData?.length || 0
      });
    } else {
      cachedData = excelDataCache.getFlattenedData(pdfId, excelFileName, sheetName);
      console.log('📦 检查扁平化数据缓存:', {
        是否存在: !!cachedData,
        数据长度: cachedData?.length || 0
      });
    }

    // 🎯 阶段2: 如果有缓存，使用缓存
    if (cachedData && cachedData.length > 0) {
      console.log('✅ 使用缓存数据');
      console.log('📊 缓存数据样本:', cachedData.slice(0, 2));

      if (showFlatMode.value) {
        flatData.value = [...cachedData];
        console.log('📥 设置 flatData:', flatData.value.length);
      } else {
        excelData.value = [...cachedData];
        console.log('📥 设置 excelData:', excelData.value.length);
      }

      // 生成表格列
      if (Array.isArray(cachedData) && cachedData.length > 0) {
        generateTableColumns(cachedData);
        console.log('✅ 生成表格列完成');
      }

      console.log('🎯 加载完成: 使用缓存数据');
      return { success: true, fromCache: true, data: cachedData };
    }

    console.log('📭 缓存为空，进入API加载流程');

    // 🎯 阶段3: 从API加载
    console.log('🔄 阶段2: 调用 loadFromAPI');
    const result = await loadFromAPI(pdfId, excelFileName, sheetName);

    console.log('📡 loadFromAPI 返回结果:', {
      成功: result.success,
      是否有数据: !!result.data,
      数据长度: result.data?.length || 0,
      数据类型: typeof result.data,
      是否为数组: Array.isArray(result.data),
      数据样本: result.data ? result.data.slice(0, 2) : '无数据'
    });

    if (!result.success) {
      console.error('❌ loadFromAPI 返回失败:', result.error);
      throw new Error(result.error || 'API调用失败');
    }

    if (!result.data || !Array.isArray(result.data)) {
      console.error('❌ API返回数据格式错误:', result.data);
      throw new Error('API返回数据格式不正确');
    }

    console.log('✅ API数据接收成功，长度:', result.data.length);

    // 🎯 阶段4: 处理API返回的数据
    console.log('🔄 阶段3: 处理数据');
    if (showFlatMode.value) {
      flatData.value = Array.isArray(result.data) ? [...result.data] : [];
      console.log('📥 设置 flatData:', flatData.value.length);
    } else {
      excelData.value = Array.isArray(result.data) ? [...result.data] : [];
      console.log('📥 设置 excelData:', excelData.value.length);
    }

    // 🎯 阶段5: 生成表格列
    console.log('🔄 阶段4: 生成表格列');
    if (Array.isArray(result.data) && result.data.length > 0) {
      generateTableColumns(result.data);
      console.log('✅ 表格列生成完成');
    } else {
      console.warn('⚠️ 数据为空，跳过生成表格列');
    }

    console.log('🎯 加载完成: 使用API数据');
    return { success: true, fromCache: false, data: result.data };

  } catch (error) {
    console.error('💥💥💥 整个加载流程失败:', error);
    console.error('📋 错误详情:', {
      消息: error.message,
      堆栈: error.stack
    });
    return { success: false, error: error.message };
  }
};


   const loadExcelData = async (sheetName, excelFileName) => {
      try {
        console.log('🔍🔍🔍🔍🔍🔍 开始加载Excel数据流程 🔍🔍🔍🔍🔍🔍')
        console.log('📋 输入参数:', { pdfId: selectedPdf.value?.id, sheetName, excelFileName, tableType: 'original' })

        // 阶段1: 检查缓存
        console.log('🔄 阶段1: 检查缓存')
        const cachedData = excelDataCache.getOriginalData(selectedPdf.value?.id, excelFileName, sheetName)
        console.log('📦 检查原始数据缓存:', { 是否存在: !!cachedData, 数据长度: cachedData?.length || 0 })

        if (cachedData && cachedData.length > 0) {
          console.log('✅ 使用缓存数据')
          excelData.value = cachedData
          return { success: true, fromCache: true, data: cachedData }
        }

        console.log('📭 缓存为空，进入API加载流程')

        // 阶段2: 调用API
        console.log('🔄 阶段2: 调用 loadFromAPI')
        const result = await loadFromAPI(selectedPdf.value?.id, excelFileName, sheetName)

        console.log('📊📊 API返回数据:', {
          状态: result.success,
          总行数: result.data?.length,
          数据类型: typeof result.data,
          data是数组: Array.isArray(result.data),
          完整响应: result
        })

        if (!result.success) {
          console.log('❌ API调用失败')
          throw new Error(result.error || 'API调用失败')
        }

        // 🔥🔥🔥 关键修复：确保 data 是数组
        let tableData = []

        if (Array.isArray(result.data)) {
          // 情况1: data是数组（正确的格式）
          tableData = result.data
          console.log('✅ 数据格式正确: 二维数组')
        }
        else if (result.data && typeof result.data === 'object') {
          // 情况2: data是对象，尝试提取
          console.log('🔄 数据是对象格式，尝试提取数组')

          // 检查常见的数组字段
          const possibleArrayKeys = ['rows', 'data', 'tableData', 'values', 'sheetData']
          for (const key of possibleArrayKeys) {
            if (Array.isArray(result.data[key])) {
              tableData = result.data[key]
              console.log(`✅ 从对象中提取数组: ${key}，长度: ${tableData.length}`)
              break
            }
          }
        }

        // 如果还是空数组，使用空数组
        if (tableData.length === 0) {
          console.warn('⚠️ 无法提取表格数据，使用空数组')
          tableData = []
        }

        console.log(`✅ 最终表格数据: ${tableData.length}行 x ${tableData[0]?.length || 0}列`)

        // 缓存数据
        excelDataCache.setOriginalData(selectedPdf.value?.id, excelFileName, sheetName, tableData)
        excelData.value = tableData

        console.log('✅ 数据加载完成')
        return { success: true, fromCache: false, data: tableData }

      } catch (error) {
        console.error('💥💥💥 整个加载流程失败:', error)
        console.error('📋 错误详情:', { 消息: error.message, 堆栈: error.stack })

        // 设置空数据避免界面崩溃
        excelData.value = []
        return { success: false, error: error.message, data: [] }
      }
    }


  /**
   * 生成表格列配置
   */
  const generateTableColumns = (data) => {
    if (!data || data.length === 0) {
      console.log('没有数据，清空表格列')
      tableColumns.value = []
      return []
    }

    // 从第一行数据获取列名
    const firstRow = data[0]
    const columns = Object.keys(firstRow).map(key => ({
      prop: key,
      label: key,
      width: 120
    }))

    tableColumns.value = columns
    console.log('生成的表格列:', columns)
    return columns
  }

  /**
   * 生成目录表格的列配置
   */
  const generateDirectoryTableColumns = () => {
    const columns = [
      { prop: '班级名称', label: '班级名称', width: 120 },
      { prop: '表格类型', label: '表格类型', width: 120 },
      { prop: '数据条数', label: '数据条数', width: 100 },
      { prop: '平均总分', label: '平均总分', width: 100 }
    ]

    tableColumns.value = columns
    return columns
  }

  /**
   * 下载PDF文件
   */
  const downloadPdf = async (pdf) => {
    if (!pdf) return

    downloadLoading.value = true
    try {
      let downloadUrl = ''

      if (pdf.id) {
        downloadUrl = `/api/file-by-id/${pdf.id}`
      } else {
        downloadUrl = `/api/file/${encodeURIComponent(pdf.name)}`
      }

      // 创建隐藏的下载链接
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = pdf.name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      ElMessage.success('开始下载PDF文件')
    } catch (error) {
      console.error('下载PDF失败:', error)
      ElMessage.error('下载PDF失败')
    } finally {
      downloadLoading.value = false
    }
  }

  /**
   * 获取sheet中的页码
   */
   const getPageFromSheetName = (sheetName) => {
        // ✅ 添加空值检查
        if (!sheetName || typeof sheetName !== 'string') {
            console.log('⚠️ getPageFromSheetName: sheetName为空，返回null')
            return null
        }

        const pageMatch = sheetName.match(/P(\d+)_/)
        if (pageMatch && pageMatch[1]) {
            const page = parseInt(pageMatch[1])
            console.log(`🔢 从sheet名称提取页码: "${sheetName}" -> ${page}`)
            return page
        }

        console.log(`🔢 未从sheet名称找到页码: "${sheetName}"`)
        return null
    }

  /**
   * 获取所有sheet中的最大页码
   */
  const getMaxPageFromSheets = (excelFiles) => {
    let maxPage = 1
    excelFiles.forEach(file => {
      file.sheets.forEach(sheet => {
        const pageNum = getPageFromSheetName(sheet.name)
        if (pageNum && pageNum > maxPage) {
          maxPage = pageNum
        }
      })
    })
    return maxPage
  }

  return {
    // 注入状态
    searchResults,
    isSearching,

    // 主要状态
    selectedPdf,
    pdfUrl,
    downloadLoading,
    isMiddleCollapsed,
    showFlatMode,
    flatData,
    sheetList,
    excelFiles,
    selectedSheet,
    selectedExcelFile,
    excelData,
    tableColumns,
    currentTableMode,
    hasGlobalChanges,
    globalModifiedCount,

    // 计算属性
    filteredPdfCount,
    tableCount,
    hasChanges,

    // 方法
    selectPdf,
    loadExcelData,
    generateTableColumns,
    generateDirectoryTableColumns,
    downloadPdf,
    getPageFromSheetName,
    getMaxPageFromSheets
  }
}