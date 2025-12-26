// frontend/src/components/excel/useExcelEdit.js
import { ref } from 'vue'

export default function useExcelEdit(getSafeHotInstance) {
  // ============ 状态 ============
  const isEditMode = ref(false)
  const hasChanges = ref(false)
  const saving = ref(false)
  const modifiedCellsCount = ref(0)
  const modifiedCells = ref(new Set())

  // ============ 数据变化处理函数 ============
const onDataChange = (changes, source) => {
  console.log('📝 onDataChange 被调用:', {
    changes: changes,
    source: source,
    isEditMode: isEditMode.value,
    changesCount: changes ? changes.length : 0
  })

  // 如果不是编辑模式，忽略所有更改
  if (!isEditMode.value) {
    console.log('ℹ️ 非编辑模式，忽略更改')
    return
  }

  // 如果来源是 'loadData'，忽略
  if (source === 'loadData') {
    console.log('ℹ️ 数据加载来源，忽略更改')
    return
  }

  if (!changes || changes.length === 0) {
    console.log('ℹ️ 无有效更改')
    return
  }

  console.log('✅ 处理有效更改，数量:', changes.length)

  // 处理每个更改
  changes.forEach(([row, col, oldValue, newValue]) => {
    // 跳过空行或无效行
    if (row === null || col === null) {
      console.log(`⚠️ 跳过无效坐标: row=${row}, col=${col}`)
      return
    }

    const cellKey = `${row},${col}`

    // 如果值没有实际变化，跳过
    const oldStr = String(oldValue !== null && oldValue !== undefined ? oldValue : '')
    const newStr = String(newValue !== null && newValue !== undefined ? newValue : '')

    if (oldStr === newStr) {
      console.log(`ℹ️ 单元格 [${row},${col}] 值未变化，跳过`)
      return
    }

    console.log(`📝 检测到更改: [${row},${col}] "${oldStr}" -> "${newStr}"`)

    // 添加到修改集合
    if (!modifiedCells.value.has(cellKey)) {
      modifiedCells.value.add(cellKey)
      console.log(`➕ 新增修改单元格: ${cellKey}`)
    }
  })

  // 更新修改计数
  modifiedCellsCount.value = modifiedCells.value.size
  hasChanges.value = modifiedCellsCount.value > 0

  console.log('📊 更改统计:', {
    totalChanges: modifiedCellsCount.value,
    hasChanges: hasChanges.value,
    modifiedCells: Array.from(modifiedCells.value)
  })

  // 立即更新样式
  if (modifiedCellsCount.value > 0) {
    updateModifiedCellsStyle()
  }
}

  // 切换编辑模式（直接从原文件复制完整逻辑）
  // 切换编辑模式（完整修复版）
  const toggleEditMode = (showMessageCallback) => {
  if (isEditMode.value && hasChanges.value) {
    // 这里需要 ElMessageBox.confirm，通过回调传递
    if (window.__showConfirm) {
      window.__showConfirm(
        '有未保存的更改，确定要退出编辑模式吗？',
        '提示',
        () => {
          resetChanges()
          isEditMode.value = false
          updateTableReadOnly()
          showMessageCallback?.('已退出编辑模式', 'success')
        },
        () => {
          console.log('用户取消退出编辑模式')
        }
      )
    } else {
      // 如果没有确认框，直接切换
      resetChanges()
      isEditMode.value = !isEditMode.value
      updateTableReadOnly()
      showMessageCallback?.(isEditMode.value ? '已进入编辑模式' : '已退出编辑模式', 'success')
    }
  } else {
    isEditMode.value = !isEditMode.value
    if (!isEditMode.value) {
      resetChanges()
    }
    updateTableReadOnly()
    showMessageCallback?.(isEditMode.value ? '已进入编辑模式' : '已退出编辑模式', 'success')
  }

  // 关键：切换编辑模式时也更新样式
  setTimeout(() => {
    updateModifiedCellsStyle()
  }, 100)

  console.log('🎛️ 编辑模式切换:', {
    newMode: isEditMode.value,
    hasChanges: hasChanges.value,
    readOnly: !isEditMode.value
  })
}

  // 保存更改（直接从原文件复制完整逻辑）
  const saveChanges = async (saveApiCallback) => {
    if (!hasChanges.value) return

    saving.value = true
    try {
      console.log('💾 开始保存修改的数据:', {
        modifiedCells: Array.from(modifiedCells.value),
        totalChanges: modifiedCellsCount.value
      })

      // 收集修改的数据
      const modifiedData = collectModifiedData()

      // 调用保存API（通过回调）
      if (saveApiCallback) {
        await saveApiCallback(modifiedData, modifiedCellsCount.value)
      }

      // 显示成功消息（通过回调）
      window.__showMessage?.(`数据保存成功，共保存 ${modifiedCellsCount.value} 个修改`, 'success')
      resetChanges()

    } catch (error) {
      console.error('保存失败:', error)
      window.__showMessage?.(`保存失败: ${error.message}`, 'error')
    } finally {
      saving.value = false
    }
  }


  // ============ 辅助方法 ============

  // 收集修改的数据（直接从原文件复制完整逻辑）
  const collectModifiedData = () => {
    const hot = getSafeHotInstance()
    if (!hot) {
      return []
    }

    const modifiedData = []

    // 遍历所有修改的单元格
    modifiedCells.value.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      const newValue = hot.getDataAtCell(row, col)

      modifiedData.push({
        row: row,
        column: col,
        value: newValue,
        cell_key: cellKey
      })
    })

    console.log('📋 收集的修改数据:', modifiedData)
    return modifiedData
  }

  // 更新表格只读状态（直接从原文件复制完整逻辑）
  const updateTableReadOnly = () => {
    const hot = getSafeHotInstance()
    if (!hot) {
      console.log('ℹ️ 表格实例无效，跳过只读状态更新')
      return
    }

    const readOnly = !isEditMode.value
    console.log('🔒 更新表格只读状态:', { readOnly })

    try {
      hot.updateSettings({
        readOnly: readOnly
      })

      // 更新列配置的只读状态
      const currentColumns = hot.getSettings().columns || []
      const updatedColumns = currentColumns.map(col => ({
        ...col,
        readOnly: readOnly
      }))

      hot.updateSettings({
        columns: updatedColumns
      })

      hot.render()
    } catch (error) {
      console.warn('⚠️ 更新只读状态失败:', error.message)
    }
  }

  // 更新修改单元格样式（增强版）
  // 更新修改单元格样式（完整修复版）
  const updateModifiedCellsStyle = () => {
  console.log('🎨 开始更新修改单元格样式...')

  const hot = getSafeHotInstance()
  if (!hot) {
    console.log('❌ 表格实例无效，无法更新样式')
    return
  }

  try {
    // 关键修复：使用合并的方式更新设置，而不是替换
    const currentSettings = hot.getSettings()
    const currentCellConfig = currentSettings.cell || []

    console.log('📋 当前设置:', {
      单元格配置数: currentCellConfig.length,
      修改单元格数: modifiedCells.value.size
    })

    // 创建单元格样式映射
    const cellStyleMap = new Map()

    // 先收集现有的非修改样式
    currentCellConfig.forEach(config => {
      if (config.row !== undefined && config.col !== undefined) {
        const key = `${config.row},${config.col}`

        // 如果已经是修改单元格样式，跳过
        if (!config.className?.includes('modified-cell')) {
          cellStyleMap.set(key, config)
        }
      }
    })

    // 添加所有修改单元格的样式
    modifiedCells.value.forEach(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      const key = `${row},${col}`

      cellStyleMap.set(key, {
        row: row,
        col: col,
        className: 'modified-cell'
      })

      console.log(`➕ 设置修改样式: [${row},${col}]`)
    })

    // 转换回数组
    const newCellConfig = Array.from(cellStyleMap.values())

    console.log('📊 最终样式配置:', {
      总数: newCellConfig.length,
      修改样式数: modifiedCells.value.size
    })

    // 关键：只更新 cell 配置，保留其他所有设置
    hot.updateSettings({
      cell: newCellConfig
    }, false) // false 表示不覆盖其他设置

    // 立即渲染
    hot.render()

    // 验证
    setTimeout(() => {
      const modifiedCellsInDOM = hot.rootElement.querySelectorAll('.modified-cell')
      console.log('🔍 DOM验证 - 修改单元格数:', modifiedCellsInDOM.length)

      if (modifiedCellsInDOM.length > 0) {
        console.log('✅ 样式成功应用到DOM')
        // 检查第一个修改单元格的样式
        const firstCell = modifiedCellsInDOM[0]
        console.log('🎯 第一个修改单元格样式:', {
          背景色: window.getComputedStyle(firstCell).backgroundColor,
          边框: window.getComputedStyle(firstCell).border
        })
      } else {
        console.warn('⚠️ 修改单元格样式未应用到DOM')
      }
    }, 50)

  } catch (error) {
    console.error('❌ 更新单元格样式失败:', error)
  }
}

  // 重置更改状态时也要清除样式
  // 重置更改状态时也要清除样式
  const resetChanges = () => {
  hasChanges.value = false
  modifiedCellsCount.value = 0
  modifiedCells.value.clear()

  // 清除修改样式
  const hot = getSafeHotInstance()
  if (hot) {
    try {
      // 获取当前所有单元格样式配置
      const currentCellConfig = hot.getSettings().cell || []

      // 过滤掉修改样式
      const filteredCellConfig = currentCellConfig.filter(config =>
        !config.className || !config.className.includes('modified-cell')
      )

      hot.updateSettings({
        cell: filteredCellConfig
      }, false) // false 表示不覆盖其他设置

      hot.render()

      console.log('✅ 修改样式已清除，剩余样式规则:', filteredCellConfig.length)
    } catch (error) {
      console.warn('⚠️ 清除修改样式失败:', error.message)
    }
  }
}



  return {
    // refs
    isEditMode,
    hasChanges,
    saving,
    modifiedCellsCount,
    modifiedCells,

    // methods
    toggleEditMode,
    saveChanges,
    onDataChange,
    updateTableReadOnly,
    updateModifiedCellsStyle,
    resetChanges,
    collectModifiedData
  }
}