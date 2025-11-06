import { useFileState } from '@/composables/state/useFileState'
import { useAppState } from '@/composables/state/useAppState'

export function useFileOperations() {
  const { addPdfFile, addOtherFile, removeFile, setUploadProgress } = useFileState()
  const { setLoading } = useAppState()

  const uploadFiles = async (files) => {
    setLoading(true)
    setUploadProgress(0)

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        // 模拟上传进度
        setUploadProgress(((i + 1) / files.length) * 100)

        if (file.type === 'application/pdf') {
          addPdfFile({
            id: Date.now() + i,
            name: file.name,
            size: file.size,
            type: file.type,
            file: file
          })
        } else {
          addOtherFile({
            id: Date.now() + i,
            name: file.name,
            size: file.size,
            type: file.type,
            file: file
          })
        }

        // 模拟上传延迟
        await new Promise(resolve => setTimeout(resolve, 500))
      }
    } finally {
      setLoading(false)
      setUploadProgress(100)
    }
  }

  const deleteFile = (fileId) => {
    removeFile(fileId)
  }

  const clearAllFiles = () => {
    const { clearFiles } = useFileState()
    clearFiles()
  }

  return {
    uploadFiles,
    deleteFile,
    clearAllFiles
  }
}