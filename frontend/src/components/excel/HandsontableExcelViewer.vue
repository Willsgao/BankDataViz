<template>
  <div class="handsontable-excel-viewer">
    <!-- 第一行：主控栏（保持不变） @click="exportFinalFile" -->
    <div class="main-toolbar">


      <div class="toolbar-section left-section">
          <el-button
            type="primary"
            size="small"
            @click="exportData"
            :loading="exportFinalLoading"
          >
            <el-icon><Download /></el-icon>导出
          </el-button>



          <!-- 将原来的"高亮空格"按钮改为"高亮数值" -->
            <el-button
              v-if="hasNumericCells"
              :type="showNumericCellsHighlight ? 'primary' : ''"
              size="small"
              @click="toggleNumericCellsHighlight"
            >
              <el-icon><View /></el-icon>{{ showNumericCellsHighlight ? '隐藏数据' : '高亮数据' }}
            </el-button>



          <!-- 保存按钮 -->
          <el-button
            type="success"
            size="small"
            :disabled="!enableSaveButtons || saving"
            @click="triggerSave"
            :loading="saving"
          >
            <el-icon><Check /></el-icon>保存
          </el-button>

          <!-- 🔥🔥🔥 新增：将编辑状态标签移动到这里（保存按钮后面） -->
          <el-tooltip
            :content="`编辑模式${hasChanges ? ` (已修改 ${modifiedCellsCount} 个单元格)` : ''}`"
            placement="bottom"
          >
            <el-tag
              :type="hasChanges ? 'warning' : 'success'"
              size="small"
              class="status-tag edit-status-highlight"
              :class="{ 'has-changes': hasChanges }"
            >
              <el-icon><Edit /></el-icon>
              {{ hasChanges ? `已修改(${modifiedCellsCount})` : '编辑中' }}
            </el-tag>
          </el-tooltip>
        </div>

      <div class="toolbar-section center-section" v-if="tableData.length > 0">
        <el-tag size="small" type="info" class="data-summary">
          <el-icon><Grid /></el-icon>
          {{ tableData.length - 1 }}行 × {{ columns.length }}列
        </el-tag>

        <el-divider
          v-if="hasDualHeaders && tableInfo"
          direction="vertical"
          style="margin: 0 8px;"
        />

        <div v-if="hasDualHeaders && tableInfo" class="dual-header-info">
          <el-tag type="success" size="small">
            <el-icon><Menu /></el-icon>双表头
          </el-tag>
          <span class="structure-info">
            {{ tableInfo.横向表头 }}列 × {{ tableInfo.纵向表头 }}行
          </span>
        </div>
      </div>

      <div class="toolbar-section right-section">
        <!-- 将整体扁平化按钮移动到这里 -->
        <el-button
          type="primary"
          size="small"
          :disabled="!globalFlattenEnabled"
          @click="handleGlobalFlatten"
          :loading="globalFlattenLoading"
          class="global-flatten-btn"
        >
          <el-icon><DataBoard /></el-icon>
          整体扁平化
        </el-button>

      </div>
    </div>

    <!-- 第三行：功能操作栏（原有逻辑保持不变） -->
    <div class="action-toolbar compact-line" v-if="tableData.length > 0 && (showStatsPanel || selectedCell.position)">
      <!-- 左侧：选中统计（原有） -->
      <div v-if="showStatsPanel" class="action-group selection-stats-group">
        <div class="group-header">
          <el-icon><DataAnalysis /></el-icon>
          <span class="group-title">选中区域统计</span>
          <el-tag size="small" :type="stats.selectionType === 'column' ? 'info' : 'success'">
            {{ stats.selectionType === 'column' ? '整列' : '区域' }}
          </el-tag>
        </div>
        <div class="stats-content">
          <div class="stats-grid">
            <div class="stat-item"><span class="stat-label">单元格数:</span><span class="stat-value">{{ stats.rowCount }}</span></div>
            <div class="stat-item"><span class="stat-label">数值:</span><span class="stat-value">{{ stats.numericCount }}</span></div>
            <div class="stat-item"><span class="stat-label">总和:</span><span class="stat-value">{{ stats.sum }}</span></div>
            <div class="stat-item"><span class="stat-label">平均值:</span><span class="stat-value">{{ stats.average }}</span></div>
            <div class="stat-item"><span class="stat-label">最大值:</span><span class="stat-value">{{ stats.max }}</span></div>
            <div class="stat-item"><span class="stat-label">最小值:</span><span class="stat-value">{{ stats.min }}</span></div>
          </div>
          <el-button size="small" type="info" link @click="clearSelection" title="清除选择" class="clear-btn"><el-icon><Close /></el-icon></el-button>
        </div>
      </div>

      <!-- 右侧：当前单元格完整信息（合并进来，不省略） -->
      <div v-if="selectedCell.position" class="action-group current-cell-inline">
        <el-tag size="small" type="info" style="white-space: normal; line-height: 1.4;">
          <el-icon><Position /></el-icon>
          <span class="cell-pos">{{ selectedCell.position }}</span> |
          <span class="cell-type">{{ selectedCell.type }}</span> |
          <span class="cell-content">{{ selectedCell.content || '[空]' }}</span>
          <span v-if="selectedCell.isModified" style="color: #f56c6c;">（已修改）</span>
        </el-tag>
      </div>
    </div>

    <!-- 表格区域（完全不动） :contextMenu="getContextMenuConfig" -->
    <div class="excel-container" ref="excelContainer">
        <HotTable
          ref="hotTable"
          :data="tableData"
          :columns="computedColumns"
          :colWidths="colWidths"
          :colHeaders="true"
          :rowHeaders="true"
          :width="'100%'"
          :height="tableHeight"
          licenseKey="non-commercial-and-evaluation"
          :language="currentLanguage"
          :filters="false"
          :dropdownMenu="true"
          :contextMenu="true"
          :manualColumnResize="true"
          :manualRowResize="true"
          :wordWrap="false"
          :columnSorting="true"
          :multiColumnSorting="false"
          :autoRowSize="false"
          :autoColumnSize="false"
          :renderAllRows="false"
          :fixedRowsTop="fixedRowsTop"
          :fixedColumnsLeft="fixedColumnsLeft"
          :key="langKey"
          :allowInsertColumn="true"
          :allowRemoveColumn="true"
          @afterFilter="onFilter"
          @after-change="onDataChange"
          @after-init="onHotInit"
          @afterSelection="handleSelection"
          @afterDeselect="clearSelection"
        />

      <div v-if="tableData.length === 0" class="empty-state">
        <el-empty description="暂无表格数据" />
      </div>

      <div v-if="showScrollHint" class="horizontal-scroll-hint">
        ← → 可左右滚动查看完整表格
      </div>
    </div>
  </div>
</template>



<script setup>
import { registerLanguageDictionary, zhCN } from 'handsontable/i18n'
import { ref, computed, defineEmits, defineProps, nextTick, onMounted, onUnmounted, defineExpose, watch } from 'vue'

import { HotTable } from '@handsontable/vue3'
// import 'handsontable/dist/handsontable.full.min.css'  // 使用最新样式
import 'handsontable/styles/handsontable.css'

import {
  Download, Edit, View, Grid, Menu, DataAnalysis,
  Close, Position, DataBoard
} from '@element-plus/icons-vue'

