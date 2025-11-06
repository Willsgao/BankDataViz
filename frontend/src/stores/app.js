import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    currentView: 'two-column', // 'two-column' | 'three-column'
    isLoading: false,
    activePdfFile: null,
    activeTable: null
  }),

  actions: {
    setCurrentView(view) {
      this.currentView = view
    },

    setLoading(loading) {
      this.isLoading = loading
    },

    setActivePdfFile(file) {
      this.activePdfFile = file
    },

    setActiveTable(table) {
      this.activeTable = table
    }
  }
})