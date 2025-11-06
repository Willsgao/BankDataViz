import { defineStore } from 'pinia'

export const usePdfStore = defineStore('pdf', {
  state: () => ({
    currentPage: 1,
    totalPages: 0,
    scale: 1.0,
    rotation: 0,
    pdfDocument: null,
    pageImages: [],
    selectedRegions: []
  }),

  getters: {
    hasPdf: (state) => state.pdfDocument !== null,

    currentPageImage: (state) => {
      return state.pageImages.find(img => img.page === state.currentPage)
    }
  },

  actions: {
    setPdfDocument(doc) {
      this.pdfDocument = doc
    },

    setTotalPages(pages) {
      this.totalPages = pages
    },

    setCurrentPage(page) {
      if (page >= 1 && page <= this.totalPages) {
        this.currentPage = page
      }
    },

    nextPage() {
      if (this.currentPage < this.totalPages) {
        this.currentPage++
      }
    },

    prevPage() {
      if (this.currentPage > 1) {
        this.currentPage--
      }
    },

    setScale(scale) {
      this.scale = scale
    },

    setRotation(rotation) {
      this.rotation = rotation
    },

    addPageImage(pageImage) {
      this.pageImages = this.pageImages.filter(img => img.page !== pageImage.page)
      this.pageImages.push(pageImage)
    },

    addSelectedRegion(region) {
      this.selectedRegions.push(region)
    },

    clearSelectedRegions() {
      this.selectedRegions = []
    },

    resetPdfState() {
      this.currentPage = 1
      this.totalPages = 0
      this.scale = 1.0
      this.rotation = 0
      this.pdfDocument = null
      this.pageImages = []
      this.selectedRegions = []
    }
  }
})