// src/utils/SheetStateManager.js - 升级版本

import { ref } from 'vue'

class SheetStateManager {
  constructor() {
    console.log('✅ SheetStateManager 初始化完成')
    this.sheetStates = new Map()
    this.activeContext = null

    // 添加响应式触发器 - 新增这3行
    this.triggerUpdate = ref(0)
    console.log('🎯 响应式触发器已创建')
  }

  // ============ 基础方法 ============
  _createKey(pdfId, excelFile, sheetName) {
    return `${pdfId}_${excelFile}_${sheetName}`
  }



  getOrCreateSheetState(pdfId, excelFile, sheetName) {
  const key = this._createKey(pdfId, excelFile, sheetName)

  if (!this.sheetStates.has(key)) {
    console.log(`📝 创建新的sheet状态: ${key}`)

    this.sheetStates.set(key, {
      // 基础信息
      pdfId,
      excelFile,
      sheetName,

      // 数据存储
      data: {
        original: null,      // 原始Excel数据
        flattened: null,     // 扁平化数据
      },

      // 修改记录（按表类型分离）
      modifications: {
        original: new Map(),  // 键: "row,col" -> {oldValue, newValue, timestamp}
        flattened: new Map()  // 同上
      },

      // 修改统计 - 修复这里
      stats: {
        original: {
          unsavedCount: 0,
          savedCount: 0,
          unsaved: 0,  // 新增：为了兼容 updateStats 方法
          saved: 0,    // 新增：为了兼容 updateStats 方法
          total: 0     // 新增：为了兼容 updateStats 方法
        },
        flattened: {
          unsavedCount: 0,
          savedCount: 0,
          unsaved: 0,
          saved: 0,
          total: 0
        }
      },

      // 新增：为了兼容保存逻辑
      savedModifications: {
        original: new Map(),
        flattened: new Map()
      }
    })
  }

  return this.sheetStates.get(key)
}


  // ============ 上下文管理 ============
  setActiveContext(pdfId, excelFile, sheetName, tableType = 'original') {
    this.activeContext = { pdfId, excelFile, sheetName, tableType }
  }

  getActiveContext() {
    return this.activeContext
  }

  getActiveSheetState() {
    if (!this.activeContext) return null
    const { pdfId, excelFile, sheetName } = this.activeContext
    return this.getOrCreateSheetState(pdfId, excelFile, sheetName)
  }

  // ============ 数据管理 ============
  setData(tableType, data) {
    const state = this.getActiveSheetState()
    if (!state) {
      console.error('❌ 没有活跃的sheet状态')
      return false
    }

    if (tableType !== 'original' && tableType !== 'flattened') {
      console.error(`❌ 无效的表类型: ${tableType}`)
      return false
    }

    state.data[tableType] = data
    console.log(`✅ 设置${tableType}数据，行数: ${data?.length || 0}`)
    return true
  }

  getData(tableType) {
    const state = this.getActiveSheetState()
    return state ? state.data[tableType] : null
  }