import { ElMessageBox, ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'


// 导入组合式函数
import useExcelTable from './useExcelTable.js'
import useExcelData from './useExcelData.js'
import useExcelEdit from './useExcelEdit.js'
import useExcelSelection from './useExcelSelection.js'
import useExcelViewerLogic from './useExcelViewerLogic.js'
import useExcelViewerExpose from './useExcelViewerExpose.js'
import { useSelectionSum } from './useSelectionSum.js'
import { getApiUrl } from '@/utils/config'


// 在现有的import语句后添加
import Handsontable from 'handsontable';

// 注册中文语言包
try {
  registerLanguageDictionary(zhCN)
  console.log('✅ 中文语言包已注册')
} catch (error) {
  console.warn('⚠️ 注册中文语言包失败，使用英文:', error.message)
}

// 在现有的响应式变量后添加新变量
const globalFlattenLoading = ref(false)


// 添加计算属性：判断是否启用整体扁平化按钮
const globalFlattenEnabled = computed(() => {
  return props.pdfId && props.excelFileName && props.sheetName && tableData.value.length > 0
})

// 表头数组
const computedColHeaders = computed(() => {
  return computedColumns.value.map(col => col.title || `列${col.data + 1}`);
});


// ============ 新增：选区处理 ============
const selectedRange = ref(null)
const selectedCellsCount = ref(0)



// 添加选区事件处理
const handleSelection = (startRow, startCol, endRow, endCol) => {
  console.log('🎯🎯🎯🎯 选区选择事件被触发:', {
    startRow,
    startCol,
    endRow,
    endCol,
    时间: new Date().toLocaleTimeString()
  })

  // 检查是否是有效的选区（不是单个单元格）
  const isSingleCell = (startRow === endRow && startCol === endCol)

  if (isSingleCell) {
    console.log('⏸⏸⏸️ 这是单个单元格，不是选区')
    // 单个单元格的处理
    const cellValue = tableData.value[startRow]?.[startCol] || ''
    emit('cell-selected', {
      isRange: false,
      position: `R${startRow + 1}C${startCol + 1}`,
      content: cellValue,
      type: typeof cellValue === 'number' ? '数值' : '文本',
      isNumeric: typeof cellValue === 'number',
      row: startRow,
      col: startCol
    })
    return
  }

  // 多个单元格选区
  const rowCount = Math.abs(endRow - startRow) + 1
  const colCount = Math.abs(endCol - startCol) + 1
  const totalCells = rowCount * colCount

  selectedRange.value = {
    start: { row: startRow, col: startCol },
    end: { row: endRow, col: endCol },
    rowCount,
    colCount,
    totalCells
  }

  selectedCellsCount.value = totalCells

  console.log('📊📊 选区统计:', {
    行数: rowCount,
    列数: colCount,
    总单元格数: totalCells
  })

  // 发射选区信息给父组件
  emit('cell-selected', {
    isRange: true,
    range: selectedRange.value,
    totalCells: totalCells,
    position: `R${startRow + 1}C${startCol + 1}:R${endRow + 1}C${endCol + 1}`,
    content: `选中 ${totalCells} 个单元格`,
    type: '选区',
    rangeInfo: {
      rowCount: rowCount,
      colCount: colCount,
      totalCells: totalCells
    }
  })

  console.log('📤📤 发射选区信息完成')
}


// 1. 先添加辅助函数（放在文件顶部或合适位置）
const convertObjectArrayToArray = (objectArray) => {
  if (!objectArray || objectArray.length === 0) return [];

  const keys = Object.keys(objectArray[0] || {});
  const result = [keys]; // 第一行是表头

  objectArray.forEach(row => {
    const rowArray = keys.map(key => row[key] ?? '');
    result.push(rowArray);
  });

  return result;
};


const handleInsertColumn = async (colIndex) => {
  try {
    const hot = getSafeHotInstance();
    if (!hot) return;

    console.log('🎯 插入列到索引:', colIndex);

    // 1. 获取当前数据（对象数组格式）
    const currentData = hot.getSourceData();
    if (!currentData || currentData.length === 0) {
      ElMessage.warning('表格数据为空，无法插入列');
      return;
    }

    // 2. 生成新的列名（避免重复）
    const newColName = generateNewColumnName(currentData[0], colIndex);

    // 3. 构建新的数据：在指定位置插入新列
    const newData = currentData.map((row, rowIndex) => {
      const newRow = {};
      const keys = Object.keys(row);

      // 在指定位置插入新键
      keys.forEach((key, index) => {
        if (index === colIndex) {
          newRow[newColName] = ''; // 新列空值
        }
        newRow[key] = row[key];
      });

      // 如果插入位置在最后
      if (colIndex >= keys.length) {
        newRow[newColName] = '';
      }

      return newRow;
    });

    // 4. 🔥 关键：更新 columns 配置，插入新列定义
    if (columns.value && columns.value.length > 0) {
      const newColumnDef = {
        data: newColName,  // 使用字段名而不是索引
        title: newColName,
        readOnly: !isEditMode.value
      };

      // 在指定位置插入
      const newColumns = [...columns.value];
      newColumns.splice(colIndex, 0, newColumnDef);

      // 更新 columns（这会触发 computedColumns 重新计算）
      columns.value = newColumns;
    }

    // 5. 使用 loadData 更新数据（不触发 afterChange 的修改标记）
    hot.loadData(newData);

    console.log('✅ 插入列完成，新列数:', Object.keys(newData[0]).length);
    ElMessage.success(`已插入新列 "${newColName}"`);

  } catch (error) {
    console.error('❌ 插入列失败:', error);
    ElMessage.error('插入列失败: ' + error.message);
  }
};

// 生成唯一的列名
const generateNewColumnName = (firstRow, insertIndex) => {
  const existingKeys = Object.keys(firstRow);
  let newName = `列${insertIndex + 1}`;
  let counter = 1;

  while (existingKeys.includes(newName)) {
    newName = `新列${counter}`;
    counter++;
  }

  return newName;
};


// 3. 然后修改现有的 getContextMenuConfig 函数
const getContextMenuConfig = computed(() => {
  return {
    items: {
      'row_above': {
        name: '在上方插入行',
        disabled: !isEditMode.value
      },
      'row_below': {
        name: '在下方插入行',
        disabled: !isEditMode.value
      },
      'col_left': {
        name: '在左侧插入列',
        disabled: !isEditMode.value,
        callback: function(key, selection) {
          const startCol = selection[0]?.[1] || 0;
          handleInsertColumn(startCol); // 使用新的处理函数
        }
      },
      'col_right': {
        name: '在右侧插入列',
        disabled: !isEditMode.value,
        callback: function(key, selection) {
          const startCol = selection[0]?.[1] || 0;
          handleInsertColumn(startCol + 1); // 在右侧插入
        }
      },
      'remove_row': {
        name: '删除行',
        disabled: !isEditMode.value
      },
      'remove_col': {
        name: '删除列',
        disabled: !isEditMode.value
      },
      'separator': Handsontable.plugins.ContextMenu.SEPARATOR,
      'clear_custom': {
        name: '清除内容',
        callback: function(key, selection) {
          const hot = this
          selection.forEach(([startRow, startCol, endRow, endCol]) => {
            for (let row = startRow; row <= endRow; row++) {
              for (let col = startCol; col <= endCol; col++) {
                hot.setDataAtCell(row, col, '')
              }
            }
          })
        }
      }
    }
  }
})



// 清除选区
const clearSelection = () => {
  console.log('🗑🗑️ 清除选区')
  selectedRange.value = null
  selectedCellsCount.value = 0

  // 发射清除选区事件
  emit('cell-selected', {
    isRange: false,
    position: '',
    content: '',
    type: '文本'
  })
}


// 在接收数据的组件中
const handleGlobalFlattenComplete = (eventData) => {
  console.log('📥 接收到的数据:', {
    数据长度: eventData.flattenedData?.length,
    数据来源: '整体扁平化',
    时间戳: new Date().toLocaleTimeString()
  })

  // 强制更新状态
  if (eventData.flattenedData && eventData.flattenedData.length > 0) {
    // 清空旧数据
    flattenedData.value = []

    // 下一帧再设置新数据，确保DOM更新
    nextTick(() => {
      flattenedData.value = eventData.flattenedData
      console.log('✅ 数据已更新')
    })
  }
}





// 获取路由实例
const router = useRouter()

// 🔥🔥🔥 新增：离开页面提醒相关状态
const hasUnsavedChanges = computed(() => hasChanges.value && modifiedCellsCount.value > 0)
const isNavigatingAway = ref(false)

// 🔥🔥🔥 新增：浏览器标签页关闭提醒
const handleBeforeUnload = (event) => {
  if (hasUnsavedChanges.value) {
    event.preventDefault()
    // 标准浏览器提示
    event.returnValue = '您有未保存的修改，确定要离开吗？'
    return '您有未保存的修改，确定要离开吗？'
  }
}

// 🔥🔥🔥 新增：离开页面确认对话框
const showLeaveConfirmation = () => {
  return new Promise((resolve) => {
    ElMessageBox({
      title: '未保存的修改',
      message: `您有 ${modifiedCellsCount.value} 个未保存的修改，确定要离开当前页面吗？`,
      confirmButtonText: '立即保存',
      cancelButtonText: '仍要离开',
      type: 'warning',
      showClose: true,
      closeOnClickModal: false,
      closeOnPressEscape: false,
      beforeClose: async (action, instance, done) => {
        if (action === 'confirm') {
          // 立即保存
          instance.confirmButtonLoading = true
          instance.confirmButtonText = '保存中...'

          try {
            // 🔥🔥🔥 使用原有的保存逻辑
            await triggerSave() // 调用原有的保存函数
            done()
            resolve(true) // 保存后允许离开
          } catch (error) {
            instance.confirmButtonLoading = false
            instance.confirmButtonText = '立即保存'
            ElMessage.error('保存失败: ' + error.message)
            // 保存失败，不关闭对话框
          }
        } else if (action === 'cancel') {
          // 不保存直接离开
          done()
          resolve(true)
        } else {
          // 点击关闭按钮，取消离开
          done()
          resolve(false)
          ElMessage.info('已取消离开操作')
        }
      }
    }).then(action => {
      if (action === 'confirm' || action === 'cancel') {
        resolve(true)
      }
    }).catch(() => {
      resolve(false)
    })
  })
}

// 🔥🔥🔥 新增：Vue Router 导航守卫
const setupNavigationGuard = () => {
  const guard = router.beforeEach((to, from, next) => {
    // 同一页面或没有未保存修改，直接放行
    if (to.fullPath === from.fullPath || !hasUnsavedChanges.value || isNavigatingAway.value) {
      next()
      return
    }

    // 阻止导航，显示确认对话框
    showLeaveConfirmation().then((canLeave) => {
      if (canLeave) {
        isNavigatingAway.value = true
        next()
      } else {
        next(false)
      }
    })
  })

  return guard
}

// 🔥🔥🔥 新增：设置事件监听
onMounted(() => {
  // 监听浏览器标签页关闭/刷新
  window.addEventListener('beforeunload', handleBeforeUnload)

  // 设置 Vue Router 导航守卫
  setupNavigationGuard()
})

onUnmounted(() => {
  // 清理事件监听
  window.removeEventListener('beforeunload', handleBeforeUnload)

  // 🔥🔥🔥 清理自动保存定时器
  if (logic.cleanupAutoSave) {
    logic.cleanupAutoSave()
  }
})



// 前端调用时，需要将pdf_id放在URL路径中
const handleGlobalFlatten = async () => {
  if (!props.pdfId) {
    ElMessage.warning('请先选择PDF文件')
    return
  }

  globalFlattenLoading.value = true

  try {
    console.log('🔄 开始整体扁平化处理', {
      pdfId: props.pdfId,
      excelFileName: props.excelFileName,
      sheetName: props.sheetName
    })

    // 构建请求数据（注意：pdf_id现在放在URL路径中）
    const requestData = {
      excel_file: props.excelFileName,
      sheet_name: props.sheetName,
      request_timestamp: Date.now()
    }

    const response = await fetch(getApiUrl(`/excel/global-flatten/${props.pdfId}`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData)
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const result = await response.json()
    console.log('📥 整体扁平化API返回:', result)
    console.log('🔍 返回数据结构检查:', {
      成功: result.success,
      长格式数据长度: result.long_format_data?.length || 0,
      前端行数: result.rows?.length || 0,
      源信息: result.source_info,
      所有字段: Object.keys(result)
    })

    if (result.success && result.long_format_data) {  // 🔥 修改：使用 long_format_data
      // 发射事件给父组件处理数据 - 使用统一格式
      emit('global-flatten-complete', {
        flattenedData: result.long_format_data,  // 🔥 修改：使用 long_format_data
        frontendRows: result.rows,               // 🔥 新增：前端格式数据
        pdfId: result.pdf_id || props.pdfId,     // 使用返回的pdf_id确认
        excelFile: result.source_info?.excel_file || props.excelFileName,
        sheetName: result.source_info?.table_name || '整体扁平化数据',
        sourceInfo: result.source_info,          // 🔥 新增：源信息
        fileInfo: result.file_info,
        processingInfo: {
          originalRows: result.stats?.original_rows || 0,
          flattenedRows: result.stats?.converted_records || result.long_format_data.length
        },
        summary: result.summary                  // 🔥 新增：处理摘要
      })

      // 🔥🔥🔥 关键修复：使用正确的PDF ID
      console.log('🔄🔄🔄🔄 扁平化完成，触发中间栏刷新')

      // 使用扁平化返回的PDF ID，而不是props.pdfId
      const actualPdfId = result.pdf_id || props.pdfId
      await triggerMiddleColumnRefresh(actualPdfId)

      ElMessage.success(`整体扁平化完成，生成 ${result.long_format_data.length} 行数据`)
    } else {
      throw new Error(result.error || '整体扁平化处理失败')
    }

  } catch (error) {
    console.error('❌ 整体扁平化失败:', error)
    ElMessage.error(`整体扁平化失败: ${error.message}`)
  } finally {
    globalFlattenLoading.value = false
  }
}


// 🔥🔥🔥 修改：接收正确的pdfId参数
const triggerMiddleColumnRefresh = async (pdfId) => {
  try {
    console.log('🔄🔄🔄🔄 开始刷新中间栏Excel文件列表', { pdfId })

    // 方法1：通过事件总线通知父组件刷新
    if (typeof window !== 'undefined') {
      // 使用传入的正确pdfId
      window.dispatchEvent(new CustomEvent('excel-list-refresh', {
        detail: {
          pdfId: pdfId, // 🔥 使用正确的ID
          timestamp: Date.now(),
          source: 'global-flatten'
        }
      }))
    }

    // 方法2：直接调用父组件的刷新方法（如果可用）
    if (window.$parent && window.$parent.loadExcelSheets) {
      console.log('🔄🔄 直接重新加载Excel文件列表', { pdfId })
      await window.$parent.loadExcelSheets(pdfId)
    }

    console.log('✅✅ 中间栏刷新触发完成')

  } catch (error) {
    console.warn('⚠️⚠️ 刷新中间栏时出错:', error)
  }
}

// 统一的处理函数
const handleGlobalFlattenedData = (flattenedData, sourceInfo) => {
  try {
    console.log('🔄🔄🔄🔄 处理整体扁平化数据', {
      数据行数: flattenedData.length,
      第一行样本: flattenedData[0],
      源信息: sourceInfo
    })

    if (Array.isArray(flattenedData) && flattenedData.length > 0) {
      // ✅ 正确方式：通过emit通知父组件更新
      emit('update-flat-data', flattenedData)

      // 如果有源信息，也一并传递
      if (sourceInfo) {
        console.log('✅ 同时更新源信息:', sourceInfo)
        // 可以根据需要将源信息传递给父组件
      }

      console.log('✅ 已通知父组件更新扁平化数据', {
        新数据行数: flattenedData.length
      })
    }

    // 自动切换到扁平化模式
    if (!props.showFlatMode) {
      console.log('🔄🔄🔄🔄 自动切换到扁平化模式')
      emit('toggle-flat-mode')
    }

    nextTick(() => {
      if (flatViewer.value) {
        const hotInstance = flatViewer.value.getSafeHotInstance?.()
        if (hotInstance && !hotInstance.isDestroyed) {
          hotInstance.render()
          console.log('✅ 表格已刷新显示')
        }
      }
    })

  } catch (error) {
    console.error('❌❌❌❌ 处理整体扁平化数据失败:', error)
    ElMessage.error(`处理失败: ${error.message}`)
  }
}


const exportFinalLoading = ref(false)
// 导出最终的excel文件
const exportFinalFile = async () => {
  console.log('🎯🎯🎯 最终导出按钮被点击')
  exportFinalLoading.value = true

  try {

    const requestData = {
      pdf_id: props.pdfId,
      excel_file: props.excelFileName, // 当前文件名
      request_timestamp: Date.now()
    }

    // const response = await fetch('/api/excel/export-final-file', {
    const response = await fetch(getApiUrl('/excel/export-final-file'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData)
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`HTTP ${response.status}: ${errorText}`)
    }

    const result = await response.json()

    if (result.success) {
      if (result.file_exists) {
        // 后端返回下载URL
        window.open(result.download_url, '_blank')
        ElMessage.success('最终文件导出成功')
      } else {
        ElMessage.warning('最终文件未生成')
      }
    } else {
      throw new Error(result.error || '导出失败')
    }

  } catch (error) {
    console.error('❌❌❌ 最终导出失败:', error)
    console.error('错误堆栈:', error.stack)
    ElMessage.error(`导出失败: ${error.message}`)
  } finally {
    console.log('🏁 导出流程结束')
    exportFinalLoading.value = false
  }
}


// ============ 核心：Handsontable 实例控制器 ============
class HotInstanceController {
  constructor() {
    this.instance = null
    this.ready = false
    this.waiters = []
    this.initPromise = null
    this.timeout = 5000
  }

  setInstance(hot) {
    if (!hot || hot.isDestroyed) return

    this.instance = hot
    this.ready = true

    // 解决所有等待者
    this.resolveWaiters()

    console.log('🎯 HotInstanceController: 实例已设置', {
      行数: hot.countRows?.(),
      列数: hot.countCols?.()
    })
  }

  waitForReady(timeout = 5000) {
    if (this.ready && this.instance && !this.instance.isDestroyed) {
      return Promise.resolve(this.instance)
    }

    return new Promise((resolve, reject) => {
      const waiterId = Date.now() + Math.random()
      this.waiters.push({ id: waiterId, resolve, reject })

      const timer = setTimeout(() => {
        const index = this.waiters.findIndex(w => w.id === waiterId)
        if (index > -1) {
          this.waiters.splice(index, 1)
          reject(new Error(`Handsontable 实例 ${timeout}ms 内未就绪`))
        }
      }, timeout)

      // 为第一个等待者启动健康检查
      if (this.waiters.length === 1 && !this.initPromise) {
        this.startHealthCheck()
      }
    })
  }

  startHealthCheck() {
    this.initPromise = new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (this.ready && this.instance && !this.instance.isDestroyed) {
          clearInterval(checkInterval)
          resolve(this.instance)
          this.resolveWaiters()
        }
      }, 100)

      // 超时停止检查
      setTimeout(() => {
        clearInterval(checkInterval)
        if (!this.ready) {
          console.warn('⚠️ Handsontable 健康检查超时')
        }
      }, this.timeout)
    })
  }

  resolveWaiters() {
    while (this.waiters.length > 0) {
      const waiter = this.waiters.shift()
      if (waiter.resolve) {
        try {
          waiter.resolve(this.instance)
        } catch (err) {
          console.error('解析等待者失败:', err)
        }
      }
    }
  }

  getInstance() {
    return this.instance
  }

  isReady() {
    return this.ready && this.instance && !this.instance.isDestroyed
  }

  destroy() {
    this.ready = false
    this.waiters = []
    this.initPromise = null
    if (this.instance && !this.instance.isDestroyed) {
      this.instance.destroy()
    }
    this.instance = null
  }
}

