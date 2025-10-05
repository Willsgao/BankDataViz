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
          <div class="file-meta">
            <div class="file-name">{{ fileItem.filename }}</div>
            <div class="file-date">上传于：{{ formatDate(fileItem.created_at) }}</div>
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
