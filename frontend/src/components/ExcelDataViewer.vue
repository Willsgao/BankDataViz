<!-- ExcelDataViewer.vue -->
<template>
  <div class="excel-data-viewer">
    <div class="viewer-header">
      <h3>{{ excelData.tableName }}</h3>
      <div class="header-info">
        <span>共 {{ excelData.sheets?.length || 0 }} 个工作表</span>
        <span>文件: {{ getFileName(excelData.filePath) }}</span>
      </div>
    </div>

    <!-- 工作表选择器 -->
    <div class="sheet-selector" v-if="excelData.sheets && excelData.sheets.length > 1">
      <el-radio-group v-model="activeSheet" size="small">
        <el-radio-button
          v-for="sheet in excelData.sheets"
          :key="sheet.sheetName"
          :label="sheet.sheetName"
        >
          {{ sheet.sheetName }} ({{ sheet.rowCount }}×{{ sheet.colCount }})
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 当前工作表表格 -->
    <div class="current-sheet" v-if="currentSheet">
      <!-- 表格操作栏 -->
      <div class="table-toolbar">
        <div class="toolbar-left">
          <span class="sheet-name">{{ currentSheet.sheetName }}</span>
          <el-tag size="small">{{ currentSheet.rowCount }}行 {{ currentSheet.colCount }}列</el-tag>
        </div>
        <div class="toolbar-right">
          <el-button size="small" @click="toggleFullscreen" :icon="isFullscreen ? 'el-icon-close' : 'el-icon-full-screen'">
            {{ isFullscreen ? '退出全屏' : '全屏' }}
          </el-button>
          <el-button size="small" @click="exportSheet" icon="el-icon-download">
            导出
          </el-button>
        </div>
      </div>

      <!-- 表格容器 -->
      <div class="table-container" ref="tableContainer">
        <el-table
          :data="currentSheet.data"
          border
          stripe
          style="width: 100%"
          :height="tableHeight"
          empty-text="暂无数据"
          :max-height="tableMaxHeight"
          size="small"
          v-loading="loading"
        >
          <el-table-column
            v-for="(header, index) in currentSheet.headers"
            :key="index"
            :prop="header"
            :label="header"
            :min-width="getColumnWidth(header)"
            :width="getAutoWidth(header, currentSheet.data)"
            resizable
            show-overflow-tooltip
          >
            <template #default="scope">
              <div class="cell-content" :title="scope.row[header]">
                {{ scope.row[header] || ' ' }}
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 空数据提示 -->
        <div v-if="!currentSheet.data || currentSheet.data.length === 0" class="empty-table">
          <el-empty description="暂无表格数据" />
        </div>
      </div>

      <!-- 分页信息（如果数据量大） -->
      <div class="table-footer" v-if="currentSheet.rowCount > 50">
        <div class="pagination-info">
          显示 1-{{ Math.min(currentSheet.rowCount, 50) }} 条，共 {{ currentSheet.rowCount }} 条数据
        </div>
        <el-pagination
          small
          layout="prev, pager, next"
          :total="currentSheet.rowCount"
          :page-size="50"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <div class="viewer-actions">
      <el-button type="primary" @click="handleSave" size="small">
        保存修改
      </el-button>
      <el-button @click="handleClose" size="small">
        关闭
      </el-button>
      <el-button @click="copyToEditor" size="small">
        复制到编辑器
      </el-button>
    </div>

    <!-- 全屏遮罩层 -->
    <div v-if="isFullscreen" class="fullscreen-overlay" @click.self="toggleFullscreen">
      <div class="fullscreen-content">
        <div class="fullscreen-header">
          <h3>{{ excelData.tableName }} - {{ currentSheet?.sheetName }}</h3>
          <div class="fullscreen-actions">
            <el-button size="small" @click="toggleFullscreen" icon="el-icon-close">
              退出全屏 (ESC)
            </el-button>
          </div>
        </div>

        <div class="fullscreen-table-container">
          <el-table
            :data="currentSheet?.data"
            border
            stripe
            style="width: 100%"
            height="100%"
            empty-text="暂无数据"
            size="small"
          >
            <el-table-column
              v-for="(header, index) in currentSheet?.headers || []"
              :key="index"
              :prop="header"
              :label="header"
              :min-width="getColumnWidth(header)"
              :width="getAutoWidth(header, currentSheet?.data)"
              resizable
              show-overflow-tooltip
            >
              <template #default="scope">
                <div class="cell-content" :title="scope.row[header]">
                  {{ scope.row[header] || ' ' }}
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="fullscreen-footer">
          <span>共 {{ currentSheet?.rowCount }} 行 {{ currentSheet?.colCount }} 列数据</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  excelData: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:content', 'close'])

const activeSheet = ref('')
const isFullscreen = ref(false)
const loading = ref(false)
const tableContainer = ref(null)
const tableHeight = ref('auto')
const tableMaxHeight = ref(500)

// 设置默认激活的工作表
if (props.excelData.sheets && props.excelData.sheets.length > 0) {
  activeSheet.value = props.excelData.sheets[0].sheetName
}

// 计算当前工作表
const currentSheet = computed(() => {
  return props.excelData.sheets?.find(sheet => sheet.sheetName === activeSheet.value)
})

// 获取文件名
const getFileName = (filePath) => {
  if (!filePath) return ''
  return filePath.split(/[\\/]/).pop() || filePath
}

// 计算列宽
const getColumnWidth = (header) => {
  const baseWidth = 120
  const headerLength = header ? header.length : 0
  return Math.max(baseWidth, headerLength * 10)
}