// 创建全局控制器
const hotController = new HotInstanceController()
const hotInstanceRef = ref(null)

// ============ Props & Emits ============
const emit = defineEmits([
  'cell-changed',
  'data-changed',
  'edit-status-changed',
  'cell-change',
  'instance-ready',
  'global-flatten-complete',
  'cell-selected',
  'save-data',
  'selection-sum-changed'
])

const props = defineProps({
  excelData: {
    type: Array,
    default: () => []
  },
  flatData: {
    type: Array,
    default: () => []
  },
  sheetName: String,
  pdfId: String,
  excelFileName: String,
  enableSaveButtons: {
    type: Boolean,
    default: false
  },
  saving: {
    type: Boolean,
    default: false
  }
})

// ============ 组合式函数初始化 ============

// 表格实例管理
const {
  hotTable,
  excelContainer,
  tableHeight,
  showScrollHint,
  getSafeHotInstance,
  setupEventListeners,
  cleanup,
} = useExcelTable(props)

// 语言相关
const currentLanguage = ref('zh-CN')
const langKey = ref('zh-CN-' + Date.now())


// 添加保存按钮点击处理函数
const triggerSave = () => {
  console.log('💾💾 HandsontableExcelViewer: 保存按钮点击')
  // 发射事件给父组件处理保存
  emit('save-data')
}

