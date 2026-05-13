<template>
  <div class="table-list-container">
    <div class="section-header">
      <span class="section-title">表格名称列表</span>
      <el-tag type="info">
        {{ tableCount }} 个表格
      </el-tag>
    </div>
    <div class="table-content">
      <div
        v-if="loadingSheets"
        class="loading-state"
      >
        <el-icon class="is-loading">
          <Loading />
        </el-icon>
        加载表格列表中...
      </div>
      <div
        v-else-if="excelFiles.length === 0"
        class="empty-state"
      >
        <p>暂无表格数据</p>
        <p class="tip">
          选中的PDF没有对应的Excel文件
        </p>
      </div>
      <div
        v-else
        class="excel-files-container"
      >
        <div
          v-for="excelFile in excelFiles"
          :key="excelFile.excel_file"
          class="excel-file-item"
        >
          <div class="excel-file-header">
            <el-icon><Document /></el-icon>
            <span class="excel-file-name">{{ excelFile.excel_file }}</span>
            <el-tag
              size="small"
              type="info"
            >
              {{ excelFile.total_sheets }} 个表
            </el-tag>
          </div>
          <div class="sheet-items">
            <div
              v-for="sheet in excelFile.sheets"
              :key="`${excelFile.excel_file}-${sheet.name}`"
              class="sheet-item"
              :class="{
                'active': selectedSheet &&
                  selectedSheet.name === sheet.name &&
                  selectedSheet.excel_file === excelFile.excel_file
              }"
              @click="$emit('select-sheet', sheet, excelFile.excel_file)"
            >
              <el-icon><Grid /></el-icon>
              <span class="sheet-name">{{ sheet.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Document, Grid, Loading } from '@element-plus/icons-vue'

defineProps({
  excelFiles: {
    type: Array,
    default: () => []
  },
  loadingSheets: {
    type: Boolean,
    default: false
  },
  tableCount: {
    type: Number,
    default: 0
  },
  selectedSheet: Object,
  selectedExcelFile: String
})

defineEmits(['select-sheet'])
</script>

<style scoped>
.table-list-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.section-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.section-title {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.table-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.loading-state {
  padding: 20px;
  text-align: center;
  color: #909399;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #909399;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.tip {
  font-size: 12px;
  margin-top: 8px;
}

.excel-files-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.excel-file-item {
  margin-bottom: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}

.excel-file-item:last-child {
  margin-bottom: 0;
}

.excel-file-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  gap: 8px;
}

.excel-file-name {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sheet-items {
  background: white;
}

.sheet-item {
  display: flex;
  align-items: center;
  padding: 10px 16px 10px 32px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  gap: 8px;
  transition: background-color 0.2s;
}

.sheet-item:hover {
  background: #f5f7fa;
}

.sheet-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.sheet-item:last-child {
  border-bottom: none;
}

.sheet-name {
  flex: 1;
  font-size: 13px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

