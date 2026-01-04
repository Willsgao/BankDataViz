// scripts/cache-audit.js
const fs = require('fs');
const path = require('path');

// 工具函数：递归遍历目录
function traverseDirectory(dirPath, callback) {
  if (!fs.existsSync(dirPath)) {
    console.log(`❌ 目录不存在: ${dirPath}`);
    return;
  }

  const items = fs.readdirSync(dirPath);

  items.forEach(item => {
    const fullPath = path.join(dirPath, item);
    const stat = fs.statSync(fullPath);

    if (stat.isDirectory()) {
      // 跳过node_modules和隐藏目录
      if (!item.startsWith('.') && item !== 'node_modules') {
        traverseDirectory(fullPath, callback);
      }
    } else if (stat.isFile()) {
      // 只处理JavaScript和Vue文件
      if (item.endsWith('.js') || item.endsWith('.vue') || item.endsWith('.ts')) {
        try {
          const content = fs.readFileSync(fullPath, 'utf8');
          callback(fullPath, content);
        } catch (error) {
          console.log(`❌ 读取文件失败: ${fullPath}`, error.message);
        }
      }
    }
  });
}

// 缓存关键词定义
const CACHE_KEYWORDS = [
  // localStorage相关
  'localStorage', 'sessionStorage',
  'getItem', 'setItem', 'removeItem',

  // IndexedDB相关
  'indexedDB', 'openDB', 'db.transaction',

  // 你的自定义缓存类
  'excelDataCache', 'ExcelDataCache',
  'sheetStateManager', 'SheetStateManager',
  'indexedDBManager', 'IndexedDBManager',

  // 缓存键生成
  'getDraftKey', 'getCellKey', 'getBizDraftKey',
  'DraftKey', 'CellKey',

  // 状态管理
  'unsavedCells', 'hasUnsavedChanges',
  'saveDraft', 'restoreDraft', 'clearDraft',

  // 数据操作
  'setOriginalData', 'getOriginalData',
  'setFlattenedData', 'getFlattenedData',
  'saveData', 'autoSaveDraft'
];

function analyzeCacheDependencies() {
  console.log('🔍 开始分析缓存依赖关系...');

  const cachePoints = new Map(); // 文件路径 -> 使用的缓存关键词
  const keywordUsage = new Map(); // 关键词 -> 使用该词的文件列表

  // 初始化关键词使用统计
  CACHE_KEYWORDS.forEach(keyword => {
    keywordUsage.set(keyword, []);
  });

  let totalFiles = 0;
  let cacheFiles = 0;

  // 遍历src目录
  traverseDirectory('./src', (filePath, content) => {
    totalFiles++;

    const foundKeywords = new Set();

    // 检查每个关键词
    CACHE_KEYWORDS.forEach(keyword => {
      // 简单的字符串包含检查（可以优化为正则表达式）
      if (content.includes(keyword)) {
        foundKeywords.add(keyword);
        keywordUsage.get(keyword).push(filePath);
      }
    });

    if (foundKeywords.size > 0) {
      cacheFiles++;
      cachePoints.set(filePath, foundKeywords);
    }
  });

  return {
    cachePoints,
    keywordUsage,
    statistics: {
      totalFiles,
      cacheFiles,
      cacheFileRatio: (cacheFiles / totalFiles * 100).toFixed(1)
    }
  };
}

// 生成报告
function generateReport(analysisResult) {
  const { cachePoints, keywordUsage, statistics } = analysisResult;

  console.log('\n📊 ========== 缓存依赖分析报告 ==========\n');

  // 统计信息
  console.log('📈 统计概览:');
  console.log(`   总文件数: ${statistics.totalFiles}`);
  console.log(`   涉及缓存的文件: ${statistics.cacheFiles}`);
  console.log(`   缓存文件占比: ${statistics.cacheFileRatio}%`);

  // 按文件显示缓存使用情况
  console.log('\n📁 按文件分析:');
  cachePoints.forEach((keywords, filePath) => {
    // 计算相对路径，便于阅读
    const relativePath = path.relative(process.cwd(), filePath);
    console.log(`\n📄 ${relativePath}`);
    console.log(`   🔧 使用的缓存功能: ${Array.from(keywords).join(', ')}`);

    // 显示代码片段（可选）
    if (keywords.size > 0) {
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\n');

        // 找到包含缓存关键词的行
        keywords.forEach(keyword => {
          const relevantLines = lines
            .map((line, index) => ({ line, index: index + 1 }))
            .filter(({ line }) => line.includes(keyword))
            .slice(0, 3); // 只显示前3个匹配行

          if (relevantLines.length > 0) {
            console.log(`   💡 ${keyword} 使用位置:`);
            relevantLines.forEach(({ line, index }) => {
              console.log(`      ${index}: ${line.trim().slice(0, 100)}`);
            });
          }
        });
      } catch (error) {
        console.log(`   ❌ 无法读取文件内容`);
      }
    }
  });

  // 按关键词显示使用情况
  console.log('\n🔑 按缓存功能分析:');
  keywordUsage.forEach((files, keyword) => {
    if (files.length > 0) {
      console.log(`\n${keyword}:`);
      console.log(`   被 ${files.length} 个文件使用`);
      files.slice(0, 5).forEach(file => { // 只显示前5个文件
        const relativePath = path.relative(process.cwd(), file);
        console.log(`   - ${relativePath}`);
      });
      if (files.length > 5) {
        console.log(`   ... 还有 ${files.length - 5} 个文件`);
      }
    }
  });

  // 生成热点分析
  console.log('\n🔥 缓存热点分析:');
  const hotFiles = Array.from(cachePoints.entries())
    .filter(([_, keywords]) => keywords.size >= 3) // 使用3个以上缓存功能
    .sort((a, b) => b[1].size - a[1].size);

  if (hotFiles.length > 0) {
    console.log('   以下文件使用了3个以上的缓存功能（需要重点关注）:');
    hotFiles.forEach(([filePath, keywords]) => {
      const relativePath = path.relative(process.cwd(), filePath);
      console.log(`   ⚠️  ${relativePath} (${keywords.size}个功能)`);
    });
  }

  // 保存详细报告到文件
  const report = {
    generatedAt: new Date().toISOString(),
    statistics,
    files: Array.from(cachePoints.entries()).map(([file, keywords]) => ({
      file: path.relative(process.cwd(), file),
      keywords: Array.from(keywords),
      isHotspot: keywords.size >= 3
    })),
    keywords: Array.from(keywordUsage.entries()).map(([keyword, files]) => ({
      keyword,
      fileCount: files.length,
      files: files.map(f => path.relative(process.cwd(), f)).slice(0, 10)
    }))
  };

  fs.writeFileSync('cache-audit-report.json', JSON.stringify(report, null, 2));
  console.log('\n💾 详细报告已保存: cache-audit-report.json');
}

// 主执行函数
function main() {
  try {
    const analysisResult = analyzeCacheDependencies();
    generateReport(analysisResult);
  } catch (error) {
    console.error('❌ 分析过程中出错:', error);
  }
}

// 如果直接运行此文件，则执行分析
if (require.main === module) {
  main();
}

module.exports = { analyzeCacheDependencies, generateReport };