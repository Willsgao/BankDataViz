// useExcelViewerExpose.js - 更新为
import { getCurrentInstance } from 'vue'

export default function useExcelViewerExpose(methods) {
  const instance = getCurrentInstance()

  if (instance) {
    // 直接暴露所有方法到组件实例
    Object.keys(methods).forEach(key => {
      if (typeof methods[key] === 'function') {
        instance.exposed = instance.exposed || {}
        instance.exposed[key] = methods[key]
      }
    })

    // 也通过 defineExpose 暴露
    instance.exposed = {
      ...instance.exposed,
      ...methods
    }
  }

  return methods
}