// 优化的实例获取函数
const getHotInstanceDirect = () => {
  try {
    // 优先级1：通过控制器获取
    if (hotController.isReady()) {
      return hotController.getInstance()
    }

    // 优先级2：通过组件ref获取
    if (hotTable.value && hotTable.value.hotInstance) {
      const instance = hotTable.value.hotInstance
      if (!instance.isDestroyed) {
        hotController.setInstance(instance)
        return instance
      }
    }

    // 优先级3：从DOM获取
    const hotElement = excelContainer.value?.querySelector?.('.handsontable')
    if (hotElement && hotElement.hotInstance) {
      const instance = hotElement.hotInstance
      if (!instance.isDestroyed) {
        hotController.setInstance(instance)
        return instance
      }
    }

    // 优先级4：全局变量
    if (window.__excelHotInstance && !window.__excelHotInstance.isDestroyed) {
      hotController.setInstance(window.__excelHotInstance)
      return window.__excelHotInstance
    }

    return null
  } catch (error) {
    console.warn('直接获取 Handsontable 实例失败:', error)
    return null
  }
}


// 🔥🔥🔥🔥 修改：将空格相关状态改为数据高亮状态
const showNumericCellsHighlight = ref(false)
const numericCellsStats = ref({
  count: 0,
  sum: 0,
  average: 0,
  max: 0,
  min: 0
})

