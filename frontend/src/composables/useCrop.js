import { layoutDetect, fetchPngBlob as fetchFileBlob } from '@/api/layout'
import { ElMessage } from 'element-plus'

export async function useCrop(filename, loadingRef, resultRef) {
  loadingRef.value[filename] = true
  try {    const folder = filename.replace(/\.(png|jpe?g|gif)$/i, '')
    const { table_zones } = await layoutDetect(folder, filename)
    if (!table_zones.length) {
      ElMessage.info('未检测到表格区域')
      return { zones: 0 }    }
    const blob = await fetchFileBlob(filename)
    const base64 = await blobToBase64(blob)
    const { data } = await fetch('/cut-table', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64, zones: table_zones })
    }).then(r => r.json())
    resultRef.value[filename] = data.slices
    return { zones: table_zones.length }
  } catch (e) {
    ElMessage.error('切图失败：' + (e.response?.data?.error || e.message))
    return { zones: 0 }
  } finally {
    loadingRef.value[filename] = false
  }
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}