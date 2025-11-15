<template>
  <div class="handsontable-excel-viewer">


    <!-- 工具栏部分 -->
    <div class="excel-toolbar">
      <div class="toolbar-left">

        <!-- 在工具栏按钮组中添加 -->
        <el-button-group size="small">
          <el-button @click="exportData" :disabled="!tableData.length">
            <el-icon><Download /></el-icon>
            导出数据
          </el-button>
          <el-button @click="toggleFilters" :type="filtersEnabled ? 'primary' : ''" :disabled="!tableData.length">
            <el-icon><Filter /></el-icon>
            筛选
          </el-button>

          <!-- 编辑模式切换按钮 -->
          <el-button
            @click="toggleEditMode"
            :type="isEditMode ? 'success' : ''"
            :disabled="!tableData.length"
          >
            <el-icon><Edit /></el-icon>
            {{ isEditMode ? '退出编辑' : '进入编辑' }}
          </el-button>

          <!-- 保存按钮 -->
          <el-button
            @click="saveChanges"
            type="primary"
            :disabled="!hasChanges || !isEditMode"
            :loading="saving"
          >
            <el-icon><Check /></el-icon>
            保存更改
          </el-button>


        </el-button-group>


      </div>


      <!-- 在工具栏右侧添加调试信息（开发时使用） -->
        <div class="toolbar-right">
          <span class="data-info" v-if="tableData.length > 0">
            共 {{ tableData.length - 1 }} 行 {{ columns.length }} 列
          </span>

          <!-- 调试信息 -->
          <div v-if="false" class="debug-info" style="font-size: 12px; color: #666;">
            | 编辑模式: {{ isEditMode }} | 有更改: {{ hasChanges }} | 修改数: {{ modifiedCellsCount }} |
          </div>


          <!-- 调试信息 - 添加在这里 -->
        <div v-if="true" class="debug-info" style="font-size: 12px; color: #666; margin-right: 10px;">
          | 编辑模式: {{ isEditMode }} | 有更改: {{ hasChanges }} | 修改数: {{ modifiedCellsCount }} |
        </div>

          <!-- 状态提示 -->
          <div class="status-indicators">
            <el-tag v-if="isEditMode" type="success" size="small">
              <el-icon><Edit /></el-icon>
              编辑模式
            </el-tag>
            <el-tag v-if="hasChanges" type="warning" size="small">
              <el-icon><Warning /></el-icon>
              有未保存的更改
            </el-tag>
            <span v-if="modifiedCellsCount > 0" class="modified-count">
              已修改 {{ modifiedCellsCount }} 个单元格
            </span>
          </div>
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
        :height="tableHeight"
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
        :renderAllRows="true"
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