// 🔥🔥🔥🔥 修改：切换数据高亮显示
const toggleNumericCellsHighlight = () => {
  showNumericCellsHighlight.value = !showNumericCellsHighlight.value

  if (showNumericCellsHighlight.value) {
    // 检测数据单元格
    const numericData = detectNumericCells()
    hasNumericCells.value = numericData.hasNumericCells
    numericCellsStats.value = getNumericStats()

    // 高亮显示数据单元格
    highlightNumericCells()

    ElMessage.success(`发现 ${numericData.totalNumericCells} 个数据单元格`)
  } else {
    // 清除高亮
    clearNumericCellsHighlight()
  }
}

// 在现有的响应式变量后添加（约第60行附近）
const hasNumericCells = computed(() => {
  if (!tableData.value || tableData.value.length === 0) return false

  // 简化的数值单元格检测逻辑
  for (let row = 0; row < tableData.value.length; row++) {
    if (!tableData.value[row]) continue

    for (let col = 0; col < tableData.value[row].length; col++) {
      const value = tableData.value[row][col]

      // 检测数值类型
      if (typeof value === 'number' && !isNaN(value)) {
        return true
      }

      // 检测可转换为数字的字符串
      if (typeof value === 'string' && value.trim() !== '') {
        const num = Number(value.trim())
        if (!isNaN(num) && isFinite(num)) {
          return true
        }
      }
    }
  }
  return false
})

// 🔥🔥🔥🔥 新增：高亮数据单元格
const highlightNumericCells = () => {
  const hot = getSafeHotInstance()
  if (!hot || hot.isDestroyed) return

  const { numericCells } = detectNumericCells()
  const cellConfig = numericCells.map(cell => ({
    row: cell.row,
    col: cell.col,
    className: 'numeric-cell-highlight'
  }))

  if (cellConfig.length > 0) {
    hot.updateSettings({ cell: cellConfig }, false)
    hot.render()
    console.log('✅ 数据单元格高亮已应用')
  }
}

// 🔥🔥🔥🔥 新增：清除数据单元格高亮
const clearNumericCellsHighlight = () => {
  const hot = getSafeHotInstance()
  if (!hot || hot.isDestroyed) return

  // 清除所有 numeric-cell-highlight 类
  const currentCellConfig = hot.getSettings().cell || []
  const filteredCellConfig = currentCellConfig.filter(cell =>
    cell.className !== 'numeric-cell-highlight'
  )

  hot.updateSettings({ cell: filteredCellConfig }, false)
  hot.render()
  console.log('✅ 数据单元格高亮已清除')
}


// 1. 检测数值单元格函数（支持千位符、括号负数、负号等）
const detectNumericCells = () => {
  if (!tableData.value || tableData.value.length === 0) {
    return { hasNumericCells: false, totalNumericCells: 0, numericCells: [] }
  }

  console.log('🔍🔍 开始检测数值单元格...')
  const numericCells = []

  // 数值解析函数（支持多种格式）
  const parseNumericValue = (value) => {
    if (value === null || value === undefined || value === '') {
      return null
    }

    // 如果是数字类型直接返回
    if (typeof value === 'number') {
      return !isNaN(value) && isFinite(value) ? value : null
    }

    // 字符串处理
    if (typeof value === 'string') {
      let str = value.trim()

      if (str === '') return null

      // 排除常见的非数值文本
      const nonNumericPatterns = [
        'null', 'NULL', 'Null', 'nan', 'NaN', 'NAN', 'Nan',
        'none', 'None', 'NONE', 'n/a', 'N/A', 'na', 'NA',
        '空', '空白', '空缺', '缺省', 'undefined', 'Undefined', 'UNDEFINED'
      ]

      if (nonNumericPatterns.includes(str.toLowerCase())) {
        return null
      }

      // 处理括号表示的负数，如：(322) -> -322
      if (str.startsWith('(') && str.endsWith(')')) {
        str = '-' + str.slice(1, -1)
      }

      // 移除千位符（逗号）
      str = str.replace(/,/g, '')

      // 移除货币符号、空格等
      str = str.replace(/[$\s¥€£]/g, '')

      // 处理百分比（如果有）
      let isPercentage = false
      if (str.endsWith('%')) {
        str = str.slice(0, -1)
        isPercentage = true
      }

      // 尝试转换为数字
      const num = Number(str)
      if (!isNaN(num) && isFinite(num)) {
        return isPercentage ? num / 100 : num
      }
    }

    return null
  }

  // 遍历所有单元格
  for (let row = 0; row < tableData.value.length; row++) {
    if (!tableData.value[row]) continue

    for (let col = 0; col < tableData.value[row].length; col++) {
      const cellValue = tableData.value[row][col]
      const numericValue = parseNumericValue(cellValue)

      if (numericValue !== null) {
        numericCells.push({
          row,
          col,
          value: numericValue,
          originalValue: cellValue,
          formattedValue: formatNumericValue(numericValue)
        })
      }
    }
  }

  console.log('📊📊 数值单元格统计（支持千位符、括号负数等）:', {
    总数: numericCells.length,
    样本: numericCells.slice(0, 5).map(cell => ({
      原始值: cell.originalValue,
      解析值: cell.value,
      位置: `R${cell.row + 1}C${cell.col + 1}`
    }))
  })

  return {
    hasNumericCells: numericCells.length > 0,
    totalNumericCells: numericCells.length,
    numericCells
  }
}

// 2. 获取数值统计信息函数
const getNumericStats = () => {
  const { numericCells } = detectNumericCells()

  if (numericCells.length === 0) {
    return {
      count: 0,
      sum: 0,
      average: 0,
      max: 0,
      min: 0
    }
  }

  const values = numericCells.map(cell => cell.value)
  const sum = values.reduce((acc, val) => acc + val, 0)
  const average = sum / values.length
  const max = Math.max(...values)
  const min = Math.min(...values)

  return {
    count: values.length,
    sum: formatNumericValue(sum),
    average: formatNumericValue(average),
    max: formatNumericValue(max),
    min: formatNumericValue(min)
  }
}

// 3. 数值格式化函数（需要同时添加）
const formatNumericValue = (value) => {
  if (typeof value !== 'number' || isNaN(value) || !isFinite(value)) {
    return String(value)
  }

  // 整数直接返回
  if (Number.isInteger(value)) {
    return value.toLocaleString() // 添加千位分隔符
  }

  // 浮点数保留2位小数，并添加千位分隔符
  return value.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}




// 在现有代码之后添加求和功能
const {
  getFormattedValues,
  formatNumber,
  selectionSum,
  calculateSelectionSum,
  clearSelectionSum,
  setupSelectionSumListener
} = useSelectionSum(getSafeHotInstance)

watch(selectionSum, (newVal) => {
  emit('selection-sum-changed', newVal)
}, { deep: true })


onMounted(() => {
  // 确保Handsontable已加载
  if (typeof Handsontable === 'undefined') {
    console.error('❌ Handsontable未加载')
    return
  }

  // 强制注册Alter插件
  if (!Handsontable.plugins.Alter) {
    console.log('🔥 强制注册Alter插件...')

    Handsontable.plugins.Alter = function(hotInstance) {
      this.hot = hotInstance;
      this.enabled = true;
    };

    Handsontable.plugins.Alter.prototype.isEnabled = function() {
      return this.enabled;
    };

    Handsontable.plugins.Alter.prototype.enablePlugin = function() {
      if (this.enabled) {
        return;
      }
      this.enabled = true;
    };

    Handsontable.plugins.Alter.prototype.disablePlugin = function() {
      this.enabled = false;
    };

    Handsontable.plugins.Alter.prototype.alter = function(action, index, amount, source, keepEmptyRows) {
      if (!this.enabled) {
        return;
      }

      const dataMap = this.hot.getDataMap();
      const result = dataMap.createCol(index, amount, source);

      if (result) {
        this.hot.forceFullRender();
        this.hot.view.adjustElementsSize(true);
      }

      return result;
    };

    console.log('✅ Alter插件已强制注册')
  }
})


