// src/utils/dataManager.js
import indexedDBManager from './indexedDBManager.js'
import { ElMessage } from 'element-plus'

class DataManager {
  constructor() {
    // 当前编辑上下文
    this.currentContext = {
      pdfId: null,
      excelFile: null,
      sheetName: null,
      sessionId: null
    }

    // 修改追踪
    this.modifiedCells = new Map()  // key: "row_col", value: {old, new, timestamp}

    // 自动保存计时器
    this.autoSaveTimer = null
    this.autoSaveDelay = 5000  // 5秒自动保存

    // 初始化
    this.init()
  }

  /**
   * 初始化
   */
  async init() {
    try {
      await indexedDBManager.initDatabase()
      console.log('✅ DataManager 初始化完成')
    } catch (error) {
      console.error('❌ DataManager 初始化失败:', error)
    }
  }

  /**
   * 设置当前编辑上下文
   */
  setContext(context) {
    this.currentContext = {
      ...this.currentContext,
      ...context
    }

    if (!this.currentContext.sessionId) {
      this.currentContext.sessionId = indexedDBManager.getSessionId()
    }

    console.log('🎯 设置编辑上下文:', this.currentContext)
  }

    // dataManager.js - 完全分离原始表和扁平化表的修改
    recordCellChange(row, col, oldValue, newValue, tableType = 'original') {

      const change = {
        row,
        col,
        oldValue,
        newValue,
        timestamp: Date.now(),
        tableType: tableType, // 关键：记录是哪个表的修改
        context: {
          pdfId: this.currentContext.pdfId,
          excelFile: this.currentContext.excelFile,
          sheetName: this.currentContext.sheetName,
          // 不混用坐标系统
        }
      };

      console.log('📝 记录单元格修改:', {
        表类型: tableType,
        坐标: `[${row},${col}]`,
        新值: newValue,
        当前上下文: this.currentContext
      });

      // 使用表类型作为键的一部分，完全分离
      const changeKey = `${this.currentContext.pdfId}_${this.currentContext.excelFile}_${this.currentContext.sheetName}_${tableType}_${row},${col}`;
      this.modifiedCells.set(changeKey, change);


      console.log('🔥 dataManager 里 recordCellChange 末尾：准备刷样式')

      return change;
    }



    // 新增：按表类型获取修改
    /**
     * 按表类型获取修改
     */
    async getChangesByTableType(tableType) {
      const changes = []

      for (const [key, change] of this.modifiedCells.entries()) {
        // 检查是否匹配当前上下文和表类型
        if (change.context.pdfId === this.currentContext.pdfId &&
            change.context.excelFile === this.currentContext.excelFile &&
            change.context.sheetName === this.currentContext.sheetName &&
            change.tableType === tableType) {
          changes.push(change)
        }
      }

      console.log(`📊 获取${tableType}表的修改:`, changes.length)
      return changes
    }

    /**
     * 按表类型清除修改
     */
    clearChangesByTableType(tableType) {
      const keysToDelete = []

      for (const [key, change] of this.modifiedCells.entries()) {
        if (change.context.pdfId === this.currentContext.pdfId &&
            change.context.excelFile === this.currentContext.excelFile &&
            change.context.sheetName === this.currentContext.sheetName &&
            change.tableType === tableType) {
          keysToDelete.push(key)
        }
      }

      // 删除匹配的修改
      keysToDelete.forEach(key => {
        this.modifiedCells.delete(key)
      })

      console.log(`🗑️ 清除${tableType}表的修改:`, keysToDelete.length)
      return keysToDelete.length
    }


    // 修改 restoreUnsavedEdits 方法
    async restoreUnsavedEdits() {
      if (!this.currentContext.pdfId || !this.currentContext.sheetName) {
        return { success: false, message: '没有上下文信息' }
      }

      try {
        // 从 IndexedDB 获取当前上下文的修改
        const allChanges = await this.getChangesForContext(
          this.currentContext.pdfId,
          this.currentContext.excelFile,
          this.currentContext.sheetName
        )

        console.log('📥 恢复未保存编辑:', {
          上下文: this.currentContext,
          找到修改数: allChanges.length,
          修改示例: allChanges.slice(0, 3)
        })

        return {
          success: true,
          message: `找到 ${allChanges.length} 个未保存修改`,
          changes: allChanges
        }

      } catch (error) {
        console.error('恢复未保存编辑失败:', error)
        return { success: false, message: error.message }
      }
    }

    // 新增方法：根据上下文获取修改
    async getChangesForContext(pdfId, excelFile, sheetName) {
      const changes = []

      // 遍历所有修改，筛选出匹配当前上下文的
      for (const [key, change] of this.modifiedCells.entries()) {
        const changeContext = change.context || {}

        // 检查是否匹配当前上下文
        if (changeContext.pdfId === pdfId &&
            changeContext.excelFile === excelFile &&
            changeContext.sheetName === sheetName) {
          changes.push(change)
        }
      }

      return changes
    }

  /**
   * 获取所有修改
   */
  getChanges() {
    const changes = Array.from(this.modifiedCells.values()).map(cell => [
      cell.row,
      cell.col,
      cell.old,
      cell.new,
      cell.timestamp
    ])

    return changes
  }

  /**
   * 获取修改数量
   */
  getChangeCount() {
    return this.modifiedCells.size
  }

  /**
   * 是否有未保存的修改
   */
  hasUnsavedChanges() {
    return this.modifiedCells.size > 0
  }

  /**
   * 计划自动保存
   */
  scheduleAutoSave() {
    // 清除之前的计时器
    if (this.autoSaveTimer) {
      clearTimeout(this.autoSaveTimer)
    }

    // 设置新的计时器
    this.autoSaveTimer = setTimeout(() => {
      this.autoSave()
    }, this.autoSaveDelay)
  }

