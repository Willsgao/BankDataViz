<template>
  <div class="excel-data-viewer">
    <div class="viewer-header">
      <h3>{{ excelData.tableName }}</h3>
      <div class="header-info">
        <span>最后更新: {{ formatDate(excelData.lastUpdated) }}</span>
        <span>路径: {{ excelData.excelPath }}</span>
      </div>
    </div>

    <div class="table-container">
      <el-table
        :data="excelData.data"
        border
        stripe
        style="width: 100%"
        max-height="400"
      >
        <el-table-column
          v-for="(header, index) in excelData.headers"
          :key="index"
          :prop="header"
          :label="header"
          min-width="120"
        >
          <template #default="scope">
            <editable-cell
              :value="scope.row[header]"
              @update:value="handleCellUpdate(scope.$index, header, $event)"
            />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="viewer-actions">
      <el-button type="primary" @click="handleSave" size="small">
        保存修改
      </el-button>
      <el-button @click="handleClose" size="small">
        关闭
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  excelData: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:content'])

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '未知'
  return new Date(dateString).toLocaleString()
}

// 处理单元格更新
const handleCellUpdate = (rowIndex, column, newValue) => {
  const newData = [...props.excelData.data]
  newData[rowIndex][column] = newValue
  emit('update:content', newData)
}

// 保存修改
const handleSave = () => {
  ElMessage.success('表格数据已更新')
  // 这里可以添加保存到后端的逻辑
}

// 关闭查看器
const handleClose = () => {
  emit('update:content', null)
}
</script>

<style scoped>
.excel-data-viewer {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.viewer-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.viewer-header h3 {
  margin: 0 0 8px 0;
  color: #303133;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #909399;
}

.table-container {
  flex: 1;
  overflow: auto;
}

.viewer-actions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>