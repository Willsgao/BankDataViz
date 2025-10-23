// src/composables/usePreviewMessenger.js
import { onMounted, onUnmounted } from 'vue'

export function usePreviewMessenger(previewFolder, previewPngs, previewVisible) {
  // 统一的消息处理函数
  const handler = (e) => {
    console.log('📮 收到 postMessage', e.data)
    if (e.data?.type === 'openPreview') {
      previewFolder.value = e.data.folder
      previewPngs.value   = e.data.pngs
      previewVisible.value = true
    }
  }

  // 组件挂载时注册
  onMounted(() => {
    window.removeEventListener('message', handler)
    window.addEventListener('message', handler)
  })

  // 组件卸载时清理，防止重复监听
  onUnmounted(() => {
    window.removeEventListener('message', handler)
  })
}