import { useTableState } from '@/composables/state/useTableState'
import { useAppState } from '@/composables/state/useAppState'

export function useConvertOperations() {
  const { setProcessingStatus } = useTableState()
  const { setLoading } = useAppState()

  const batchConvertTables = async (tables) => {
    setProcessingStatus('processing')
    setLoading(true)

    try {
      // 模拟批量转换过程
      const results = []

      for (let i = 0; i < tables.length; i++) {
        const table = tables[i]

        // 模拟每个表格的转换时间
        await new Promise(resolve => setTimeout(resolve, 1000))

        const result = {
          tableId: table.id,
          tableName: table.name,
          status: 'success',
          excelData: {
            headers: [`${table.name}列1`, `${table.name}列2`],
            rows: [
              [`${table.name}数据1`, `${table.name}数据2`],
              [`${table.name}数据3`, `${table.name}数据4`]
            ]
          }
        }

        results.push(result)
      }

      setProcessingStatus('completed')
      return results
    } catch (error) {
      setProcessingStatus('error')
      throw error
    } finally {
      setLoading(false)
    }
  }

  const exportToExcel = (excelData, filename = 'exported_data.xlsx') => {
    // 模拟Excel导出
    console.log('Exporting to Excel:', excelData)
    // 这里可以集成实际的Excel导出库
    alert(`导出成功: ${filename}`)
  }

  const validateTableData = (tableData) => {
    if (!tableData || !tableData.headers || !tableData.rows) {
      return false
    }

    return tableData.headers.length > 0 && tableData.rows.length > 0
  }

  return {
    batchConvertTables,
    exportToExcel,
    validateTableData
  }
}