// src/composables/usePageJump.js
import { ref } from 'vue'

export function usePageJump(previewPngs) {
  const jumpPage = ref(1)

  function jumpToPage() {
    const idx = Number(jumpPage.value) - 1
    if (!jumpPage.value || jumpPage.value < 1 || jumpPage.value > previewPngs.value.length) return
    const vm = document.querySelector('.el-image-viewer')?.__vueParentComponent?.proxy
    if (vm) {
      if (typeof vm.activeIndex === 'number') vm.activeIndex = idx
      else vm.setActiveItem?.(idx)
    } else {
      // 弹窗未打开：先点开第一张再跳转
      document.querySelector('.el-image')?.$el?.click()
      const wait = setInterval(() => {
        const vm = document.querySelector('.el-image-viewer')?.__vueParentComponent?.proxy
        if (vm) {
          clearInterval(wait)
          if (typeof vm.activeIndex === 'number') vm.activeIndex = idx
          else vm.setActiveItem?.(idx)
        }
      }, 100)
    }
  }

  return { jumpPage, jumpToPage }
}