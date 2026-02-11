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

      return availableHeight
    })


  // ============ 实例安全函数 ============
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
  const setupEventListeners = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    retryCount++
    if (retryCount < MAX_RETRY_COUNT && isComponentActive.value) {
      console.log(`❌❌ 表格实例未准备好，延迟重试 (${retryCount}/${MAX_RETRY_COUNT})`)
      safeSetTimeout(() => {
        if (isComponentActive.value) {
          setupEventListeners()
        }
      }, 500)
    } else {
      console.error('❌❌ 表格实例初始化失败，停止重试')
    }
    return
  }

  try {
    // 清除所有旧监听器
    hot.removeHook('afterChange')
    hot.removeHook('afterFilter')
    hot.removeHook('afterDropdownMenuShow')
    hot.removeHook('afterDropdownMenuHide')
    hot.removeHook('beforeOnCellMouseDown')
    hot.removeHook('afterOnCellMouseDown')
    hot.removeHook('beforeSelection')
  } catch (e) {
    console.log('ℹℹ️ 清除旧监听时出错:', e.message)
  }

  // 🔥🔥🔥 核心修复：直接修改Handsontable的表头行为
  try {
    // 关键配置：禁用表头选择整列的功能
    hot.updateSettings({
      // 禁用表头选择功能
      selectionMode: 'single', // 改为单格选择模式
      selectionModeHighlights: false,
      // 启用筛选
      filters: true,
      dropdownMenu: {
        items: {
          filter_by_value: {name: '按值筛选'},
          filter_operators: {name: '筛选条件'},
          filter_action_bar: {name: '筛选操作'}
        }
      },
      // 禁用排序，避免冲突
      columnSorting: false,
      // 禁用其他可能冲突的功能
      manualColumnResize: false,
      manualRowResize: false
    }, false)

    console.log('✅✅ 已禁用表头选择功能，启用筛选')
  } catch (error) {
    console.error('❌❌ 配置更新失败:', error)
  }

  // 🔥 添加表头点击的精确控制
  hot.addHook('afterOnCellMouseDown', function(event, coords, td) {
    // 只处理表头点击
    if (coords.row < 0) {
      console.log('🎯🎯 表头被点击，阻止选择整列')

      // 立即阻止事件传播，防止触发选择操作
      event.stopImmediatePropagation()
      event.preventDefault()

      // 🔥 关键：手动触发筛选菜单
      setTimeout(() => {
        try {
          // 获取筛选插件
          const filterPlugin = hot.getPlugin('filters')
          if (filterPlugin && filterPlugin.enabled) {
            // 使用正确的方法打开筛选菜单
            if (filterPlugin.openDropdown) {
              filterPlugin.openDropdown(coords.col)
            } else if (filterPlugin.open) {
              filterPlugin.open(coords.col)
            } else if (filterPlugin.showColumnFilter) {
              filterPlugin.showColumnFilter(coords.col)
            }
            console.log('📋📋 筛选菜单已触发')
          } else {
            console.warn('⚠️ 筛选插件未找到或未启用')
          }
        } catch (menuError) {
          console.warn('⚠️ 触发筛选菜单失败:', menuError)
        }
      }, 10)

      return false // 完全阻止默认行为
    }
  })

  // 🔥 完全阻止表头选择
  hot.addHook('beforeSelection', function(currentRow, currentColumn, endRow, endColumn, selectionLayerLevel) {
    // 如果开始或结束行是表头（row < 0），阻止选择
    if (currentRow < 0 || endRow < 0) {
      console.log('🚫🚫 阻止表头选择操作')
      return false // 返回false阻止选择
    }
    return true // 允许正常单元格选择
  })

  // 其他监听器保持不变...
  hot.addHook('afterChange', function(changes, source) {
    safeAsyncOperation(() => {
      window.__onDataChange?.(changes, source)
    })
  })

  hot.addHook('afterFilter', function(conditionsStack) {
    safeAsyncOperation(() => {
      console.log('🔍🔍 筛选条件已应用')
    })
  })

  hot.addHook('afterDropdownMenuShow', function() {
    console.log('📋📋 下拉菜单显示')
  })

  hot.addHook('afterDropdownMenuHide', function() {
    console.log('📋📋 下拉菜单隐藏')
  })

  retryCount = 0
}


  const setupEventListeners0000 = () => {

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