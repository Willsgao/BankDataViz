import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import dataManager from '@/utils/dataManager.js'
import sheetStateManager from '@/utils/SheetStateManager.js'
import { getApiUrl } from '@/utils/config.js'
import { http } from '@/api/index.js'


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
   * 保存数据
   */
    // useDataManager.js - 修改 saveDataFromManager 函数中的 API 调用部分
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

      // 安全地获取未保存修改
      let unsavedChanges = []

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
        unsavedChanges = Array.from(modifications.values()).map(mod => ({
          row: mod.row,
          col: mod.col,
          oldValue: mod.oldValue,
          newValue: mod.newValue,
          cellKey: `${mod.row},${mod.col}`,
          tableType: mod.tableType
        }))

        console.log('📤 未保存修改:', unsavedChanges.length, '个', unsavedChanges)

        if (unsavedChanges.length === 0) {
          console.log('📝 没有需要保存的修改')
          return { success: false, error: '没有修改' }
        }

        // ============ 使用 http 实例调用 API ============
        console.log('📤 发送保存请求...')

        const response = await http.post('/save-excel-changes', {
          pdf_id: context.pdfId,
          excel_file: context.excelFile,
          sheet_name: context.sheetName,
          changes: unsavedChanges,
          save_type: saveType,
          table_type: context.tableType
        })

        console.log('✅ API响应:', response)

        if (response.success) {
          console.log('✅ 保存成功:', response)

          // 清空已保存的修改
          if (modifications && modifications.clear) {
            modifications.clear()
            console.log('🗑️ 已清空未保存修改')

            // 更新统计
            if (typeof sheetStateManager.updateStats === 'function') {
              sheetStateManager.updateStats()
            }
          }

          return {
            success: true,
            message: `已${saveType === 'draft' ? '保存草稿' : '最终保存'} (${unsavedChanges.length}个单元格)`,
            reload_required: response.reload_required || false,
            data: response.data
          }
        } else {
          return {
            success: false,
            error: response.message || '保存失败',
            data: response
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
    saveDataFromManager
  }
}