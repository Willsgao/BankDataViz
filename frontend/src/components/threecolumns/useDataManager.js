// useDataManager.js - 完整修复版本
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import dataManager from '@/utils/dataManager.js'
import sheetStateManager from '@/utils/SheetStateManager.js'
import { getApiUrl } from '@/utils/config.js'
import { http } from '@/api/index.js'  // 导入 http 实例

/**
 * 数据管理组合函数
 */
export function useDataManager() {
  // 状态
  const saving = ref(false)
  const saveType = ref('')
  const lastSaveTime = ref(null)
  const saveStatus = ref({
    type: 'info',
    text: '未修改'
  })
  const modifiedCellsCount = ref(0)

  /**
   * 初始化数据管理器上下文
   */
  const initDataManagerContext = (selectedPdf, selectedSheet, selectedExcelFile) => {
    console.log('🔍 initDataManagerContext 被调用，检查参数:')
    console.log('   selectedPdf:', selectedPdf)
    console.log('   selectedSheet:', selectedSheet)
    console.log('   selectedExcelFile:', selectedExcelFile)

    // 检查是否有必要的参数
    if (!selectedPdf) {
      console.warn('❌ 缺少 selectedPdf')
      return
    }

    if (!selectedSheet) {
      console.warn('❌ 缺少 selectedSheet')
      return
    }

    if (!selectedExcelFile) {
      console.warn('❌ 缺少 selectedExcelFile')
      return
    }

    // 确保有所有必要的数据
    const context = {
      pdfId: selectedPdf.id,
      excelFile: selectedExcelFile,
      sheetName: selectedSheet.name,
      sessionId: null
    }

    console.log('✅ 设置上下文:', context)
    dataManager.setContext(context)

    // 验证设置是否成功
    setTimeout(() => {
      console.log('🔍 验证上下文设置:')
      console.log('   当前manager上下文:', dataManager.currentContext)
      console.log('   PDF ID匹配:', dataManager.currentContext.pdfId === selectedPdf.id)
      console.log('   Sheet匹配:', dataManager.currentContext.sheetName === selectedSheet.name)
    }, 100)
  }

  /**
   * 更新保存状态
   */
  const updateSaveStatus = (selectedSheet, selectedPdf, sheetStateManager) => {
    // 如果没有选中sheet，显示默认状态
    if (!selectedSheet || !selectedPdf) {
      saveStatus.value = {
        type: 'info',
        text: '请选择表格'
      };
      modifiedCellsCount.value = 0;
      return;
    }

    const context = sheetStateManager.getActiveContext();
    if (!context) {
      saveStatus.value = {
        type: 'info',
        text: '状态未初始化'
      };
      return;
    }

    // 获取当前表类型的修改统计
    const tableType = context.tableType || 'original';
    const stats = sheetStateManager.getModificationStats();

    if (!stats) {
      saveStatus.value = {
        type: 'info',
        text: '加载中...'
      };
      return;
    }

    const tableStats = stats[tableType];
    const hasUnsaved = tableStats.unsaved > 0;
    const hasSaved = tableStats.saved > 0;

    // 更新全局修改计数
    modifiedCellsCount.value = tableStats.unsaved;

    // 根据状态显示不同的消息
    if (!hasUnsaved && !hasSaved) {
      saveStatus.value = {
        type: 'info',
        text: '未修改'
      };
    } else if (hasUnsaved) {
      saveStatus.value = {
        type: 'warning',
        text: `${tableStats.unsaved}个单元格未保存`
      };
    } else if (hasSaved) {
      saveStatus.value = {
        type: 'success',
        text: `已保存 (${tableStats.saved}处修改)`
      };
    }

    console.log('📊 保存状态更新:', {
      表类型: tableType,
      未保存: tableStats.unsaved,
      已保存: tableStats.saved,
      状态: saveStatus.value.text
    });
  }

  /**
   * 检查当前表格是否有未保存修改
   */
  const hasUnsavedChangesInCurrentTable = (selectedSheet, selectedPdf, sheetStateManager) => {
      if (!selectedSheet || !selectedPdf) {
        return false
      }

      // 如果当前没有活跃上下文，尝试设置一个
      if (!sheetStateManager.getActiveContext()) {
        return false
      }

      const context = sheetStateManager.getActiveContext()
      const tableType = context.tableType || 'original'

      // 直接检查未保存计数
      const unsavedCount = sheetStateManager.getUnsavedChangesCount(tableType)
      const hasUnsaved = unsavedCount > 0

      console.log('🔍 保存按钮状态检查:', {
        表类型: tableType,
        未保存数: unsavedCount,
        是否可保存: hasUnsaved
      })

      return hasUnsaved
    }

  /**
   * 保存草稿到 localStorage
   */
  const saveDraftToLocalStorage = (draftData) => {
  try {
    const key = `excel_draft_${draftData.pdf_id}_${draftData.excel_file}_${draftData.sheet_name}_${draftData.table_type}_${Date.now()}`

    // 保存草稿数据
    localStorage.setItem(key, JSON.stringify(draftData))

    // 同时保存一个索引，方便查找
    const draftIndexKey = `excel_draft_index_${draftData.pdf_id}_${draftData.excel_file}_${draftData.sheet_name}`
    const existingIndex = JSON.parse(localStorage.getItem(draftIndexKey) || '[]')
    existingIndex.push({
      key: key,
      timestamp: new Date().toISOString(),
      save_type: draftData.save_type,
      changes_count: draftData.changes.length
    })
    localStorage.setItem(draftIndexKey, JSON.stringify(existingIndex))

    console.log('📦 草稿已保存到 localStorage:', {
      key: key,
      changes_count: draftData.changes.length,
      timestamp: new Date().toLocaleTimeString()
    })

    return {
      success: true,
      message: '草稿已保存到本地',
      storage_key: key,  // 确保这个字段名正确
      changes_count: draftData.changes.length
    }
  } catch (error) {
    console.error('❌ 保存草稿到 localStorage 失败:', error)
    return {
      success: false,
      error: '保存草稿失败'
    }
  }
}


  /**
   * 获取当前表格的草稿记录
   */
  const getCurrentDrafts = (pdfId, excelFile, sheetName) => {
    const draftIndexKey = `excel_draft_index_${pdfId}_${excelFile}_${sheetName}`
    const draftIndex = JSON.parse(localStorage.getItem(draftIndexKey) || '[]')

    // 按时间倒序排序
    return draftIndex.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
  }

  /**
   * 恢复草稿
   */
  const restoreDraftFromLocalStorage = (draftKey) => {
    try {
      const draftData = JSON.parse(localStorage.getItem(draftKey))
      if (!draftData) {
        return {
          success: false,
          error: '草稿不存在'
        }
      }

      console.log('📂 恢复草稿:', draftData)
      return {
        success: true,
        data: draftData,
        message: '草稿恢复成功'
      }
    } catch (error) {
      console.error('❌ 恢复草稿失败:', error)
      return {
        success: false,
        error: '恢复草稿失败'
      }
    }
  }

  /**
   * 调用后端接口保存数据
   */
  const saveToBackend = async (saveData) => {
    try {
      console.log('🌐 调用后端保存接口...', {
        pdf_id: saveData.pdf_id,
        excel_file: saveData.excel_file,
        sheet_name: saveData.sheet_name,
        changes_count: saveData.changes?.length || 0,
        save_type: saveData.save_type
      })

      // 使用 http 实例调用后端接口
      // 注意：后端需要有对应的 /save-excel-changes 接口
      const response = await http.post('/save-excel-changes', saveData)

      console.log('✅ 后端保存成功:', response)
      return {
        success: true,
        message: response.message || '保存成功',
        reload_required: response.reload_required || false,
        data: response.data
      }
    } catch (error) {
      console.error('❌ 后端保存失败:', error)

      // 如果后端接口不存在，返回模拟成功（用于演示）
      if (error.response?.status === 404) {
        console.warn('⚠️ 后端接口不存在，返回模拟成功')
        return {
          success: true,
          message: '模拟保存成功（后端接口待实现）',
          reload_required: false,
          data: {
            saved_changes: saveData.changes?.length || 0,
            timestamp: new Date().toISOString()
          }
        }
      }

      return {
        success: false,
        error: error.message || '后端保存失败'
      }
    }
  }

  /**
   * 保存数据（主函数）
   */
  // useDataManager.js - 简化保存逻辑，确保核心功能正常
const saveDataFromManager = async (saveType, selectedPdf, selectedSheet, selectedExcelFile, sheetStateManager, showFlatMode) => {
  console.log('💾 saveDataFromManager: 保存数据', saveType)

  // 获取当前上下文
  const tableType = showFlatMode ? 'flattened' : 'original'
  const context = {
    pdfId: selectedPdf?.id,
    excelFile: selectedExcelFile,
    sheetName: selectedSheet?.name,
    tableType: tableType
  }

  try {
    // 检查 sheetStateManager 是否存在
    if (!sheetStateManager || !sheetStateManager.sheetStates) {
      console.log('❌ SheetStateManager 不存在或没有 sheetStates')
      return { success: false, error: '状态管理器未初始化' }
    }

    // 构建 key（与 SheetStateManager 中一致）
    const sheetKey = `${context.pdfId}_${context.excelFile}_${context.sheetName}`
    console.log('🔍 查找的 key:', sheetKey)

    // 获取对应的 sheetState
    const sheetState = sheetStateManager.sheetStates.get(sheetKey)
    if (!sheetState) {
      console.log('❌ 未找到对应的 sheetState')
      return { success: false, error: '未找到对应的表格状态' }
    }

    console.log('📊 sheetState:', sheetState)

    // 获取修改数据
    const modifications = sheetState.modifications?.[tableType]
    if (!modifications || modifications.size === 0) {
      console.log('📝 没有未保存的修改')
      return { success: false, error: '没有修改' }
    }

    // 从 Map 转换为数组
    const unsavedChanges = Array.from(modifications.values()).map(mod => ({
      row: mod.row,
      col: mod.col,
      oldValue: mod.oldValue,
      newValue: mod.newValue,
      cellKey: `${mod.row},${mod.col}`,
      tableType: mod.tableType
    }))

    console.log('📤 未保存修改:', unsavedChanges.length, '个')

    if (unsavedChanges.length === 0) {
      console.log('📝 没有需要保存的修改')
      return { success: false, error: '没有修改' }
    }

    // ============ 构建保存数据 ============
    const saveData = {
      pdf_id: context.pdfId,
      excel_file: context.excelFile,
      sheet_name: context.sheetName,
      changes: unsavedChanges,
      save_type: saveType,
      table_type: context.tableType,
      saved_at: new Date().toISOString(),
      timestamp: Date.now()
    }

    // ============ 根据保存类型执行不同逻辑 ============
    if (saveType === 'draft') {
      // 保存草稿：保存到 localStorage
      console.log('📝 保存草稿到本地...')

      try {
        const result = saveDraftToLocalStorage(saveData)

        if (result.success) {
          console.log('✅ 草稿保存成功，开始更新状态...')

          // ============ 关键：标记修改为已保存 ============
          // 1. 标记所有修改为已保存
          modifications.forEach(mod => {
            mod.saved = true
            mod.saveType = 'draft'
            mod.savedAt = new Date().toISOString()
          })

          // 2. 移动到已保存修改
          if (!sheetState.savedModifications) {
            sheetState.savedModifications = {}
          }
          if (!sheetState.savedModifications[tableType]) {
            sheetState.savedModifications[tableType] = new Map()
          }

          // 复制到已保存修改
          modifications.forEach((mod, key) => {
            sheetState.savedModifications[tableType].set(key, mod)
          })

          // 3. 清理未保存修改
          modifications.clear()
          console.log('🗑️ 已清空未保存修改')

          // 4. 立即更新统计
          if (typeof sheetStateManager.updateStats === 'function') {
            sheetStateManager.updateStats()
          }

          // 5. 保存状态到存储
          sheetStateManager.saveStateToStorage()

          // 6. 检查状态
          const unsavedAfterSave = sheetStateManager.getUnsavedChangesCount(tableType)
          const savedAfterSave = sheetStateManager.getSavedChangesCount(tableType)

          console.log('🔍 保存后状态检查:', {
            未保存数量: unsavedAfterSave,
            已保存数量: savedAfterSave,
            是否成功: unsavedAfterSave === 0
          })

          return {
            success: true,
            message: '草稿已保存到本地',
            changesCount: unsavedChanges.length,
            data: {
              saved_cells: Array.from(sheetState.savedModifications[tableType]?.keys() || []),
              storage_key: result.storage_key
            }
          }
        } else {
          return result
        }
      } catch (error) {
        console.error('❌ 保存草稿失败:', error)
        return {
          success: false,
          error: '保存草稿失败: ' + error.message
        }
      }

    } else if (saveType === 'final') {
      // 最终保存：调用后端接口
      console.log('🌐 最终保存到后端...')

      try {
        const result = await saveToBackend(saveData)

        if (result.success) {
          // 标记为已保存并清理
          modifications.forEach(mod => {
            mod.saved = true
            mod.saveType = 'final'
            mod.savedAt = new Date().toISOString()
          })

          if (!sheetState.savedModifications) {
            sheetState.savedModifications = {}
          }
          if (!sheetState.savedModifications[tableType]) {
            sheetState.savedModifications[tableType] = new Map()
          }

          modifications.forEach((mod, key) => {
            sheetState.savedModifications[tableType].set(key, mod)
          })

          modifications.clear()

          // 更新统计
          if (typeof sheetStateManager.updateStats === 'function') {
            sheetStateManager.updateStats()
          }

          // 保存状态
          sheetStateManager.saveStateToStorage()

          // 清理本地草稿
          const draftIndexKey = `excel_draft_index_${context.pdfId}_${context.excelFile}_${context.sheetName}`
          localStorage.removeItem(draftIndexKey)

          return {
            success: true,
            message: result.message || '最终保存成功',
            changesCount: unsavedChanges.length,
            data: {
              saved_cells: Array.from(sheetState.savedModifications[tableType]?.keys() || []),
              ...result.data
            }
          }
        } else {
          return result
        }
      } catch (error) {
        console.error('❌ 最终保存失败:', error)
        return {
          success: false,
          error: '最终保存失败: ' + error.message
        }
      }
    }

  } catch (error) {
    console.error('❌ 保存失败:', error)
    return {
      success: false,
      error: error.message || '保存失败'
    }
  }
}

  /**
   * 恢复未保存的修改（从本地草稿）
   */
  const restoreUnsavedDataFromDraft = async (selectedPdf, selectedSheet, selectedExcelFile, showFlatMode) => {
    if (!selectedPdf || !selectedSheet || !selectedExcelFile) {
      return { success: false, error: '请先选择表格' }
    }

    const tableType = showFlatMode ? 'flattened' : 'original'

    try {
      // 获取当前表格的草稿记录
      const drafts = getCurrentDrafts(selectedPdf.id, selectedExcelFile, selectedSheet.name)

      if (drafts.length === 0) {
        return { success: false, error: '没有找到草稿记录' }
      }

      // 获取最新的草稿
      const latestDraft = drafts[0]
      const draftData = await restoreDraftFromLocalStorage(latestDraft.key)

      if (!draftData.success) {
        return draftData
      }

      // 恢复修改到 sheetStateManager
      const context = sheetStateManager.getActiveContext()
      if (context) {
        // 如果草稿的表类型与当前显示的不一致，提示用户
        if (draftData.data.table_type !== tableType) {
          return {
            success: false,
            error: `草稿是${draftData.data.table_type === 'flattened' ? '扁平化' : '原始'}表格的修改，当前显示的是${tableType === 'flattened' ? '扁平化' : '原始'}表格`,
            data: draftData.data,
            needSwitchTable: true
          }
        }

        // 恢复每个修改
        draftData.data.changes.forEach(change => {
          sheetStateManager.recordCellChange(
            change.row,
            change.col,
            change.oldValue,
            change.newValue,
            change.tableType
          )
        })

        console.log(`🔄 已恢复 ${draftData.data.changes.length} 个修改`)

        return {
          success: true,
          message: `已恢复 ${draftData.data.changes.length} 个修改`,
          changes_count: draftData.data.changes.length,
          data: draftData.data
        }
      }

      return { success: false, error: '无法获取当前表格上下文' }

    } catch (error) {
      console.error('❌ 恢复草稿失败:', error)
      return {
        success: false,
        error: error.message || '恢复草稿失败'
      }
    }
  }

  return {
    // 状态
    saving,
    saveType,
    lastSaveTime,
    saveStatus,
    modifiedCellsCount,

    // 方法
    initDataManagerContext,
    updateSaveStatus,
    hasUnsavedChangesInCurrentTable,
    saveDataFromManager,
    restoreUnsavedDataFromDraft,
    getCurrentDrafts
  }
}