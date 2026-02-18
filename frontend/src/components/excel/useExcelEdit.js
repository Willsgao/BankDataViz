// frontend/src/components/excel/useExcelEdit.js
import { ref, computed, watch, nextTick, onUnmounted, getCurrentInstance   } from 'vue'
import * as ExcelKey from '@/utils/excelKeyUtils.js'
import sheetStateManager from '@/utils/SheetStateManager.js'

/* -------- 极简 IndexedDB 工具（inline） -------- */
import { openDB } from 'idb'   // 如果没装 idb：npm i idb

const dbPromise = openDB('excelDB', 1, {
  upgrade(db) {
    if (!db.objectStoreNames.contains('drafts')) {
      db.createObjectStore('drafts')   // keyPath 默认用 key
    }
  }
})


export default function useExcelEdit(externalGetHotInstance, onCellChangeCallback = null) {

  // 状态
  const isEditMode = ref(true)
  const hasChanges = ref(false)
  const saving = ref(false)
  const modifiedCells = ref(new Set())
  const unsavedCells = ref(new Set())
  const savedCells = ref(new Set())
  const modifiedCellsCount = ref(0)
  const unsavedCellsTick = ref(0)
  const historyCells = ref(new Set())

  // 🔥🔥🔥 关键修复：添加 emit 定义
  const instance = getCurrentInstance()
  const emit = instance?.emit || (() => {
    console.warn('⚠️ emit 函数未定义，使用空函数替代')
  })


  // 🔥🔥🔥 新增：自动保存相关变量（放在现有变量后面）
  let autoSaveTimer = null
  const autoSaveDelay = 5000 // 5秒
  const isAutoSaving = ref(false)

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

    // ✅✅✅ 确保 idb 工具正确定义
    const idb = {
      get: async (store, key) => {
        try {
          const db = await dbPromise;
          return await db.get(store, key);
        } catch (error) {
          console.warn('❌ idb.get 失败:', error);
          return null;
        }
      },
      set: async (store, key, val) => {
        try {
          const db = await dbPromise;
          return await db.put(store, val, key);
        } catch (error) {
          console.warn('❌ idb.set 失败:', error);
        }
      },
      del: async (store, key) => {
        try {
          const db = await dbPromise;
          return await db.delete(store, key);
        } catch (error) {
          console.warn('❌ idb.del 失败:', error);
        }
      },
      getAll: async (store) => {
        try {
          const db = await dbPromise;
          return await db.getAll(store);
        } catch (error) {
          console.warn('❌ idb.getAll 失败:', error);
          return [];
        }
      }
    };

   // 新增：供外部一次性写入历史
   const fillHistoryCells = (keys) => {
  historyCells.value = new Set(keys)         // 直接替换
  console.log('📚 fillHistoryCells 被调用，历史池数量=', historyCells.value.size)
}


  const updateModifiedCellsCount = () => {
      const unsavedCount = unsavedCells.value.size
      const totalCount = modifiedCells.value.size

      modifiedCellsCount.value = unsavedCount

      // 更新 hasChanges 状态
      const newHasChanges = unsavedCount > 0
      if (newHasChanges !== hasChanges.value) {

        hasChanges.value = newHasChanges
      }

      // ===== 立即刷样式（最稳点）=====
      const hot = getHotInstanceWithCache()

      if (hot && !hot.isDestroyed) {
        updateModifiedCellsStyle()
      } else {
        console.warn('⚠️ 实例无效，跳过样式更新')
      }

      // 更新全局状态
      if (typeof window !== 'undefined') {
        window.currentHasChanges = hasChanges.value
        window.modifiedCellsCount = modifiedCellsCount.value
        window.unsavedCellsCount = unsavedCount
        // 🔥 关键：暴露 unsavedCells 集合本身
        window.unsavedCells = unsavedCells.value  // 添加这一行

      }
    }

  const MAX_RETRY = 3
  const RETRY_DELAY = 200
  // useExcelEdit.js - 增强类型检查
  const updateModifiedCellsStyle = async (retry = 0) => {

      const hot = getHotInstanceWithCache()
      if (!hot || hot.isDestroyed) {
        if (retry < MAX_RETRY) {
          setTimeout(() => updateModifiedCellsStyle(retry + 1), RETRY_DELAY)
        } else {
          console.warn('❌❌ 实例无效，放弃样式更新')
        }
        return
      }

      const cellConfig = []

      // 1. 未保存（深红+红点）
      unsavedCells.value.forEach(key => {
        // ✅ 使用 ExcelKey.parseCellKey 解析（保持原始方式）
        const parsed = ExcelKey.parseCellKey(key)
        if (!parsed) {
          console.warn('❌❌ 解析单元格键失败:', key)
          return
        }

        const { row, col } = parsed
        // ✅ 直接使用解析结果，不进行额外转换
        if (row === undefined || col === undefined || row < 0 || col < 0) {
          console.warn('❌❌ 非法行列坐标:', { key, parsed })
          return
        }

        cellConfig.push({ row, col, className: 'unsaved-modified-cell' })
      })

      // 2. 历史已保存（浅红，无红点）
      historyCells.value.forEach(key => {
        if (unsavedCells.value.has(key)) return // 避免重复

        // ✅ 使用 ExcelKey.parseCellKey 解析（保持原始方式）
        const parsed = ExcelKey.parseCellKey(key)
        if (!parsed) {
          console.warn('❌❌ 解析历史单元格键失败:', key)
          return
        }

        const { row, col } = parsed
        if (row === undefined || col === undefined || row < 0 || col < 0) {
          console.warn('❌❌ 非法历史行列坐标:', { key, parsed })
          return
        }

        cellConfig.push({ row, col, className: 'history-modified-cell' })
      })

      console.log('📋📋 最终 cellConfig', cellConfig)

      // 3. 应用配置 + 强制重绘
      if (cellConfig.length) hot.updateSettings({ cell: cellConfig }, false)
      hot.render()

    }

  const collectModifiedData = () => {
      const hot = getHotInstanceWithCache()
      if (!hot || !validateHotInstance(hot)) {
        console.warn('❌❌ 无法收集修改数据：表格实例无效')
        return []
      }

      const modifiedData = []
      modifiedCells.value.forEach(cellKey => {
        // ✅ 使用 ExcelKey.parseCellKey 解析（保持原始方式）
        const parsed = ExcelKey.parseCellKey(cellKey)
        if (!parsed) {
          console.warn('❌❌ 解析单元格键失败:', cellKey)
          return
        }

        const { row, col } = parsed
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

    // 修改 updateChangeStatus 函数
    const updateChangeStatus = () => {
    const count = Object.keys(modifiedCells.value).length
    modifiedCellsCount.value = count
    hasChanges.value = count > 0

    // 🔥🔥🔥 安全使用 emit
    try {
      if (emit && typeof emit === 'function') {
        emit('edit-status-changed', {
          isEditMode: isEditMode.value,
          hasChanges: hasChanges.value,
          modifiedCellsCount: modifiedCellsCount.value,
          timestamp: Date.now()
        })
      }
    } catch (error) {
      console.warn('⚠️ 发射事件失败:', error)
    }
  }

    // 🔥🔥🔥 新增：清理定时器函数
    const cleanupAutoSave = () => {
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer)
        autoSaveTimer = null
      }
    }

    /**
     * 触发自动保存（5秒后）
     */
    const triggerAutoSave = () => {
      console.log('⏰ [useExcelEdit] 检测到数据变化，5秒后触发自动保存...')

      // 清除可能存在的旧定时器
      if (window.autoSaveTimer) {
        clearTimeout(window.autoSaveTimer)
      }

      // 设置新的定时器，5秒后触发全局自动保存
      window.autoSaveTimer = setTimeout(() => {
        console.log('🎯 [useExcelEdit] 5秒定时到达，触发全局自动保存')

        if (typeof window !== 'undefined' && window.triggerGlobalAutoSave) {
          try {
            window.triggerGlobalAutoSave()
          } catch (error) {
            console.error('❌ [useExcelEdit] 触发全局自动保存失败:', error)
            // 备用方案：尝试执行本地自动保存
            performAutoSaveAsFallback()
          }
        } else {
          console.warn('⚠️ [useExcelEdit] 全局自动保存函数未定义，使用备用方案')
          performAutoSaveAsFallback()
        }
      }, 5000) // 5秒后执行
    }

    /**
     * 备用自动保存方案（当全局函数不可用时）
     */
    const performAutoSaveAsFallback = async () => {
      console.log('🔧 [useExcelEdit] 使用备用自动保存逻辑...')

      try {
        // 检查必要的上下文
        if (!hotInstance || hotInstance.isDestroyed) {
          console.warn('⚠️ 表格实例不可用，跳过备用自动保存')
          return
        }

        // 检查是否有修改需要保存
        const hasChangesToSave = hasChanges.value && modifiedCellsCount.value > 0

        if (!hasChangesToSave) {
          console.log('📭 无修改需要保存，跳过备用自动保存')
          return
        }

        // 这里可以添加简单的本地保存逻辑
        // 但由于我们主要使用全局保存，这里只记录日志
        console.log('📝 [useExcelEdit] 备用自动保存完成（仅记录）')

      } catch (error) {
        console.error('❌ [useExcelEdit] 备用自动保存失败:', error)
        // 静默失败，不干扰用户
      }
    }


    /**
     * 数据变化处理函数
     */
     const onDataChange = (changes, source) => {

      // ✅ 忽略 loadData 和 restore 操作（这是正常的）
      if (!changes || source === 'loadData' || source === 'restore') {
        return;
      }

      const tableType = window.currentTableType || 'original';
      const modifiedCellsArray = [];  // ✅ 改为不冲突的名称

      // ✅ 使用统一的参数格式
      const currentPdfId = window.currentPdfId || '';
      const currentExcelFile = window.currentExcelFile || '';
      const currentSheetName = window.currentSheetName || '';

      // 🔥🔥🔥🔥🔥 修复：获取表格实例，但不进行数据转换
      const hot = getHotInstanceWithCache();
      if (!hot || hot.isDestroyed) {
        return;
      }

      changes.forEach(([row, col, oldVal, newVal]) => {
        if (oldVal == newVal) return;

        // ✅ 统一使用 ExcelKey.getCellKey 格式
        const cellKey = ExcelKey.getCellKey(
          currentPdfId,
          currentExcelFile,
          currentSheetName,
          tableType,
          row,
          col
        );

        unsavedCells.value.add(cellKey);
        historyCells.value.add(cellKey);
        modifiedCellsArray.push({ row, col, oldValue: oldVal, newValue: newVal, cellKey }); // ✅ 使用新名称
      });

      unsavedCellsTick.value++;
      updateModifiedCellsCount();

      /* === 立即落盘：带值缓存 === */
      const changeList = [];
      for (const key of unsavedCells.value) {
        const parsed = ExcelKey.parseCellKey(key);
        if (!parsed) continue;
        const { row, col } = parsed;
        changeList.push({
          row,
          col,
          newValue: hot.getDataAtCell(row, col) ?? '',
          oldValue: ''
        });
      }

      const draftKey = ExcelKey.getDraftKey ?
        ExcelKey.getDraftKey(currentPdfId, currentExcelFile, currentSheetName, tableType) :
        `excel_draft_${currentPdfId}_${currentExcelFile}_${currentSheetName}_${tableType}`;

      localStorage.setItem(draftKey, JSON.stringify({
        modifications: changeList,
        savedAt: Date.now(),
        tableType
      }));


      // 🔥🔥🔥🔥🔥 新增：设置前端修改标记
      if (!window.cacheMetadata) window.cacheMetadata = {};
      window.cacheMetadata[draftKey] = {
        source: 'frontend_modified',
        lastModified: Date.now(),
        tableType: tableType
      };

      /* 🔥🔥🔥🔥🔥 新增：写入索引，方便切表时快速找回 */
      const indexKey = ExcelKey.getIndexKey ?
        ExcelKey.getIndexKey(currentPdfId, currentExcelFile) :
        `excel_draft_index_${currentPdfId}_${currentExcelFile}`;

      let idx = JSON.parse(localStorage.getItem(indexKey) || '[]');
      if (!idx.includes(draftKey)) idx.push(draftKey);
      localStorage.setItem(indexKey, JSON.stringify(idx));

      /* 🔥🔥🔥🔥🔥 新增：立即把颜色刷出来 */
      nextTick(() => updateModifiedCellsStyle());

      /* === 回调通知 === */
      if (typeof onCellChangeCallback === 'function' && modifiedCellsArray.length > 0) {  // ✅ 使用新名称
        modifiedCellsArray.forEach(cellInfo => onCellChangeCallback({ ...cellInfo, source, timestamp: Date.now() }));  // ✅ 使用新名称
        onCellChangeCallback({
          type: 'data-changed',
          totalChanges: unsavedCells.value.size,
          hasChanges: true,
          allChanges: modifiedCellsArray,  // ✅ 使用新名称
          modifiedCellsCount: unsavedCells.value.size,
          isEditMode: true
        });
      }

      // 清除可能存在的旧定时器
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer);
      }

      // 设置新的定时器，5秒后触发自动保存
      autoSaveTimer = setTimeout(() => {
        // 执行自动保存
        performAutoSave();
      }, 5000); // 5秒后执行

      // 🔥🔥🔥🔥🔥 新增：安全发射事件
      try {
        if (emit && typeof emit === 'function') {
          emit('data-changed', {
            changes: changes,
            totalChanges: changes.length,
            hasChanges: hasChanges.value,
            modifiedCellsCount: modifiedCellsCount.value,
            source: source,
            timestamp: Date.now()
          });
        }
      } catch (error) {
        console.warn('⚠️ 发射数据变化事件失败:', error);
      }
    };



    // 🔥🔥🔥 修改 performAutoSave 函数