// 在现有的导入部分添加
import { Download, Filter, Edit, Check, Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import 'handsontable/dist/handsontable.full.css'



// 在现有变量后面添加这些
const isEditMode = ref(false)
const hasChanges = ref(false)
const saving = ref(false)
const modifiedCellsCount = ref(0)
const modifiedCells = ref(new Set())
const originalData = ref([])


// 新增方法：更新修改单元格样式
const updateModifiedCellsStyle = () => {
  if (hotTable.value && hotTable.value.hotInstance) {
    const hot = hotTable.value.hotInstance

    // 清除之前的修改样式
    hot.updateSettings({
      cell: []
    })

    // 为修改过的单元格添加红色背景
    const modifiedCellSettings = Array.from(modifiedCells.value).map(cellKey => {
      const [row, col] = cellKey.split(',').map(Number)
      return {
        row: row,
        col: col,
        className: 'modified-cell'
      }
    })

    hot.updateSettings({
      cell: modifiedCellSettings
    })

    hot.render()
  }
}



// 修复 manualSetupEventListeners 方法
const manualSetupEventListeners = () => {
  console.log('🛠️ 手动配置事件监听')

  // 方法1：优先使用组件内部的实例
  if (hotTable.value?.hotInstance) {
    const hot = hotTable.value.hotInstance
    console.log('✅ 找到 Handsontable 实例（内部引用）')

    // 清除可能存在的重复监听
    try {
      hot.removeHook('afterChange')
    } catch (e) {
      console.log('ℹ️ 清除旧监听时无异常或已清除')
    }

    // 添加新的事件监听
    hot.addHook('afterChange', function(changes, source) {
      console.log('🎯 afterChange 事件触发（手动配置）:', {
        changes: changes ? changes.length : 0,
        source: source,
        timestamp: new Date().toISOString()
      })

      // 直接调用组件的方法
      onDataChange(changes, source)
    })

    console.log('✅ 事件监听已配置完成（内部实例）')
    ElMessage.success('事件监听配置成功')
    return
  }

  // 方法2：回退到 window 实例
  const instance = window.excelViewerInstance
  if (instance?.hotTable?.hotInstance) {
    const hot = instance.hotTable.hotInstance
    console.log('✅ 找到 Handsontable 实例（window 实例）')

    try {
      hot.removeHook('afterChange')
    } catch (e) {}

    hot.addHook('afterChange', function(changes, source) {
      console.log('🎯 afterChange 事件触发（window实例）:', {
        changes: changes ? changes.length : 0,
        source: source,
        timestamp: new Date().toISOString()
      })

      // 使用 window 实例中的方法
      if (instance.methods && instance.methods.onDataChange) {
        instance.methods.onDataChange(changes, source)
      } else {
        // 回退到直接调用
        onDataChange(changes, source)
      }
    })

    console.log('✅ 事件监听已配置完成（window实例）')
    ElMessage.success('事件监听配置成功')
    return
  }

  // 方法3：如果实例都不存在，尝试重新初始化
  console.log('❌ 无法访问 Handsontable 实例，尝试重新初始化')

  // 延迟重试
  setTimeout(() => {
    if (hotTable.value?.hotInstance) {
      manualSetupEventListeners()
    } else {
      console.log('❌ 重试后仍然无法访问实例')
      ElMessage.error('无法配置事件监听：表格实例未准备好')
    }
  }, 500)
}



// 新增方法：保存更改
const saveChanges = async () => {
  if (!hasChanges.value) return

  saving.value = true
  try {
    console.log('💾 开始保存修改的数据:', {
      modifiedCells: Array.from(modifiedCells.value),
      totalChanges: modifiedCellsCount.value,
      pdfId: props.pdfId,
      excelFileName: props.excelFileName,
      sheetName: props.sheetName
    })

    // 收集修改的数据
    const modifiedData = collectModifiedData()

    // 调用后台API保存数据
    const response = await fetch('/api/save-excel-data', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        pdf_id: props.pdfId,
        excel_file: props.excelFileName,
        sheet_name: props.sheetName,
        modified_cells: modifiedData,
        total_changes: modifiedCellsCount.value
      })
    })

    if (!response.ok) {
      throw new Error(`保存失败: ${response.status}`)
    }

    const result = await response.json()
    console.log('✅ 保存成功:', result)

    ElMessage.success(`数据保存成功，共保存 ${modifiedCellsCount.value} 个修改`)
    resetChanges()

  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error(`保存失败: ${error.message}`)
  } finally {
    saving.value = false
  }
}

// 新增方法：收集修改的数据
const collectModifiedData = () => {
  if (!hotTable.value || !hotTable.value.hotInstance) {
    return []
  }

  const hot = hotTable.value.hotInstance
  const modifiedData = []

  // 遍历所有修改的单元格
  modifiedCells.value.forEach(cellKey => {
    const [row, col] = cellKey.split(',').map(Number)
    const newValue = hot.getDataAtCell(row, col)

    modifiedData.push({
      row: row,
      column: col,
      value: newValue,
      cell_key: cellKey
    })
  })

  console.log('📋 收集的修改数据:', modifiedData)
  return modifiedData
}



