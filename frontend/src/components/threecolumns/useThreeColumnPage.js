import { ref, computed, inject } from 'vue'
import { ElMessage } from 'element-plus'
import { getApiUrl, getBackendUrl } from '@/utils/config'

/**
 * 三列页面主逻辑组合函数
 */
export function useThreeColumnPage() {
  // 注入的搜索数据
  const searchResults = inject('searchResults', [])
  const isSearching = inject('isSearching', ref(false))

  // 主要状态
  const selectedPdf = ref(null)
  const pdfUrl = ref('')
  const downloadLoading = ref(false)
  const isMiddleCollapsed = ref(false)
  const showFlatMode = ref(false)
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
  const filteredPdfCount = computed(() => searchResults.value.length)
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
      let fileId = pdf.id
      if (!fileId) {
        // 如果没有ID，尝试通过文件名查找
        console.log('PDF没有ID，尝试通过文件名查找:', pdf.name)
        const fileResponse = await fetch(getApiUrl(`/search-pdf?keyword=${encodeURIComponent(pdf.name)}`))

        if (fileResponse.ok) {
          const fileData = await fileResponse.json()
          const matchedFile = fileData.files.find(f => f.name === pdf.name)
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

  /**
   * 加载Excel数据
   */
  const loadExcelData = async (sheetName, excelFileName, getApiUrlFn = getApiUrl) => {
    if (!selectedPdf.value) {
      console.error('没有选中的PDF')
      return { success: false, error: '没有选中的PDF' }
    }

    console.log('开始加载Excel数据，sheet:', sheetName, '文件:', excelFileName)

    try {
      const pdfId = selectedPdf.value.id
      const apiUrl = getApiUrlFn(`/excel-data/${pdfId}/${encodeURIComponent(excelFileName)}/${encodeURIComponent(sheetName)}`)

      const response = await fetch(apiUrl)

      if (response.ok) {
        const data = await response.json()
        return {
          success: true,
          data: data.rows || [],
          totalRows: data.total_rows || 0
        }
      } else {
        const errorData = await response.json().catch(() => ({ error: '未知错误' }))
        return {
          success: false,
          error: errorData.error || '未知错误'
        }
      }
    } catch (error) {
      console.error('加载Excel数据失败:', error)
      return { success: false, error }
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
    const pageMatch = sheetName.match(/P(\d+)_/)
    if (pageMatch && pageMatch[1]) {
      return parseInt(pageMatch[1])
    }
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