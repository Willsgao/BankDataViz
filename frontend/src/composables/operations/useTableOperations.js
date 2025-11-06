import { useTableState } from '@/composables/state/useTableState'
import { useAppState } from '@/composables/state/useAppState'

export function useTableOperations() {
  const {
    setExtractedTables,
    setCurrentTable,
    setExcelData,
    setProcessingStatus,
    setTableData
  } = useTableState()

  const { setLoading } = useAppState()

  const extractTablesFromPdf = async (pdfDocument, pageNumber) => {
    setProcessingStatus('processing')
    setLoading(true)

    try {
      // 模拟表格提取过程
      await new Promise(resolve => setTimeout(resolve, 2000))

      const mockTables = [
        { id: 1, name: '表格1', page: pageNumber, region: { x: 100, y: 200, width: 300, height: 200 } },
        { id: 2, name: '表格2', page: pageNumber, region: { x: 100, y: 500, width: 300, height: 150 } }
      ]

      setExtractedTables(mockTables)
      setProcessingStatus('completed')

      return mockTables
    } catch (error) {
      setProcessingStatus('error')
      throw error
    } finally {
      setLoading(false)
    }
  }

  const convertTableToExcel = async (table) => {
    setProcessingStatus('processing')

    try {
      // 模拟Excel转换过程
      await new Promise(resolve => setTimeout(resolve, 1000))

      const mockExcelData = {
        headers: ['列1', '列2', '列3'],
        rows: [
          ['数据1', '数据2', '数据3'],
          ['数据4', '数据5', '数据6']
        ]
      }

      setExcelData(mockExcelData)
      setCurrentTable(table)
      setProcessingStatus('completed')

      return mockExcelData
    } catch (error) {
      setProcessingStatus('error')
      throw error
    }
  }

  const updateTableCell = (tableId, rowIndex, colIndex, value) => {
    const { tableData } = useTableState()
    const currentData = tableData.value[tableId] || { headers: [], rows: [] }

    if (rowIndex === -1) {
      // 更新表头
      currentData.headers[colIndex] = value
    } else {
      // 更新数据单元格
      if (!currentData.rows[rowIndex]) {
        currentData.rows[rowIndex] = []
      }
      currentData.rows[rowIndex][colIndex] = value
    }

    setTableData(tableId, currentData)
  }

  return {
    extractTablesFromPdf,
    convertTableToExcel,
    updateTableCell
  }
}