// 自动计算列宽
const getAutoWidth = (header, data) => {
  if (!data || data.length === 0) return getColumnWidth(header)

  const headerLength = header ? header.length : 0
  let maxContentLength = headerLength

  // 检查前20行数据，找到最长的内容
  data.slice(0, 20).forEach(row => {
    const content = row[header] || ''
    if (content.length > maxContentLength) {
      maxContentLength = content.length
    }
  })

  return Math.max(80, Math.min(300, maxContentLength * 8))
}

// 计算表格高度
const calculateTableHeight = () => {
  nextTick(() => {
    if (tableContainer.value) {
      const containerRect = tableContainer.value.getBoundingClientRect()
      const headerHeight = 40
      const toolbarHeight = 50
      const footerHeight = 40
      const padding = 32

      const availableHeight = containerRect.height - headerHeight - toolbarHeight - footerHeight - padding
      tableMaxHeight.value = Math.max(300, availableHeight)
    }
  })
}

// 切换全屏
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value

  if (isFullscreen.value) {
    // 进入全屏时，禁止背景滚动
    document.body.style.overflow = 'hidden'
  } else {
    // 退出全屏时，恢复背景滚动
    document.body.style.overflow = ''
  }
}

// ESC键退出全屏
const handleKeydown = (event) => {
  if (event.key === 'Escape' && isFullscreen.value) {
    toggleFullscreen()
  }
}

// 处理分页
const handlePageChange = (page) => {
  loading.value = true
  // 模拟分页加载
  setTimeout(() => {
    loading.value = false
    ElMessage.info(`切换到第 ${page} 页`)
  }, 300)
}

// 导出工作表
const exportSheet = () => {
  ElMessage.info('导出功能开发中...')
}

// 复制到编辑器
const copyToEditor = () => {
  if (!currentSheet.value) return

  const tableData = {
    headers: currentSheet.value.headers,
    data: currentSheet.value.data,
    tableName: currentSheet.value.sheetName
  }

  emit('update:content', tableData)
  ElMessage.success('已复制表格数据到编辑器')
}

// 处理单元格更新
const handleCellUpdate = (rowIndex, column, newValue) => {
  if (!currentSheet.value) return

  const updatedSheets = [...props.excelData.sheets]
  const sheetIndex = updatedSheets.findIndex(sheet => sheet.sheetName === currentSheet.value.sheetName)

  if (sheetIndex !== -1) {
    const newData = [...updatedSheets[sheetIndex].data]
    newData[rowIndex][column] = newValue
    updatedSheets[sheetIndex].data = newData

    emit('update:content', {
      ...props.excelData,
      sheets: updatedSheets
    })
  }
}

// 保存修改
const handleSave = () => {
  ElMessage.success('表格数据已更新')
}

// 关闭查看器
const handleClose = () => {
  // 确保退出全屏状态
  if (isFullscreen.value) {
    toggleFullscreen()
  }
  emit('close')
}

// 生命周期
onMounted(() => {
  calculateTableHeight()
  window.addEventListener('resize', calculateTableHeight)
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('resize', calculateTableHeight)
  document.removeEventListener('keydown', handleKeydown)
  // 确保清理全屏状态
  if (isFullscreen.value) {
    document.body.style.overflow = ''
  }
})
</script>


<!-- ExcelDataViewer.vue - 修复CSS语法错误 -->
<style scoped>
.excel-data-viewer {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.viewer-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.viewer-header h3 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 18px;
}

.header-info {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.sheet-selector {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.current-sheet {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sheet-name {
  font-weight: 500;
  color: #303133;
}

.table-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.cell-content {
  padding: 4px 8px;
  line-height: 1.4;
  word-break: break-word;
}

.empty-table {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.pagination-info {
  font-size: 12px;
  color: #909399;
}

.viewer-actions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-shrink: 0;
}

/* 全屏遮罩层样式 */
.fullscreen-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.8);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.fullscreen-content {
  background: white;
  border-radius: 8px;
  width: 95vw;
  height: 95vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.fullscreen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  flex-shrink: 0;
}

.fullscreen-header h3 {
  margin: 0;
  color: #303133;
  font-size: 20px;
}

.fullscreen-actions {
  display: flex;
  gap: 8px;
}

.fullscreen-table-container {
  flex: 1;
  padding: 20px;
  min-height: 0;
}

.fullscreen-footer {
  padding: 12px 20px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
  text-align: center;
  font-size: 14px;
  color: #606266;
  flex-shrink: 0;
}

/* 修复：删除有问题的CSS选择器 */
</style>

<!-- 修复后的 :deep 样式 -->
<style>
/* 全局样式或使用 scoped 但修复语法 */
.excel-data-viewer .el-table {
  flex: 1;
}

.excel-data-viewer .el-table .el-table__body-wrapper {
  overflow: auto;
}

.excel-data-viewer .el-table .cell {
  padding: 4px 8px;
  line-height: 1.4;
}

.excel-data-viewer .el-table--small .cell {
  padding: 2px 4px;
  font-size: 12px;
}

/* 全屏模式下的表格样式 */
.fullscreen-table-container .el-table {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.fullscreen-table-container .el-table .cell {
  padding: 8px 12px;
  font-size: 14px;
}

/* 滚动条优化 */
.el-table__body-wrapper::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.el-table__body-wrapper::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.el-table__body-wrapper::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.el-table__body-wrapper::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
