import { openDB } from 'idb'

const DB_NAME = 'excel_draft'
const STORE   = 'draft'
const VERSION = 1

/** 获取数据库实例 */
async function getDB() {
  return openDB(DB_NAME, VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE)) {
        // 主键：pdfId|excelFile|sheetName|tableType
        db.createObjectStore(STORE, { keyPath: 'id' })
      }
    }
  })
}

/** 保存草稿 */
export async function saveDraftToIndexedDB({ pdfId, excelFile, sheetName, tableType, data, savedAt }) {
  const id = `${pdfId}|${excelFile}|${sheetName}|${tableType}`
  const db = await getDB()
  await db.put(STORE, { id, data, savedAt })
  console.log('💾 草稿已写入 IndexedDB', id)
}

/** 读取草稿 */
export async function loadDraftFromIndexedDB(pdfId, excelFile, sheetName, tableType) {
  const id = `${pdfId}|${excelFile}|${sheetName}|${tableType}`
  const db = await getDB()
  return db.get(STORE, id) // 找不到返回 undefined
}

/** 删除草稿 */
export async function clearDraftFromIndexedDB(pdfId, excelFile, sheetName, tableType) {
  const id = `${pdfId}|${excelFile}|${sheetName}|${tableType}`
  const db = await getDB()
  await db.delete(STORE, id)
  console.log('🗑️ 草稿已清除', id)
}