// 获取增强版实例（兼容原有逻辑）
const getEnhancedHotInstance = () => {
  const instance = getSafeHotInstance()
  if (instance) {
    try {
      if (instance.isDestroyed) {
        console.warn('⚠️ 表格实例已销毁')
        return null
      }
      const settings = instance.getSettings()
      if (!settings) {
        console.warn('⚠️ 无法获取表格设置')
        return null
      }
      return instance
    } catch (error) {
      console.warn('⚠️ 验证表格实例失败:', error)
      return null
    }
  }
  return null
}

// 数据处理
const {
  tableData,
  hasDualHeaders,
  tableInfo,
  fixedRowsTop,
  fixedColumnsLeft,
  columns,
  verifyTableStructure,
  exportData,
  detectEmptyCells,
  hasEmptyCells,
  emptyCellsStats
} = useExcelData(props)

// 编辑功能
const {
  isEditMode,
  hasChanges,
  saving,
  modifiedCellsCount,
  modifiedCells,
  saveChanges: saveChangesInternal,
  onDataChange,
  updateTableReadOnly,
  resetChanges,
  savedCells,
  unsavedCells,
  collectModifiedData,
  updateModifiedCellsStyle,
  markSavedCells,
  toggleEditMode: toggleEditModeFromHook,
  checkInstanceHealth,
  refreshCache,
  clearCache,
  validateHotInstance,
  getHotInstance: getHotInstanceFromHook
} = useExcelEdit(getEnhancedHotInstance)

// 选择统计
const {
  showStatsPanel,
  stats,
  currentSelection,
  calculateSelectionStats,
  clearSelection: clearSelectionStats,
  setupColumnSelectionListener
} = useExcelSelection(getSafeHotInstance, selectedRange)

// 主要逻辑
const logic = useExcelViewerLogic(
  props,
  {
    hotTable,
    getSafeHotInstance,
    isEditMode,
    hasChanges,
    modifiedCells,
    modifiedCellsCount,
    savedCells,
    unsavedCells,
    tableData,
    hasDualHeaders,
    tableInfo,
    columns,
    hasEmptyCells,
    detectEmptyCells,
    emptyCellsStats,
    showStatsPanel,
    stats,
    calculateSelectionStats,
    clearSelection,
    updateTableReadOnly,
    markSavedCells,
    toggleEditModeFromHook,
    highlightEmptyCells: () => {},
    clearEmptyCellsHighlight: () => {},
    cleanup,
    onDataChange
  },
  emit
)

// 添加这3个关键方法
defineExpose({
  clearSelectionSum,
  waitForInstanceReady: (timeout = 5000) => hotController.waitForReady(timeout),
  getHotInstance: () => hotController.getInstance(),
  isInstanceReady: () => hotController.isReady(),
})

// 保留原有的 useExcelViewerExpose 调用（不要删除）
useExcelViewerExpose({
  exportData,
  tableData,
  verifyTableStructure,
  clearSelection,
  getSafeHotInstance,
  markSavedCells: logic.markSavedCells,
  markMultipleCellsAsSaved: logic.markMultipleCellsAsSaved,
  forceFixSavedCellsStyles: logic.forceFixSavedCellsStyles,
  clearSavedMarks: logic.clearSavedMarks,
  getSavedCellsState: logic.getSavedCellsState,
  debugSavedCells: logic.debugSavedCells,
  restoreCellStates: logic.restoreCellStates,
  toggleEditMode: logic.toggleEditMode,
  forceFixStyles: logic.forceFixStyles,
})


// 在现有的代码后面添加这个测试函数
const testSelectionEvent = () => {
  console.log('🧪🧪 手动测试选区事件')

  // 模拟一个选区事件
  handleSelection(0, 0, 2, 2) // 选择 3x3 的选区

  // 检查事件是否被发射
  console.log('🔍🔍 检查 selectedRange:', selectedRange.value)
}

// 暴露给全局用于测试
if (typeof window !== 'undefined') {
  window.testSelection = testSelectionEvent
  console.log('✅ testSelection 函数已暴露到全局')
}


// 模板中使用的属性和方法
const {
  showEmptyCellsHighlight,
  selectedCell,
  colWidths,
  computedColumns,
  toggleEmptyCellsHighlight,
  toggleEditMode,
  onFilter
} = logic

// 组件销毁时清理
onUnmounted(() => {
  hotController.destroy()
  if (window.__excelHotInstance === hotInstanceRef.value) {
    window.__excelHotInstance = null
  }
})



const onHotInit = () => {
  setTimeout(() => {
    const hot = getHotInstanceDirect()
    if (hot) {
      hotInstanceRef.value = hot
      hotController.setInstance(hot)
      window.__excelHotInstance = hot

      console.log('⚡⚡ Handsontable 实例已立即暴露', {
        行数: hot.countRows(),
        列数: hot.countCols(),
        实例ID: hot.guid,
        时间戳: Date.now()
      })

      // 🔥🔥 关键修复：禁用排序，避免三角号重叠
      console.log('🔍🔍 配置筛选下拉菜单（禁用排序）...')
      hot.updateSettings({
        filters: true,
        dropdownMenu: {
            items: {
              filter_by_value: {name: '按值筛选'},
              filter_operators: {name: '筛选条件'},
              filter_action_bar: {name: '筛选操作'}
            }
          },
        columnSorting: false  // ✅ 修改这里：禁用排序功能
      }, false)

      console.log('✅ 筛选下拉菜单已配置（排序已禁用）')

      // 检查当前配置
      const settings = hot.getSettings()
      console.log('🔍🔍 当前生效配置:')
      console.log('- filters:', settings.filters)
      console.log('- dropdownMenu:', settings.dropdownMenu)
      console.log('- columnSorting:', settings.columnSorting)  // 现在应该是 false

      // 🔥🔥 详细检查筛选插件
      const filterPlugin = hot.getPlugin('filters')
      if (filterPlugin) {
        console.log('✅ Filters 插件状态:', {
          已启用: filterPlugin.isEnabled(),
          插件方法: Object.keys(filterPlugin)
        })
      }

      // 🔥🔥 检查下拉菜单容器
      setTimeout(() => {
        console.log('🔍🔍 检查下拉菜单容器...')
        const dropdownContainers = document.querySelectorAll('.htDropdownMenu')
        console.log(`✅ 找到 ${dropdownContainers.length} 个下拉菜单容器`)

        dropdownContainers.forEach((container, index) => {
          console.log(`下拉菜单容器 ${index}:`, {
            可见性: window.getComputedStyle(container).visibility,
            显示: window.getComputedStyle(container).display,
            zIndex: window.getComputedStyle(container).zIndex
          })
        })
      }, 1000)

      emit('instance-ready', {
        instance: hot,
        guid: hot.guid,
        pdfId: props.pdfId,
        excelFileName: props.excelFileName,
        sheetName: props.sheetName,
        tableType: props.excelData === props.flatData ? 'flattened' : 'original',
        timestamp: Date.now()
      })

      nextTick(() => restoreModifiedCellsStyle())
    }
  }, 0)

  setTimeout(() => {
    setupSelectionSumListener()
  }, 100)
}



// 监听选中区域统计事件
onMounted(() => {
  const handleSelectionSumChanged = (event) => {
    console.log('📥 HandsontableExcelViewer 收到统计事件:', event.detail)
    // 转发给父组件 ExcelContent
    emit('selection-sum-changed', event.detail)
  }

  window.addEventListener('selection-sum-changed', handleSelectionSumChanged)

  // 清理事件监听
  onUnmounted(() => {
    window.removeEventListener('selection-sum-changed', handleSelectionSumChanged)
  })
})