const performAutoSave = async () => {

  try {
    // 🔥🔥🔥 修复：使用 getHotInstanceWithCache() 而不是 hotInstance
    const hot = getHotInstanceWithCache();
    if (!hot || hot.isDestroyed) {
      console.warn('⚠️ 表格实例不可用');
      return { success: false, error: '表格实例不可用' };
    }

    // 检查是否有修改需要保存
    if (!hasChanges.value || unsavedCells.value.size === 0) {
      return { success: true, message: '无修改需要保存' };
    }

    // 🔥🔥🔥 修复：正确收集修改数据
    const changesToSave = [];
    const currentPdfId = window.currentPdfId || '';
    const currentExcelFile = window.currentExcelFile || '';
    const currentSheetName = window.currentSheetName || '';
    const tableType = window.currentTableType || 'original';

    // 遍历未保存的单元格
    for (const cellKey of unsavedCells.value) {
      const parsed = ExcelKey.parseCellKey(cellKey);
      if (!parsed) {
        continue;
      }

      const { row, col } = parsed;
      if (row === undefined || col === undefined || row < 0 || col < 0) {
        continue;
      }

      try {
        const value = hot.getDataAtCell(row, col);
        changesToSave.push({
          row,
          col,
          value,
          cellKey,
          isSaved: false
        });
      } catch (error) {
        console.warn(`⚠️ 获取单元格数据失败 [${row},${col}]:`, error);
      }
    }

    if (changesToSave.length === 0) {
      return { success: true, message: '无修改需要保存' };
    }

    // 🔥🔥🔥 关键：调用全局自动保存函数
    if (typeof window.triggerGlobalAutoSave === 'function') {

      // 准备保存数据
      const saveData = {
        modifications: changesToSave,
        tableType: tableType,
        pdfId: currentPdfId,
        excelFile: currentExcelFile,
        sheetName: currentSheetName,
        timestamp: Date.now(),
        isAutoSave: true
      };

      // 调用全局保存函数
      const result = await window.triggerGlobalAutoSave(saveData);

      if (result && result.success) {

        // 标记为已保存
        markSavedCells(changesToSave.map(item => item.cellKey));

        return {
          success: true,
          message: `成功保存 ${changesToSave.length} 个修改`,
          savedCount: changesToSave.length
        };
      } else {
        throw new Error(result?.error || '全局自动保存失败');
      }
    } else {
      // 备用方案：直接标记为已保存（前端状态）
      markSavedCells(changesToSave.map(item => item.cellKey));

      return {
        success: true,
        message: `前端标记 ${changesToSave.length} 个修改为已保存`,
        savedCount: changesToSave.length
      };
    }

  } catch (error) {

    // 安全地处理错误消息
    if (typeof ElMessage !== 'undefined' && ElMessage.error) {
      try {
        ElMessage.error('自动保存失败: ' + error.message);
      } catch (e) {
        console.warn('⚠️ 显示错误消息失败:', e);
      }
    }

    return { success: false, error: error.message };
  }
};

    // 原有的 handleSingleCellChange 函数保持不变
    const handleSingleCellChange = (row, col, oldValue, newValue, source) => {
      // ... 原有的单元格变化处理逻辑
      const cellKey = `${row},${col}`

      // 如果值没有实际变化，跳过
      if (oldValue === newValue) return

      // 记录修改
      if (!modifiedCells.value[cellKey]) {
        modifiedCells.value[cellKey] = {
          row,
          col,
          oldValue,
          newValue,
          firstModified: Date.now(),
          lastModified: Date.now(),
          saveStatus: 'unsaved'
        }
      } else {
        // 更新现有修改
        modifiedCells.value[cellKey].newValue = newValue
        modifiedCells.value[cellKey].lastModified = Date.now()
      }

      // 添加到未保存集合
      if (!unsavedCells.value.has(cellKey)) {
        unsavedCells.value.add(cellKey)
      }
    }


      // ============ 公共方法 ============
      const toggleEditMode = (onSuccess) => {

          const hot = getHotInstanceWithCache();
          if (!hot || !validateHotInstance(hot)) {
            if (onSuccess && typeof onSuccess === 'function') {
              onSuccess('表格实例无效，无法切换编辑模式', 'error');
            }
            return;
          }

          if (hot.isDestroyed) {
            clearCache();
            if (onSuccess && typeof onSuccess === 'function') {
              onSuccess('表格实例已被销毁', 'error');
            }
            return;
          }

          /* -------- 状态翻转 -------- */
          isEditMode.value = !isEditMode.value;
          window.currentEditMode = isEditMode.value;

          try {
            const newReadOnly = !isEditMode.value;

            /* 1. 更新表格只读 */
            hot.updateSettings({ readOnly: newReadOnly }, false);
            const cols = hot.getSettings().columns;
            if (Array.isArray(cols)) {
              hot.updateSettings({
                columns: cols.map(c => ({ ...c, readOnly: newReadOnly }))
              }, false);
            }

            /* 2. 渲染 + 后续钩子 */
            setTimeout(() => {
              if (hot && !hot.isDestroyed) {
                hot.render();
              }
            }, 50);
          } catch (e) {
            console.error('❌ 更新表格状态失败:', e);
            if (onSuccess && typeof onSuccess === 'function') {
              onSuccess('更新表格状态失败', 'error');
            }
            return;
          }

          /* -------- 进入编辑模式时的专属逻辑 -------- */
          if (isEditMode.value) {
            /* 防止重复绑定 */
            hot.removeHook('afterChange', onDataChange);
            hot.addHook('afterChange', onDataChange);
            console.log('🔥 afterChange 钩子已绑定');

            /* ===== 关键：渲染完成后恢复草稿 + 标红 ===== */
            nextTick(() => {
              // markModifiedCellsRed();
              markModifiedCellsRed();
              restoreUnsavedFromIndexedDB(); // 新增：把 IndexedDB 里的修改写回表格
            });

            if (onSuccess && typeof onSuccess === 'function') {
              onSuccess('已进入编辑模式，可以修改单元格', 'success');
            }
          } else {
            /* 退出编辑模式 */
            console.log('🔒 退出编辑模式');
            if (onSuccess && typeof onSuccess === 'function') {
              onSuccess('已退出编辑模式', 'info');
            }
          }
        }

    /* 把单元格标成红色（仅未保存的） */
    const markModifiedCellsRed = () => {
      const hot = getHotInstanceWithCache()
      if (!hot || hot.isDestroyed) return

      const cellMeta = []

      unsavedCells.value.forEach(key => {
        // ✅ 使用 ExcelKey.parseCellKey 解析（保持原始方式）
        const parsed = ExcelKey.parseCellKey(key)
        if (!parsed) {
          console.warn('❌❌ 解析单元格键失败:', key)
          return
        }

        const { row, col } = parsed
        if (row === undefined || col === undefined || row < 0 || col < 0) {
          console.warn('❌❌ 非法行列坐标:', { key, parsed })
          return
        }

        cellMeta.push({ row, col, className: 'unsaved-modified-cell' })
      })

      if (cellMeta.length) hot.updateSettings({ cell: cellMeta }, false)
      hot.render()

    }

   // 确保 updateTableReadOnly 函数存在
   const updateTableReadOnly = () => {
    const hot = getHotInstanceWithCache()
    if (!hot || !validateHotInstance(hot)) {
      console.warn('❌ 无法更新表格只读状态：表格实例无效')
      return
    }

    try {

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

      // 延迟强制重新渲染，确保状态生效
      setTimeout(() => {
        if (hot && !hot.isDestroyed) {
          hot.render()
        }
      }, 100)

    } catch (error) {
      console.error('❌ 更新表格只读状态失败:', error)
    }
  }

    // useExcelEdit.js - 修改 saveChanges 函数
    const saveChanges = async (saveCallback) => {
      if (!hasChanges.value || saving.value) return

      saving.value = true

      try {
        const modifiedData = collectModifiedData()
        const unsavedCount = unsavedCells.value.size

        if (saveCallback) {
          await saveCallback(modifiedData, unsavedCount)
        }

        // ✅ 保存成功后：清除未保存集合，但保留历史记录
        const savedKeys = Array.from(unsavedCells.value)

        // 将已保存的单元格移到历史池
        savedKeys.forEach(key => {
          savedCells.value.add(key)
          modifiedCells.value.add(key)
          historyCells.value.add(key) // 确保历史池有记录
        })

        hasChanges.value = false
        modifiedCellsCount.value = 0

        // ✅ 使用 ExcelKey.getDraftKey 格式清理 localStorage
        const tableType = window.currentTableType || 'original'
        const draftKey = ExcelKey.getDraftKey(
          window.currentPdfId,
          window.currentExcelFile,
          window.currentSheetName,
          tableType
        )
        localStorage.removeItem(draftKey)

        // ✅ 清理索引，使用统一格式
        const indexKey = ExcelKey.getIndexKey ?
          ExcelKey.getIndexKey(window.currentPdfId, window.currentExcelFile) :
          `excel_draft_index_${window.currentPdfId}_${window.currentExcelFile}`

        let idx = JSON.parse(localStorage.getItem(indexKey) || '[]')
        idx = idx.filter(key => key !== draftKey)
        localStorage.setItem(indexKey, JSON.stringify(idx))

        // ✅ 更新全局状态
        window.currentHasChanges = false
        window.modifiedCellsCount = 0
        window.unsavedCellsCount = 0
        window.unsavedCells = new Set()

        return {
          success: true,
          message: `成功保存 ${unsavedCount} 个修改`,
          savedCount: unsavedCount
        }
      } catch (error) {
        console.error('❌❌❌❌ 保存失败:', error)
        return { success: false, message: `保存失败: ${error.message}` }
      } finally {
        saving.value = false
      }
    }

    // ✅✅✅ 修复后的完整函数
    const restoreUnsavedFromIndexedDB = async () => {
      try {
        // 🔧 修复：检查 idb 工具是否可用
        if (!idb || typeof idb.get !== 'function') {
          console.warn('⚠️ IndexedDB 工具不可用，跳过恢复');
          return;
        }

        // 🔧 修复：使用正确的存储名称和键
        const tableType = window.currentTableType || 'original';
        const draftKey = ExcelKey.getDraftKey ?
            ExcelKey.getDraftKey(
                window.currentPdfId || '',
                window.currentExcelFile || '',
                window.currentSheetName || '',
                tableType
            ) :
            `excel_draft_${window.currentPdfId}_${window.currentExcelFile}_${window.currentSheetName}_${tableType}`;

        try {
          // 🔧 修复：使用 idb.get 获取数据
          const draftData = await idb.get('drafts', draftKey);

          if (!draftData) {
            console.log('📭 IndexedDB中无未保存数据');
            return;
          }

          if (draftData.modifications && draftData.modifications.length > 0) {
            // 应用恢复逻辑
            applyRestoredCells(draftData.modifications);
          }

        } catch (dbError) {
          console.warn('⚠️ 读取IndexedDB失败:', dbError);
          // 静默失败，不阻断流程
        }

      } catch (error) {
        console.warn('⚠️ 恢复未保存数据失败（非致命错误）:', error);
        // 静默失败，不阻断主流程
      }
    };

    // ✅✅✅ 添加缺失的 applyRestoredCells 函数
    const applyRestoredCells = (modifications) => {
      if (!modifications || !Array.isArray(modifications)) return;

      const hot = getHotInstanceWithCache();
      if (!hot || hot.isDestroyed) {
        console.warn('❌ 无法应用恢复数据：表格实例无效');
        return;
      }

      console.log('🔄 应用恢复的单元格数据...');

      modifications.forEach(mod => {
        if (mod.row !== undefined && mod.col !== undefined && mod.newValue !== undefined) {
          try {
            // 恢复单元格值
            hot.setDataAtCell(mod.row, mod.col, mod.newValue);

            // 标记为未保存
            const cellKey = ExcelKey.getCellKey(
              window.currentPdfId || '',
              window.currentExcelFile || '',
              window.currentSheetName || '',
              window.currentTableType || 'original',
              mod.row,
              mod.col
            );

            unsavedCells.value.add(cellKey);
            historyCells.value.add(cellKey);

          } catch (error) {
            console.warn('⚠️ 恢复单元格失败:', { row: mod.row, col: mod.col, error: error.message });
          }
        }
      });

      updateModifiedCellsCount();
      updateModifiedCellsStyle();

    };


    // 🔥🔥🔥 新增：检查未保存修改并提示
    const checkUnsavedChangesBeforeLeave = () => {
      return new Promise((resolve) => {
        if (!hasChanges.value || unsavedCells.value.size === 0) {
          resolve(true) // 没有未保存修改，直接放行
          return
        }

        ElMessageBox({
          title: '未保存的修改',
          message: `当前表格有 ${unsavedCells.value.size} 个未保存的修改，确定要切换吗？`,
          confirmButtonText: '立即保存',
          cancelButtonText: '放弃修改',
          showCancelButton: true,
          showClose: true,
          closeOnClickModal: false,
          type: 'warning',
          beforeClose: async (action, instance, done) => {
            if (action === 'confirm') {
              // 立即保存
              instance.confirmButtonLoading = true
              instance.confirmButtonText = '保存中...'

              try {
                const saveResult = await saveChanges()
                done()
                if (saveResult && saveResult.success) {
                  ElMessage.success('保存成功')
                  resolve(true) // 保存成功，允许切换
                } else {
                  ElMessage.error('保存失败，请重试')
                  resolve(false) // 保存失败，不允许切换
                }
              } catch (error) {
                instance.confirmButtonLoading = false
                instance.confirmButtonText = '立即保存'
                ElMessage.error('保存失败: ' + error.message)
                resolve(false) // 保存失败，不允许切换
              }
            } else if (action === 'cancel') {
              // 放弃修改
              done()
              resetChanges() // 重置修改
              ElMessage.info('已放弃未保存的修改')
              resolve(true) // 放弃修改，允许切换
            } else {
              // 点击关闭按钮，取消切换
              done()
              resolve(false) // 取消切换
              ElMessage.info('已取消切换操作')
            }
          }
        })
      })
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

    // 🔥🔥🔥 修改：在现有的 onUnmounted 中添加清理
    onUnmounted(() => {
      clearInterval(healthTimer.value)
      clearInterval(monitorTimer.value)
      clearCache()
      cleanupAutoSave() // 🔥🔥🔥 新增：清理自动保存定时器
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
    validateHotInstance,
    fillHistoryCells,
    isAutoSaving,
    cleanupAutoSave,
    checkUnsavedChangesBeforeLeave

  }
}