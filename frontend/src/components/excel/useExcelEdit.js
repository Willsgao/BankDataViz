// frontend/src/components/excel/useExcelEdit.js
import { ref, computed, watch, nextTick, onUnmounted  } from 'vue'

export default function useExcelEdit(externalGetHotInstance, onCellChangeCallback = null) {
  console.log('🔄 useExcelEdit 初始化，回调:', typeof onCellChangeCallback)

  // 状态
  const isEditMode = ref(false)
  const hasChanges = ref(false)
  const saving = ref(false)
  const modifiedCells = ref(new Set())
  const unsavedCells = ref(new Set())
  const savedCells = ref(new Set())
  const modifiedCellsCount = ref(0)

  // 实例缓存
  let cachedHotInstance = null
  let cacheValid = false
  let lastCacheTime = 0
  const CACHE_TIMEOUT = 5000 // 5秒缓存超时

  // ============ 带缓存的实例获取函数 ============
  const getHotInstanceWithCache = () => {
  try {
    // 检查缓存是否有效
    const now = Date.now()
    const isCacheValid = cacheValid &&
                       cachedHotInstance &&
                       !cachedHotInstance.isDestroyed &&
                       (now - lastCacheTime) < CACHE_TIMEOUT

    if (isCacheValid) {
      // console.log('📦 使用缓存的表格实例')  // 减少日志
      return cachedHotInstance
    }

    // 缓存无效，重新获取实例
    if (externalGetHotInstance && typeof externalGetHotInstance === 'function') {
      const instance = externalGetHotInstance()
      if (instance && !instance.isDestroyed) {
        cachedHotInstance = instance
        cacheValid = true
        lastCacheTime = now
        // console.log('🔄 更新实例缓存')  // 减少日志
        return instance
      } else {
        // console.warn('❌ 获取的实例无效或已销毁')  // 减少日志
        // 不要清除缓存，只是返回 null
        return null
      }
    } else {
      console.warn('❌ externalGetHotInstance 函数无效')
    }

    return null
  } catch (error) {
    console.warn('❌ 获取表格实例失败:', error)
    // 不要清除缓存
    return null
  }
}




  // ============ 清理缓存 ============
  const clearCache = () => {
    cachedHotInstance = null
    cacheValid = false
    lastCacheTime = 0
  }

  // ============ 验证实例 ============
  const validateHotInstance = (instance) => {
    if (!instance) return false

    try {
      // 基本验证
      if (instance.isDestroyed) {
        console.warn('⚠️ 表格实例已被销毁')
        clearCache()
        return false
      }

      // 功能验证
      const settings = instance.getSettings()
      if (!settings) {
        console.warn('⚠️ 无法获取表格设置')
        return false
      }

      // 验证核心功能
      const hasCoreMethods = typeof instance.updateSettings === 'function' &&
                           typeof instance.render === 'function' &&
                           typeof instance.getDataAtCell === 'function'

      if (!hasCoreMethods) {
        console.warn('⚠️ 表格实例缺少核心方法')
        clearCache()
        return false
      }

      return true

    } catch (error) {
      console.warn('❌ 验证表格实例失败:', error)
      clearCache()
      return false
    }
  }

  // ============ 核心修复：处理单元格修改 ============
  const onDataChange = (changes, source) => {
  console.log('📝 onDataChange 触发:', {
    changes数量: changes?.length || 0,
    source,
    编辑模式: isEditMode.value
  })

  // 跳过无效修改
  if (!changes || source === 'loadData') {
    console.log('⏸️ 跳过无效修改')
    return
  }

  // 自动进入编辑模式
  const isEditingAction = source === 'edit' ||
                         source === 'Autofill.fill' ||
                         source === 'CopyPaste.paste'

  if (isEditingAction && !isEditMode.value) {
    console.log('🎯 检测到编辑操作，自动进入编辑模式')
    isEditMode.value = true
    window.currentEditMode = true
    setTimeout(() => {
      try {
        const hot = getHotInstanceWithCache()
        if (hot) {
          hot.updateSettings({ readOnly: false }, false)
          hot.render()
          console.log('✅ 已设置表格为编辑模式')
        }
      } catch (error) {
        console.warn('⚠️ 设置编辑模式失败，但继续处理:', error)
      }
    }, 100)
  }

  // 收集真实修改
  const cellModifications = []
  let hasActualChanges = false

  changes.forEach(([row, col, oldValue, newValue]) => {
    if (oldValue === newValue) return
    hasActualChanges = true
    const cellKey = `${row},${col}`
    const isNewModification = !savedCells.value.has(cellKey)

    if (isNewModification) {
      unsavedCells.value.add(cellKey)
      modifiedCells.value.add(cellKey)
    }

    cellModifications.push({
      row,
      col,
      oldValue,
      newValue,
      source,
      timestamp: Date.now(),
      cellKey
    })

    console.log('📝 记录单元格修改:', { cellKey, 旧值: oldValue, 新值: newValue, 是否新修改: isNewModification })
  })

  if (!hasActualChanges) return

  // 更新内部计数 & 通知父组件
  updateModifiedCellsCount()
  if (onCellChangeCallback && typeof onCellChangeCallback === 'function') {
    cellModifications.forEach(m => {
      m.isEditMode = isEditMode.value
      onCellChangeCallback(m)
    })
    console.log('📤 已通知父组件修改:', cellModifications.length, '个单元格')
  }

  // 关键：实例有效时再刷样式（只保留这一次调用）
  nextTick(() => {
    try {
      const hot = getHotInstanceWithCache()
      if (hot && !hot.isDestroyed) {
        updateModifiedCellsStyle()
        console.log('✅ updateModifiedCellsStyle 已调用')
      } else {
        console.warn('⚠️ 实例无效，跳过样式更新')
      }
    } catch (error) {
      console.warn('⚠️ 更新样式失败:', error)
    }
  })


  // ===== 立即刷样式（同步，确保实例存在） =====
    const hotRightNow = getHotInstanceWithCache()
    console.log('🔍 同步实例检查', { hotExist: !!hotRightNow, destroyed: hotRightNow?.isDestroyed })

    if (hotRightNow && !hotRightNow.isDestroyed) {
      updateModifiedCellsStyle()
      console.log('✅ updateModifiedCellsStyle 已同步调用')
    } else {
      console.warn('⚠️ 同步实例无效，样式未刷')
    }

}



   const updateModifiedCellsCount = () => {
      const unsavedCount = unsavedCells.value.size
      const totalCount = modifiedCells.value.size

      modifiedCellsCount.value = unsavedCount

      // 更新 hasChanges 状态
      const newHasChanges = unsavedCount > 0
      if (newHasChanges !== hasChanges.value) {
        console.log('🔄 hasChanges 状态变化:', {
          旧值: hasChanges.value,
          新值: newHasChanges,
          未保存数: unsavedCount,
          总修改数: totalCount
        })
        hasChanges.value = newHasChanges
      }

      // ===== 立即刷样式（最稳点）=====
      const hot = getHotInstanceWithCache()
      console.log('🔥 updateModifiedCellsCount 里实例检查', {
        hotExist: !!hot,
        destroyed: hot?.isDestroyed,
        未保存数: unsavedCount,
        总修改数: totalCount
      })

      if (hot && !hot.isDestroyed) {
        updateModifiedCellsStyle()
        console.log('✅ updateModifiedCellsCount 里已调用 updateModifiedCellsStyle')
      } else {
        console.warn('⚠️ 实例无效，跳过样式更新')
      }

      // 更新全局状态
      if (typeof window !== 'undefined') {
        window.currentHasChanges = hasChanges.value
        window.modifiedCellsCount = modifiedCellsCount.value
        window.unsavedCellsCount = unsavedCount
      }
    }



  const MAX_RETRY = 3
  const RETRY_DELAY = 200

  const updateModifiedCellsStyle = async (retry = 0) => {
  console.log('🎨 进入刷样式函数', {
    saved: savedCells.value.size,
    unsaved: unsavedCells.value.size,
    retry
  })

  const hot = getHotInstanceWithCache()

  // 每次刷样式前，顺手把实例写回全局，保证后面一定能拿到
    if (hot && !hot.isDestroyed) {
      window.__excelHotInstance = hot        // ←新增
      console.log('🔁 实例已写回 window.__excelHotInstance', hot)
    }


  // 实例无效 && 还没超过重试次数
  if (!hot || hot.isDestroyed || !hot.getSettings) {
    if (retry < MAX_RETRY) {
      console.warn(`⚠️ 实例无效，${RETRY_DELAY}ms 后重试(${retry + 1}/${MAX_RETRY})`)
      setTimeout(() => updateModifiedCellsStyle(retry + 1), RETRY_DELAY)
    } else {
      console.warn('❌ 实例持续无效，放弃样式更新')
    }
    return
  }

  try {
    const cellConfig = []

    // 已保存（绿色）
    savedCells.value.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      cellConfig.push({ row, col, className: 'saved-modified-cell' })
    })

    // 未保存（红色）- 仅编辑模式
    if (isEditMode.value) {
      unsavedCells.value.forEach(cellKey => {
        const [row, col] = cellKey.split(',').map(Number)
        cellConfig.push({ row, col, className: 'unsaved-modified-cell' })
      })
    }

    hot.updateSettings({ cell: cellConfig }, false)
    hot.render()

  } catch (err) {
    console.error('❌ 更新样式失败:', err)
  }


}

  const collectModifiedData = () => {
    const hot = getHotInstanceWithCache()
    if (!hot || !validateHotInstance(hot)) {
      console.warn('❌ 无法收集修改数据：表格实例无效')
      return []
    }

    const modifiedData = []
    modifiedCells.value.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      const value = hot.getDataAtCell(row, col)
      modifiedData.push({
        row,
        col,
        value,
        cellKey,
        isSaved: savedCells.value.has(cellKey)
      })
    })

    return modifiedData
  }

  // ============ 公共方法 ============
  const toggleEditMode = (onSuccess) => {
    console.log('🔄 toggleEditMode 被调用，当前状态:', isEditMode.value, '回调:', typeof onSuccess)

    // 使用带缓存的实例获取
    const hot = getHotInstanceWithCache()
    if (!hot || !validateHotInstance(hot)) {
      console.warn('❌ 无法切换编辑模式：表格实例无效')
      if (onSuccess && typeof onSuccess === 'function') {
        onSuccess('表格实例无效，无法切换编辑模式', 'error')
      }
      return
    }

    // 检查实例状态
    if (hot.isDestroyed) {
      console.warn('❌ 表格实例已被销毁')
      clearCache()
      if (onSuccess && typeof onSuccess === 'function') {
        onSuccess('表格实例已被销毁', 'error')
      }
      return
    }

    // 切换状态
    isEditMode.value = !isEditMode.value

    // 立即更新表格只读状态
    try {
      const newReadOnly = !isEditMode.value

      // 更新表格的 readOnly 设置
      hot.updateSettings({
        readOnly: newReadOnly
      }, false)

      // 更新所有列的 readOnly
      const columns = hot.getSettings().columns
      if (columns && Array.isArray(columns)) {
        const newColumns = columns.map(col => ({
          ...col,
          readOnly: newReadOnly
        }))
        hot.updateSettings({
          columns: newColumns
        }, false)
      }

      // 强制重新渲染
      setTimeout(() => {
        if (hot && !hot.isDestroyed) {
          hot.render()
          console.log('📋 表格只读状态已同步:', {
            编辑模式: isEditMode.value,
            表格只读: newReadOnly
          })
        }
      }, 50)

    } catch (error) {
      console.error('❌ 更新表格状态失败:', error)
      if (onSuccess && typeof onSuccess === 'function') {
        onSuccess('更新表格状态失败', 'error')
      }
      return
    }

    // 更新全局状态
    window.currentEditMode = isEditMode.value
    console.log('🌐 全局编辑模式更新为:', window.currentEditMode)

    // 显示消息
    if (isEditMode.value) {
      console.log('✅ 进入编辑模式')
      if (onSuccess && typeof onSuccess === 'function') {
        onSuccess('已进入编辑模式，可以修改单元格', 'success')
      }
    } else {
      console.log('🔒 退出编辑模式')
      if (onSuccess && typeof onSuccess === 'function') {
        onSuccess('已退出编辑模式', 'info')
      }
    }
  }

  // 确保 updateTableReadOnly 函数存在
  const updateTableReadOnly = () => {
    const hot = getHotInstanceWithCache()
    if (!hot || !validateHotInstance(hot)) {
      console.warn('❌ 无法更新表格只读状态：表格实例无效')
      return
    }

    try {
      console.log('📋 更新表格只读状态:', {
        编辑模式: isEditMode.value,
        当前只读状态: hot.getSettings().readOnly
      })

      // 更新所有列的 readOnly 设置
      const columns = hot.getSettings().columns
      if (columns && Array.isArray(columns)) {
        const newColumns = columns.map(col => ({
          ...col,
          readOnly: !isEditMode.value
        }))

        hot.updateSettings({
          columns: newColumns
        }, false)
      }

      // 直接设置表格的 readOnly
      hot.updateSettings({
        readOnly: !isEditMode.value
      }, false)

      console.log('📋 表格只读状态更新:', {
        编辑模式: isEditMode.value,
        表格只读: !isEditMode.value
      })

      // 延迟强制重新渲染，确保状态生效
      setTimeout(() => {
        if (hot && !hot.isDestroyed) {
          hot.render()
          console.log('✅ 表格只读状态更新完成:', {
            新状态: hot.getSettings().readOnly
          })
        }
      }, 100)

    } catch (error) {
      console.error('❌ 更新表格只读状态失败:', error)
    }
  }

  const saveChanges = async (saveCallback) => {
    if (!hasChanges.value || saving.value) return

    saving.value = true
    console.log('💾 开始保存修改...')

    try {
      const modifiedData = collectModifiedData()
      const unsavedCount = unsavedCells.value.size

      if (saveCallback) {
        await saveCallback(modifiedData, unsavedCount)
      }

      // 将未保存的单元格标记为已保存
      unsavedCells.value.forEach(cellKey => savedCells.value.add(cellKey))
      unsavedCells.value.clear()
      hasChanges.value = false

      updateModifiedCellsStyle()

      console.log('✅ 保存完成:', {
        保存单元格数: modifiedData.length,
        标记为已保存: savedCells.value.size
      })

      return {
        success: true,
        message: `成功保存 ${unsavedCount} 个修改`,
        savedCount: unsavedCount
      }
    } catch (error) {
      console.error('❌ 保存失败:', error)
      return { success: false, message: `保存失败: ${error.message}` }
    } finally {
      saving.value = false
    }
  }

  const resetChanges = () => {
    console.log('🔄 重置所有修改')
    modifiedCells.value.clear()
    unsavedCells.value.clear()
    savedCells.value.clear()
    hasChanges.value = false

    const hot = getHotInstanceWithCache()
    if (hot && validateHotInstance(hot)) {
      hot.updateSettings({ cell: [] }, false)
      hot.render()
    }

    return { success: true, message: '已重置所有修改' }
  }

  // 标记已保存单元格
  const markSavedCells = (savedCellKeys) => {
    if (!Array.isArray(savedCellKeys)) return

    savedCellKeys.forEach(cellKey => {
      if (typeof cellKey === 'string') {
        savedCells.value.add(cellKey)
        unsavedCells.value.delete(cellKey)
        modifiedCells.value.add(cellKey)
      }
    })

    updateModifiedCellsCount()
    updateModifiedCellsStyle()

    return {
      success: true,
      message: `已标记 ${savedCellKeys.length} 个单元格为已保存`
    }
  }

  // ============ 实例健康检查 ============
  const checkInstanceHealth = () => {
  const hot = getHotInstanceWithCache()
  if (!hot) {
    // console.log('❌ 实例健康检查：实例不存在')  // ❌ 减少日志
    return { healthy: false, reason: '实例不存在' }
  }

  try {
    if (hot.isDestroyed) {
      console.log('❌ 实例健康检查：实例已销毁')
      // 不清除缓存，让调用者决定
      return { healthy: false, reason: '实例已销毁' }
    }

    const settings = hot.getSettings()
    if (!settings) {
      console.log('❌ 实例健康检查：无法获取设置')
      return { healthy: false, reason: '无法获取设置' }
    }

    // 检查关键方法
    const methods = ['updateSettings', 'render', 'getDataAtCell', 'getCellMeta']
    const missingMethods = methods.filter(method => typeof hot[method] !== 'function')

    if (missingMethods.length > 0) {
      console.log('❌ 实例健康检查：缺少方法', missingMethods)
      return {
        healthy: false,
        reason: `缺少方法: ${missingMethods.join(', ')}`
      }
    }

    // console.log('✅ 实例健康检查通过')  // ❌ 减少日志
    return { healthy: true, settings: settings }

  } catch (error) {
    console.log('❌ 实例健康检查异常:', error)
    // 不清除缓存
    return { healthy: false, reason: `检查异常: ${error.message}` }
  }
}

  // ============ 刷新缓存 ============
  const refreshCache = () => {
    clearCache()
    const hot = getHotInstanceWithCache()
    return {
      success: !!hot,
      message: hot ? '缓存已刷新' : '刷新缓存失败',
      instance: hot
    }
  }

  // ============ 监听器 ============
  watch(isEditMode, (newVal) => {
    console.log('🎛️ 编辑模式变化:', newVal)
    if (newVal) {
      // 进入编辑模式时，立即更新表格状态
      nextTick(() => {
        const hot = getHotInstanceWithCache()
        if (hot && validateHotInstance(hot)) {
          try {
            hot.updateSettings({ readOnly: false }, false)
            setTimeout(() => {
              if (hot && !hot.isDestroyed) {
                hot.render()
                console.log('✅ 编辑模式变化后更新表格状态')
              }
            }, 50)
          } catch (error) {
            console.error('❌ 编辑模式更新失败:', error)
          }
        }
      })

      updateModifiedCellsStyle()
    }
  })

  // 改成
    const healthTimer = ref(0)
    const monitorTimer = ref(0)

    // 健康检查（开发环境）
