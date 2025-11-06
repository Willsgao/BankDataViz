// src/composables/useConvert.js

import { ElMessage } from 'element-plus'
import { convertPdf, getProgress, getPngList } from '@/api/convert'

/**
 * 转图 + 进度 + 缓存处理
 * 缓存命中时主动触发预览
 */
export function useConvert(
  pdfName,
  cache,
  visible,
  percent,
  status,
  msg,
  loadingObj,
  refreshPreview   // ⬅ 放在最后
) {
  async function convert() {
    const key = pdfName
    console.log('🚀 convert() 开始', key)

    loadingObj.value[key] = true
    visible.value = true
    percent.value = 0
    status.value = ''
    msg.value = '检查缓存...'

    /* 1. 缓存命中 → 直接预览 */
    if (cache[key]) {
      console.log('🚪 走进本地缓存命中分支')
      console.log('✅ 缓存命中，直接预览', cache[key])
      window.postMessage({
        type: 'openPreview',
        folder: key.replace('.pdf', ''),
        pngs: cache[key]
      }, '*')
      console.log('📤 postMessage 已发出11，origin=*', Date.now())
      refreshPreview()   // ⬅ 正确位置：在 convert 内部调用
      loadingObj.value[key] = false
      delete loadingObj.value[key]
      visible.value = false
      // progressVisible.value = false
      return { ok: true, pngs: cache[key], folder: key.replace('.pdf', '') }
    }

    /* 2. 无缓存 → 真正转图 */
    try {
      msg.value = '提交任务...'
      console.log('📡 即将请求 convertPdf', key)
      const { jobId, hitCache, pngs } = await convertPdf(key)
      console.log('📨 后端返回', { jobId, hitCache, pngs })

      if (hitCache) {

        console.log('🚪 走进后端已缓存分支')
        cache[key] = pngs
        console.log('📤 准备 postMessage', {   // ← 加这条
          type: 'openPreview',
          folder: key.replace('.pdf', ''),
          pngs
        })
        window.postMessage({
          type: 'openPreview',
          folder: key.replace('.pdf', ''),
          pngs
        }, '*')
        console.log('📤 postMessage 已发送（后端缓存）')
        refreshPreview()   // ⬅ 缓存命中也调用
        visible.value = false
        // progressVisible.value = false
        loadingObj.value[key] = false
        delete loadingObj.value[key]
        return { ok: true, pngs, folder: key.replace('.pdf', '') }
      }

      /* 3. 轮询进度 */
      msg.value = '任务已提交，正在转图...'
      console.log('⏳ 开始轮询进度', jobId)
      await poll(jobId)

      if (status.value === 'success') {
        const list = await getPngList(key.replace('.pdf', ''))
        console.log('✅ 轮询成功，去取 png 列表')
        cache[key] = list.pngs

        console.log('📤 即将 postMessage', {
          type: 'openPreview',
          folder: key.replace('.pdf', ''),
          pngs: cache[key],
          timestamp: Date.now()
        })

        window.postMessage({
          type: 'openPreview',
          folder: key.replace('.pdf', ''),
          pngs: list.pngs
        }, '*')
        console.log('📤 postMessage 已发出，origin=*', Date.now())

        refreshPreview()   // ⬅ 成功也调用
        visible.value = false
        // progressVisible.value = false
        return { ok: true, pngs: list.pngs, folder: key.replace('.pdf', '') }
      } else {
        ElMessage.error('转图失败：' + msg.value)
        return { ok: false }
      }
    } catch (e) {
      ElMessage.error('请求失败：' + (e.response?.data?.error || e.message))
      return { ok: false }
    } finally {
      loadingObj.value[key] = false
      delete loadingObj.value[key]
    }
  }

  async function poll(jobId) {
    return new Promise((resolve) => {
      const timer = setInterval(async () => {
        try {
          const { data } = await getProgress(jobId)
          percent.value = data.percent
          if (data.percent === 100) {
            status.value = 'success'
            msg.value = '转图完成，正在加载预览...'
            clearInterval(timer)
            resolve()
          } else if (data.percent < 0) {
            status.value = 'exception'
            msg.value = data.error || '未知错误'
            clearInterval(timer)
            resolve()
          } else {
            msg.value = `正在转换第 ${data.finished} / ${data.total} 页...`
          }
        } catch {
          status.value = 'exception'
          msg.value = '获取进度失败'
          clearInterval(timer)
          resolve()
        }
      }, 500)
    })
  }

  return { convert }
}