// 新增方法：重置更改状态
const resetChanges = () => {
  hasChanges.value = false
  modifiedCellsCount.value = 0
  modifiedCells.value.clear()

  // 清除修改样式
  if (hotTable.value && hotTable.value.hotInstance) {
    const hot = hotTable.value.hotInstance
    hot.updateSettings({
      cell: []
    })
    hot.render()
  }
}



// 修复更新表格只读状态的方法
const updateTableReadOnly = () => {
  if (hotTable.value && hotTable.value.hotInstance) {
    const hot = hotTable.value.hotInstance
    const readOnly = !isEditMode.value

    console.log('🔒 更新表格只读状态:', { readOnly })

    hot.updateSettings({
      readOnly: readOnly
    })

    // 强制重新渲染
    setTimeout(() => {
      hot.render()
    }, 100)
  }
}




// 修复 toggleEditMode 方法
const toggleEditMode = () => {
  if (isEditMode.value && hasChanges.value) {
    ElMessageBox.confirm(
      '有未保存的更改，确定要退出编辑模式吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    ).then(() => {
      resetChanges()
      isEditMode.value = false
      updateTableReadOnly()
      ElMessage.success('已退出编辑模式')
    }).catch(() => {
      // 用户取消，保持编辑模式
      console.log('用户取消退出编辑模式')
    })
  } else {
    isEditMode.value = !isEditMode.value
    if (!isEditMode.value) {
      resetChanges()
    }
    updateTableReadOnly()

    // === 使用与控制台完全相同的代码 ===
    if (isEditMode.value) {
      console.log('🔧 执行控制台代码')

      // 完全复制控制台能工作的代码
      const instance = window.excelViewerInstance
      if (instance?.hotTable?.hotInstance) {
        const hot = instance.hotTable.hotInstance

        try {
          hot.removeHook('afterChange')
        } catch (e) {}

        hot.addHook('afterChange', function(changes, source) {
          console.log('🎯 afterChange 事件触发:', {
            changes: changes ? changes.length : 0,
            source: source,
            timestamp: new Date().toISOString()
          })

          // 关键：使用 instance.methods.onDataChange
          instance.methods.onDataChange(changes, source)
        })

        console.log('✅ 事件监听配置完成')
      }
    }
    // === 结束 ===

    console.log('🎛️ 编辑模式切换:', {
      newMode: isEditMode.value,
      hasChanges: hasChanges.value,
      readOnly: !isEditMode.value
    })

    ElMessage.success(isEditMode.value ? '已进入编辑模式' : '已退出编辑模式')
  }
}







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



// 新增方法：配置事件监听
const setupEventListeners = () => {
  console.log('🔧 开始配置事件监听...')

  if (!hotTable.value || !hotTable.value.hotInstance) {
    console.log('❌ 表格实例未准备好，延迟重试')
    setTimeout(setupEventListeners, 200)
    return
  }

  const hot = hotTable.value.hotInstance
  console.log('✅ 表格实例已准备好，配置事件监听')

  // 清除可能存在的重复监听
  try {
    hot.removeHook('afterChange')
    console.log('✅ 已清除旧的 afterChange 监听')
  } catch (e) {
    console.log('ℹ️ 清除旧监听时出错:', e.message)
  }

  // 添加原生事件监听
  hot.addHook('afterChange', function(changes, source) {
    console.log('🎯 afterChange 事件触发:', {
      changes: changes ? changes.length : 0,
      source: source,
      timestamp: new Date().toISOString()
    })

    // 调用我们的处理方法
    onDataChange(changes, source)
  })

  console.log('✅ 事件监听配置完成')
}



