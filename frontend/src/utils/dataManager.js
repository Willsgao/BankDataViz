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

  /**
   * 记录单元格修改
   */
  recordCellChange(row, col, oldValue, newValue) {
    if (oldValue === newValue) return

    const cellKey = `${row}_${col}`

    // 如果这个单元格已经被修改过，更新记录
    if (this.modifiedCells.has(cellKey)) {
      const existing = this.modifiedCells.get(cellKey)
      existing.new = newValue
      existing.timestamp = Date.now()
    } else {
      // 新增修改记录
      this.modifiedCells.set(cellKey, {
        row,
        col,
        old: oldValue,
        new: newValue,
        timestamp: Date.now()
      })
    }

    console.log('📝 记录单元格修改:', { row, col, old: oldValue, new: newValue })

    // 触发自动保存
    this.scheduleAutoSave()
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
      const cacheKey = await indexedDBManager.saveFlattenedCache(
        this.currentContext.pdfId,
        this.currentContext.excelFile,
        this.currentContext.sheetName,
        flattenedData,
        sourceData
      )

      return cacheKey

    } catch (error) {
      console.error('保存扁平化缓存失败:', error)
      return null
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