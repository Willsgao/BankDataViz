<!-- frontend/src/layouts/TwoColumnLayout.vue -->
<template>
  <div class="two-column-layout">
    <!-- 左侧：PDF预览和文件操作区域 -->
    <div class="left-panel">
      <file-upload @uploaded="$emit('loadFiles')"/>
      <file-list
        :files="files"
        :crop-loading="cropLoading"
        :crop-results="cutResults"
        :converting="convertingObj"
        :convert-cache="convertCache"
        :batch-crop-loading="batchCropLoading"
        :joined-results="joinedResults"
        @delete="$emit('deleteFile', $event)"
        @crop="$emit('cutTable', $event)"
        @convert="$emit('convertAndPreview', $event)"
        @batch-crop="$emit('handleBatchCrop', $event)"
        @open-llm-config="$emit('openLLMConfig')"
        @image-selected="$emit('handleImageSelected', $event)"
        @recognize-table="$emit('handleRecognizeTable', $event)"
        @excel-data-received="$emit('handleExcelDataReceived', $event)"
      />
    </div>

    <!-- 右侧：Excel数据展示区域 -->
    <div class="right-panel">
      <!-- 右侧面板内容保持不变 -->
      <div class="panel-header">
        <div class="header-title">
          <span v-if="currentExcelData">
            <i class="el-icon-document"></i>
            表格数据 - {{ currentExcelData.tableName }}
          </span>
          <span v-else>
            <i class="el-icon-document"></i>
            表格数据查看器
          </span>
        </div>
        <div class="header-actions">
          <!-- 操作按钮保持不变 -->
          <div class="action-row first-row">
            <el-button type="danger" @click="$emit('manuallyTriggerExcelUpdate')" icon="el-icon-magic-stick" size="small">
              调试更新
            </el-button>
            <el-button type="warning" @click="$emit('forceRefreshExcel')" icon="el-icon-refresh" size="small" :disabled="!currentExcelData">
              强制刷新
            </el-button>
            <el-button type="primary" @click="$emit('openVisualization')" icon="el-icon-data-analysis" size="small" :disabled="!currentExcelData">
              可视化分析
            </el-button>
          </div>
          <div class="action-row second-row">
            <el-button type="primary" @click="$emit('openLLMConfig')" icon="el-icon-cpu" size="small">
              LLM配置
            </el-button>
            <el-button type="success" @click="$emit('saveExcelData')" icon="el-icon-document" size="small" :disabled="!currentExcelData">
              保存Excel
            </el-button>
            <el-button type="info" @click="$emit('exportAllData')" icon="el-icon-download" size="small" :disabled="!currentExcelData">
              导出数据
            </el-button>
          </div>
        </div>
      </div>

      <!-- Excel数据展示区域 -->
      <div class="excel-content" v-if="currentExcelData">
        <ExcelDataViewer
          :excel-data="currentExcelData"
          @update:content="$emit('updateExcelContent', $event)"
          @close="currentExcelData = null"
        />
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <el-empty description="暂无表格数据">
          <div class="empty-tips">
            <p>请从左侧选择图片并点击"识别"按钮</p>
            <p>或对PDF文件进行批量裁切后识别表格</p>
          </div>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
// 导入组件
import FileUpload from '@/components/file/FileUpload.vue'
import FileList from '@/components/file/FileList.vue'
import ExcelDataViewer from '@/components/table/ExcelViewer.vue'

// 定义props - 所有需要从父组件传递的数据
defineProps({
  files: Array,
  cropLoading: Object,
  cutResults: Object,
  convertingObj: Object,
  convertCache: Object,
  batchCropLoading: Object,
  joinedResults: Object,
  currentExcelData: Object
})

// 定义emit事件 - 所有需要向父组件触发的事件
defineEmits([
  'loadFiles',
  'deleteFile',
  'cutTable',
  'convertAndPreview',
  'handleBatchCrop',
  'openLLMConfig',
  'handleImageSelected',
  'handleRecognizeTable',
  'handleExcelDataReceived',
  'manuallyTriggerExcelUpdate',
  'forceRefreshExcel',
  'openVisualization',
  'saveExcelData',
  'exportAllData',
  'updateExcelContent'
])
</script>

<style scoped>
.two-column-layout {
  display: flex;
  height: 100vh;
  gap: 16px;
  padding: 16px;
  background: #f5f5f5;
  overflow: hidden;
}

.left-panel {
  flex: 1.5;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

/* 复制原有的面板样式 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  flex-shrink: 0;
  min-height: 80px;
}

.header-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.action-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.header-title {
  font-weight: 600;
  color: #303133;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.excel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
}

.empty-tips {
  text-align: center;
  color: #909399;
  font-size: 14px;
  line-height: 1.6;
}

.empty-tips p {
  margin: 4px 0;
}
</style>