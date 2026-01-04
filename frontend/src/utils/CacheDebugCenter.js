// src/utils/CacheDebugCenter.js
class CacheDebugCenter {
  constructor() {
    this.logs = [];
    this.enabled = true;
    console.log('🔧 CacheDebugCenter 已初始化');
  }

  // 统一的日志记录
  log(component, action, data, context = {}) {
    if (!this.enabled) return;

    const entry = {
      timestamp: new Date().toISOString(),
      component: component.replace(/\\/g, '/'), // 统一路径格式
      action,
      data: this.safeStringify(data),
      context: this.safeStringify(context),
      stack: new Error().stack.split('\n').slice(2, 5).join(' | ') // 获取调用堆栈
    };

    this.logs.push(entry);
    console.log(`[CACHE_DEBUG] ${component}.${action}`, data);

    // 保持最近200条日志
    if (this.logs.length > 200) this.logs.shift();
  }

  // 获取当前系统状态快照
  getSystemSnapshot() {
    const snapshot = {
      // 核心缓存实例状态
      excelDataCache: window.excelDataCache ? '已定义' : '未定义',
      sheetStateManager: window.sheetStateManager ? '已定义' : '未定义',
      dataManager: window.dataManager ? '已定义' : '未定义',

      // 全局状态
      unsavedCells: {
        original: window.unsavedCells?.original?.size || 0,
        flattened: window.unsavedCells?.flattened?.size || 0,
        exists: !!window.unsavedCells
      },

      // localStorage扫描
      localStorage: this.scanStorage('localStorage'),
      sessionStorage: this.scanStorage('sessionStorage'),

      // 当前活跃上下文
      activeContext: {
        pdfId: window.currentPdfId || '未设置',
        excelFile: window.currentExcelFile || '未设置',
        sheetName: window.currentSheetName || '未设置',
        tableType: window.currentTableType || '未设置'
      },

      // 调试日志
      recentLogs: this.logs.slice(-5), // 最近5条日志
      totalLogs: this.logs.length
    };

    // 如果缓存实例存在，获取更详细的信息
    if (window.excelDataCache && typeof window.excelDataCache.getStats === 'function') {
      try {
        snapshot.excelDataCache = window.excelDataCache.getStats();
      } catch (e) {
        snapshot.excelDataCache = { error: e.message };
      }
    }

    if (window.sheetStateManager && typeof window.sheetStateManager.getActiveContext === 'function') {
      try {
        snapshot.sheetStateManager = window.sheetStateManager.getActiveContext();
      } catch (e) {
        snapshot.sheetStateManager = { error: e.message };
      }
    }

    return snapshot;
  }

  // 扫描指定存储
  scanStorage(storageType) {
    try {
      const storage = storageType === 'localStorage' ? localStorage : sessionStorage;
      const items = [];

      for (let i = 0; i < storage.length; i++) {
        const key = storage.key(i);
        if (key.includes('excel') || key.includes('draft') || key.includes('cache')) {
          try {
            const value = storage.getItem(key);
            items.push({
              key,
              value: value ? value.slice(0, 100) + '...' : '空值', // 限制长度
              length: value ? value.length : 0
            });
          } catch (e) {
            items.push({ key, error: e.message });
          }
        }
      }

      return {
        count: items.length,
        items: items.slice(0, 10) // 只显示前10个
      };
    } catch (error) {
      return { error: error.message };
    }
  }

  // 安全序列化
  safeStringify(obj) {
    try {
      if (obj === null || obj === undefined) return String(obj);
      if (typeof obj === 'string') return obj.slice(0, 200); // 限制长度

      return JSON.stringify(obj, (key, value) => {
        if (typeof value === 'function') return '[Function]';
        if (value instanceof HTMLElement) return '[HTMLElement]';
        if (value instanceof Window) return '[Window]';
        if (value instanceof Error) return `[Error: ${value.message}]`;
        if (typeof value === 'object' && value !== null) {
          // 处理循环引用
          try {
            JSON.stringify(value);
            return value;
          } catch (e) {
            return `[Circular Reference]`;
          }
        }
        return value;
      }).slice(0, 500); // 限制长度
    } catch (e) {
      return `[Stringify Error: ${e.message}]`;
    }
  }

  // 清空日志
  clearLogs() {
    this.logs = [];
    console.log('🧹 调试日志已清空');
  }

  // 启用/禁用调试
  setEnabled(enabled) {
    this.enabled = enabled;
    console.log(`🔧 调试${enabled ? '启用' : '禁用'}`);
  }

  // 获取日志统计
  getStats() {
    const components = {};
    this.logs.forEach(log => {
      components[log.component] = (components[log.component] || 0) + 1;
    });

    return {
      totalLogs: this.logs.length,
      components,
      firstLog: this.logs[0]?.timestamp,
      lastLog: this.logs[this.logs.length - 1]?.timestamp
    };
  }
}

// 创建全局单例
const cacheDebug = new CacheDebugCenter();

// 全局调试函数
window.debugCacheIssue = function() {
  console.log('🩺 开始缓存系统诊断...');

  // 1. 获取当前状态快照
  const snapshot = cacheDebug.getSystemSnapshot();
  console.log('📊 当前系统状态快照:', snapshot);

  // 2. 检查关键状态
  const issues = [];

  // 检查unsavedCells状态
  if (!window.unsavedCells) {
    issues.push('❌ window.unsavedCells 未定义');
  } else {
    const originalCount = window.unsavedCells.original?.size || 0;
    const flattenedCount = window.unsavedCells.flattened?.size || 0;
    console.log(`📝 未保存单元格统计: 原始表${originalCount}个, 扁平表${flattenedCount}个`);

    if (originalCount > 0 || flattenedCount > 0) {
      console.log('🔍 未保存单元格详情:', {
        original: window.unsavedCells.original ? Array.from(window.unsavedCells.original).slice(0, 3) : '无',
        flattened: window.unsavedCells.flattened ? Array.from(window.unsavedCells.flattened).slice(0, 3) : '无'
      });
    }
  }

  // 检查缓存实例
  if (!window.excelDataCache) issues.push('❌ excelDataCache 未定义');
  if (!window.sheetStateManager) issues.push('❌ sheetStateManager 未定义');

  // 3. 输出问题报告
  if (issues.length > 0) {
    console.log('🚨 发现问题:');
    issues.forEach(issue => console.log('   ' + issue));
  } else {
    console.log('✅ 基础状态正常');
  }

  // 4. 显示日志统计
  const stats = cacheDebug.getStats();
  console.log('📈 调试日志统计:', stats);

  return { issues, snapshot, stats };
};

// 导出单例
export default cacheDebug;