<template>
  <div class="app-container">
    <div class="file-panel">
      <el-upload
        class="upload-area"
        action="http://127.0.0.1:5000/upload"
        :show-file-list="false"
        :on-success="loadFiles"
        :before-upload="beforeUpload"
        drag
      >
        <i class="el-icon-upload"></i>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">只能上传PDF/图片文件</div>
        </template>
      </el-upload>

      <div class="file-list">
        <div v-for="fileItem in files" :key="fileItem.id" class="file-item">
          <!-- 预览区域 -->
          <div v-if="isPDF(fileItem.filename)" class="pdf-container">
            <iframe
              :src="`http://127.0.0.1:5000/file/${fileItem.filename}`"
              width="100%"
              height="700px"
              frameborder="0"
            ></iframe>
          </div>

          <el-image
            v-else
            :src="`http://127.0.0.1:5000/file/${fileItem.filename}`"
            :preview-src-list="[`http://127.0.0.1:5000/file/${fileItem.filename}`]"
            fit="contain"
            style="max-height: 500px; width: 100%;"
          />

          <!-- 文件信息 + 操作按钮 -->
            <div class="file-meta">
              <div class="file-name">{{ fileItem.filename }}</div>
              <div class="file-date">上传于：{{ formatDate(fileItem.created_at) }}</div>

              <!-- 通用操作：删除 + 切割（每个文件都有） -->
              <div style="margin-top: 8px;">
                <el-button
                  type="danger"
                  size="small"
                  icon="el-icon-delete"
                  @click="deleteFile(fileItem.filename)"
                >删除</el-button>

                <el-button
                  size="small"
                  type="primary"
                  icon="el-icon-crop"
                  @click="cutTable(fileItem.filename)"
                  :loading="cutLoading && !!cutLoading[fileItem.filename]"
                  style="margin-left: 8px;"
                >图表切割</el-button>
              </div>

              <!-- 切割结果（有就展示） -->
            <el-collapse
              v-if="cutResults && cutResults[fileItem.filename]"
              style="margin-top: 10px"
            >
              <el-collapse-item title="查看切割子图">
                <!-- 滚动容器 -->
                <div style="max-height: 360px; overflow-y: auto;">
                  <div
                    v-for="(img, idx) in cutResults[fileItem.filename]"
                    :key="idx"
                    class="cut-sub-box"
                  >
                    <!-- 图片 -->
                    <img :src="subSrc(fileItem.filename, idx)" width="100%" />
                    <!-- 悬浮按钮 -->
                    <div class="sub-tool">
                      <el-button
                        size="mini"
                        type="primary"
                        icon="el-icon-check"
                        @click="rotateSub(fileItem.filename, idx)"
                      >保存旋转</el-button>
                    </div>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>

            </div>


          <!-- 新增 -->
          <el-button
            v-if="isPDF(fileItem.filename)"
            size="small"
            type="success"
            icon="el-icon-picture"
            @click="convertAndPreview(fileItem.filename)"
            :loading="!!convertingObj[fileItem.filename]"
          >转图并预览</el-button>

          <!-- 进度条弹窗 -->
          <el-dialog
            v-model="progressVisible"
            title="转图进度"
            width="400px"
            :close-on-click-modal="false"
            :show-close="false"
          >
            <div style="text-align:center">
              <el-progress
                :percentage="progressPercent"
                :status="progressStatus"
                :stroke-width="12"
              />
              <div style="margin-top:10px;color:#999">{{ progressMsg }}</div>
            </div>
          </el-dialog>

        </div>
      </div>
    </div>

    <!-- 分页预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      title="PDF 分页预览"
      width="85vw"
      top="5vh"
      :close-on-click-modal="false"
    >
      <!-- 缩略图列表 -->
      <div style="height:70vh;overflow-y:auto;">
        <img
          v-for="(p,idx) in previewPngs"
          :key="p"
          :src="`http://127.0.0.1:5000/api/png/${previewFolder}/${p}`"
          fit="contain"
          style="width:100%;margin-bottom:10px;cursor:zoom-in"
          @click="openPagePreview(idx)"
        />
      </div>
    </el-dialog>

    <!-- 自己可控的图片预览弹窗（代替 el-image-viewer） -->


    <div class="editor-panel">
      <div class="editor-container">
        <quill-editor
          v-model:content="content"
          :options="editorOptions"
          contentType="html"
        />
      </div>
      <el-button type="primary" @click="saveText" class="save-btn">保存</el-button>
    </div>
  </div>
