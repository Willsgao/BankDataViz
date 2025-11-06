import { defineStore } from 'pinia'

export const useFileStore = defineStore('files', {
  state: () => ({
    pdfFiles: [],
    otherFiles: [],
    selectedFiles: [],
    uploadProgress: 0
  }),

  getters: {
    hasFiles: (state) => state.pdfFiles.length > 0 || state.otherFiles.length > 0,

    selectedPdfFiles: (state) => {
      return state.pdfFiles.filter(file => state.selectedFiles.includes(file.id))
    }
  },

  actions: {
    addPdfFile(file) {
      this.pdfFiles.push(file)
    },

    addOtherFile(file) {
      this.otherFiles.push(file)
    },

    removeFile(fileId) {
      this.pdfFiles = this.pdfFiles.filter(file => file.id !== fileId)
      this.otherFiles = this.otherFiles.filter(file => file.id !== fileId)
      this.selectedFiles = this.selectedFiles.filter(id => id !== fileId)
    },

    setSelectedFiles(fileIds) {
      this.selectedFiles = fileIds
    },

    setUploadProgress(progress) {
      this.uploadProgress = progress
    },

    clearFiles() {
      this.pdfFiles = []
      this.otherFiles = []
      this.selectedFiles = []
    }
  }
})