     // ============ 修改记录管理 ============
    async recordCellChange(row, col, oldValue, newValue, tableType = null) {
      console.log('🔍 SheetStateManager.recordCellChange 入口', { row, col, newValue })

      // 🔥 关键：先验证参数类型（新增代码）
      const safeRow = Math.max(0, parseInt(row, 10) || 0);
      const safeCol = Math.max(0, parseInt(col, 10) || 0);

      if (isNaN(safeRow) || isNaN(safeCol)) {
        console.error('❌ 无效的行列参数:', { row, col, safeRow, safeCol });
        return false;
      }

      // 使用安全值替换原始值（新增代码）
      row = safeRow;
      col = safeCol;

      const contextTableType = tableType || (this.activeContext?.tableType || 'original')
      const state = this.getActiveSheetState()

      if (!state) {
        console.error('❌ 无法记录修改：没有活跃的sheet状态')
        return false
      }

      // 确保统计对象存在且有正确的初始值
      if (!state.stats) {
        state.stats = {
          original: { unsavedCount: 0, savedCount: 0 },
          flattened: { unsavedCount: 0, savedCount: 0 }
        }
      }

      // 确保两个表类型的统计都存在
      if (!state.stats.original) {
        state.stats.original = { unsavedCount: 0, savedCount: 0 }
      }
      if (!state.stats.flattened) {
        state.stats.flattened = { unsavedCount: 0, savedCount: 0 }
      }

      // 确保当前表类型的统计存在
      if (!state.stats[contextTableType]) {
        state.stats[contextTableType] = { unsavedCount: 0, savedCount: 0 }
      }

      // 确保 unsavedCount 是数字
      if (typeof state.stats[contextTableType].unsavedCount !== 'number') {
        state.stats[contextTableType].unsavedCount = 0
      }

      // 确保另一个表类型的统计也是数字（防止 undefined）
      const otherTableType = contextTableType === 'original' ? 'flattened' : 'original'
      if (typeof state.stats[otherTableType]?.unsavedCount !== 'number') {
        state.stats[otherTableType] = state.stats[otherTableType] || { unsavedCount: 0, savedCount: 0 }
        state.stats[otherTableType].unsavedCount = 0
      }

      const cellKey = `${row},${col}`
      const modification = {
        row,
        col,
        oldValue,
        newValue,
        tableType: contextTableType,
        timestamp: Date.now(),
        saved: false
      }

      // 记录到对应的表类型
      state.modifications[contextTableType].set(cellKey, modification)

      // 安全地更新统计
      state.stats[contextTableType].unsavedCount = Number(state.stats[contextTableType].unsavedCount || 0) + 1

      // 触发响应式更新
      this.triggerUpdate.value++
      console.log(`🔄 触发响应式更新，计数器: ${this.triggerUpdate.value}`)

      // ===== 同步刷样式 =====
      let hot = window.__excelHotInstance
      if (!hot || hot.isDestroyed) {
        // 兜底：从 ref 再摸一次
        const hotTable = document.querySelector('.handsontable')?.__vueParentComponent?.refs?.hotTable
        hot = hotTable?.hotInstance
        if (hot && !hot.isDestroyed) {
          window.__excelHotInstance = hot   // 立即补挂
          console.log('🔁 兜底拿到实例并写回', hot)
        }
      }

      // 🔥 注意：这里直接使用已经转换过的 row 和 col，不需要再次转换
      console.log('🔍 最终行列:', { row, col, type: `${typeof row},${typeof col}` });

      if (hot && !hot.isDestroyed) {
        try {
          // 确保行列在有效范围内（新增范围检查）
          const maxRow = hot.countRows() - 1;
          const maxCol = hot.countCols() - 1;

          if (row > maxRow || col > maxCol) {
            console.warn(`⚠️ 行列超出范围: [${row},${col}] 最大: [${maxRow},${maxCol}]`);
            console.log('⏭️ 跳过样式设置');
          } else {
            hot.setCellMeta(row, col, 'className', 'unsaved-modified-cell');
            hot.render();
            console.log(`✅ 已强制加类名并 render [${row},${col}]`);
          }
        } catch (error) {
          console.error('❌ 设置单元格样式失败:', error);
        }
      } else {
        console.warn('⚠️ 实例无效，没刷样式');
      }

      return true
    }

  // ============ 查询方法 ============
  getUnsavedChangesCount(tableType = null) {
    const state = this.getActiveSheetState()
    if (!state) return 0

    if (tableType) {
      return state.stats[tableType]?.unsavedCount || 0
    }

    // 返回所有表类型的未保存计数
    return state.stats.original.unsavedCount + state.stats.flattened.unsavedCount
  }

  hasUnsavedChanges(tableType = null) {
    return this.getUnsavedChangesCount(tableType) > 0
  }

  getModifications(tableType = null) {
    const state = this.getActiveSheetState()
    if (!state) return []

    if (tableType) {
      return Array.from(state.modifications[tableType].values())
    }

    // 返回所有修改
    return [
      ...Array.from(state.modifications.original.values()),
      ...Array.from(state.modifications.flattened.values())
    ]
  }

