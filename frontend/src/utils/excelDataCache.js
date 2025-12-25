/**
 * Excel数据缓存管理器
 * 管理原始数据、扁平化数据和二维表格数据的缓存
 */

class ExcelDataCache {
  constructor() {
    this.cache = new Map() // key: sheetKey, value: cacheItem
    this.twoDimensionalTables = new Map() // key: sheetKey, value: 二维表格数据
    this.currentSheetKey = null
  }

  /**
   * 生成sheet缓存键
   * @param {string} pdfId PDF ID
   * @param {string} excelFile Excel文件名
   * @param {string} sheetName Sheet名称
   * @returns {string} 缓存键
   */
  generateSheetKey(pdfId, excelFile, sheetName) {
    return `${pdfId}|${excelFile}|${sheetName}`
  }

  /**
   * 设置当前sheet
   */
  setCurrentSheet(pdfId, excelFile, sheetName) {
    this.currentSheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)
    return this.currentSheetKey
  }

  /**
   * 获取当前sheet的缓存
   */
  getCurrentCache() {
    if (!this.currentSheetKey) return null
    return this.cache.get(this.currentSheetKey) || null
  }

  /**
   * 获取当前sheet信息
   */
  getCurrentSheet() {
    if (!this.currentSheetKey) return null

    const cacheItem = this.cache.get(this.currentSheetKey)
    if (!cacheItem) return null

    return {
      pdfId: cacheItem.sourceInfo?.pdfId,
      excelFile: cacheItem.sourceInfo?.excelFile,
      sheetName: cacheItem.sourceInfo?.sheetName,
      key: this.currentSheetKey
    }
  }

  /**
   * 设置原始数据（初始化或更新）
   */
  setOriginalData(pdfId, excelFile, sheetName, originalData) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)

    let cacheItem = this.cache.get(sheetKey)
    if (!cacheItem) {
      cacheItem = {
        original: null,
        flattened: null,
        isFlattening: false,
        lastUpdate: null,
        sourceInfo: { pdfId, excelFile, sheetName }
      }
    }

    cacheItem.original = originalData
    cacheItem.lastUpdate = new Date().toISOString()

    // 当原始数据更新时，清空扁平化缓存和二维表格缓存（数据可能已变化）
    if (cacheItem.flattened) {
      console.log('🔄 原始数据已更新，清空扁平化缓存')
      cacheItem.flattened = null
    }

    // 清空二维表格缓存
    this.clearTwoDimensionalTable(pdfId, excelFile, sheetName)

    this.cache.set(sheetKey, cacheItem)
    console.log(`📦 缓存原始数据: ${sheetKey} (${originalData?.length || 0}行)`)
    return cacheItem
  }

  /**
   * 设置扁平化数据
   */
  setFlattenedData(pdfId, excelFile, sheetName, flattenedData) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)

    let cacheItem = this.cache.get(sheetKey)
    if (!cacheItem) {
      console.warn('⚠️ 设置扁平化数据时未找到原始数据缓存')
      cacheItem = {
        original: null,
        flattened: null,
        isFlattening: false,
        lastUpdate: null,
        sourceInfo: { pdfId, excelFile, sheetName }
      }
    }

    cacheItem.flattened = flattenedData
    cacheItem.isFlattening = false
    cacheItem.lastUpdate = new Date().toISOString()

    this.cache.set(sheetKey, cacheItem)
    console.log(`📦 缓存扁平化数据: ${sheetKey} (${flattenedData?.length || 0}条记录)`)
    return cacheItem
  }

  /**
   * 设置二维表格数据
   */
  setTwoDimensionalTable(pdfId, excelFile, sheetName, tableData) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)

    this.twoDimensionalTables.set(sheetKey, {
      data: tableData,
      timestamp: Date.now()
    })

    console.log(`📦 缓存二维表格数据: ${sheetKey} (${tableData.length}行 × ${tableData[0]?.length || 0}列)`)
    return this.getTwoDimensionalTable(pdfId, excelFile, sheetName)
  }

  /**
   * 获取原始数据
   */
  getOriginalData(pdfId, excelFile, sheetName) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)
    const cacheItem = this.cache.get(sheetKey)
    return cacheItem ? cacheItem.original : null
  }

  /**
   * 获取扁平化数据
   */
  getFlattenedData(pdfId, excelFile, sheetName) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)
    const cacheItem = this.cache.get(sheetKey)
    return cacheItem ? cacheItem.flattened : null
  }

  /**
   * 获取二维表格数据
   */
  getTwoDimensionalTable(pdfId, excelFile, sheetName) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)
    const tableCache = this.twoDimensionalTables.get(sheetKey)
    return tableCache ? tableCache.data : null
  }

  /**
   * 检查是否有二维表格数据缓存
   */
  hasTwoDimensionalTable(pdfId, excelFile, sheetName) {
    const tableData = this.getTwoDimensionalTable(pdfId, excelFile, sheetName)
    return !!tableData && Array.isArray(tableData) && tableData.length > 0
  }

  /**
   * 检查是否有扁平化数据缓存
   */
  hasFlattenedData(pdfId, excelFile, sheetName) {
    const flattened = this.getFlattenedData(pdfId, excelFile, sheetName)
    return !!flattened && Array.isArray(flattened) && flattened.length > 0
  }

  /**
   * 设置扁平化状态
   */
  setFlatteningState(pdfId, excelFile, sheetName, isFlattening) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)
    const cacheItem = this.cache.get(sheetKey)
    if (cacheItem) {
      cacheItem.isFlattening = isFlattening
      this.cache.set(sheetKey, cacheItem)
    }
  }

  /**
   * 清除指定sheet的缓存
   */
  clearSheetCache(pdfId, excelFile, sheetName) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)
    this.cache.delete(sheetKey)
    this.clearTwoDimensionalTable(pdfId, excelFile, sheetName)
    console.log(`🗑️ 清除缓存: ${sheetKey}`)
  }

  /**
   * 清除二维表格缓存
   */
  clearTwoDimensionalTable(pdfId, excelFile, sheetName) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)
    if (this.twoDimensionalTables.has(sheetKey)) {
      this.twoDimensionalTables.delete(sheetKey)
      console.log(`🗑️ 清除二维表格缓存: ${sheetKey}`)
    }
  }

  /**
   * 清除所有缓存
   */
  clearAll() {
    this.cache.clear()
    this.twoDimensionalTables.clear()
    this.currentSheetKey = null
    console.log('🗑️ 清除所有数据缓存')
  }

  /**
   * 获取缓存统计信息
   */
  getStats() {
    const totalSheets = this.cache.size
    const total2DTables = this.twoDimensionalTables.size
    let withOriginal = 0
    let withFlattened = 0
    let totalFlattenedRows = 0
    let total2DRows = 0

    for (const [key, item] of this.cache.entries()) {
      if (item.original) {
        withOriginal++
      }
      if (item.flattened) {
        withFlattened++
        totalFlattenedRows += (Array.isArray(item.flattened) ? item.flattened.length : 0)
      }
    }

    for (const [key, tableCache] of this.twoDimensionalTables.entries()) {
      if (tableCache.data) {
        total2DRows += (Array.isArray(tableCache.data) ? tableCache.data.length : 0)
      }
    }

    return {
      totalSheets,
      total2DTables,
      sheetsWithOriginal: withOriginal,
      sheetsWithFlattened: withFlattened,
      totalFlattenedRows,
      total2DRows,
      currentSheet: this.currentSheetKey
    }
  }

  /**
   * 调试输出
   */
  debug() {
    const stats = this.getStats()
    console.log('📊 Excel数据缓存状态:', stats)

    console.log('📋 原始数据缓存详情:')
    for (const [key, item] of this.cache.entries()) {
      console.log(`  ${key}:`, {
        原始数据行数: Array.isArray(item.original) ? item.original.length : '无',
        扁平化记录数: Array.isArray(item.flattened) ? item.flattened.length : '无',
        最后更新: item.lastUpdate,
        正在扁平化: item.isFlattening
      })
    }

    console.log('📋 二维表格缓存详情:')
    for (const [key, tableCache] of this.twoDimensionalTables.entries()) {
      const data = tableCache.data
      console.log(`  ${key}:`, {
        行数: Array.isArray(data) ? data.length : '无',
        列数: Array.isArray(data) && data[0] ? data[0].length : '无',
        缓存时间: new Date(tableCache.timestamp).toLocaleTimeString()
      })
    }
  }

  /**
   * 重建二维表格数据（如果缓存中没有）
   */
  rebuildTwoDimensionalTableIfNeeded(pdfId, excelFile, sheetName) {
    const sheetKey = this.generateSheetKey(pdfId, excelFile, sheetName)

    // 如果已经有缓存，直接返回
    if (this.hasTwoDimensionalTable(pdfId, excelFile, sheetName)) {
      console.log(`📦 使用缓存的二维表格数据: ${sheetKey}`)
      return this.getTwoDimensionalTable(pdfId, excelFile, sheetName)
    }

    // 从原始数据重建
    const originalData = this.getOriginalData(pdfId, excelFile, sheetName)
    if (!originalData || !Array.isArray(originalData) || originalData.length === 0) {
      console.warn(`⚠️ 无法重建二维表格数据: 原始数据为空 (${sheetKey})`)
      return null
    }

    console.log(`🔄 重建二维表格数据: ${sheetKey}`)

    // 调用重建函数（这个函数需要在外部定义）
    if (typeof window.rebuildTwoDimensionalTable === 'function') {
      const tableData = window.rebuildTwoDimensionalTable(originalData)
      if (tableData && Array.isArray(tableData) && tableData.length > 0) {
        this.setTwoDimensionalTable(pdfId, excelFile, sheetName, tableData)
        return tableData
      }
    }

    console.warn(`⚠️ 重建二维表格数据失败: ${sheetKey}`)
    return null
  }
}

// 创建单例实例
const excelDataCache = new ExcelDataCache()

// 暴露给控制台调试
if (typeof window !== 'undefined') {
  window.excelDataCache = excelDataCache
}

export default excelDataCache