// 在 setupEventListeners 函数之前定义 onDataChange
const onDataChange = (changes, source) => {
  console.log('📝 onDataChange 被调用:', {
    changes: changes,
    source: source,
    isEditMode: isEditMode.value
  })

  // 如果不是编辑模式，忽略所有更改
  if (!isEditMode.value) {
    console.log('ℹ️ 非编辑模式，忽略更改')
    return
  }

  // 如果来源是 'loadData'，忽略
  if (source === 'loadData') {
    console.log('ℹ️ 数据加载来源，忽略更改')
    return
  }

  if (!changes) {
    console.log('ℹ️ 无有效更改')
    return
  }

  console.log('✅ 处理有效更改:', changes.length)

  // 处理每个更改
  changes.forEach(([row, col, oldValue, newValue]) => {
    // 跳过空行或无效行
    if (row === null || col === null) return

    const cellKey = `${row},${col}`

    // 如果值没有实际变化，跳过
    if (oldValue === newValue) {
      console.log(`ℹ️ 单元格 [${row},${col}] 值未变化，跳过`)
      return
    }

    console.log(`📝 检测到更改: [${row},${col}] ${oldValue} -> ${newValue}`)

    // 添加到修改集合
    if (!modifiedCells.value.has(cellKey)) {
      modifiedCells.value.add(cellKey)
      modifiedCellsCount.value = modifiedCells.value.size
      console.log(`➕ 新增修改单元格: ${cellKey}`)
    }

    // 标记有更改
    hasChanges.value = true
  })

  // 更新修改单元格的样式
  nextTick(() => {
    updateModifiedCellsStyle()
  })

  console.log('📊 更改统计:', {
    totalChanges: modifiedCellsCount.value,
    hasChanges: hasChanges.value,
    modifiedCells: Array.from(modifiedCells.value)
  })
}

// 改进的 onMounted
onMounted(() => {
  console.log('🎯 HandsontableExcelViewer onMounted 开始执行')

  // 初始计算高度
  nextTick(() => {
    calculateHeight()
  })

  // 改进的实例暴露函数
  const exposeInstance = () => {
    window.excelViewerInstance = {
      isEditMode: isEditMode.value,
      hasChanges: hasChanges.value,
      modifiedCellsCount: modifiedCellsCount.value,
      hotTable: hotTable.value,
      methods: {
        onDataChange,
        updateTableReadOnly,
        setupEventListeners,
        manualSetupEventListeners // 暴露这个方法
      }
    }
    console.log('✅ ExcelViewer 实例已暴露到 window.excelViewerInstance', {
      hasHotInstance: !!hotTable.value?.hotInstance
    })
  }

  // 立即暴露
  exposeInstance()

  // 延迟再次暴露，确保实例已创建
  setTimeout(() => {
    exposeInstance()
    setupEventListeners()
  }, 500)

  // 使用 ResizeObserver 监听容器尺寸变化
  if (excelContainer.value) {
    resizeObserver.value = new ResizeObserver(() => {
      calculateHeight()
      nextTick(() => {
        if (hotTable.value && hotTable.value.hotInstance) {
          hotTable.value.hotInstance.updateSettings({
            height: tableHeight.value
          })
          hotTable.value.hotInstance.render()
        }
      })
    })
    const parentContainer = excelContainer.value.closest('.excel-content') || excelContainer.value.parentElement
    if (parentContainer) {
      resizeObserver.value.observe(parentContainer)
    }
  }
})



// 计算容器可用高度
const calculateHeight = () => {
  if (excelContainer.value) {
    // 获取父容器的高度，而不是当前容器
    const parentContainer = excelContainer.value.closest('.excel-content') || excelContainer.value.parentElement
    if (parentContainer) {
      const parentRect = parentContainer.getBoundingClientRect()
      containerHeight.value = parentRect.height - 60 // 减去工具栏高度
      console.log('📏 计算表格高度:', {
        parentHeight: parentRect.height,
        containerHeight: containerHeight.value,
        rows: tableData.value.length
      })
    }
  }
}


// 动态计算表格高度
const tableHeight = computed(() => {
  if (tableData.value.length === 0) {
    return 200
  }

  // 计算所需的最小高度（显示部分行，其余通过滚动查看）
  const visibleRows = 30 // 可见行数
  const rowHeight = 25
  const headerHeight = 25
  const visibleHeight = (visibleRows * rowHeight) + headerHeight + 10

  console.log('🎯 表格高度计算（启用滚动）:', {
    总行数: tableData.value.length,
    可见行数: visibleRows,
    表格高度: visibleHeight
  })

  return visibleHeight
})





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