  // ============ 保存相关 ============
  markChangesAsSaved(tableType = null) {
    const state = this.getActiveSheetState()
    if (!state) return false

    const typesToSave = tableType ? [tableType] : ['original', 'flattened']

    typesToSave.forEach(type => {
      // 将未保存计数转移到已保存计数
      state.stats[type].savedCount += state.stats[type].unsavedCount
      state.stats[type].unsavedCount = 0

      // 标记所有修改为已保存
      state.modifications[type].forEach(mod => {
        mod.saved = true
      })

      console.log(`💾 ${type}表修改标记为已保存，已保存总数: ${state.stats[type].savedCount}`)
    })

    // 触发响应式更新 - 新增这2行
    this.triggerUpdate.value++
    console.log(`💾 保存后触发响应式更新，计数器: ${this.triggerUpdate.value}`)

    return true
  }



  // 在 SheetStateManager.js 的类中添加这个方法
    getSavedChangesCount(tableType = null) {
      const state = this.getActiveSheetState()
      if (!state) return 0

      if (tableType) {
        return state.stats[tableType]?.savedCount || 0
      }

      // 返回所有表类型的已保存计数
      return (state.stats.original.savedCount || 0) + (state.stats.flattened.savedCount || 0)
    }

  clearUnsavedChanges(tableType = null) {
    const state = this.getActiveSheetState()
    if (!state) return false

    const typesToClear = tableType ? [tableType] : ['original', 'flattened']

    typesToClear.forEach(type => {
      // 只清除未保存的修改
      const unsavedKeys = []
      state.modifications[type].forEach((mod, key) => {
        if (!mod.saved) {
          unsavedKeys.push(key)
        }
      })

      // 删除未保存的修改
      unsavedKeys.forEach(key => {
        state.modifications[type].delete(key)
      })

      state.stats[type].unsavedCount = 0
      console.log(`🧹 清除${type}表未保存修改，删除${unsavedKeys.length}条记录`)
    })

    // 触发响应式更新 - 新增这2行
    this.triggerUpdate.value++
    console.log(`🧹 清除后触发响应式更新，计数器: ${this.triggerUpdate.value}`)

    return true
  }

    /**
     * 保存所有状态到localStorage（用于页面刷新）
     */
    saveStateToStorage() {
      try {
        console.log('💾 开始保存状态到localStorage...');

        // 准备要保存的数据
        const stateToSave = {
          activeContext: this.activeContext,
          sheetStates: []
        };

        // 转换Map为可序列化的数组
        this.sheetStates.forEach((state, key) => {
          try {
            const serializableState = {
              pdfId: state.pdfId,
              excelFile: state.excelFile,
              sheetName: state.sheetName,
              data: state.data,
              // 安全序列化modifications
              modifications: {
                original: Array.from(state.modifications.original.entries()),
                flattened: Array.from(state.modifications.flattened.entries())
              },
              stats: state.stats
            };

            stateToSave.sheetStates.push([key, serializableState]);
            console.log(`   💾 保存sheet: ${key}`);

          } catch (stateError) {
            // // console.warn(`   ⚠️ 序列化sheet ${key} 失败:`, stateError.message);
          }
        });

        const jsonString = JSON.stringify(stateToSave);
        localStorage.setItem('sheetStateManager', jsonString);

        console.log(`✅ 状态保存完成，包含 ${this.sheetStates.size} 个sheet，数据大小: ${jsonString.length} 字节`);
        return true;

      } catch (error) {
        console.error('❌ 保存状态到localStorage失败:', error);
        return false;
      }
    }

    /**
     * 从localStorage加载状态
     */
    // 在 SheetStateManager.js 中修复状态加载
loadStateFromStorage() {
  try {
    const saved = localStorage.getItem('sheetStateManager')
    if (saved) {
      const parsed = JSON.parse(saved)

      // 恢复 sheetStates
      this.sheetStates = new Map()
      if (parsed.sheetStates) {
        Object.entries(parsed.sheetStates).forEach(([key, state]) => {
          // 恢复 Map 结构
          const sheetState = { ...state }

          // 恢复 modifications Map
          if (sheetState.modifications) {
            const mods = {}
            if (sheetState.modifications.original) {
              mods.original = new Map(Object.entries(sheetState.modifications.original))
            }
            if (sheetState.modifications.flattened) {
              mods.flattened = new Map(Object.entries(sheetState.modifications.flattened))
            }
            sheetState.modifications = mods
          }

          // 恢复 savedModifications Map
          if (sheetState.savedModifications) {
            const savedMods = {}
            if (sheetState.savedModifications.original) {
              savedMods.original = new Map(Object.entries(sheetState.savedModifications.original))
            }
            if (sheetState.savedModifications.flattened) {
              savedMods.flattened = new Map(Object.entries(sheetState.savedModifications.flattened))
            }
            sheetState.savedModifications = savedMods
          }

          this.sheetStates.set(key, sheetState)
        })
      }

      console.log('📂 从存储加载状态:', {
        加载的sheet数: this.sheetStates.size,
        活跃上下文: parsed.activeContext
      })

      this.activeContext = parsed.activeContext || null

      // 更新统计数据
      this.updateStats()

      return true
    }
  } catch (error) {
    console.error('❌ 加载状态失败:', error)
  }
  return false
}