  /**
   * 自动保存到IndexedDB
   */
  async autoSave() {
    if (!this.hasUnsavedChanges()) {
      return
    }

    const changes = this.getChanges()

    try {
      await indexedDBManager.saveSheetEdit(
        this.currentContext.pdfId,
        this.currentContext.excelFile,
        this.currentContext.sheetName,
        changes,
        this.currentContext.sessionId
      )

      console.log('💾 自动保存完成:', {
        changes: changes.length,
        sheet: this.currentContext.sheetName
      })

    } catch (error) {
      console.error('自动保存失败:', error)
    }
  }

  /**
   * 手动保存
   */
  async manualSave() {
    if (!this.hasUnsavedChanges()) {
      return { success: false, message: '没有需要保存的修改' }
    }

    const changes = this.getChanges()

    try {
      const id = await indexedDBManager.saveSheetEdit(
        this.currentContext.pdfId,
        this.currentContext.excelFile,
        this.currentContext.sheetName,
        changes,
        this.currentContext.sessionId
      )

      // 清空修改记录（假设保存成功）
      this.modifiedCells.clear()

      console.log('💾 手动保存完成:', { id, changes: changes.length })

      return {
        success: true,
        message: `已保存 ${changes.length} 处修改`,
        saveId: id
      }

    } catch (error) {
      console.error('手动保存失败:', error)
      return { success: false, message: '保存失败: ' + error.message }
    }
  }

  /**
   * 保存扁平化数据缓存
   */
    async saveFlattenedData(flattenedData, sourceData = null) {
      if (!flattenedData || flattenedData.length === 0) {
        return null
      }

      try {
        // 🔥 关键修复：简单有效的数据清理
        const cleanData = (data) => {
          if (!data) return data;
          try {
            // 使用 JSON 序列化来清理数据
            return JSON.parse(JSON.stringify(data));
          } catch (error) {
            console.warn('数据清理失败，返回空数组:', error);
            return [];
          }
        };

        const serializableFlattenedData = cleanData(flattenedData);
        const serializableSourceData = cleanData(sourceData);

        console.log('🔧 保存清理后的数据到 IndexedDB');

        const cacheKey = await indexedDBManager.saveFlattenedCache(
          this.currentContext.pdfId,
          this.currentContext.excelFile,
          this.currentContext.sheetName,
          serializableFlattenedData,
          serializableSourceData
        )

        return cacheKey

      } catch (error) {
        console.error('保存扁平化缓存失败:', error)

        // 简单降级：跳过缓存，但不阻塞主流程
        console.log('⏸️ 缓存失败，跳过但不阻塞流程');
        return 'cache_skipped';
      }
    }

  /**
   * 获取扁平化数据缓存
   */
  async getFlattenedData() {
    try {
      const cachedData = await indexedDBManager.getFlattenedCache(
        this.currentContext.pdfId,
        this.currentContext.excelFile,
        this.currentContext.sheetName
      )

      return cachedData

    } catch (error) {
      console.error('获取扁平化缓存失败:', error)
      return null
    }
  }

  /**
   * 恢复未保存的编辑
   */
  async restoreUnsavedEdits() {
    if (!this.currentContext.pdfId || !this.currentContext.sheetName) {
      return { success: false, message: '没有设置上下文' }
    }

    try {
      const unsavedEdits = await indexedDBManager.getUnsavedEdits(
        this.currentContext.pdfId,
        this.currentContext.excelFile,
        this.currentContext.sheetName
      )

      if (unsavedEdits.length === 0) {
        return { success: true, message: '没有未保存的编辑', edits: [] }
      }

      // 合并所有编辑记录
      const allChanges = []
      unsavedEdits.forEach(edit => {
        allChanges.push(...edit.changes)
      })

      console.log('🔄 找到未保存的编辑:', {
        editCount: unsavedEdits.length,
        changeCount: allChanges.length
      })

      return {
        success: true,
        message: `找到 ${allChanges.length} 处未保存的修改`,
        edits: unsavedEdits,
        changes: allChanges
      }

    } catch (error) {
      console.error('恢复未保存编辑失败:', error)
      return { success: false, message: '恢复失败: ' + error.message }
    }
  }

  /**
   * 清空当前Sheet的修改记录
   */
  clearChanges() {
    this.modifiedCells.clear()
    console.log('🧹 已清空修改记录')
  }

  /**
   * 设置页面保护（防止刷新丢失）
   */
  setupPageProtection() {
    // 监听页面刷新/关闭
    window.addEventListener('beforeunload', (event) => {
      if (this.hasUnsavedChanges()) {
        event.preventDefault()
        event.returnValue = '您有未保存的修改，确定要离开吗？'

        // 紧急保存
        this.emergencySave()
      }
    })

    // 监听页面隐藏（切换标签页）
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && this.hasUnsavedChanges()) {
        this.emergencySave()
      }
    })

    console.log('🛡️ 页面保护已启用')
  }

  /**
   * 紧急保存
   */
  async emergencySave() {
    if (!this.hasUnsavedChanges()) {
      return
    }

    console.log('🚨 执行紧急保存')

    try {
      await this.manualSave()
      console.log('✅ 紧急保存成功')
    } catch (error) {
      console.error('紧急保存失败:', error)
    }
  }

  /**
   * 获取数据库信息（调试用）
   */
  async getDatabaseInfo() {
    return await indexedDBManager.getDatabaseInfo()
  }
}

// 创建单例实例
const dataManager = new DataManager()

// 导出单例
export default dataManager