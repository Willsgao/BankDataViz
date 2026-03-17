// @/utils/excelKeyUtils.js
/**
 * Excel 数据键生成工具
 * 统一所有跨文件的键生成规则，确保缓存、状态、单元格标识同步
 */

/**
 * 生成草稿存储键
 * @param {string} pdfId - PDF文档ID
 * @param {string} excelFile - Excel文件名（原始名称）
 * @param {string} sheetName - 工作表名（原始名称）
 * @param {string} tableType - 表格类型：'original' 或 'flattened'
 * @returns {string} 草稿键
 */
export const getDraftKey = (pdfId, excelFile, sheetName, tableType) => {
  return `excel_draft_${pdfId}_${excelFile}_${sheetName}_${tableType}`;
};

/**
 * 生成单元格唯一标识键
 * @param {string} pdfId - PDF文档ID
 * @param {string} excelFile - Excel文件名
 * @param {string} sheetName - 工作表名
 * @param {string} tableType - 表格类型：'original' 或 'flattened'
 * @param {number} row - 行索引
 * @param {number} col - 列索引
 * @returns {string} 单元格键
 */
export const getCellKey = (pdfId, excelFile, sheetName, tableType, row, col) => {
  return `${pdfId}_${excelFile}_${sheetName}_${tableType}_${row},${col}`;
};


/**
 * 生成业务草稿单元格键（简化版，用于草稿恢复）
 * @param {string} pdfId - PDF文档ID
 * @param {string} sheetName - 工作表名
 * @param {string} tableType - 表格类型：'original' 或 'flattened'
 * @param {number} row - 行索引
 * @param {number} col - 列索引
 * @returns {string} 单元格键
 */
export const getBizCellKey = (pdfId, sheetName, tableType, row, col) => {
  // 保持与 getCellKey 格式一致，但不包含 excelFile
  // 格式: pdfId_sheetName_tableType_row,col
  return `${pdfId}_${sheetName}_${tableType}_${row},${col}`;
};

/**
 * 从业务单元格键解析（兼容 getBizCellKey 生成的键）
 * @param {string} bizCellKey - 业务单元格键
 * @returns {object|null} 解析结果
 */
export const parseBizCellKey = (bizCellKey) => {
  if (!bizCellKey || typeof bizCellKey !== 'string') return null;

  // 格式: pdfId_sheetName_tableType_row,col
  const parts = bizCellKey.split('_');
  if (parts.length < 4) return null;

  const pdfId = parts[0];
  const sheetName = parts[1];
  const tableType = parts[2];

  // 解析行列
  const rowColPart = parts.slice(3).join('_'); // 处理可能的额外下划线
  const [rowStr, colStr] = rowColPart.split(',');

  const row = parseInt(rowStr, 10);
  const col = parseInt(colStr, 10);

  if (isNaN(row) || isNaN(col)) return null;

  return {
    pdfId,
    sheetName,
    tableType,
    row,
    col
  };
};


// 仅用 pdfId + sheetName 生成草稿 key
export const getBizDraftKey = (pdfId, sheetName, tableType) =>
  `biz_draft_${pdfId}_${sheetName}_${tableType}`;

/**
 * 生成前缀匹配键（用于过滤当前表格的单元格）
 * @param {string} pdfId - PDF文档ID
 * @param {string} excelFile - Excel文件名
 * @param {string} sheetName - 工作表名
 * @returns {string} 前缀键（注意：末尾带下划线，用于startsWith匹配）
 */
export const getPrefixKey = (pdfId, excelFile, sheetName) => {
  return `${pdfId}_${excelFile}_${sheetName}_`;
};

/**
 * 从单元格键解析出各组成部分
 * @param {string} cellKey - 单元格键
 * @returns {object|null} 解析结果或null（解析失败）
 */
export const parseCellKey = (cellKey) => {
  if (!cellKey || typeof cellKey !== 'string') return null;

  const parts = cellKey.split('_');
  if (parts.length < 5) return null;

  const pdfId = parts[0];
  const tableType = parts[parts.length - 2];
  const rowCol = parts[parts.length - 1];

  // 正确解析中间部分：excelFile + sheetName
  const middleParts = parts.slice(1, parts.length - 2);

  // 使用正则表达式识别excelFile的结束位置
  const excelFileRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_合并_\d{8}_\d{6}\.xlsx$/;

  let excelFile = '';
  let sheetName = '';

  // 尝试找到excelFile的完整名称
  for (let i = 0; i < middleParts.length; i++) {
    const testStr = middleParts.slice(0, i + 1).join('_');
    if (excelFileRegex.test(testStr)) {
      excelFile = testStr;
      sheetName = middleParts.slice(i + 1).join('_');
      break;
    }
  }

  // 如果正则匹配失败，使用启发式方法
  if (!excelFile) {
    // 查找时间戳部分（如20251224）
    const timestampIndex = middleParts.findIndex(part =>
      part.length === 8 && /^\d{8}$/.test(part)
    );

    if (timestampIndex !== -1 && timestampIndex + 2 < middleParts.length) {
      // 时间戳后的部分应该是.xlsx
      if (middleParts[timestampIndex + 2].endsWith('.xlsx')) {
        excelFile = middleParts.slice(0, timestampIndex + 3).join('_');
        sheetName = middleParts.slice(timestampIndex + 3).join('_');
      }
    }

    // 如果还是失败，使用保守方法
    if (!excelFile && middleParts.length >= 2) {
      excelFile = middleParts[0]; // 第一个部分作为excelFile
      sheetName = middleParts.slice(1).join('_');
    }
  }

  const [row, col] = rowCol.split(',').map(Number);

  if (isNaN(row) || isNaN(col)) return null;

  return {
    pdfId,
    excelFile,
    sheetName,
    tableType,
    row,
    col
  };
};

/**
 * 生成索引键（预留函数）
 * @param {string} pdfId - PDF文档ID
 * @param {string} excelFile - Excel文件名
 * @returns {string} 索引键
 */
export const getIndexKey = (pdfId, excelFile) => {
  return `excel_draft_index_${pdfId}_${excelFile}`;
};

export default {
  getDraftKey,
  getCellKey,
  getBizDraftKey,
  getBizCellKey,
  getPrefixKey,
  parseCellKey,
  parseBizCellKey,
  getIndexKey
};