    /**
     * 安全恢复Map对象（增强版）
     */
    _safeRestoreMap(mapData) {
      try {
        if (!mapData) {
          console.log('   🗂️  mapData为空，返回空Map');
          return new Map();
        }

        console.log('   🔍 恢复Map，数据类型:', typeof mapData, '是否为数组:', Array.isArray(mapData));

        // 情况1：已经是Map对象（理论上不会发生，因为JSON会序列化）
        if (mapData instanceof Map) {
          console.log('   ✅ mapData是Map实例');
          return mapData;
        }

        // 情况2：数组格式 [[key, value], ...]
        if (Array.isArray(mapData)) {
          console.log(`   ✅ mapData是数组，长度: ${mapData.length}`);

          // 验证数组中的每个元素都是有效的键值对
          const validEntries = [];
          mapData.forEach((entry, idx) => {
            if (Array.isArray(entry) && entry.length >= 2) {
              validEntries.push([entry[0], entry[1]]);
            } else {
              // // console.warn(`     跳过无效entry ${idx}:`, entry);
            }
          });

          return new Map(validEntries);
        }

        // 情况3：对象格式 {key: value, ...}
        if (typeof mapData === 'object' && mapData !== null && !Array.isArray(mapData)) {
          console.log(`   ✅ mapData是对象，键数量: ${Object.keys(mapData).length}`);
          return new Map(Object.entries(mapData));
        }

        // 情况4：其他格式，返回空Map
        // // console.warn('   ⚠️ mapData格式未知:', mapData);
        return new Map();

      } catch (error) {
        // // console.warn('   ❌ 恢复Map失败，返回空Map:', error.message);
        return new Map();
      }
    }

    /**
     * 清理指定sheet的状态
     */
    clearSheetState(pdfId, excelFile, sheetName) {
      const key = this._createKey(pdfId, excelFile, sheetName);
      if (this.sheetStates.has(key)) {
        this.sheetStates.delete(key);
        console.log(`🧹 清理sheet状态: ${key}`);
        return true;
      }
      return false;
    }

    /**
     * 检查sheet是否有数据
     */
    hasData(tableType = 'original') {
      const state = this.getActiveSheetState();
      if (!state) return false;

      const data = state.data[tableType];
      return data && Array.isArray(data) && data.length > 0;
    }

    /**
     * 获取修改统计信息
     */
    getModificationStats() {
      const state = this.getActiveSheetState();
      if (!state) return null;

      return {
        original: {
          total: state.modifications.original.size,
          saved: state.stats.original.savedCount,
          unsaved: state.stats.original.unsavedCount
        },
        flattened: {
          total: state.modifications.flattened.size,
          saved: state.stats.flattened.savedCount,
          unsaved: state.stats.flattened.unsavedCount
        },
        all: {
          total: state.modifications.original.size + state.modifications.flattened.size,
          saved: state.stats.original.savedCount + state.stats.flattened.savedCount,
          unsaved: state.stats.original.unsavedCount + state.stats.flattened.unsavedCount
        }
      };
    }

    /**
     * 重置sheet的修改记录
     */
    resetModifications(tableType = null) {
  const state = this.getActiveSheetState();
  if (!state) return false;

  const typesToReset = tableType ? [tableType] : ['original', 'flattened'];

  typesToReset.forEach(type => {
    state.modifications[type].clear();
    state.stats[type].unsavedCount = 0;
    state.stats[type].savedCount = 0;
  });

  console.log(`🔄 重置${tableType ? tableType + '表' : '所有表'}修改记录`);
  return true;
}