</script>


<style scoped>
/* ====================
   基础容器和重置样式
   ==================== */
.handsontable-excel-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.horizontal-scroll-hint {
  position: absolute;
  bottom: 5px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 100;
  animation: fadeInOut 2s ease-in-out;
}

@keyframes fadeInOut {
  0%, 100% { opacity: 0; }
  50% { opacity: 1; }
}

/* ====================
   工具栏区域样式
   ==================== */
.main-toolbar {
  flex-shrink: 0;
  padding: 8px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 52px;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.left-section {
  flex: 1;
}

.center-section {
  flex: 1;
  justify-content: center;
}

.right-section {
  flex: 1;
  justify-content: flex-end;
}

.data-summary {
  background: #f0f9ff;
  border-color: #e1f5fe;
  color: #1890ff;
}

.dual-header-info {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  background: #f6ffed;
  border-radius: 4px;
  border: 1px solid #b7eb8f;
}

.structure-info {
  font-size: 12px;
  color: #52c41a;
  font-weight: 500;
}

.status-tag {
  cursor: default;
  transition: all 0.2s;
  min-width: 60px;
  text-align: center;
}

.status-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.global-flatten-btn {
  background-color: #1890ff;
  border-color: #1890ff;
  color: white;
  font-weight: 600;
}

.global-flatten-btn:hover {
  background-color: #40a9ff;
  border-color: #40a9ff;
}

.global-flatten-btn:disabled {
  background-color: #a0d0ff;
  border-color: #a0d0ff;
  color: #e6f7ff;
}

/* ====================
   选中区域统计栏
   ==================== */
.selection-summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: linear-gradient(135deg, #f6ffed 0%, #f0fff3 100%);
  border-bottom: 1px solid #b7eb8f;
  border-left: 4px solid #52c41a;
  animation: slideDown 0.3s ease;
  margin: 2px 0;
}

.sum-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  flex-wrap: wrap;
}

.sum-info .el-icon {
  color: #52c41a;
  font-size: 16px;
}

.sum-label {
  font-weight: 600;
  color: #389e0d;
}

.sum-value {
  font-weight: 700;
  color: #135200;
  font-size: 16px;
  background: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #b7eb8f;
  box-shadow: 0 1px 3px rgba(82, 196, 26, 0.2);
}

.sum-details {
  color: #73d13d;
  font-size: 12px;
  margin-left: 8px;
}

.sum-stats {
  color: #95de64;
  font-size: 11px;
  margin-left: 12px;
  opacity: 0.8;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ====================
   功能操作栏
   ==================== */
.action-toolbar {
  flex-shrink: 0;
  padding: 8px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.action-toolbar.compact-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-direction: row;
}

.action-group {
  background: white;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 8px 12px;
}

.selection-stats-group {
  flex: 1;
  min-width: 0;
  border-left: 3px solid #52c41a;
}

.current-cell-inline {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: center;
}

.operation-buttons-group {
  flex-shrink: 0;
}

.operation-buttons-group.right-aligned {
  margin-left: auto;
  border-left: 3px solid #1890ff;
  padding: 6px 12px;
}

.operation-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #f0f0f0;
}

.group-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.stats-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  flex: 1;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 8px;
  background: #f0f9ff;
  border-radius: 4px;
  border: 1px solid #e1f5fe;
  min-width: 120px;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

.stat-value {
  font-size: 12px;
  font-weight: 500;
  color: #1890ff;
}

.clear-btn {
  margin-left: 12px;
}

/* ====================
   表格容器区域
   ==================== */
.excel-container {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  position: relative;
  border: 1px solid #e0e0e0;
  background: white;
  padding-top: 1px;
  height: 100%;
}

/* ====================
   Handsontable 深度样式
   ==================== */
:deep(.handsontable .wtHolder) {
  overflow: auto !important;
}

:deep(.handsontable) {
  height: 100%;
}

:deep(.ht_clone_top) {
  z-index: 999 !important;
  overflow: visible !important;
}

:deep(.ht_clone_top .wtHolder) {
  overflow: hidden !important;
}

:deep(.ht_master .wtHolder) {
  overflow: auto !important;
  width: 100% !important;
}

:deep(.ht_clone_left::-webkit-scrollbar) {
  display: none !important;
}

:deep(.vertical-header-column) {
  background-color: #f6ffed !important;
  font-weight: 600 !important;
  min-width: 120px !important;
}

:deep(.ht_clone_left) {
  -ms-overflow-style: none !important;
  scrollbar-width: none !important;
}

:deep(.ht_clone_top th) {
  background-color: #f0f9ff !important;
  border-bottom: 2px solid #409eff !important;
}

:deep(.ht_clone_left table) {
  height: 100% !important;
}

