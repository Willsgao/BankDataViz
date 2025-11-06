import { useFileStore } from '@/stores/files'

export function useFileState() {
  const fileStore = useFileStore()

  return {
    // 状态
    pdfFiles: computed(() => fileStore.pdfFiles),
    otherFiles: computed(() => fileStore.otherFiles),
    selectedFiles: computed(() => fileStore.selectedFiles),
    uploadProgress: computed(() => fileStore.uploadProgress),
    hasFiles: computed(() => fileStore.hasFiles),

    // 操作
    addPdfFile: (file) => fileStore.addPdfFile(file),
    addOtherFile: (file) => fileStore.addOtherFile(file),
    removeFile: (fileId) => fileStore.removeFile(fileId),
    setSelectedFiles: (fileIds) => fileStore.setSelectedFiles(fileIds),
    setUploadProgress: (progress) => fileStore.setUploadProgress(progress),
    clearFiles: () => fileStore.clearFiles()
  }
}