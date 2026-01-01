// frontend/src/components/excel/useExcelTable.js
import { ref, computed, onUnmounted } from 'vue'

export default function useExcelTable(props) {
  const hotTable = ref(null)
  const excelContainer = ref(null)
  const containerHeight = ref(400)
  const showScrollHint = ref(false)

  // 新增：定时器管理
  const activeTimeouts = ref([])
  const isComponentActive = ref(true)

  // 新增：重试计数器
  let retryCount = 0
  const MAX_RETRY_COUNT = 10

  // ============ 核心函数 ============

  // 计算容器高度（直接从原文件复制）
  const calculateHeight = () => {
    if (excelContainer.value) {
      const parentContainer = excelContainer.value.closest('.excel-content') || excelContainer.value.parentElement
      if (parentContainer) {
        const parentRect = parentContainer.getBoundingClientRect()
        containerHeight.value = parentRect.height - 60

      }
    }
  }

  // 表格高度计算属性（直接从原文件复制）
    const tableHeight11 = computed(() => {
      // 如果没有 tableData 参数，直接使用容器高度
      const minHeight = 400
      const calculatedHeight = Math.max(minHeight, containerHeight.value)

      return calculatedHeight
    })

    const tableHeight = computed(() => {
      // 获取窗口高度
      const windowHeight = window.innerHeight
      const fixedHeights = 60 + 40 + 50 + 30

      // 计算可用高度
      const availableHeight = Math.max(windowHeight - fixedHeights, 300)

      console.log('📏 表格高度计算:', {
        窗口高度: windowHeight,
        固定高度: fixedHeights,
        可用高度: availableHeight,
        原计算高度: containerHeight.value
      })

      return availableHeight
    })


  // ============ 实例安全函数 ============

  // 检查实例是否有效（直接从原文件复制）
  // 修复：更严格的实例安全检查函数
    const isHotInstanceValid = () => {
      if (!hotTable.value?.hotInstance) {
        return false
      }

      const hot = hotTable.value.hotInstance
      try {
        // 通过检查实例状态来验证是否有效
        return !hot.isDestroyed &&
               hot.rootElement !== null &&
               hot.rootElement.isConnected &&
               typeof hot.getSettings === 'function'
      } catch (error) {
        return false
      }
    }

  // 获取安全实例（直接从原文件复制）
  const getSafeHotInstance = () => {
    if (!isHotInstanceValid()) {
      return null
    }

    try {
      const hot = hotTable.value.hotInstance
      const settings = hot.getSettings()
      return settings ? hot : null
    } catch (error) {
      return null
    }
  }

  // ============ 工具函数 ============

  // 安全的定时器（直接从原文件复制）
  const safeSetTimeout = (callback, delay) => {
    if (!isComponentActive.value) {
      console.log('ℹ️ 组件已卸载，跳过定时器设置')
      return null
    }

    const timeoutId = setTimeout(() => {
      if (isComponentActive.value) {
        callback()
      }
    }, delay)

    activeTimeouts.value.push(timeoutId)
    return timeoutId
  }

  // 清理所有定时器（直接从原文件复制）
  const clearAllTimeouts = () => {
    activeTimeouts.value.forEach(timeoutId => {
      clearTimeout(timeoutId)
    })
    activeTimeouts.value = []
  }

  // 安全的异步操作（直接从原文件复制）
  const safeAsyncOperation = (callback) => {
    if (!isComponentActive.value || !isHotInstanceValid()) {
      console.log('ℹ️ 组件已卸载或实例无效，跳过操作')
      return
    }
    try {
      callback()
    } catch (error) {
      console.warn('⚠️ 异步操作失败:', error.message)
    }
  }

  // ============ 事件监听 ============

  // 配置事件监听（直接从原文件复制 setupEventListeners 函数）
  const setupEventListeners = () => {

    const hot = getSafeHotInstance()
    if (!hot) {
      retryCount++
      if (retryCount < MAX_RETRY_COUNT && isComponentActive.value) {
        console.log(`❌ 表格实例未准备好，延迟重试 (${retryCount}/${MAX_RETRY_COUNT})`)
        safeSetTimeout(() => {
          if (isComponentActive.value) {
            setupEventListeners()
          }
        }, 500)
      } else {
        console.error('❌ 表格实例初始化失败，停止重试')
      }
      return
    }

    try {
      hot.removeHook('afterChange')
    } catch (e) {
      console.log('ℹ️ 清除旧监听时出错:', e.message)
    }

    // 这里只是设置监听器，实际处理逻辑在 useExcelEdit.js 中
    hot.addHook('afterChange', function(changes, source) {
      safeAsyncOperation(() => {
        console.log('🎯 afterChange 事件触发:', {
          changes: changes ? changes.length : 0,
          source: source,
          timestamp: new Date().toISOString()
        })

        // 这个函数需要在主组件中定义并传递
        window.__onDataChange?.(changes, source)
      })
    })

    retryCount = 0
  }

  // ============ 清理函数 ============

  const cleanup = () => {
    console.log('🔧 清理表格资源...')
    isComponentActive.value = false
    clearAllTimeouts()
  }

  // 监听窗口变化（直接从原文件复制）
  const handleResize = () => {
      nextTick(() => {
        calculateHeight()
        if (hotTable.value && hotTable.value.hotInstance) {
          hotTable.value.hotInstance.render()
        }
      })
    }

  // ============ 返回所有需要的变量和函数 ============

  return {
    // refs
    hotTable,
    excelContainer,
    containerHeight,
    showScrollHint,
    isComponentActive,

    // computed
    tableHeight,

    // functions
    calculateHeight,
    getSafeHotInstance,
    isHotInstanceValid,
    safeSetTimeout,
    safeAsyncOperation,
    setupEventListeners,
    cleanup,
    handleResize,

    // 内部状态（如果需要）
    retryCount: () => retryCount,
    MAX_RETRY_COUNT
  }
}