:deep(.ht_clone_top th:first-child) {
  background: linear-gradient(135deg, #f0f9ff 50%, #f6ffed 50%) !important;
  border-right: 2px solid #409eff !important;
  border-bottom: 2px solid #52c41a !important;
}

:deep(.ht_clone_left td) {
  background-color: #f6ffed !important;
  border-right: 2px solid #52c41a !important;
}

:deep(.ht_clone_top th) {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
  height: 20px !important;
  min-height: 20px !important;
  line-height: 20px !important;
  box-sizing: border-box !important;
}

:deep(.ht_clone_top) {
  background-color: #f8f9fa !important;
}

/* ====================
   单元格样式
   ==================== */
:deep(.handsontable td.modified-cell),
:deep(.handsontable .htCore td.modified-cell),
:deep(.handsontable .htCore tbody tr td.modified-cell),
:deep(.handsontable .htCore thead tr th.modified-cell) {
  background-color: #ffd8d2 !important;
  border: 1px solid #ff7875 !important;
  position: relative;
  z-index: 10;
}

:deep(.handsontable td.modified-cell::after),
:deep(.handsontable .htCore td.modified-cell::after) {
  content: '';
  position: absolute;
  top: 3px;
  right: 3px;
  width: 6px;
  height: 6px;
  background-color: #ff4d4f;
  border-radius: 50%;
  z-index: 100;
  display: block !important;
}

.edit-mode :deep(.handsontable .htCore td:not([readonly])) {
  background-color: #f9f9f9 !important;
  border: 1px solid #d9d9d9 !important;
}

.edit-mode :deep(.handsontable .htCore td) {
  cursor: cell !important;
}

:not(.edit-mode) :deep(.handsontable .htCore td) {
  cursor: default !important;
}

:deep(.handsontable .htCore td:not(.modified-cell):hover) {
  background-color: #f0f6ff !important;
  border-color: #1890ff !important;
}

:deep(.handsontable .htCore td.modified-cell:hover) {
  background-color: #ffe7d9 !important;
  border-color: #ff7a45 !important;
  box-shadow: 0 0 0 1px #ff7a45;
}

:deep(.handsontable .htCore td.modified-cell.current) {
  background-color: #ffd8bf !important;
  border-color: #ff7a45 !important;
}

:deep(.handsontable td.empty-cell) {
  background-color: #f0f9ff !important;
  border: 2px dashed #1890ff !important;
  position: relative;
}

:deep(.handsontable td.empty-cell::after) {
  content: '空';
  position: absolute;
  top: 1px;
  right: 1px;
  font-size: 9px;
  color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
  padding: 0 2px;
  border-radius: 2px;
  opacity: 0.7;
}

.edit-mode :deep(.handsontable td.empty-cell) {
  background-color: #e6f7ff !important;
  border: 2px dotted #1890ff !important;
}

:deep(.handsontable td.unsaved-modified-cell) {
  background-color: #ffd8d2 !important;
  border: 1px solid #ff7875 !important;
  position: relative;
}

:deep(.handsontable td.unsaved-modified-cell::after) {
  content: '';
  position: absolute;
  top: 2px;
  right: 2px;
  width: 6px;
  height: 6px;
  background: #ff4d4f;
  border-radius: 50%;
}

:deep(.handsontable td.history-modified-cell) {
  background-color: #ffe7e6 !important;
  border: 1px solid #ffb7b3 !important;
}

/* ====================
   表头和下拉菜单样式
   ==================== */
:deep(.handsontable thead th) {
  position: relative;
  cursor: pointer;
  overflow: visible !important;
}



:deep(.handsontable thead th:hover::after) {
  opacity: 1;
  color: #409eff;
}

:deep(.htDropdownMenu) {
  z-index: 10000 !important;
  visibility: visible !important;
  display: block !important;
}

:deep(.handsontable .changeType) {
  pointer-events: auto !important;
  cursor: pointer !important;
}

:deep(.handsontable thead th .changeType:hover) {
  background-color: rgba(64, 158, 255, 0.1) !important;
}

:deep(.ht_clone_top) {
  z-index: 100 !important;
}

:deep(.htDropdownMenu .ht_master .wtHolder) {
  z-index: 10001 !important;
}

/* ====================
   响应式设计
   ==================== */
@media (max-width: 1200px) {
  .main-toolbar {
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 12px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stat-item {
    min-width: 140px;
  }

  .operation-buttons {
    gap: 6px;
  }

  .operation-buttons .el-button {
    font-size: 12px;
    padding: 6px 8px;
  }
}

@media (max-width: 1024px) {
  .action-toolbar.compact-line {
    flex-wrap: wrap;
    gap: 12px;
  }

  .operation-buttons-group.right-aligned {
    margin-left: 0;
    width: 100%;
    justify-content: flex-end;
  }

  .operation-buttons {
    justify-content: flex-end;
  }
}

@media (max-width: 768px) {
  .main-toolbar {
    flex-direction: column;
    gap: 8px;
    align-items: stretch;
    padding: 8px 12px;
  }

  .toolbar-section {
    justify-content: center;
    width: 100%;
  }

  .action-toolbar {
    padding: 8px 12px;
    max-height: 400px;
  }

  .action-toolbar.compact-line {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .action-group {
    padding: 8px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .stats-content {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .clear-btn {
    margin-left: 0;
    align-self: flex-end;
  }

  .operation-buttons-group.right-aligned {
    width: 100%;
    border-left: none;
    border-top: 3px solid #1890ff;
    padding: 8px 0;
  }

  .operation-buttons {
    justify-content: space-around;
    flex-wrap: wrap;
  }

  .operation-buttons .el-button {
    flex: 1;
    min-width: 120px;
    margin: 2px;
  }

  .selection-summary-bar {
    padding: 6px 12px;
  }

  .sum-info {
    flex-wrap: wrap;
    gap: 4px;
  }

  .sum-details, .sum-stats {
    margin-left: 0;
  }
}

@media (max-width: 480px) {
  .operation-buttons {
    flex-direction: column;
    gap: 6px;
  }

  .operation-buttons .el-button {
    width: 100%;
    min-width: auto;
  }

  .main-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .toolbar-section {
    justify-content: space-between;
    width: 100%;
  }

  .primary-actions {
    width: 100%;
    justify-content: center;
  }

  .global-status {
    justify-content: center;
    width: 100%;
  }

  .group-header {
    flex-wrap: wrap;
    gap: 4px;
  }
}

/* ====================
   筛选下拉菜单专用样式
   ==================== */


:deep(.htDropdownMenu) {
  min-width: 200px !important;
  max-height: 300px !important;
  overflow-y: auto !important;
}

:deep(.htDropdownMenu .htCore) {
  border: none !important;
}

:deep(.htDropdownMenu .htItem) {
  cursor: pointer !important;
  transition: background-color 0.2s !important;
}

:deep(.htDropdownMenu .htItem:last-child) {
  border-bottom: none !important;
}

/* 筛选条件样式 */
:deep(.htCondition) {
  margin: 4px 0 !important;
}

:deep(.htCondition select) {
  border: 1px solid #dcdfe6 !important;
  border-radius: 4px !important;
  padding: 4px !important;
  font-size: 12px !important;
}


/* 强制显示筛选图标，隐藏排序三角号 */
:deep(.handsontable thead th) {
  position: relative;
  cursor: pointer;
  overflow: visible !important;
}




/* 隐藏排序三角号 */
:deep(.handsontable thead th .columnSortingIndicator) {
  display: none !important;
}



/* ====================
   高对比度筛选图标（更明显）
   ==================== */

:deep(.handsontable thead th .changeType) {
  display: inline-block !important;
  width: 22px !important;
  height: 22px !important;
  position: absolute !important;
  right: 4px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23ffffff"><path d="M10 18h4v-2h-4v2zM3 6v2h18V6H3zm3 7h12v-2H6v2z"/></svg>') no-repeat center !important;
  background-size: 12px 12px !important;
  opacity: 0.9;
  transition: all 0.3s ease;
  z-index: 10;
  pointer-events: auto !important;
  cursor: pointer !important;
  border-radius: 4px;
  background-color: #4096ff !important;  /* 蓝色背景 */
  border: 2px solid #4096ff !important;
  box-shadow: 0 2px 8px rgba(64, 150, 255, 0.4);
}

:deep(.handsontable thead th:hover .changeType) {
  opacity: 1;
  background-color: #1a73e8 !important;  /* 深蓝色 */
  border-color: #1a73e8 !important;
  box-shadow: 0 4px 12px rgba(64, 150, 255, 0.6);
  transform: translateY(-50%) scale(1.1);
}

/* 有筛选条件时显示为橙色 */
:deep(.handsontable thead th.columnFiltered .changeType) {
  background-color: #ff9800 !important;
  border-color: #ff9800 !important;
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23ffffff"><path d="M10 18h4v-2h-4v2zM3 6v2h18V6H3zm3 7h12v-2H6v2z"/></svg>') !important;
  box-shadow: 0 0 0 3px rgba(255, 152, 0, 0.3);
}


/* 数据单元格高亮样式 */
:deep(.handsontable td.numeric-cell-highlight) {
  background-color: #f0f9ff !important;
  border: 2px solid #1890ff !important;
  position: relative;
}

:deep(.handsontable td.numeric-cell-highlight::after) {
  content: '数据';
  position: absolute;
  top: 1px;
  right: 1px;
  font-size: 9px;
  color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
  padding: 0 2px;
  border-radius: 2px;
  opacity: 0.7;
}

.edit-mode :deep(.handsontable td.numeric-cell-highlight) {
  background-color: #e6f7ff !important;
  border: 2px dotted #1890ff !important;
}


/* 数值单元格高亮样式 - 红色主题 */
:deep(.handsontable td.numeric-cell-highlight) {
  background-color: #fff2f0 !important;
  border: 2px solid #ff4d4f !important;
  position: relative;
}

:deep(.handsontable td.numeric-cell-highlight::after) {
  content: '数据';
  position: absolute;
  top: 1px;
  right: 1px;
  font-size: 9px;
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
  padding: 0 2px;
  border-radius: 2px;
  opacity: 0.7;
}

.edit-mode :deep(.handsontable td.numeric-cell-highlight) {
  background-color: #ffece8 !important;
  border: 2px dotted #ff4d4f !important;
}


</style>


