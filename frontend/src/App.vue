<template>
  <div class="app-container">
    <div class="file-panel">
      <el-upload
        class="upload-area"
        action="http://118.25.92.108:5000/upload"
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
              :src="`http://118.25.92.108:5000/file/${fileItem.filename}`"
              width="100%"
              height="700px"
              frameborder="0"
            ></iframe>
          </div>
          <el-image
            v-else
            :src="`http://118.25.92.108:5000/file/${fileItem.filename}`"
            :preview-src-list="[`http://118.25.92.108:5000/file/${fileItem.filename}`]"
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
                  size="mini"
                  icon="el-icon-delete"
                  @click="deleteFile(fileItem.filename)"
                >删除</el-button>

                <el-button
                  size="mini"
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
                  <div
                    v-for="(img, idx) in cutResults[fileItem.filename]"
                    :key="idx"
                    style="margin-bottom: 8px"
                  >
                    <img :src="'data:image/png;base64,' + img" width="100%" />
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>





        </div>
      </div>
    </div>

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

export default {
  components: {
    QuillEditor
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
        placeholder: '请输入内容...',
        theme: 'snow'
      }
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
        const res = await axios.get('http://118.25.92.108:5000/files')
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
        const res = await axios.get('http://118.25.92.108:5000/text')
        this.content = res.data.content || res.data.text || '';
      } catch (error) {
        console.error('加载文本失败:', error)
      }
    },
    async saveText() {
      try {
        await axios.post('http://118.25.92.108:5000/text', { content: this.content })
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
        await axios.delete(`http://118.25.92.108:5000/file/${filename}`)
        this.$message.success('删除成功')
        this.loadFiles()   // 刷新列表
      } catch (e) {
        if (e !== 'cancel') {
          console.error('删除失败:', e)
          this.$message.error('删除失败')
        }
      }
    },




    /* 图表切割 */
    async cutTable(filename) {
      if (this.isPDF(filename)) return
      this.$set(this.cutLoading, filename, true)

      try {
        const res = await axios.get(
          `http://118.25.92.108:5000/file/${filename}`,
          { responseType: 'blob' }
        )
        const reader = new FileReader()
        reader.onload = async () => {
          const base64 = reader.result
          const cutRes = await axios.post(
            'http://118.25.92.108:5000/cut-table',
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
</style>