</template>





<script>
import axios from 'axios'
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css'

// ✅ 统一设置后端基地址
// axios.defaults.baseURL = 'http://127.0.0.1:12345/api/v1'

export default {
  components: {
    QuillEditor
  },
  computed: {
  convertingObj() {
    // 把响应式对象原样返回即可，Vue3 能追踪
    return this.converting || {}
  }
},
  data() {
    return {
      files: [],
      content: '',
      editorOptions: {
        modules: {
          toolbar: [
            ['bold', 'italic', 'underline', 'strike'],
            ['blockquote', 'code-block'],
            [{ 'header': 1 }, { 'header': 2 }],
            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
            [{ 'script': 'sub'}, { 'script': 'super' }],
            [{ 'indent': '-1'}, { 'indent': '+1' }],
            [{ 'direction': 'rtl' }],
            [{ 'size': ['small', false, 'large', 'huge'] }],
            [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
            [{ 'color': [] }, { 'background': [] }],
            [{ 'font': [] }],
            [{ 'align': [] }],
            ['clean'],
            ['link', 'image', 'video']
          ]
        },
        cutRotateTs: {},   // pdfFolder_pngName -> 当前角度
        innerPreviewVisible: false,   // 自己预览弹窗
        innerPreviewIndex: 0,          // 当前大图索引
        innerPreviewVisible: false,   // 单张/连续大图弹窗
        innerPreviewIndex: 0,         // 当前页号
        innerPreviewUrls: [],         // 大图 url 列表
        placeholder: '请输入内容...',
        theme: 'snow'
      },

      cutLoading: {},
      cutResults: {},
      converting: {},
      previewVisible: false,
      previewFolder: '',
      previewPngs: [],

      /* ===== 进度相关 ===== */
      progressVisible: false,
      progressPercent: 0,
      progressStatus: '',  // '' | success | exception
      progressMsg: '',
      jobId: ''

    }
  },
  mounted() {
    this.loadFiles()
    this.loadText()
  },
  methods: {
    formatDate(timestamp) {
      if (!timestamp) return '未知时间';
      const date = new Date(timestamp);
      return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    },


    beforeUpload(file) {
      const isAllowed = ['pdf', 'png', 'jpg', 'jpeg', 'gif'].some(ext =>
        file.name.toLowerCase().endsWith(`.${ext}`)
      )
      if (!isAllowed) {
        this.$message.error('只能上传PDF或图片文件!')
      }
      return isAllowed
    },
    isPDF(name) {
      return name && name.toLowerCase().endsWith('.pdf')
    },

    async loadFiles() {
      try {
        const res = await axios.get('http://127.0.0.1:5000/files')
        if (Array.isArray(res.data)) {
          this.files = res.data.map(item => {
            return {
              id: item.id,
              filename: item.filename || item.name || '',
              file_type: item.file_type || this.getFileType(item.filename),
              created_at: item.created_at
            }
          });
        } else {
          console.error('文件格式错误:', res.data)
          this.files = [];
        }
      } catch (error) {
        console.error('加载文件列表失败:', error)
        this.$message.error('加载文件失败')
      }
    },
    getFileType(filename) {
      if (!filename) return '';
      const ext = filename.split('.').pop().toLowerCase();
      if (ext === 'pdf') return 'pdf';
      return ['png', 'jpg', 'jpeg', 'gif'].includes(ext) ? 'image' : 'unknown';
    },

    async loadText() {
      try {
        const res = await axios.get('http://127.0.0.1:5000/text')
        this.content = res.data.content || res.data.text || '';
      } catch (error) {
        console.error('加载文本失败:', error)
      }
    },
    async saveText() {
      try {
        await axios.post('http://127.0.0.1:5000/text', { content: this.content })
        this.$message.success("保存成功")
      } catch (error) {
        console.error('保存文本失败:', error)
        this.$message.error("保存失败")
      }
    },

    async deleteFile(filename) {
      try {
        await this.$confirm('确定删除该文件？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        await axios.delete(`http://127.0.0.1:5000/file/${filename}`)
        this.$message.success('删除成功')
        this.loadFiles()   // 刷新列表
      } catch (e) {
        if (e !== 'cancel') {
          console.error('删除失败:', e)
          this.$message.error('删除失败')
        }
      }
    },

    /* 打开指定页的大图预览 */
    openPagePreview(idx) {
      this.innerPreviewIndex = idx
      this.innerPreviewVisible = true
    },


    /* 构造子图 url + 时间戳 */
    subSrc(filename, idx) {
      const ts = this.cutRotateTs[`${filename}_${idx}`] || 0
      // 子图我们统一用 folder = filename 无后缀
      const folder = filename.replace(/\.[^.]+$/, '')
      const pngName = `slice_${idx}.png`   // 你后端切割时起的名字，保持一致即可
      return `http://127.0.0.1:5000/api/png/${folder}/${pngName}?t=${ts}`
    },

    /* 旋转并保存 */
    async rotateSub(filename, idx) {
      const base64 = this.cutResults[filename][idx]          // 当前 base64
      const folder = filename.replace(/\.[^.]+$/, '')
      const pngName = `slice_${idx}.png`

      try {
        await axios.post(
          `http://127.0.0.1:5000/api/save-rotated-sub/${folder}/${pngName}`,
          { image: base64 },
          { headers: { 'Content-Type': 'application/json' } }
        )
        this.$message.success('已旋转并保存')
        // 更新时间戳强制刷新
        this.$set(this.cutRotateTs, `${filename}_${idx}`, Date.now())
      } catch (e) {
        this.$message.error('保存失败：' + (e.response?.data?.error || e.message))
      }
    },


    // 把服务器上的文件再拉成 Blob
    async fetchFileBlob(filename) {
      const res = await axios.get(
        `http://127.0.0.1:5000/file/${filename}`,
        { responseType: 'blob' }
      )
      return res.data
    },



    /*******************************
   * 带实时进度的 PDF→PNG
       *******************************/
      async convertAndPreview(pdfName) {
          this.converting[pdfName] = true
          this.progressVisible = true
          this.progressPercent = 0
          this.progressStatus = ''
          this.progressMsg = '正在提交任务...'

          try {
            // 1. 提交异步任务（去掉空格）
            const { data } = await axios.post(
              `http://127.0.0.1:5000/api/convert-pdf-async/${pdfName}`
            )

            // 命中缓存，直接展示
            if (data.hitCache) {
              this.previewFolder = pdfName.replace(/\.pdf$/i, '')
              this.previewPngs   = data.pngs
              this.progressVisible = false
              this.previewVisible  = true
              this.converting[pdfName] = false
              delete this.converting[pdfName]
              return
            }

            this.jobId = data.jobId
            this.progressMsg = '任务已提交，正在转图...'

            // 2. 轮询进度
            await this.pollProgress()
            if (this.progressStatus === 'success') {
              this.$message.success('转图完成！')
              // 3. 拉 PNG 列表（同样去掉空格）
              const { data: list } = await axios.get(
                `http://127.0.0.1:5000/api/png-list/${pdfName.replace(/\.pdf$/i, '')}`
              )
              this.previewFolder = pdfName.replace(/\.pdf$/i, '')
              this.previewPngs   = list.pngs
              this.progressVisible = false
              this.previewVisible  = true
            } else if (this.progressStatus === 'exception') {
              this.$message.error('转图失败：' + this.progressMsg)
            }
          } catch (e) {
            this.$message.error('请求失败：' + (e.response?.data?.error || e.message))
          } finally {
            // 防止 hitCache 提前 return 导致按钮状态没复位
            this.converting[pdfName] = false
            delete this.converting[pdfName]
          }
        },

      /*******************************
       * 轮询进度，直到 100 或失败
       *******************************/
      pollProgress() {
        return new Promise((resolve) => {
          const timer = setInterval(async () => {
            try {
              const { data } = await axios.get(`http://127.0.0.1:5000/api/progress/${this.jobId}`)
              const p = data.percent
              this.progressPercent = p
              if (p === 100) {
                this.progressStatus = 'success'
                this.progressMsg = '转图完成，正在加载预览...'
                clearInterval(timer)
                resolve()
              } else if (p < 0) {
                this.progressStatus = 'exception'
                this.progressMsg = data.error || '未知错误'
                clearInterval(timer)
                resolve()
              } else {
                this.progressMsg = `正在转换第 ${data.finished} / ${data.total} 页...`
              }
            } catch (e) {
              this.progressStatus = 'exception'
              this.progressMsg = '获取进度失败'
              clearInterval(timer)
              resolve()
            }
          }, 500)
        })
      },


    /* 图表切割 */
    async cutTable(filename) {
      if (this.isPDF(filename)) return
      this.$set(this.cutLoading, filename, true)

      try {
        const res = await axios.get(
          `http://127.0.0.1:5000/file/${filename}`,
          { responseType: 'blob' }
        )
        const reader = new FileReader()
        reader.onload = async () => {
          const base64 = reader.result
          const cutRes = await axios.post(
            'http://127.0.0.1:5000/cut-table',
            { image: base64 }
          )
          this.$set(this.cutResults, filename, cutRes.data.slices)
        }
        reader.readAsDataURL(res.data)
      } catch (e) {
        console.error('切割失败:', e)
        this.$message.error('切割失败')
      } finally {
        this.$set(this.cutLoading, filename, false)
      }
    }


  }
}
</script>

<style>
.app-container {
  display: flex;
  height: 100vh;
  width: 100%;
}

.file-panel {
  flex: 1;
  padding: 20px;
  border-right: 1px solid #e6e6e6;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.upload-area {
  margin-bottom: 20px;
}

.file-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 10px;
  max-height: calc(100vh - 170px);
}

.file-item {
  margin-bottom: 20px;
  border: 1px solid #eee;
  padding: 10px;
  border-radius: 4px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.file-meta {
  margin-top: 10px;
  text-align: center;
}

.file-name {
  color: #333;
  font-weight: bold;
}

.file-date {
  color: #888;
  font-size: 12px;
}

.editor-panel {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.editor-container {
  flex: 1;
  margin-bottom: 20px;
  height: calc(100% - 60px);
}

.save-btn {
  align-self: flex-end;
  margin-top: 20px;
}

.pdf-container {
  width: 100%;
  height: 700px;
  border: 1px solid #eee;
}

@media (max-width: 1200px) {
  .app-container {
    flex-direction: column;
  }
  .file-panel, .editor-panel {
    flex: none;
    height: 50vh;
  }
}



/* 保存按钮：悬浮在图片上方 */
.sub-tool {
  position: absolute;
  right: 10px;
  bottom: 10px;
  z-index: 9999;        /* 高于任何 img */
  pointer-events: auto;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 4px;
  padding: 4px 6px;
}


/* 单张子图包裹 */
.cut-sub-box {
  position: relative;   /* 关键：建立层叠上下文 */
  margin-bottom: 12px;
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 6px;
  background: #fafafa;
}

</style>







<!-- 外层容器添加相对定位，确保按钮定位基准 -->
  <div style="position: relative; height:70vh; overflow-y:auto;">
    <div v-for="p in previewPngs" :key="p" style="margin-bottom:10px; position:relative; text-align:center;">
      <!-- 仅保留保存按钮，并调整到图片右侧中间位置 -->
      <div style="position: absolute; right: -5px; top: 50%; transform: translateY(-50%); z-index: 10;">
        <!-- 保存按钮：绿色背景 + 💾 符号 -->
        <el-button
          size="medium"
          @click.stop="saveRotatedImage(p)"
          :loading="saveLoading[p]"
          circle
          style="background: #52c41a; color: white; border: none;"
          title="保存旋转状态"
        >
          💾
        </el-button>
      </div>

      <!-- 图片展示（限制最大高度，确保完整显示） -->
      <el-image
        :src="`http://127.0.0.1:5000/api/png/${previewFolder}/${p}`"
        fit="contain"
        style="
          max-width: 200%;
          max-height: 500px;
          margin-bottom: 10px;
          margin-right: 30px; /* 右侧预留按钮空间，避免图片被按钮遮挡 */
        "
        :preview-src-list="previewPngs.map(n=>`http://127.0.0.1:5000/api/png/${previewFolder}/${n}`)"
        :style="{ transform: `rotate(${imageRotation[p] || 0}deg)` }"
      ></el-image>
    </div>
  </div>
</el-dialog>





   <!-- 分页预览弹窗 -->
<el-dialog
  v-model="previewVisible"
  title="PDF 分页预览"
  width="85vw"
  top="5vh"
  :close-on-click-modal="false"
  @open="resetAllRotation"
>
  <div style="position: relative; height:70vh; overflow-y:auto;">
    <div v-for="p in previewPngs" :key="p" style="margin-bottom:10px; position:relative; text-align:center;">
      <!-- 旋转按钮组 -->
      <div style="position: absolute; top: 10px; right: 10px; z-index: 10; display: flex; gap: 5px;">
        <!-- 左旋按钮 -->
        <el-button
          size="mini"
          @click.stop="rotateCurrentImage(p, -90)"
          circle
          style="background: #1890ff; color: white; border: none;"
          title="向左旋转90度"
        >
          ↺
        </el-button>

        <!-- 右旋按钮 -->
        <el-button
          size="mini"
          @click.stop="rotateCurrentImage(p, 90)"
          circle
          style="background: #fa8c16; color: white; border: none;"
          title="向右旋转90度"
        >
          ↻
        </el-button>

        <!-- 保存按钮 -->
        <el-button
          size="mini"
          @click.stop="saveRotatedImage(p)"
          :loading="saveLoading[p]"
          circle
          style="background: #52c41a; color: white; border: none;"
          title="保存旋转状态"
        >
          💾
        </el-button>
      </div>

      <!-- 图片展示 -->
      <el-image
        :src="`http://127.0.0.1:5000/api/png/${previewFolder}/${p}`"
        fit="contain"
        style="max-width: 100%; max-height: 500px; margin-bottom: 10px;"
        :preview-src-list="previewPngs.map(n => `http://127.0.0.1:5000/api/png/${previewFolder}/${n}`)"
        :style="{ transform: `rotate(${imageRotation[p] || 0}deg)` }"
      ></el-image>
    </div>
  </div>
</el-dialog>




<!-- 单页图片 -->
      <el-image
        :src="`http://127.0.0.1:5000/api/png/${previewFolder}/${p}?t=${refreshTimestamp}`"
        fit="contain"
        style="max-width:100%; max-height:500px; margin-bottom:10px;"
        :preview-src-list="previewPngs.map(n=>`http://127.0.0.1:5000/api/png/${previewFolder}/${n}?t=${refreshTimestamp}`)"
        :style="{ transform: `rotate(${imageRotation[p] || 0}deg)` }"
      />



<!-- 单页图片 -->
    <el-image
      :src="`http://127.0.0.1:5000/api/png/${previewFolder}/${p}?t=${refreshTimestamp}`"
      fit="contain"
      style="max-width:100%; max-height:500px; margin-bottom:10px; cursor:pointer"
      :style="{ transform: `rotate(${imageRotation[p] || 0}deg)` }"
      @click="openPreview(idx)"
    ></el-image>


<!-- 单页图片 -->
      <el-image
        :src="`http://127.0.0.1:5000/api/png/${previewFolder}/${p}?t=${refreshTimestamp}`"
        fit="contain"
        style="max-width:100%; max-height:500px; margin-bottom:10px;"
        :preview-src-list="previewPngs.map(n=>`http://127.0.0.1:5000/api/png/${previewFolder}/${n}?t=${refreshTimestamp}`)"
        :style="{ transform: `rotate(${imageRotation[p] || 0}deg)` }"
      />



<el-input
        v-model="jumpPage"
        type="number"
        :min="1"
        :max="previewPngs.length"
        style="width:90px; margin-right:6px;"
        size="small"
        @keyup.enter="jumpToPage"
      />