// 使用 ResizeObserver 监听容器尺寸变化
const resizeObserver = ref(null)

// 替换现有的监听器，合并功能
watch(() => props.excelData, (newData, oldData) => {
  console.log('🔄 Excel数据变化:', {
    newLength: newData?.length,
    oldLength: oldData?.length
  })

  if (newData && newData.length > 0) {
    // 新增：保存原始数据并重置编辑状态
    originalData.value = JSON.parse(JSON.stringify(newData))
    resetChanges()
    isEditMode.value = false
    updateTableReadOnly()

    nextTick(() => {
      calculateHeight()
      if (hotTable.value && hotTable.value.hotInstance) {
        console.log('🔄 刷新表格实例')
        const hot = hotTable.value.hotInstance
        hot.updateSettings({
          height: tableHeight.value
        })
        hot.render()
      }
    })
  }
}, { deep: true })





// 新增：监听表格数据变化，在数据加载后配置事件监听
watch(() => props.excelData, (newData) => {
  if (newData && newData.length > 0) {
    console.log('📊 表格数据已加载，配置事件监听')

    // 延迟确保表格完全渲染
    nextTick(() => {
      setTimeout(() => {
        setupEventListeners()
      }, 100)
    })
  }
}, { immediate: true })


// 简化 onMounted
onMounted(() => {
  console.log('🎯 HandsontableExcelViewer onMounted 开始执行')

  // 初始计算高度
  nextTick(() => {
    calculateHeight()
  })

  // 直接暴露实例到 window
  window.excelViewerInstance = {
    isEditMode: isEditMode.value,
    hasChanges: hasChanges.value,
    modifiedCellsCount: modifiedCellsCount.value,
    hotTable: hotTable.value,
    methods: {
      onDataChange,
      updateTableReadOnly,
      setupEventListeners
    }
  }

  console.log('✅ ExcelViewer 实例已暴露到 window.excelViewerInstance')

  // 使用 ResizeObserver 监听容器尺寸变化
  if (excelContainer.value) {
    resizeObserver.value = new ResizeObserver(() => {
      calculateHeight()
      nextTick(() => {
        if (hotTable.value && hotTable.value.hotInstance) {
          hotTable.value.hotInstance.updateSettings({
            height: tableHeight.value
          })
          hotTable.value.hotInstance.render()
        }
      })
    })
    const parentContainer = excelContainer.value.closest('.excel-content') || excelContainer.value.parentElement
    if (parentContainer) {
      resizeObserver.value.observe(parentContainer)
    }
  }
})


onUnmounted(() => {
  if (resizeObserver.value) {
    resizeObserver.value.disconnect()
  }
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




.excel-container {
  flex: 1;
  min-height: 0;
  overflow: auto;  /* 改为 auto 允许滚动 */
  position: relative;
  border: 1px solid #e0e0e0;
}

/* 确保 Handsontable 容器可以滚动 */
:deep(.handsontable .wtHolder) {
  overflow: auto !important;
  position: relative !important;
}

/* 设置表格最小宽度，确保内容不会压缩 */
:deep(.handsontable) {
  min-width: fit-content;
}








/* 在现有样式后面添加 */
:deep(.modified-cell) {
  background-color: #ffebee !important;
  border: 1px solid #f44336 !important;
}

:deep(.modified-cell):hover {
  background-color: #ffcdd2 !important;
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modified-count {
  font-size: 12px;
  color: #e6a23c;
  font-weight: 500;
}

:deep(.handsontable.readOnly td) {
  background-color: #f8f9fa;
  cursor: not-allowed;
}

:deep(.handsontable.readOnly .modified-cell) {
  background-color: #fff3e0 !important;
  border: 1px solid #ff9800 !important;
}



</style>