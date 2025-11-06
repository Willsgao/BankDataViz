import { usePdfStore } from '@/stores/pdf'

export function usePdfState() {
  const pdfStore = usePdfStore()

  return {
    // 状态
    currentPage: computed(() => pdfStore.currentPage),
    totalPages: computed(() => pdfStore.totalPages),
    scale: computed(() => pdfStore.scale),
    rotation: computed(() => pdfStore.rotation),
    pdfDocument: computed(() => pdfStore.pdfDocument),
    pageImages: computed(() => pdfStore.pageImages),
    selectedRegions: computed(() => pdfStore.selectedRegions),
    hasPdf: computed(() => pdfStore.hasPdf),
    currentPageImage: computed(() => pdfStore.currentPageImage),

    // 操作
    setPdfDocument: (doc) => pdfStore.setPdfDocument(doc),
    setTotalPages: (pages) => pdfStore.setTotalPages(pages),
    setCurrentPage: (page) => pdfStore.setCurrentPage(page),
    nextPage: () => pdfStore.nextPage(),
    prevPage: () => pdfStore.prevPage(),
    setScale: (scale) => pdfStore.setScale(scale),
    setRotation: (rotation) => pdfStore.setRotation(rotation),
    addPageImage: (pageImage) => pdfStore.addPageImage(pageImage),
    addSelectedRegion: (region) => pdfStore.addSelectedRegion(region),
    clearSelectedRegions: () => pdfStore.clearSelectedRegions(),
    resetPdfState: () => pdfStore.resetPdfState()
  }
}