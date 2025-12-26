// src/utils/indexedDBManager.js
import { ElMessage } from 'element-plus'

class IndexedDBManager {
  constructor() {
    this.db = null
    this.dbName = 'ExcelEditorDB'
    this.dbVersion = 2

    // 初始化
    this.initPromise = this.initDatabase()
  }

  /**
   * 初始化数据库
   */
  async initDatabase() {
    return new Promise((resolve, reject) => {
      console.log('🔄 初始化 IndexedDB...')

      const request = indexedDB.open(this.dbName, this.dbVersion)

      request.onerror = (event) => {
        console.error('❌ IndexedDB 初始化失败:', event.target.error)
        reject(event.target.error)
      }

      request.onsuccess = (event) => {
        this.db = event.target.result
        console.log('✅ IndexedDB 初始化成功')
        resolve(this.db)
      }

      request.onupgradeneeded = (event) => {
        const db = event.target.result

        // 1. 存储Sheet编辑数据
        if (!db.objectStoreNames.contains('sheet_edits')) {
          const store = db.createObjectStore('sheet_edits', {
            keyPath: 'id',
            autoIncrement: true
          })

          // 创建索引
          store.createIndex('pdf_id', 'pdf_id', { unique: false })
          store.createIndex('sheet_name', 'sheet_name', { unique: false })
          store.createIndex('pdf_sheet', ['pdf_id', 'sheet_name'], { unique: false })
          store.createIndex('timestamp', 'timestamp', { unique: false })
          store.createIndex('session_id', 'session_id', { unique: false })
        }

        // 2. 存储扁平化缓存
        if (!db.objectStoreNames.contains('flattened_data')) {
          const store = db.createObjectStore('flattened_data', {
            keyPath: 'cache_key'
          })

          // 创建索引
          store.createIndex('pdf_id', 'pdf_id', { unique: false })
          store.createIndex('pdf_sheet', ['pdf_id', 'sheet_name'], { unique: true })
          store.createIndex('timestamp', 'timestamp', { unique: false })
        }

        // 3. 存储合并历史
        if (!db.objectStoreNames.contains('merge_history')) {
          const store = db.createObjectStore('merge_history', {
            keyPath: 'id',
            autoIncrement: true
          })

          store.createIndex('timestamp', 'timestamp', { unique: false })
        }

        console.log('📊 IndexedDB 表结构创建完成')
      }
    })
  }

  /**
   * 确保数据库已初始化
   */
  async ensureDB() {
    if (!this.db) {
      await this.initPromise
    }
    return this.db
  }

  /**
   * 通用方法：添加记录
   */
  async addRecord(storeName, record) {
    try {
      await this.ensureDB()

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.add(record)

        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error(`添加记录到 ${storeName} 失败:`, error)
      throw error
    }
  }

  /**
   * 通用方法：获取记录
   */
  async getRecord(storeName, key) {
    try {
      await this.ensureDB()

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction([storeName], 'readonly')
        const store = transaction.objectStore(storeName)
        const request = store.get(key)

        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error(`从 ${storeName} 获取记录失败:`, error)
      return null
    }
  }

  /**
   * 通用方法：查询记录
   */
  async queryRecords(storeName, indexName, value) {
    try {
      await this.ensureDB()

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction([storeName], 'readonly')
        const store = transaction.objectStore(storeName)
        const index = store.index(indexName)
        const request = index.getAll(value)

        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error(`查询 ${storeName} 失败:`, error)
      return []
    }
  }

  /**
   * 通用方法：删除记录
   */
  async deleteRecord(storeName, key) {
    try {
      await this.ensureDB()

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.delete(key)

        request.onsuccess = () => resolve(true)
        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error(`删除 ${storeName} 记录失败:`, error)
      return false
    }
  }

  /**
   * 通用方法：清空存储
   */
  async clearStore(storeName) {
    try {
      await this.ensureDB()

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        const request = store.clear()

        request.onsuccess = () => resolve(true)
        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error(`清空 ${storeName} 失败:`, error)
      return false
    }
  }

  /**
   * 保存Sheet编辑数据
   */
  async saveSheetEdit(pdfId, excelFile, sheetName, changes, sessionId = null) {
    const record = {
      pdf_id: pdfId,
      excel_file: excelFile,
      sheet_name: sheetName,
      changes: changes,                    // 修改记录数组
      change_count: changes.length,
      timestamp: Date.now(),
      session_id: sessionId || this.getSessionId(),
      status: 'unsaved'                   // unsaved/saved/committed
    }

    const id = await this.addRecord('sheet_edits', record)
    console.log('💾 编辑数据已保存到 IndexedDB:', {
      pdfId, sheetName, changeCount: changes.length, id
    })

    return id
  }

