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


                <el-button
                  v-if="isPDF(fileItem.filename) && convertCache[fileItem.disk_name]"
                  size="small"
                  type="primary"
                  icon="el-icon-crop"
                  @click="cutTablesForPDF(fileItem.disk_name)"
                >批量切表格</el-button>

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




          <!-- 文件卡片里展示中文文件名 -->
          <div class="file-meta">
            <div class="file-name">{{ fileItem.filename }}</div>
            <!-- 其余信息 -->
          </div>


          <!-- 新增 -->
          <el-button
            v-if="isPDF(fileItem.filename)"
            size="small"
            type="success"
            icon="el-icon-picture"
            @click="convertAndPreview(fileItem.disk_name)"
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



    <!-- PDF 分页预览弹窗 -->
<el-dialog
  v-model="previewVisible"
  title="PDF 分页预览"
  width="85vw"
  top="5vh"
  :close-on-click-modal="false"
>
  <!-- 标题栏右侧刷新按钮 -->
  <template #header>
    <div style="display:flex;align-items:center;justify-content:space-between;">
      <span>PDF 分页预览</span>
      <el-button
        size="small"
        circle
        icon="el-icon-refresh"
        title="刷新并重载图片"
        @click="refreshPreview"
      >
      ↺
      </el-button>

    </div>
  </template>


  <!-- 新增：页码跳转栏 -->
<div style="display:flex; align-items:center; justify-content:center; margin-bottom:10px; gap:6px;">
  <span>跳转到第</span>
  <el-input
    v-model.number="jumpPage"
    type="number"
    :min="1"
    :max="previewPngs.length"
    style="width:80px"
    size="small"
    @keyup.enter="jumpToPage"
  />
  <span>页</span>
  <el-button type="primary" size="small" @click="jumpToPage">跳转</el-button>
</div>

  <!-- 图片列表容器 -->
  <div style="position:relative; height:70vh; overflow-y:auto;">
    <div
      v-for="p in previewPngs"
      :key="p"
      style="margin-bottom:10px; position:relative; text-align:center;"
    >
      <!-- 旋转/保存按钮组 -->
      <div
        style="position:absolute; top:10px; right:10px; z-index:10; display:flex; gap:5px;"
      >
        <el-button
          size="small"
          circle
          style="background:#1890ff; color:white; border:none;"
          title="向左旋转90度"
          @click.stop="rotateImage(p, -90)"
        >
          ↺
        </el-button>

        <el-button
          size="small"
          circle
          style="background:#fa8c16; color:white; border:none;"
          title="向右旋转90度"
          @click.stop="rotateImage(p, 90)"
        >
          ↻
        </el-button>

        <el-button
          size="small"
          circle
          style="background:#52c41a; color:white; border:none;"
          title="保存旋转状态"
          :loading="!!saveLoading[p]"
          @click.stop="saveRotatedImage(p)"
        >
          💾
        </el-button>
      </div>



      <!-- 单页图片 -->
    <el-image
      :src="`http://127.0.0.1:5000/api/png/${previewFolder}/${p}?t=${refreshTimestamp}`"
      fit="contain"
      style="max-width:100%; max-height:500px; margin-bottom:4px;"
      :preview-src-list="previewPngs.map(n=>`http://127.0.0.1:5000/api/png/${previewFolder}/${n}?t=${refreshTimestamp}`)"
      :style="{ transform: `rotate(${imageRotation[p] || 0}deg)` }"
    />

    <!-- 新增：跳转控制器 -->
    <div style="text-align:center; margin-bottom:10px;">
      <el-input
          v-model="jumpPage"
          type="number"
          style="width:90px; margin-right:6px;"
          size="small"
          @keyup.enter="jumpToPage"
        />
      <el-button type="primary" size="small" @click="jumpToPage">跳转</el-button>
    </div>


    </div>
  </div>
