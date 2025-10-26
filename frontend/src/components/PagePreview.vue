
<template>
  <div class="page-preview">
    <!-- 左侧 PDF -->
    <div class="pdf-pane">
      <iframe
        :src="pdfUrl"
        width="100%"
        height="100%"
        frameborder="0"
        @load="onPdfLoad"
        ref="pdfIframe"
      ></iframe>
    </div>

    <!-- 右侧当前页 PNG -->
    <div class="png-pane">
      <div class="nav-bar">
        <span>第 {{ currentPage }} / {{ totalPages }} 页</span>
        <el-button size="mini" @click="$emit('close')">关闭</el-button>
      </div>
      <img
        v-if="pngUrl"
        :src="pngUrl"
        style="width: 100%; box-shadow: 0 0 8px rgba(0,0,0,.2)"
      />
      <div v-else class="placeholder">滚动 PDF 查看对应 PNG</div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  props: {
    pdfName: String,                     // 514001.pdf
  },
  data() {
    return {
      totalPages: 0,
      pngs: [],        // ["514001_001.png", ...]
      currentPage: 1,
      observer: null,
    }
  },
  computed: {
    pdfUrl() {
      return `http://127.0.0.1:5000/file/${this.pdfName}`
    },
    pngUrl() {
      if (!this.pngs.length) return ''
      const png = this.pngs[this.currentPage - 1]
      return `http://127.0.0.1:5000/png/${this.pdfName.replace('.pdf','')}/${png}`
    },
  },
  async mounted() {
    const { data } = await axios.get(`/pages/${this.pdfName.replace('.pdf','')}`)
    this.totalPages = data.total
    this.pngs = data.pngs
    this.$nextTick(this.listenScroll)
  },
  beforeDestroy() {
    this.observer?.disconnect()
  },
  methods: {
    onPdfLoad() {
      // PDF 加载完成后注入滚动监听脚本
      const iframe = this.$refs.pdfIframe
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document
        this.observer = new doc.defaultView.IntersectionObserver(
          (entries) => {
            entries.forEach(en => {
              if (en.isIntersecting) {
                // 简单策略：第 N 个可见页 => currentPage = N
                const idx = Array.from(doc.querySelectorAll('div.page'))
                  .findIndex(p => p === en.target)
                if (idx >= 0) this.currentPage = idx + 1
              }
            })
          },
          { root: doc.body, threshold: 0.5 }
        )
        doc.querySelectorAll('div.page').forEach(p => this.observer.observe(p))
      } catch (e) {
        // 跨域时无法访问 iframe 内容，降级方案：定时器 + 滚动高度估算
        let lastTop = 0
        const timer = setInterval(() => {
          try {
            const top = iframe.contentWindow?.pageYOffset || 0
            if (Math.abs(top - lastTop) > 5) {
              lastTop = top
              // 按页高估算
              const pageH = doc.body.scrollHeight / this.totalPages
              this.currentPage = Math.min(
                Math.ceil(top / pageH) || 1,
                this.totalPages
              )
            }
          } catch {
            clearInterval(timer)
          }
        }, 300)
      }
    },
  },
}
</script>

<style scoped>
.page-preview {
  display: flex;
  height: 100%;
}
.pdf-pane {
  flex: 1;
  border-right: 1px solid #e6e6e6;
}
.png-pane {
  width: 50%;
  padding: 16px;
  display: flex;
  flex-direction: column;
}
.nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}
</style>