  /**
   * 获取某个Sheet的未保存编辑
   */
  async getUnsavedEdits(pdfId, excelFile, sheetName) {
    try {
      await this.ensureDB()

      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction(['sheet_edits'], 'readonly')
        const store = transaction.objectStore('sheet_edits')
        const index = store.index('pdf_sheet')

        // 查询指定PDF和Sheet的记录
        const keyRange = IDBKeyRange.bound(
          [pdfId, sheetName],
          [pdfId, sheetName + '\uffff']
        )

        const request = index.getAll(keyRange)

        request.onsuccess = () => {
          // 过滤出未保存的记录
          const unsaved = request.result
            .filter(record => record.status === 'unsaved')
            .sort((a, b) => b.timestamp - a.timestamp) // 最新的在前

          console.log(`🔍 找到 ${unsaved.length} 条未保存的编辑`)
          resolve(unsaved)
        }

        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error('获取未保存编辑失败:', error)
      return []
    }
  }

  /**
   * 保存扁平化数据缓存
   */
  async saveFlattenedCache(pdfId, excelFile, sheetName, flattenedData, sourceData) {
    const cacheKey = `${pdfId}_${excelFile}_${sheetName}_flattened`

    const record = {
      cache_key: cacheKey,
      pdf_id: pdfId,
      excel_file: excelFile,
      sheet_name: sheetName,
      data: flattenedData,               // 扁平化数据
      source_data: sourceData,           // 源数据（用于重新生成）
      timestamp: Date.now(),
      data_type: 'flattened',
      size: JSON.stringify(flattenedData).length
    }

    await this.addRecord('flattened_data', record)
    console.log('📦 扁平化数据已缓存:', { pdfId, sheetName })

    return cacheKey
  }

  /**
   * 获取扁平化数据缓存
   */
  async getFlattenedCache(pdfId, excelFile, sheetName) {
    const cacheKey = `${pdfId}_${excelFile}_${sheetName}_flattened`
    const cached = await this.getRecord('flattened_data', cacheKey)

    if (cached) {
      console.log('📦 找到扁平化缓存:', {
        pdfId, sheetName,
        rows: cached.data.length,
        age: Math.round((Date.now() - cached.timestamp) / 1000) + '秒前'
      })
    }

    return cached ? cached.data : null
  }

  /**
   * 获取当前会话ID
   */
  getSessionId() {
    let sessionId = sessionStorage.getItem('excel_editor_session_id')
    if (!sessionId) {
      sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
      sessionStorage.setItem('excel_editor_session_id', sessionId)
    }
    return sessionId
  }

  /**
   * 清除当前会话的未保存数据
   */
  async clearSessionData(sessionId = null) {
    const targetSessionId = sessionId || this.getSessionId()

    try {
      await this.ensureDB()

      // 删除指定会话的编辑记录
      const edits = await this.queryRecords('sheet_edits', 'session_id', targetSessionId)
      for (const edit of edits) {
        if (edit.status === 'unsaved') {
          await this.deleteRecord('sheet_edits', edit.id)
        }
      }

      console.log(`🧹 已清理会话 ${targetSessionId} 的未保存数据`)
      return true
    } catch (error) {
      console.error('清理会话数据失败:', error)
      return false
    }
  }

  /**
   * 获取数据库信息（调试用）
   */
  async getDatabaseInfo() {
    try {
      await this.ensureDB()

      const info = {
        name: this.db.name,
        version: this.db.version,
        objectStores: Array.from(this.db.objectStoreNames),
        stats: {}
      }

      // 获取各表的数据量
      for (const storeName of info.objectStores) {
        const count = await this.getStoreCount(storeName)
        info.stats[storeName] = { count }
      }

      return info
    } catch (error) {
      console.error('获取数据库信息失败:', error)
      return null
    }
  }

  /**
   * 获取存储的记录数量
   */
  async getStoreCount(storeName) {
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      const request = store.count()

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * 导出数据库（备份用）
   */
  async exportDatabase() {
    try {
      await this.ensureDB()

      const exportData = {}
      const storeNames = Array.from(this.db.objectStoreNames)

      for (const storeName of storeNames) {
        const records = await this.getAllRecords(storeName)
        exportData[storeName] = records
      }

      return exportData
    } catch (error) {
      console.error('导出数据库失败:', error)
      return null
    }
  }

  /**
   * 获取所有记录
   */
  async getAllRecords(storeName) {
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      const request = store.getAll()

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }
}

// 创建单例实例
const indexedDBManager = new IndexedDBManager()

// 导出单例
export default indexedDBManager