// src/composables/useBatchTableCrop.js
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/api/index'

export function useBatchTableCrop(resultRef) {
  const batchCropLoading = ref({})

  async function cutTablesForPDF(pdfDiskName, convertCache) {
    batchCropLoading.value[pdfDiskName] = true

    try {
      // 1. 统一 key：去掉 .pdf
      const folderKey = pdfDiskName.replace(/\.pdf$/i, '')

      // 2. 取图片列表
      const pngList = convertCache[folderKey]
      if (!pngList || !pngList.length) {
        ElMessage.info('请先完成「转图并预览」')
        return
      }

      // 3. 发请求（字段名、URL 都与后端对齐）
      const { data } = await http.post(
        `/api/batch-cut-table/${Date.now()}`,   // task_id 任意
        {
          pdf_folder: folderKey,   // 后端要求的字段
          png_names: pngList       // 后端要求的字段
        }
      )

      // 4. 处理返回
      if (data.success) {
        resultRef.value[pdfDiskName] = data.slices
        ElMessage.success(`批量裁切完成，共 ${data.slices.length} 个表格`)
      } else {
        ElMessage.error(`裁切失败：${data.message || '未知错误'}`)
      }
    } catch (e) {
      console.error('批量裁切接口调用失败：', e)
      ElMessage.error('网络或服务异常')
    } finally {
      batchCropLoading.value[pdfDiskName] = false
    }
  }

  return { cutTablesForPDF, batchCropLoading }
}