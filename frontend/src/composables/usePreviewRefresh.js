// src/composables/usePreviewRefresh.js
import { ref } from 'vue'

export function usePreviewRefresh(imageRotation, refreshTimestamp) {
  function refreshPreview() {
    // 清旋转缓存 + 强制刷新图片
    Object.keys(imageRotation.value).forEach(k => delete imageRotation.value[k])
    refreshTimestamp.value = Date.now()
  }
  return { refreshPreview }
}