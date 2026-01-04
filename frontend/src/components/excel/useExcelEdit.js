// frontend/src/components/excel/useExcelEdit.js
import { ref, computed, watch, nextTick, onUnmounted  } from 'vue'
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

const idb = {
  get: (store, key)       => dbPromise.then(db => db.get(store, key)),
  set: (store, key, val)  => dbPromise.then(db => db.put(store, val, key)),
  del: (store, key)       => dbPromise.then(db => db.delete(store, key))
}
/* ---------------------------------------------- */

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
  const unsavedCellsTick = ref(0)
  const historyCells = ref(new Set())     // 永久历史修改池（新增）

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
        console.log('🎯🎯 onDataChange 被执行', changes, source);
        if (!changes || source === 'loadData' || source === 'restore') return;

        const tableType = window.currentTableType || 'original';
        const modifiedCells = [];

        // ✅ 使用统一的参数格式
        const currentPdfId = window.currentPdfId || '';
        const currentExcelFile = window.currentExcelFile || '';
        const currentSheetName = window.currentSheetName || '';

        // 🔥🔥 新增：获取表格实例用于更新缓存
        const hot = getHotInstanceWithCache();
        if (!hot || hot.isDestroyed) {
            console.warn('❌❌ 无法获取表格实例，跳过缓存更新');
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
            modifiedCells.push({ row, col, oldValue: oldVal, newValue: newVal, cellKey });
        });

        unsavedCellsTick.value++;
        updateModifiedCellsCount();

        /* === 🔥🔥 关键修复：立即同步更新缓存数据 === */
        if (changes.length > 0) {
            console.log('🔄🔄 开始同步更新缓存数据...');

            try {
                // 1. 获取当前完整的表格数据
                const currentTableData = hot.getSourceData();
                console.log('📊📊 当前表格数据:', {
                    行数: currentTableData.length,
                    列数: currentTableData[0]?.length || 0
                });

                // 2. 根据当前模式更新对应的缓存
                if (tableType === 'flattened') {
                    // 更新扁平化数据缓存
                    if (excelDataCache.setFlattenedData) {
                        excelDataCache.setFlattenedData(
                            currentPdfId,
                            currentExcelFile,
                            currentSheetName,
                            currentTableData
                        );
                        console.log('✅✅ 扁平化缓存已更新');
                    }
                } else {
                    // 更新原始数据缓存
                    if (excelDataCache.setOriginalData) {
                        excelDataCache.setOriginalData(
                            currentPdfId,
                            currentExcelFile,
                            currentSheetName,
                            currentTableData
                        );
                        console.log('✅✅ 原始数据缓存已更新');
                    }
                }

                // 3. 验证缓存是否更新成功
                let cachedData = null;
                if (tableType === 'flattened') {
                    cachedData = excelDataCache.getFlattenedData(currentPdfId, currentExcelFile, currentSheetName);
                } else {
                    cachedData = excelDataCache.getOriginalData(currentPdfId, currentExcelFile, currentSheetName);
                }

                console.log('🔍🔍 缓存更新验证:', {
                    缓存行数: cachedData?.length || 0,
                    表格行数: currentTableData.length,
                    更新成功: cachedData?.length === currentTableData.length
                });

            } catch (error) {
                console.error('❌❌ 更新缓存数据失败:', error);
            }
        }

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

        console.log('💾💾 草稿已写入 localStorage', draftKey, '条数=', changeList.length);

        // 🔥🔥 新增：设置前端修改标记
        if (!window.cacheMetadata) window.cacheMetadata = {};
        window.cacheMetadata[draftKey] = {
            source: 'frontend_modified',
            lastModified: Date.now(),
            tableType: tableType
        };

        console.log('🔧🔧 缓存标记为前端修改:', { draftKey });

        /* 🔥🔥 新增：写入索引，方便切表时快速找回 */
        const indexKey = ExcelKey.getIndexKey ?
            ExcelKey.getIndexKey(currentPdfId, currentExcelFile) :
            `excel_draft_index_${currentPdfId}_${currentExcelFile}`;

        let idx = JSON.parse(localStorage.getItem(indexKey) || '[]');
        if (!idx.includes(draftKey)) idx.push(draftKey);
        localStorage.setItem(indexKey, JSON.stringify(idx));

        /* 🔥🔥 新增：立即把颜色刷出来 */
        nextTick(() => updateModifiedCellsStyle());

        /* === 回调通知 === */
        if (typeof onCellChangeCallback === 'function' && modifiedCells.length > 0) {
            modifiedCells.forEach(cellInfo => onCellChangeCallback({ ...cellInfo, source, timestamp: Date.now() }));
            onCellChangeCallback({
                type: 'data-changed',
                totalChanges: unsavedCells.value.size,
                hasChanges: true,
                allChanges: modifiedCells,
                modifiedCellsCount: unsavedCells.value.size,
                isEditMode: true
            });
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
        // 🔥 关键：暴露 unsavedCells 集合本身
        window.unsavedCells = unsavedCells.value  // 添加这一行
        console.log('🌐 全局状态已更新:', {
          currentHasChanges: window.currentHasChanges,
          unsavedCount: window.unsavedCellsCount,
          集合大小: window.unsavedCells?.size || 0
        })
      }
    }

  const MAX_RETRY = 3
  const RETRY_DELAY = 200
  // useExcelEdit.js - 增强类型检查
  const updateModifiedCellsStyle = async (retry = 0) => {
      console.log('🎨🎨 进入刷样式函数', {
        saved: savedCells.value.size,
        unsaved: unsavedCells.value.size,
        history: historyCells.value.size,
        retry
      })

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

      console.log('✅ 样式更新完成', {
        未保存单元格数: unsavedCells.value.size,
        历史单元格数: historyCells.value.size,
        样式规则数: cellConfig.length
      })
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


  // 3. 新增：启动恢复函数
  const restoreUnsavedFromIndexedDB = async () => {
  try {
    // ✅ 添加数据库连接状态检查
    if (!db || db.readyState === 'closed' || db.readyState === 'closing') {
      console.warn('⚠️ 数据库连接不可用，跳过恢复');
      return;
    }

    // ✅ 添加延迟确保数据库就绪
    await new Promise(resolve => setTimeout(resolve, 100));

    console.log('🔄 从IndexedDB恢复未保存数据...');

    const transaction = db.transaction(['unsavedCells'], 'readonly');
    const store = transaction.objectStore('unsavedCells');
    const request = store.getAll();

    return new Promise((resolve) => {
      request.onsuccess = () => {
        const unsavedCells = request.result || [];
        console.log(`📦 从IndexedDB恢复 ${unsavedCells.length} 个未保存单元格`);

        if (unsavedCells.length > 0) {
          // 应用恢复逻辑
          applyRestoredCells(unsavedCells);
        }
        resolve();
      };

      request.onerror = () => {
        console.warn('⚠️ 读取IndexedDB失败:', request.error);
        resolve(); // 不阻断流程
      };
    });

  } catch (error) {
    console.warn('⚠️ 恢复未保存数据失败（非致命错误）:', error);
    // 静默失败，不阻断主流程
  }
};


  // ============ 公共方法 ============
  const toggleEditMode = (onSuccess) => {
      console.log('🔄 toggleEditMode 被调用，当前状态:', isEditMode.value, '回调:', typeof onSuccess);

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
            console.log('📋 表格只读状态已同步:', { 编辑模式: isEditMode.value, 表格只读: newReadOnly });
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

      console.log('🔴🔴 红色标记完成，标记单元格数:', cellMeta.length)
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



    // useExcelEdit.js - 修改 saveChanges 函数
    const saveChanges = async (saveCallback) => {
      if (!hasChanges.value || saving.value) return

      saving.value = true
      console.log('💾💾💾💾 开始保存修改...')

      try {
        const modifiedData = collectModifiedData()
        const unsavedCount = unsavedCells.value.size

        if (saveCallback) {
          await saveCallback(modifiedData, unsavedCount)
        }

        // ✅ 保存成功后：清除未保存集合，但保留历史记录
        const savedKeys = Array.from(unsavedCells.value)
        unsavedCells.value.clear()

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

        console.log('✅ 保存完成，缓存已清除', {
          保存单元格数: savedKeys.length,
          历史池数量: historyCells.value.size
        })

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
    validateHotInstance,
    fillHistoryCells,
  }
}