</el-dialog>

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
        placeholder: '请输入内容...',
        theme: 'snow'
      },

      cutLoading: {},
      cutResults: {},
      converting: {},
      previewVisible: false,
      previewFolder: '',
      previewPngs: [],

      // 保留原有所有数据，仅新增以下两个旋转相关变量
      imageRotation: {},  // 存储图片旋转角度（不影响原有预览）
      saveLoading: {},    // 保存按钮加载状态（不影响原有预览）
      refreshTimestamp: Date.now(), // 强制刷新用
      convertCache: {},       // 转图缓存 { pdfName: [pngName,...] }
      jumpPage: '1',   // 或 1，不要是 ref、computed、getter

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

    /* 新增：打开分页预览 */
  openPagePreview(filename) {
    this.previewPdf = filename;
    this.showPagePreview = true;
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
          this.files = res.data.map(item => ({
            id: item.id,
            filename: item.filename || item.name || '',
            disk_name: item.disk_name,          // ← 新增
            file_type: item.file_type || this.getFileType(item.filename),
            created_at: item.created_at
          }));
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


    // 把服务器上的文件再拉成 Blob
    async fetchFileBlob(filename) {
      const res = await axios.get(
        `http://127.0.0.1:5000/file/${filename}`,
        { responseType: 'blob' }
      )
      return res.data
    },

    openPreview(startIndex) {
  this.viewerUrls = this.previewPngs.map(p =>
    `http://127.0.0.1:5000/api/png/${this.previewFolder}/${p}?t=${this.refreshTimestamp}`
  );
  this.viewerIndex = startIndex;   // 从被点那张开始
  this.showViewer = true;
},


    /*******************************
   * 带实时进度的 PDF→PNG
       *******************************/
     async convertAndPreview(pdfName) {
  const cacheKey = pdfName;          // 缓存 key

  /* ---------- 0. 按钮 loading ---------- */
  this.converting[pdfName] = true;   // Vue3 无需 $set
  this.progressVisible = true;
  this.progressPercent = 0;
  this.progressStatus = '';
  this.progressMsg = '正在检查缓存...';

  /* ---------- 1. 缓存命中 ---------- */
  if (this.convertCache[cacheKey]) {
    this.previewFolder = pdfName.replace(/\.pdf$/i, '');
    this.previewPngs = this.convertCache[cacheKey];
    this.progressVisible = false;
    this.previewVisible = true;
    this.converting[pdfName] = false;
    delete this.converting[pdfName];
    return;
  }

  /* ---------- 2. 缓存未命中 → 原异步流程 ---------- */
  try {
    this.progressMsg = '正在提交任务...';
    // 2.1 提交异步任务（URL 去掉空格）
    const { data } = await axios.post(
      `http://127.0.0.1:5000/api/convert-pdf-async/${pdfName}`
    );

    // 2.2 后端返回“已缓存”也直接展示
    if (data.hitCache) {
      this.convertCache[cacheKey] = data.pngs; // 写缓存
      this.previewFolder = pdfName.replace(/\.pdf$/i, '');
      this.previewPngs = data.pngs;
      this.progressVisible = false;
      this.previewVisible = true;
      this.converting[pdfName] = false;
      delete this.converting[pdfName];
      return;
    }

    // 2.3 轮询进度
    this.jobId = data.jobId;
    this.progressMsg = '任务已提交，正在转图...';
    await this.pollProgress();

    if (this.progressStatus === 'success') {
      this.$message.success('转图完成！');
      // 2.4 拉 PNG 列表（URL 去掉空格）
      const { data: list } = await axios.get(
        `http://127.0.0.1:5000/api/png-list/${pdfName.replace(/\.pdf$/i, '')}`
      );
      this.convertCache[cacheKey] = list.pngs; // 写缓存
      this.previewFolder = pdfName.replace(/\.pdf$/i, '');
      this.previewPngs = list.pngs;
      this.progressVisible = false;
      this.previewVisible = true;
    } else if (this.progressStatus === 'exception') {
      this.$message.error('转图失败：' + this.progressMsg);
    }
  } catch (e) {
    this.$message.error('请求失败：' + (e.response?.data?.error || e.message));
  } finally {
    this.converting[pdfName] = false;   // 复位
    delete this.converting[pdfName];
  }
},


  /* 对 PDF 转图完成后的 PNG 批量做版面检测 + 裁切 */
async cutTablesForPDF(pdfDiskName) {
  // pdfDiskName 是 UUID.pdf
  const folder = pdfDiskName.replace(/\.pdf$/i, '')          // 去掉扩展名
  try {
    // 1. 先拿 PNG 列表
    const { data: list } = await axios.get(
      `/api/png-list/${folder}`
    )
    if (!list.pngs.length) {
      this.$message.info('暂无分页图片')
      return
    }
    // 2. 依次对每张 PNG 调 /api/layout + /cut-table
    const allSlices = []
    for (const png of list.pngs) {
      const { data: lay } = await axios.get(`/api/layout/${folder}/${png}`)
      if (!lay.table_zones.length) continue
      // 拉这张图转 base64
      const blob = await axios.get(`/api/png/${folder}/${png}`, {
        responseType: 'blob'
      }).then(r => r.data)
      const base64 = await new Promise(res => {
        const rd = new FileReader()
        rd.onloadend = () => res(rd.result)
        rd.readAsDataURL(blob)
      })
      // 带坐标裁切
      const { data: cut } = await axios.post('/cut-table', {
        image: base64,
        zones: lay.table_zones
      })
      allSlices.push(...cut.slices)
    }
    // 3. 统一展示
    this.$set(this.cutResults, pdfDiskName, allSlices)
    this.$message.success(`共裁切 ${allSlices.length} 个表格区域`)
  } catch (e) {
    this.$message.error('批量切表失败：' + (e.response?.data?.error || e.message))
  }
},


 /* 跳转到指定页（1 起算） */
  jumpToPage() {
    const page = Number(this.jumpPage);
    if (!page || page < 1 || page > this.previewPngs.length) return;

    const idx = page - 1;   // 转成 0 起算下标

    /* 如果 viewer 还没打开，先点第一张图让它出来 */
    if (!document.querySelector('.el-image-viewer')) {
      const firstImg = this.$refs.firstImg?.$el;
      if (firstImg) firstImg.click();
      /* 等弹窗挂载完再跳页 */
      const wait = setInterval(() => {
        const vm = document.querySelector('.el-image-viewer')?.__vueParentComponent?.proxy;
        if (vm) {
          clearInterval(wait);
          this.doJump(idx);   // 立即切页
        }
      }, 100);
      return;
    }

    /* 弹窗已存在，直接跳 */
    this.doJump(idx);
  },

  /* 真正切页（0 起算） */
  doJump(idx) {
    this.$nextTick(() => {
      const vm = document
        .querySelector('.el-image-viewer')
        ?.__vueParentComponent?.proxy;
      if (!vm) return;
      /* 新版 Element Plus 用 activeIndex */
      if (typeof vm.activeIndex === 'number') {
        vm.activeIndex = idx;
      } else {
        vm.setActiveItem?.(idx);
      }
    });
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


      rotateImage(pngName, angle) {
    console.log('rotate key:', pngName, 'old angle:', this.imageRotation[pngName] || 0);
    this.imageRotation[pngName] = (this.imageRotation[pngName] || 0) + angle;
},

  /* 保存旋转角度到后端 */
  async saveRotatedImage(pngName) {
    this.saveLoading[pngName] = true;
    try {
      const angle = this.imageRotation[pngName] || 0;
      if (angle === 0) {
        this.$message.info('未进行旋转，无需保存');
        return;
      }
      await axios.post(
        `http://127.0.0.1:5000/api/png/rotate/${this.previewFolder}/${pngName}`,
        { angle }
      );
      this.$message.success('旋转已保存');
      // 保存成功后重置本地角度
      this.imageRotation[pngName] = 0;
      // 可选：重新加载图片
      this.refreshTimestamp = Date.now();
    } catch (e) {
      console.error('保存旋转失败:', e);
      this.$message.error('保存旋转失败');
    } finally {
      this.saveLoading[pngName] = false;
    }
  },

  /* 刷新按钮：清缓存 + 重载图片 */
  refreshPreview() {
    // 1. 清旋转缓存
    Object.keys(this.imageRotation).forEach(k => {
      delete this.imageRotation[k];
    });
    // 2. 清转图缓存（当前 PDF）
    const cacheKey = this.previewFolder + '.pdf';
    if (this.convertCache[cacheKey]) {
      delete this.convertCache[cacheKey];
    }
    // 3. 强制重新加载图片
    this.refreshTimestamp = Date.now();
  },




    /* 图表切割 */
    /* 图表切割：先版面检测，再按表格区域裁切 */
    async cutTable(filename) {
    console.log('① 进入 cutTable，文件名：', filename)
      if (this.isPDF(filename)) return;
      this.$set(this.cutLoading, filename, true);

      try {
        /* 1. 版面检测拿表格坐标 */
        const folder = filename.replace(/\.(png|jpe?g|gif)$/i, '');
        const { data } = await axios.get(
          `http://127.0.0.1:5000/api/layout/${folder}/${filename}`
        );
        const zones = data.table_zones || [];
        if (!zones.length) {
          this.$message.info('未检测到表格区域');
          return;
        }

        /* 2. 取图转 base64 */
        const res = await axios.get(
          `http://127.0.0.1:5000/file/${filename}`,   // ← 去掉空格
          { responseType: 'blob' }
        );
        console.log('② 准备请求 layout:', res)
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result);
          reader.onerror = reject;
          reader.readAsDataURL(res.data);
        });

        /* 3. 带坐标裁切 */
        const cutRes = await axios.post(
          'http://127.0.0.1:5000/cut-table',         // ← 去掉空格
          { image: base64, zones }                   // ← 把 zones 带上
        );
        this.$set(this.cutResults, filename, cutRes.data.slices);
        this.$message.success(`已裁切 ${zones.length} 个表格`);
      } catch (e) {
        console.error('切割失败:', e);
        this.$message.error('切割失败：' + (e.response?.data?.error || e.message));
      } finally {
        this.$set(this.cutLoading, filename, false);
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
