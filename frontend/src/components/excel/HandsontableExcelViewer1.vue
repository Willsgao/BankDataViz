<template>
  <div class="handsontable-excel-viewer">
    <!-- 工具栏 -->
    <div class="excel-toolbar">
      <div class="toolbar-left">
        <el-button-group size="small">
          <el-button @click="exportData" :disabled="!tableData.length">
            <el-icon><Download /></el-icon>
            导出数据
          </el-button>
          <el-button @click="toggleFilters" :type="filtersEnabled ? 'primary' : ''" :disabled="!tableData.length">
            <el-icon><Filter /></el-icon>
            筛选
          </el-button>
        </el-button-group>
      </div>
      <div class="toolbar-right">
        <span class="data-info" v-if="tableData.length > 0">
          共 {{ tableData.length - 1 }} 行 {{ columns.length }} 列
        </span>
      </div>
    </div>

    <!-- Handsontable 表格区域 -->
    <div class="excel-container" ref="excelContainer">
      <HotTable
        ref="hotTable"
        :data="tableData"
        :columns="columns"
        :colHeaders="true"
        :rowHeaders="true"
        :width="'100%'"
        :height="containerHeight"
        :licenseKey="'non-commercial-and-evaluation'"
        :filters="filtersEnabled"
        :dropdownMenu="true"
        :contextMenu="true"
        :manualColumnResize="true"
        :manualRowResize="true"
        :wordWrap="false"
        :columnSorting="true"
        :autoRowSize="false"
        :autoColumnSize="false"
        @afterChange="onDataChange"
        @afterFilter="onFilter"
      />

      <div v-if="tableData.length === 0" class="empty-state">
        <el-empty description="暂无表格数据" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { HotTable } from '@handsontable/vue3'
import { Download, Filter } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import 'handsontable/dist/handsontable.full.css'

const props = defineProps({
  excelData: {
    type: Array,
    default: () => []
  },
  sheetName: String,
  pdfId: String,
  excelFileName: String
})

// 状态管理
const filtersEnabled = ref(true)
const hotTable = ref(null)
const excelContainer = ref(null)
const containerHeight = ref(400)

// 计算容器高度
const calculateHeight = () => {
  if (excelContainer.value) {
    const containerRect = excelContainer.value.getBoundingClientRect()
    containerHeight.value = containerRect.height - 10 // 留一些边距
    console.log('📏 计算容器高度:', containerHeight.value)
  }
}

// 数据转换逻辑保持不变
const tableData = computed(() => {
  console.log('📊 原始 excelData:', props.excelData)

  if (!props.excelData || props.excelData.length === 0) {
    console.log('❌ 没有数据，返回空数组')
    return []
  }

  try {
    // 检查数据格式 - 后端返回的是对象数组
    const firstItem = props.excelData[0]

    if (typeof firstItem === 'object' && firstItem !== null) {
      // 从对象数组转换为二维数组
      const headers = Object.keys(firstItem)
      console.log('📋 表头:', headers)

      const dataArray = [
        headers, // 第一行是表头
        ...props.excelData.map(row => {
          return headers.map(header => {
            const value = row[header]
            // 处理各种空值情况
            if (value === null || value === undefined || value === '') {
              return ''
            }
            return String(value)
          })
        })
      ]

      console.log('✅ 转换后的表格数据:', {
        rows: dataArray.length - 1,
        columns: headers.length,
        sample: dataArray.slice(0, 2)
      })

      return dataArray
    }

    // 如果已经是二维数组格式，直接返回
    console.log('ℹ️ 数据已经是二维数组格式')
    return props.excelData

  } catch (error) {
    console.error('❌ 数据转换失败:', error)
    return []
  }
})

const columns = computed(() => {
  if (!tableData.value || tableData.value.length === 0) {
    return []
  }

  const headers = tableData.value[0] || []
  console.log('🎯 生成列配置，表头数量:', headers.length)

  return headers.map((header, index) => ({
    data: index,
    title: header || `列${index + 1}`,
    type: 'text',
    width: 150
  }))
})

// 方法保持不变
const exportData = () => {
  if (!tableData.value.length) return

  try {
    const headers = tableData.value[0]
    const csvContent = [
      headers.join(','),
      ...tableData.value.slice(1).map(row => row.join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)

    link.setAttribute('href', url)
    link.setAttribute('download', `${props.sheetName || 'data'}.csv`)
    link.style.visibility = 'hidden'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('数据导出成功')
  } catch (error) {
    console.error('导出数据失败:', error)
    ElMessage.error('导出数据失败')
  }
}

const toggleFilters = () => {
  filtersEnabled.value = !filtersEnabled.value
  ElMessage.info(filtersEnabled.value ? '筛选功能已启用' : '筛选功能已禁用')
}

const onDataChange = (changes) => {
  if (changes) {
    console.log('数据变化:', changes)
  }
}

const onFilter = (conditions) => {
  console.log('筛选条件:', conditions)
}

// 监听窗口大小变化
const handleResize = () => {
  nextTick(() => {
    calculateHeight()
    if (hotTable.value && hotTable.value.hotInstance) {
      hotTable.value.hotInstance.render()
    }
  })
}

// 增强的监听器
watch(() => props.excelData, (newData, oldData) => {
  console.log('🔄 Excel数据变化:', {
    newLength: newData?.length,
    oldLength: oldData?.length
  })

  if (newData && newData.length > 0) {
    nextTick(() => {
      calculateHeight()
      if (hotTable.value && hotTable.value.hotInstance) {
        console.log('🔄 刷新表格实例')
        const hot = hotTable.value.hotInstance
        hot.render()
        hot.selectCell(0, 0)
      }
    })
  }
}, { deep: true })

onMounted(() => {
  // 初始计算高度
  nextTick(() => {
    calculateHeight()
  })

  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.handsontable-excel-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 重要：防止flex布局溢出 */
}

.excel-toolbar {
  flex-shrink: 0;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 60px; /* 固定工具栏高度 */
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.data-info {
  font-size: 12px;
  color: #606266;
}

.excel-container {
  flex: 1;
  min-height: 0; /* 重要：允许flex收缩 */
  overflow: hidden;
  position: relative;
  border: 1px solid #e0e0e0; /* 添加边框以便调试 */
}

.empty-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
}

/* 确保Handsontable样式正确应用 */
:deep(.handsontable) {
  font-size: 12px;
}

:deep(.handsontable .wtHolder) {
  width: 100% !important;
  height: 100% !important;
}
</style>