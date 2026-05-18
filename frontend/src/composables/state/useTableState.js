import { computed } from 'vue'
import { useTableStore } from '@/stores/tables'

export function useTableState() {
  const tableStore = useTableStore()

  return {
    // 状态
    extractedTables: computed(() => tableStore.extractedTables),
    currentTable: computed(() => tableStore.currentTable),
    tableData: computed(() => tableStore.tableData),
    excelData: computed(() => tableStore.excelData),
    processingStatus: computed(() => tableStore.processingStatus),
    hasTables: computed(() => tableStore.hasTables),
    hasExcelData: computed(() => tableStore.hasExcelData),
    isProcessing: computed(() => tableStore.isProcessing),

    // 操作
    setExtractedTables: (tables) => tableStore.setExtractedTables(tables),
    setCurrentTable: (table) => tableStore.setCurrentTable(table),
    setTableData: (tableId, data) => tableStore.setTableData(tableId, data),
    setExcelData: (data) => tableStore.setExcelData(data),
    setProcessingStatus: (status) => tableStore.setProcessingStatus(status),
    addTable: (table) => tableStore.addTable(table),
    removeTable: (tableId) => tableStore.removeTable(tableId),
    clearTables: () => tableStore.clearTables()
  }
}