    // SheetStateManager.js
    markAsSaved(tableType) {
      console.log('✅ 标记为已保存:', tableType)

      if (this.modifications[tableType]) {
        // 清空未保存修改
        this.modifications[tableType].unsaved = {}
        this.modifications[tableType].unsavedCount = 0

        // 更新统计
        this.updateStats()

        // 触发状态变化
        if (this.callbacks.hasUnsavedChanges) {
          this.callbacks.hasUnsavedChanges(this.hasUnsavedChanges(tableType))
        }

        // 触发修改状态更新事件
        this.emitModificationUpdate()
      }
    }

    // 添加修改状态更新事件
    emitModificationUpdate() {
      if (typeof window !== 'undefined') {
        const event = new CustomEvent('modification-updated', {
          detail: {
            unsavedCount: this.getUnsavedChangesCount('all'),
            hasUnsavedChanges: this.hasUnsavedChanges('all')
          }
        })
        window.dispatchEvent(event)
      }
    }


    // 在 SheetStateManager.js 中添加或修改 updateStats 方法
    updateStats() {
      console.log('📊 更新统计数据...')

      this.sheetStates.forEach((sheetState, key) => {
        // 重置统计
        sheetState.stats = {
          original: { unsaved: 0, saved: 0, total: 0 },
          flattened: { unsaved: 0, saved: 0, total: 0 }
        }

        // 统计未保存修改
        if (sheetState.modifications?.original) {
          const unsavedOriginal = Array.from(sheetState.modifications.original.values())
            .filter(mod => !mod.saved).length
          sheetState.stats.original.unsaved = unsavedOriginal
        }

        if (sheetState.modifications?.flattened) {
          const unsavedFlattened = Array.from(sheetState.modifications.flattened.values())
            .filter(mod => !mod.saved).length
          sheetState.stats.flattened.unsaved = unsavedFlattened
        }

        // 统计已保存修改
        if (sheetState.savedModifications?.original) {
          sheetState.stats.original.saved = sheetState.savedModifications.original.size
        }

        if (sheetState.savedModifications?.flattened) {
          sheetState.stats.flattened.saved = sheetState.savedModifications.flattened.size
        }

        // 计算总数
        sheetState.stats.original.total =
          sheetState.stats.original.unsaved + sheetState.stats.original.saved
        sheetState.stats.flattened.total =
          sheetState.stats.flattened.unsaved + sheetState.stats.flattened.saved

        console.log(`📊 统计更新 [${key}]:`, sheetState.stats)
      })

      // 保存到存储
      this.saveStateToStorage()
    }

    // 添加 forceUpdate 方法
    forceUpdate() {
      console.log('🔄 强制更新 SheetStateManager 状态')
      this.updateStats()

      // 触发更新事件
      if (typeof this.onUpdate === 'function') {
        this.onUpdate()
      }
    }


  // ============ 调试方法 ============
  debugState() {
    console.log('=== SheetStateManager 调试信息 ===')
    console.log('活跃上下文:', this.activeContext)
    console.log('总sheet数量:', this.sheetStates.size)

    this.sheetStates.forEach((state, key) => {
      console.log(`\n📁 Sheet: ${key}`)
      console.log('  原始数据:', state.data.original ? `有数据(${state.data.original.length}行)` : '空')
      console.log('  扁平化数据:', state.data.flattened ? `有数据(${state.data.flattened.length}行)` : '空')
      console.log('  原始表修改:', `未保存=${state.stats.original.unsavedCount}, 已保存=${state.stats.original.savedCount}`)
      console.log('  扁平化表修改:', `未保存=${state.stats.flattened.unsavedCount}, 已保存=${state.stats.flattened.savedCount}`)
    })

    console.log('=== 调试结束 ===')
  }


  // ============ 新增：响应式触发器方法 ============
  getUpdateTrigger() {
    return this.triggerUpdate.value
  }

}


// 创建单例并导出
const sheetStateManager = new SheetStateManager()

// 全局暴露（便于调试）
if (typeof window !== 'undefined') {
  window.$sheetManager = sheetStateManager
  console.log('🔗 SheetStateManager 已绑定到 window.$sheetManager')
}

export default sheetStateManager