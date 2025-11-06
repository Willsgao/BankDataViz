import { defineStore } from 'pinia'

export const useTableStore = defineStore('tables', {
  state: () => ({
    extractedTables: [],
    currentTable: null,
    tableData: {},
    excelData: null,
    processingStatus: 'idle' // 'idle' | 'processing' | 'completed' | 'error'
  }),

  getters: {
    hasTables: (state) => state.extractedTables.length > 0,
    hasExcelData: (state) => state.excelData !== null,
    isProcessing: (state) => state.processingStatus === 'processing'
  },

  actions: {
    setExtractedTables(tables) {
      this.extractedTables = tables
    },

    setCurrentTable(table) {
      this.currentTable = table
    },

    setTableData(tableId, data) {
      this.tableData[tableId] = data
    },

    setExcelData(data) {
      this.excelData = data
    },

    setProcessingStatus(status) {
      this.processingStatus = status
    },

    addTable(table) {
      this.extractedTables.push(table)
    },

    removeTable(tableId) {
      this.extractedTables = this.extractedTables.filter(table => table.id !== tableId)
      if (this.currentTable && this.currentTable.id === tableId) {
        this.currentTable = null
      }
    },

    clearTables() {
      this.extractedTables = []
      this.currentTable = null
      this.tableData = {}
      this.excelData = null
      this.processingStatus = 'idle'
    }
  }
})