if (process.env.NODE_ENV === 'development') {
  healthTimer.value = setInterval(() => {
    if (isEditMode.value && cacheValid && cachedHotInstance) {
      const health = checkInstanceHealth()
      if (!health.healthy) refreshCache()
    }
  }, 60_000)
}

// 编辑模式监控（开发环境）
monitorTimer.value = setInterval(() => {
  const hot = getHotInstanceWithCache()
  if (hot && isEditMode.value && hot.getSettings().readOnly) {
    hot.updateSettings({ readOnly: false }, false)
  }
}, 1_000)


  // ============ 生命周期 ============
    onUnmounted(() => {
  clearInterval(healthTimer.value)
  clearInterval(monitorTimer.value)
  clearCache()
})



  return {
    // 状态
    isEditMode,
    hasChanges,
    saving,
    modifiedCellsCount,
    modifiedCells,
    unsavedCells,
    savedCells,

    // 方法
    toggleEditMode,
    saveChanges,
    onDataChange,
    updateTableReadOnly,
    resetChanges,
    collectModifiedData,
    updateModifiedCellsStyle,
    markSavedCells,

    // 新增：实例管理方法
    clearCache,
    checkInstanceHealth,
    refreshCache,
    getHotInstance: getHotInstanceWithCache,
    validateHotInstance
  }
}