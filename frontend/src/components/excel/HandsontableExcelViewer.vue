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

          <!-- 在这里添加表头指示器 -->
        <div class="header-indicator" v-if="hasDualHeaders && tableInfo">
          <el-tag type="success" size="small">
            <el-icon><Grid /></el-icon>
            双表头表格
          </el-tag>
          <span class="indicator-text">
            结构: {{ tableInfo.横向表头 }}列 × {{ tableInfo.纵向表头 }}行
            <span v-if="tableInfo.左上角"> | 左上角: {{ tableInfo.左上角 }}</span>
          </span>
          <el-button
            size="small"
            type="info"
            link
            @click="verifyTableStructure"
            title="验证表格结构"
          >
            <el-icon><InfoFilled /></el-icon>
          </el-button>
        </div>


          <span class="data-info" v-if="tableData.length > 0">
            共 {{ tableData.length - 1 }} 行 {{ columns.length }} 列
          </span>


          <!-- 统计面板 -->
          <div v-if="showStatsPanel" class="stats-panel">
            <el-tag :type="stats.selectionType === 'column' ? 'info' : 'success'" size="small">
              <el-icon><DataAnalysis /></el-icon>
              {{ stats.selectionType === 'column' ? '整列统计' : '选中区域统计' }}
            </el-tag>
            <span class="stat-item">行数: {{ stats.rowCount }}</span>
            <span class="stat-item">数值: {{ stats.numericCount }}</span>
            <span class="stat-item">总和: {{ stats.sum }}</span>
            <span class="stat-item">平均值: {{ stats.average }}</span>
            <span class="stat-item">最大值: {{ stats.max }}</span>
            <span class="stat-item">最小值: {{ stats.min }}</span>
            <el-button
              v-if="stats.selectionType === 'selection'"
              size="small"
              type="primary"
              link
              @click="clearSelection"
              title="清除选择"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>


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



    <!-- 修改 cell-content-display 部分 -->
    <div class="cell-content-display" v-if="showCellContent && selectedCell.position">
      <!-- 修改 cell-info-bar 部分，区分日期和数字 -->
    <div class="cell-info-bar">
      <div class="cell-position">
        <el-tag size="small" type="info">
          <el-icon><Position /></el-icon>
          {{ selectedCell.position }}
        </el-tag>
      </div>
      <div class="cell-type">
        <el-tag
          size="small"
          :type="getCellTypeTag(selectedCell.type)"
          :title="selectedCell.type + (selectedCell.format ? ' | ' + selectedCell.format : '')"
        >
          {{ selectedCell.type }}
          <span v-if="selectedCell.format" style="margin-left: 4px; font-size: 11px;">
            ({{ selectedCell.format }})
          </span>
        </el-tag>
      </div>

      <!-- 数字验证状态（仅显示数字类型） -->
      <div class="cell-validation" v-if="selectedCell.isNumeric && selectedCell.numberValidationMsg">
        <el-tag
          size="small"
          :type="selectedCell.isValidNumber ? 'success' : 'danger'"
          :title="selectedCell.validationDetails || selectedCell.numberValidationMsg"
        >
          {{ selectedCell.numberValidationMsg }}
        </el-tag>
      </div>

      <!-- 日期类型提示 -->
      <div class="date-hint" v-if="selectedCell.type === '日期' && !selectedCell.isNumeric">
        <el-tag size="small" type="warning" :title="selectedCell.format || '日期类型'">
          <el-icon><Calendar /></el-icon>
          {{ selectedCell.format || '日期' }}
        </el-tag>
      </div>

      <!-- 原有其他标签 -->
      <div class="cell-modified" v-if="selectedCell.isModified">
        <el-tag size="small" type="danger" title="此单元格已被修改">
          <el-icon><Edit /></el-icon>
          已修改
        </el-tag>
      </div>
      <div class="cell-readonly" v-if="selectedCell.isReadOnly">
        <el-tag size="small" type="info" title="此单元格为只读">
          <el-icon><Lock /></el-icon>
          只读
        </el-tag>
      </div>
      <div class="cell-stats">
        <span class="stat-item" title="字符数">字符: {{ selectedCell.charCount }}</span>
        <span v-if="selectedCell.lineCount > 1" class="stat-item" title="行数">
          行数: {{ selectedCell.lineCount }}
        </span>
      </div>
    </div>

      <div class="cell-content-area">
        <div
          ref="cellContentDisplay"
          class="cell-content-text"
          :title="selectedCell.content"
          :class="{
            'numeric-cell': selectedCell.isNumeric,
            'formula-cell': selectedCell.isFormula,
            'modified-cell': selectedCell.isModified,
            'invalid-number': selectedCell.isNumeric && !selectedCell.isValidNumber
          }"
        >
          {{ selectedCell.content || '[空]' }}
        </div>
        <div class="cell-actions" v-if="isEditMode && !selectedCell.isReadOnly">
          <el-button
            size="small"
            type="primary"
            link
            @click="copyCellContent"
            title="复制内容"
          >
            <el-icon><CopyDocument /></el-icon>
          </el-button>
          <el-button
            size="small"
            type="warning"
            link
            @click="editCellInModal"
            title="编辑内容"
            v-if="selectedCell.position"
          >
            <el-icon><Edit /></el-icon>
          </el-button>
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
        licenseKey="non-commercial-and-evaluation"
        :language="currentLanguage"
        :filters="true"
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
        @afterChange="onDataChange"
        @afterFilter="onFilter"
      />


      <div v-if="tableData.length === 0" class="empty-state">
        <el-empty description="暂无表格数据" />
      </div>

      <!-- 新增：横向滚动提示（可选） -->
      <div v-if="showScrollHint" class="horizontal-scroll-hint">
        ← → 可左右滚动查看完整表格
      </div>


    </div>
  </div>
</template>




<script setup>

import Handsontable from 'handsontable'
import { HotTable } from '@handsontable/vue3'
import 'handsontable/dist/handsontable.full.css'
import { Grid, InfoFilled, Position, CopyDocument, Lock, Calendar } from '@element-plus/icons-vue'

const currentLanguage = ref('zh-CN')

// 针对 16.1.1 版本的完整中文语言包
// 替换现有的语言包注册函数
const registerChineseLanguageForV16 = () => {
  try {
    if (Handsontable.languages.getLanguageDictionary('zh-CN')) {
      console.log('✅ zh-CN 语言包已存在')
      return true
    }

    console.log('🔧 注册完整中文语言包...')

    const zhCN = {
      languageCode: 'zh-CN',

      // 核心界面文本
      'labels': {
        'no_data': '暂无数据'
      },

      // 下拉菜单 - 使用更完整的键名
      'dropdownMenu': {
        // 筛选相关
        'filter_by_condition': '按条件筛选',
        'filter_by_value': '按值筛选',
        'filter_action_bar': '筛选操作栏',
        'filter_operators': '筛选运算符',
        'clear_column': '清除筛选',

        // 排序相关
        'sort_asc': '升序排序',
        'sort_desc': '降序排序',

        // 行列操作
        'insert_row_above': '在上方插入行',
        'insert_row_below': '在下方插入行',
        'remove_row': '删除行',
        'insert_col_left': '在左侧插入列',
        'insert_col_right': '在右侧插入列',
        'remove_col': '删除列',

        // 显示隐藏
        'hidden_columns_show': '显示隐藏列',
        'hidden_rows_show': '显示隐藏行',

        // 冻结
        'freeze_column': '冻结列',
        'unfreeze_column': '取消冻结列',

        // 编辑相关
        'undo': '撤销',
        'redo': '重做',
        'make_read_only': '设为只读',
        'alignment': '对齐方式',
        'readOnly': '只读',

        // 通用操作
        'copy': '复制',
        'cut': '剪切',
        'paste': '粘贴',

        // 必需的基础项
        'None': '无',
        'OK': '确定',
        'Cancel': '取消',
        'Search': '搜索',
        'Select all': '全选',
        'Clear': '清除',
        'Apply': '应用',
        'Save': '保存',
        'Add': '添加',
        'Remove': '移除',
        'Edit': '编辑',
        'Duplicate': '复制',
        'Redo': '重做',
        'Undo': '撤销'
      },

      // 上下文菜单
      'contextMenu': {
        'row_above': '在上方插入行',
        'row_below': '在下方插入行',
        'col_left': '在左侧插入列',
        'col_right': '在右侧插入列',
        'remove_row': '删除行',
        'remove_col': '删除列',
        'clear_column': '清除列',
        'clear_filters': '清除筛选',
        'undo': '撤销',
        'redo': '重做',
        'copy': '复制',
        'copy_with_headers': '复制（含表头）',
        'cut': '剪切',
        'paste': '粘贴',
        'freeze_column': '冻结列',
        'unfreeze_column': '取消冻结列',
        'mergeCells': '合并单元格',
        'unmergeCells': '取消合并单元格',
        'alignment': '对齐方式',
        'left': '左对齐',
        'center': '居中',
        'right': '右对齐',
        'justify': '两端对齐',
        'filter': '筛选',
        'readOnly': '只读',
        'borders': '边框'
      },

      // 筛选功能
      'filters': {
        'conditions': {
          'eq': '等于',
          'neq': '不等于',
          'gt': '大于',
          'gte': '大于等于',
          'lt': '小于',
          'lte': '小于等于',
          'between': '介于',
          'contains': '包含',
          'begins_with': '开头是',
          'ends_with': '结尾是',
          'empty': '为空',
          'not_empty': '不为空',
          'not_contains': '不包含',
          'not_between': '不介于'
        },
        'operators': {
          'and': '且',
          'or': '或'
        },
        'ui': {
          'filter': '筛选',
          'clear': '清除',
          'apply': '应用',
          'cancel': '取消',
          'value': '值',
          'condition': '条件',
          'no_options': '无选项',
          'search_placeholder': '搜索...'
        }
      },

      // 列排序
      'columnSorting': {
        'sortColumnByAsc': '升序排序',
        'sortColumnByDesc': '降序排序',
        'indicatorAsc': '升序',
        'indicatorDesc': '降序',
        'indicatorMulti': '多列排序'
      },

      // 复制粘贴
      'copyPaste': {
        'copy': '复制',
        'cut': '剪切',
        'paste': '粘贴'
      },

      // 合并单元格
      'mergeCells': {
        'mergeCells': '合并单元格',
        'unmergeCells': '取消合并单元格'
      }
    }

    // 注册语言包
    Handsontable.languages.registerLanguageDictionary(zhCN)

    // 验证注册
    const registered = Handsontable.languages.getLanguageDictionary('zh-CN')
    if (registered) {
      console.log('✅ 中文语言包注册成功')
      console.log('📋 注册的键名:', Object.keys(zhCN.dropdownMenu))

      // === 立即调试新注册的语言包 ===
      console.log('🔍 新注册的语言包内容:', registered)
      // === 结束调试 ===

      return true
    } else {
      console.log('❌ 中文语言包注册失败')
      return false
    }

  } catch (error) {
    console.error('❌ 注册中文语言包失败:', error)
    return false
  }
}


const setupChineseLocalization = () => {
  try {
    if (Handsontable.languages.getLanguageDictionary('zh-CN')) {
      console.log('✅ zh-CN 语言包已存在')
      return true
    }

    console.log('🔧 注册简化版中文语言包...')

    // 简化版，只包含最关键的翻译
    const zhCN = {
      languageCode: 'zh-CN',

      // 核心文本
      'labels': {
        'no_data': '暂无数据'
      },

      // 下拉菜单 - 使用最基础的键名
      'dropdownMenu': {
        'Filter by value': '按值筛选',
        'Filter by condition': '按条件筛选',
        'Sort ascending': '升序排序',
        'Sort descending': '降序排序',
        'Clear column': '清除筛选',
        'Insert row above': '在上方插入行',
        'Insert row below': '在下方插入行',
        'Remove row': '删除行',
        'Insert column left': '在左侧插入列',
        'Insert column right': '在右侧插入列',
        'Remove column': '删除列',
        'Undo': '撤销',
        'Redo': '重做',
        'Read only': '只读',
        'Alignment': '对齐方式'
      },

      // 上下文菜单
      'contextMenu': {
        'Row above': '在上方插入行',
        'Row below': '在下方插入行',
        'Insert column left': '在左侧插入列',
        'Insert column right': '在右侧插入列',
        'Remove row': '删除行',
        'Remove column': '删除列',
        'Clear column': '清除列',
        'Undo': '撤销',
        'Redo': '重做',
        'Copy': '复制',
        'Cut': '剪切',
        'Paste': '粘贴',
        'Freeze column': '冻结列',
        'Unfreeze column': '取消冻结列'
      },

      // 筛选
      'filters': {
        'conditions': {
          'None': '无',
          'Empty': '为空',
          'Not empty': '不为空',
          'Eq': '等于',
          'Neq': '不等于'
        }
      }
    }

    Handsontable.languages.registerLanguageDictionary(zhCN)
    console.log('✅ 简化版中文语言包注册成功')
    return true

  } catch (error) {
    console.error('❌ 中文语言包注册失败:', error)
    return false
  }
}



// 添加实际测试下拉菜单内容的方法
const testActualDropdownContent = () => {
  console.log('🧪 实际测试下拉菜单内容...')

  // 等待下拉菜单渲染
  safeSetTimeout(() => {
    const dropdownMenu = document.querySelector('.htDropdownMenu')
    if (dropdownMenu) {
      console.log('📋 实际下拉菜单内容:', dropdownMenu.textContent)

      const menuItems = dropdownMenu.querySelectorAll('.htItem, .htMenuItem')
      menuItems.forEach((item, idx) => {
        console.log(`菜单项 ${idx}: "${item.textContent}"`)
      })
    } else {
      console.log('❌ 未找到下拉菜单，尝试手动打开...')

      // 手动打开第一个有下拉菜单的表头
      const headers = document.querySelectorAll('.ht_clone_top th')
      for (let i = 0; i < headers.length; i++) {
        const dropdownBtn = headers[i].querySelector('.changeType')
        if (dropdownBtn) {
          dropdownBtn.click()
          break
        }
      }

      // 再次检查
      safeSetTimeout(() => {
        const dropdownMenu = document.querySelector('.htDropdownMenu')
        if (dropdownMenu) {
          console.log('📋 手动打开的下拉菜单内容:', dropdownMenu.textContent)
          const menuItems = dropdownMenu.querySelectorAll('.htItem, .htMenuItem')
          menuItems.forEach((item, idx) => {
            console.log(`菜单项 ${idx}: "${item.textContent}"`)
          })
        }
      }, 500)
    }
  }, 1000)
}


// 添加检查英文默认键名的方法
const checkDefaultEnglishKeys = () => {
  console.log('🔤 检查英文默认键名...')

  // 获取默认英文语言包
  const defaultEn = Handsontable.languages.getLanguageDictionary('en-US')
  if (!defaultEn) {
    console.log('❌ 无法获取英文语言包')
    return
  }

  console.log('📋 英文语言包下拉菜单键名:', Object.keys(defaultEn.dropdownMenu || {}))
  console.log('📋 英文语言包上下文菜单键名:', Object.keys(defaultEn.contextMenu || {}))

  // 特别检查筛选相关的键名
  const filterKeys = Object.keys(defaultEn.dropdownMenu || {}).filter(key =>
    key.includes('filter') || key.includes('sort') || key.includes('clear')
  )
  console.log('🎯 筛选相关键名:', filterKeys)
}

// 在语言包注册后立即调用
// registerChineseLanguageForV16()
// checkDefaultEnglishKeys()

window.Handsontable = Handsontable

const langKey = ref('zh')




// 添加检查实际语言包内容的方法
const debugLanguagePack = () => {
  console.log('🔍 调试语言包内容...')

  // 检查已注册的语言包
  const zhCNPack = Handsontable.languages.getLanguageDictionary('zh-CN')
  console.log('📋 已注册的中文语言包:', zhCNPack)

  // 检查默认语言包（英文）的键名
  const enPack = Handsontable.languages.getLanguageDictionary('en-US')
  console.log('📋 英文语言包键名:', enPack ? Object.keys(enPack.dropdownMenu || {}) : '未找到英文包')

  // 检查当前实例使用的语言
  const hot = getSafeHotInstance()
  if (hot) {
    const settings = hot.getSettings()
    console.log('🎯 当前实例语言设置:', {
      语言: settings.language,
      语言字典: Handsontable.languages.getLanguageDictionary(settings.language),
      下拉菜单配置: settings.dropdownMenu
    })
  }
}

// 修改 verifyLanguageSetting 函数，添加调试
const verifyLanguageSetting = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    console.log('❌ 无法获取表格实例验证语言设置')
    return
  }

  const settings = hot.getSettings()
  console.log('🔍 验证语言设置:', {
    当前语言: settings.language,
    可用语言: Handsontable.languages.getLanguages(),
    已注册中文: !!Handsontable.languages.getLanguageDictionary('zh-CN'),
    下拉菜单配置: settings.dropdownMenu
  })

  // 检查实际渲染的语言
  const headers = document.querySelectorAll('.ht_clone_top th')
  headers.forEach((header, index) => {
    const dropdownBtn = header.querySelector('.changeType')
    console.log(`表头 ${index}: 下拉按钮存在 = ${!!dropdownBtn}`)
  })

  // === 新增：调试语言包内容 ===
  safeSetTimeout(debugLanguagePack, 1000)

  // === 新增：手动测试下拉菜单 ===
  safeSetTimeout(() => {
    console.log('🧪 手动测试下拉菜单...')
    // 找到第一个有下拉菜单的表头并点击
    const headers = document.querySelectorAll('.ht_clone_top th')
    for (let i = 0; i < headers.length; i++) {
      const header = headers[i]
      const dropdownBtn = header.querySelector('.changeType')
      if (dropdownBtn) {
        console.log(`🖱️ 点击第 ${i} 列表头下拉按钮`)
        dropdownBtn.click()
        break
      }
    }
  }, 2000)
}


import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

// 在现有的导入部分添加
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Filter, Edit, Check, Warning, DataAnalysis, Close } from '@element-plus/icons-vue'



// 在现有变量后面添加这些
const isEditMode = ref(false)
const hasChanges = ref(false)
const saving = ref(false)
const modifiedCellsCount = ref(0)
const modifiedCells = ref(new Set())
const originalData = ref([])

// 新增：重试计数器
let retryCount = 0
const MAX_RETRY_COUNT = 10


// 新增：定时器管理
const activeTimeouts = ref([])
const isComponentActive = ref(true)



// 添加统计相关的响应式数据
const showStatsPanel = ref(false)
const stats = ref({
  selectionType: '', // 'column' | 'selection'
  rowCount: 0,
  numericCount: 0,
  sum: 0,
  average: 0,
  max: 0,
  min: 0,
  selectionRange: null // 存储选中区域信息
})

// 当前选中的区域
const currentSelection = ref(null)


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


// 在这里添加 showScrollHint
const showScrollHint = ref(false)




// 修改选择监听器，添加详细调试
const setupColumnSelectionListener = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  // 监听选择变化事件
  hot.addHook('afterSelection', (startRow, startCol, endRow, endCol, preventScrolling, selectionLayerLevel) => {
    console.log('🎯 选择事件触发:', {
      startRow, startCol, endRow, endCol,
      选择类型: startCol === endCol ? '单列' : '区域',
      选择大小: `${Math.abs(endRow - startRow) + 1}行 × ${Math.abs(endCol - startCol) + 1}列`
    })

    calculateSelectionStats(startRow, startCol, endRow, endCol)
  })

  // 监听数据变化（包括筛选）来更新统计
  hot.addHook('afterFilter', () => {
    console.log('🔍 筛选条件变化')
    if (currentSelection.value) {
      const { startRow, startCol, endRow, endCol } = currentSelection.value
      calculateSelectionStats(startRow, startCol, endRow, endCol)
    }
  })

  console.log('✅ 选择监听器已配置')
}




// 修复计算选择统计的方法
const calculateSelectionStats = (startRow, startCol, endRow, endCol) => {
  const hot = getSafeHotInstance()
  if (!hot) return

  console.log('📊 开始计算选择统计:', { startRow, startCol, endRow, endCol })

  // 规范化选择区域（确保 start <= end）
  const normalizedStartRow = Math.min(startRow, endRow)
  const normalizedEndRow = Math.max(startRow, endRow)
  const normalizedStartCol = Math.min(startCol, endCol)
  const normalizedEndCol = Math.max(startCol, endCol)

  console.log('📐 规范化后的选择区域:', {
    normalizedStartRow, normalizedEndRow, normalizedStartCol, normalizedEndCol,
    行数: normalizedEndRow - normalizedStartRow + 1,
    列数: normalizedEndCol - normalizedStartCol + 1
  })

  // 判断选择类型
  let selectionType = ''
  let selectedData = []

  if (normalizedStartCol === normalizedEndCol && normalizedEndRow - normalizedStartRow >= 0) {
    // 单列选择（至少选择了一行）
    selectionType = 'column'
    selectedData = getFilteredColumnData(normalizedStartCol)
    console.log('🎯 识别为单列选择')
  } else if (normalizedStartRow === normalizedEndRow && normalizedStartCol === normalizedEndCol) {
    // 单个单元格选择，不显示统计
    console.log('🎯 单个单元格选择，隐藏统计面板')
    showStatsPanel.value = false
    currentSelection.value = null
    return
  } else {
    // 区域选择（多行多列）
    selectionType = 'selection'
    selectedData = getSelectedAreaData(normalizedStartRow, normalizedStartCol, normalizedEndRow, normalizedEndCol)
    console.log('🎯 识别为区域选择', {
      选择单元格数量: selectedData.length,
      区域: `${normalizedEndRow - normalizedStartRow + 1}行 × ${normalizedEndCol - normalizedStartCol + 1}列`
    })
  }

  // 保存当前选择信息
  currentSelection.value = {
    startRow: normalizedStartRow,
    startCol: normalizedStartCol,
    endRow: normalizedEndRow,
    endCol: normalizedEndCol,
    type: selectionType
  }

  console.log('💾 保存选择信息:', currentSelection.value)

  // 更新统计信息
  updateStatistics(selectedData, selectionType)
  showStatsPanel.value = true
}



// 修复获取选中区域数据的方法
const getSelectedAreaData = (startRow, startCol, endRow, endCol) => {
  const hot = getSafeHotInstance()
  if (!hot) return []

  try {
    const data = hot.getData()
    const selectedData = []

    console.log('📋 获取选中区域数据:', {
      数据总行数: data.length,
      选择区域: `${startRow}-${endRow}行, ${startCol}-${endCol}列`
    })

    // 遍历选中区域的所有单元格
    for (let row = startRow; row <= endRow; row++) {
      for (let col = startCol; col <= endCol; col++) {
        // 确保不超出数据范围
        if (row < data.length && col < (data[row]?.length || 0)) {
          const value = data[row][col]
          selectedData.push(value)

          // 调试前几个单元格的值
          if (selectedData.length <= 3) {
            console.log(`📝 单元格 [${row},${col}]:`, value)
          }
        } else {
          console.warn(`⚠️ 单元格超出范围: [${row},${col}]`)
        }
      }
    }

    console.log('✅ 获取到选中数据:', {
      总单元格数: selectedData.length,
      样本数据: selectedData.slice(0, 5)
    })

    return selectedData
  } catch (error) {
    console.error('❌ 获取选中区域数据失败:', error)
    return []
  }
}



// 获取筛选后的列数据（修改版）
const getFilteredColumnData = (columnIndex) => {
  const hot = getSafeHotInstance()
  if (!hot) return []

  try {
    const data = hot.getData()
    const columnData = []

    // 跳过表头行（如果有）
    const startRow = hot.getSettings().colHeaders ? 1 : 0

    for (let row = startRow; row < data.length; row++) {
      if (columnIndex < data[row].length) {
        const value = data[row][columnIndex]
        columnData.push(value)
      }
    }

    return columnData
  } catch (error) {
    console.error('获取列数据失败:', error)
    return []
  }
}

// 更新统计信息（修改版）
const updateStatistics = (data, selectionType) => {
  if (!data || data.length === 0) {
    resetStatistics(selectionType)
    return
  }

  // 过滤出数值类型的数据
  const numericData = data
    .map(value => {
      if (value === null || value === undefined || value === '') return null
      const num = Number(value)
      return isNaN(num) ? null : num
    })
    .filter(value => value !== null)

  const totalCount = data.length
  const numericCount = numericData.length

  if (numericCount === 0) {
    resetStatistics(selectionType)
    stats.value.rowCount = totalCount
    stats.value.numericCount = 0
    return
  }

  const sum = numericData.reduce((acc, val) => acc + val, 0)
  const average = sum / numericCount
  const max = Math.max(...numericData)
  const min = Math.min(...numericData)

  stats.value = {
    selectionType: selectionType,
    rowCount: totalCount,
    numericCount: numericCount,
    sum: formatNumber(sum),
    average: formatNumber(average),
    max: formatNumber(max),
    min: formatNumber(min),
    selectionRange: currentSelection.value
  }
}

// 重置统计信息
const resetStatistics = (selectionType = '') => {
  stats.value = {
    selectionType: selectionType,
    rowCount: 0,
    numericCount: 0,
    sum: 0,
    average: 0,
    max: 0,
    min: 0,
    selectionRange: null
  }
}

// 清除选择
const clearSelection = () => {
  const hot = getSafeHotInstance()
  if (hot) {
    // 清除选择
    hot.deselectCell()
    showStatsPanel.value = false
    currentSelection.value = null
  }
}

// 格式化数字显示（优化版）
const formatNumber = (num) => {
  if (num === 0) return '0'
  if (Math.abs(num) < 0.001 || Math.abs(num) > 1000000) {
    return num.toExponential(4)
  }

  // 根据数值大小决定小数位数
  let decimalPlaces = 4
  if (Math.abs(num) >= 100) decimalPlaces = 2
  if (Math.abs(num) >= 1000) decimalPlaces = 0

  const rounded = Math.round(num * Math.pow(10, decimalPlaces)) / Math.pow(10, decimalPlaces)
  return rounded.toString()
}







// 计算列统计信息
const calculateColumnStats = (startCol, endCol) => {
  const hot = getSafeHotInstance()
  if (!hot) return

  // 如果选择的是单列
  if (startCol === endCol && startCol >= 0) {
    selectedColumn.value = startCol
    const columnData = getFilteredColumnData(startCol)
    updateStatistics(columnData)
    showStatsPanel.value = true
  } else {
    // 多列选择或无效选择，隐藏统计面板
    showStatsPanel.value = false
    selectedColumn.value = null
  }
}











// 新增：安全的定时器管理
const safeSetTimeout = (callback, delay) => {
  if (!isComponentActive.value) {
    console.log('ℹ️ 组件已卸载，跳过定时器设置')
    return null
  }

  const timeoutId = setTimeout(() => {
    if (isComponentActive.value) {
      callback()
    }
  }, delay)

  activeTimeouts.value.push(timeoutId)
  return timeoutId
}

// 清理所有定时器的方法
const clearAllTimeouts = () => {
  activeTimeouts.value.forEach(timeoutId => {
    clearTimeout(timeoutId)
  })
  activeTimeouts.value = []
  console.log('✅ 所有定时器已清理')
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
  safeSetTimeout(() => {
  if (isComponentActive.value && hotTable.value?.hotInstance) {
    manualSetupEventListeners()
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
  const hot = getSafeHotInstance()
  if (!hot) {
    return []
  }

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

// 新增：强制刷新表头固定状态
const forceHeaderFixed = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  try {
    // 强制重新计算布局
    safeSetTimeout(() => {
      if (isHotInstanceValid()) {
        hot.render()
        console.log('🔄 强制刷新表头固定状态')
      }
    }, 100)
  } catch (error) {
    console.warn('⚠️ 刷新表头失败:', error.message)
  }
}


// 在数据加载后调用
watch(() => props.excelData, (newData) => {
  if (newData && newData.length > 0) {
    nextTick(() => {
      safeSetTimeout(forceHeaderFixed, 500)  // 主要修复表头固定
    })
  }
}, { deep: true })


// 修复：更新修改单元格样式的方法
const updateModifiedCellsStyle = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    console.log('ℹ️ 表格实例无效，跳过样式更新')
    return
  }

  try {
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
  } catch (error) {
    console.warn('⚠️ 更新单元格样式失败:', error.message)
  }
}


// 修复：更新表格只读状态的方法
const updateTableReadOnly = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    console.log('ℹ️ 表格实例无效，跳过只读状态更新')
    return
  }

  const readOnly = !isEditMode.value
  console.log('🔒 更新表格只读状态:', { readOnly })

  try {
    hot.updateSettings({
      readOnly: readOnly
    })

    // 强制重新渲染
    safeSetTimeout(() => {
      if (isHotInstanceValid()) {
        hot.render()
      }
    }, 100)
  } catch (error) {
    console.warn('⚠️ 更新只读状态失败:', error.message)
  }
}


// 修复：重置更改状态的方法
const resetChanges = () => {
  hasChanges.value = false
  modifiedCellsCount.value = 0
  modifiedCells.value.clear()

  // 清除修改样式
  const hot = getSafeHotInstance()
  if (hot) {
    try {
      hot.updateSettings({
        cell: []
      })
      hot.render()
    } catch (error) {
      console.warn('⚠️ 重置更改状态失败:', error.message)
    }
  }
}



// 添加快捷键支持
const setupKeyboardShortcuts = () => {
  const handleKeyDown = (event) => {
    // ESC 键清除选择
    if (event.key === 'Escape' && showStatsPanel.value) {
      clearSelection()
    }
  }

  document.addEventListener('keydown', handleKeyDown)

  // 在组件卸载时移除监听器
  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeyDown)
  })
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
      const hot = getSafeHotInstance()

      if (hot && instance?.hotTable?.hotInstance) {
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


// 添加手动修复方法
const fixFilterHeaders = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  const filterPlugin = hot.getPlugin('filters')
  if (filterPlugin) {
    // 禁用再重新启用插件
    filterPlugin.disablePlugin()
    safeSetTimeout(() => {
      if (isHotInstanceValid()) {
        filterPlugin.enablePlugin()
        hot.render()
        console.log('🔄 筛选插件已重新初始化')
      }
    }, 100)
  }
}



// 在 mounted 中调用
safeSetTimeout(fixFilterHeaders, 1000)


// 添加多列排序配置（如果需要）
const multiColumnSorting = ref(true)

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

  // ========== 新增：智能统计更新 ==========
  // 延迟更新统计信息，确保数据已同步
  safeSetTimeout(() => {
    // 如果当前有选择且显示统计面板
    if (currentSelection.value && showStatsPanel.value) {
      const { startRow, startCol, endRow, endCol, type } = currentSelection.value

      // 检查更改是否影响当前选中的区域
      const affectedChanges = changes.filter(([row, col]) => {
        if (row === null || col === null) return false

        if (type === 'column') {
          // 对于列选择，只检查列匹配
          return col === startCol
        } else {
          // 对于区域选择，检查是否在区域内
          return row >= startRow && row <= endRow &&
                 col >= startCol && col <= endCol
        }
      })

      if (affectedChanges.length > 0) {
        console.log('🔄 检测到选中区域内的数据更改，更新统计信息', {
          受影响单元格: affectedChanges.length,
          选择类型: type
        })

        // 重新计算统计信息
        calculateSelectionStats(startRow, startCol, endRow, endCol)

        // 可选：显示更新提示
        if (affectedChanges.length === 1) {
          const [row, col] = affectedChanges[0]
          console.log(`📊 单元格 [${row},${col}] 更改已反映到统计中`)
        }
      }
    }
  }, 150)
  // ========== 结束新增 ==========

  console.log('📊 更改统计:', {
    totalChanges: modifiedCellsCount.value,
    hasChanges: hasChanges.value,
    modifiedCells: Array.from(modifiedCells.value)
  })
}



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


// 修改表格高度计算，确保有足够空间
const tableHeight = computed(() => {
  if (tableData.value.length === 0) {
    return 200
  }

  // 确保最小高度，避免表头被截断
  const minHeight = 400
  const calculatedHeight = Math.max(minHeight, containerHeight.value)

  console.log('🎯 表格高度计算:', {
    最小高度: minHeight,
    计算高度: calculatedHeight,
    总行数: tableData.value.length
  })

  return calculatedHeight
})



// 新增：双表头渲染函数
const renderDualHeaderTable = (metadata, dataRows) => {
  if (!metadata || !dataRows) return []

  const {
    horizontal_headers = [],
    vertical_headers = [],
    top_left_cell
  } = metadata

  console.log('🔍 渲染双表头表格:', {
    左上角单元格: top_left_cell,
    横向表头: horizontal_headers,
    纵向表头: vertical_headers,
    数据行数: dataRows.length
  })

  // 构建表格数据
  const tableRows = []

  // 查找表头行（通常是第一行数据）
  let headerRowData = null
  let dataStartIndex = 0

  for (let i = 0; i < dataRows.length; i++) {
    if (dataRows[i]?.__is_first_row) {
      headerRowData = dataRows[i]
      dataStartIndex = i + 1
      break
    }
  }

  if (!headerRowData) {
    console.warn('⚠️ 未找到表头行数据')
    return []
  }

  // 第一行：左上角单元格 + 横向表头
  const headerRow = []

  // 单元格 (0,0)：左上角
  headerRow.push(headerRowData?.__top_left_cell || top_left_cell || '')

  // 单元格 (0,1)-(0,N)：横向表头
  for (let colIdx = 0; colIdx < horizontal_headers.length; colIdx++) {
    const headerKey = `H_${colIdx + 1}`
    const headerValue = headerRowData?.[headerKey] ||
                       horizontal_headers[colIdx] ||
                       `列${colIdx + 1}`
    headerRow.push(headerValue)
  }

  tableRows.push(headerRow)

  // 数据行：纵向表头 + 数据（从第二行开始）
  for (let rowIdx = dataStartIndex; rowIdx < dataRows.length; rowIdx++) {
    const rowData = dataRows[rowIdx]

    if (!rowData?.__is_data_row) continue

    // 获取纵向表头
    const verticalHeader = rowData.__vertical_header ||
                          vertical_headers[rowIdx - dataStartIndex] ||
                          `行${rowIdx - dataStartIndex + 1}`

    const row = [verticalHeader]

    // 添加数据单元格
    for (let colIdx = 0; colIdx < horizontal_headers.length; colIdx++) {
      const headerKey = `H_${colIdx + 1}`
      const value = rowData[headerKey] ?? ''
      row.push(value)
    }

    tableRows.push(row)
  }

  console.log('📊 双表头表格构建完成:', {
    总行数: tableRows.length,
    总列数: tableRows[0]?.length || 0,
    布局: `左上角: (0,0), 横向表头: 行0, 纵向表头: 列0, 数据: (1,1)开始`
  })

  return tableRows
}


const tableData123 = computed(() => {
  if (!props.excelData || props.excelData.length === 0) {
    console.log('📊 tableData: 数据为空或长度为0')
    return []
  }

  console.log('📊 接收到的原始数据:', {
    长度: props.excelData.length,
    第一个元素类型: typeof props.excelData[0],
    第一个元素: props.excelData[0]
  })

  const firstItem = props.excelData[0]

  // 检查是否有双表头元数据（旧结构）
  if (firstItem?.__metadata?.has_dual_headers) {
    console.log('✅ 检测到双表头元数据（旧结构）')

    const metadata = firstItem.__metadata
    const dataRows = props.excelData.slice(1) // 跳过元数据

    console.log('📋 元数据详情:', {
      左上角: metadata.top_left_cell,
      横向表头数: metadata.horizontal_headers?.length,
      纵向表头数: metadata.vertical_headers?.length,
      数据行数: dataRows.length
    })

    // 关键修复：重新设计渲染逻辑
    const renderedTable = []

    // 1. 找到第一行数据（包含横向表头）
    const headerRowObj = dataRows.find(row => row?.__is_first_row)
    if (!headerRowObj) {
      console.warn('⚠️ 未找到第一行（横向表头）数据')
      return []
    }

    // 2. 构建第一行：左上角 + 横向表头
    const firstRow = []

    // 左上角单元格
    firstRow.push(headerRowObj.__top_left_cell || metadata.top_left_cell || '')

    // 横向表头（按顺序 H_1, H_2, H_3...）
    const horizontalCount = metadata.horizontal_headers?.length || 0
    for (let i = 1; i <= horizontalCount; i++) {
      const key = `H_${i}`
      const value = headerRowObj[key] ||
                   metadata.horizontal_headers?.[i-1] ||
                   `列${i}`
      firstRow.push(value || '')
    }

    renderedTable.push(firstRow)
    console.log('📊 第一行构建完成:', firstRow)

    // 3. 构建数据行：纵向表头 + 数据
    const dataRowsOnly = dataRows.filter(row => row?.__is_data_row)
    const verticalCount = metadata.vertical_headers?.length || 0

    dataRowsOnly.forEach((rowData, rowIndex) => {
      const row = []

      // 纵向表头
      const verticalHeader = rowData.__vertical_header ||
                            metadata.vertical_headers?.[rowIndex] ||
                            `行${rowIndex + 1}`
      row.push(verticalHeader || '')

      // 数据单元格
      for (let i = 1; i <= horizontalCount; i++) {
        const key = `H_${i}`
        const value = rowData[key] ?? ''
        row.push(value)
      }

      renderedTable.push(row)

      // 调试输出前3行
      if (rowIndex < 3) {
        console.log(`📊 第 ${rowIndex + 2} 行:`, row.slice(0, 4))
      }
    })

    console.log('✅ 表格构建完成（旧结构）:', {
      总行数: renderedTable.length,
      总列数: renderedTable[0]?.length || 0,
      示例: renderedTable.slice(0, 3).map(row => row.slice(0, 4))
    })

    return renderedTable
  }

  // 单表头逻辑（保持不变）
  console.log('📊 单表头模式')
  const headers = firstItem.__orderedHeaders ||
                  Object.keys(firstItem || {}).filter(key => !key.startsWith('__'))

  if (!headers.length) {
    console.warn('⚠️ 未找到表头')
    return []
  }

  const result = props.excelData.map(row =>
    headers.map(header => row[header] ?? '')
  )

  console.log('📊 单表头构建完成:', {
    行数: result.length,
    列数: result[0]?.length || 0
  })

  return result
})



// tableData 计算属性
const tableData = computed(() => {
  if (!props.excelData || props.excelData.length === 0) {
    console.log('📊 tableData: 数据为空或长度为0')
    return []
  }

  const firstItem = props.excelData[0]

  // 检查是否有双表头元数据（旧结构）
  if (firstItem?.__metadata?.has_dual_headers) {
    console.log('✅ 检测到双表头元数据（旧结构）')

    const metadata = firstItem.__metadata
    const dataRows = props.excelData.slice(1) // 跳过元数据

    console.log('📋 元数据详情:', {
      左上角: metadata.top_left_cell,
      横向表头数: metadata.horizontal_headers?.length,
      纵向表头数: metadata.vertical_headers?.length,
      数据行数: dataRows.length
    })

    // 关键修复：重新设计渲染逻辑
    const renderedTable = []

    // 1. 找到第一行数据（包含横向表头）
    const headerRowObj = dataRows.find(row => row?.__is_first_row)
    if (!headerRowObj) {
      console.warn('⚠️ 未找到第一行（横向表头）数据')
      return []
    }

    // 2. 构建第一行：左上角 + 横向表头
    const firstRow = []

    // 左上角单元格
    firstRow.push(headerRowObj.__top_left_cell || metadata.top_left_cell || '')

    // 横向表头（按顺序 H_1, H_2, H_3...）
    const horizontalCount = metadata.horizontal_headers?.length || 0
    for (let i = 1; i <= horizontalCount; i++) {
      const key = `H_${i}`
      const value = headerRowObj[key] ||
                   metadata.horizontal_headers?.[i-1] ||
                   ``
      firstRow.push(value || '')
    }

    renderedTable.push(firstRow)
    console.log('📊 第一行构建完成:', firstRow)

    // 3. 构建数据行：纵向表头 + 数据
    const dataRowsOnly = dataRows.filter(row => row?.__is_data_row)
    const verticalCount = metadata.vertical_headers?.length || 0

    dataRowsOnly.forEach((rowData, rowIndex) => {
      const row = []

      // 纵向表头
      const verticalHeader = rowData.__vertical_header ||
                            metadata.vertical_headers?.[rowIndex] ||
                            ``
      row.push(verticalHeader || '')

      // 数据单元格
      for (let i = 1; i <= horizontalCount; i++) {
        const key = `H_${i}`
        const value = rowData[key] ?? ''
        row.push(value)
      }

      renderedTable.push(row)
    })

    console.log('✅ 表格构建完成（旧结构）:', {
      总行数: renderedTable.length,
      总列数: renderedTable[0]?.length || 0
    })

    // ==================== 新增：添加空白行和列 ====================
    // 在数据后面添加6行空白
    for (let i = 0; i < 6; i++) {
      const blankRow = new Array(renderedTable[0]?.length || 0).fill('')
      renderedTable.push(blankRow)
    }

    // 在每行后面添加2列空白
    renderedTable.forEach(row => {
      for (let i = 0; i < 2; i++) {
        row.push('')
      }
    })
    // ==================== 结束新增 ====================

    console.log('✅ 添加空白行列后:', {
      最终行数: renderedTable.length,
      最终列数: renderedTable[0]?.length || 0
    })

    return renderedTable
  }

  // 单表头逻辑
  console.log('📊 单表头模式')
  const headers = firstItem.__orderedHeaders ||
                  Object.keys(firstItem || {}).filter(key => !key.startsWith('__'))

  if (!headers.length) {
    console.warn('⚠️ 未找到表头')
    return []
  }

  const result = props.excelData.map(row =>
    headers.map(header => row[header] ?? '')
  )

  console.log('📊 单表头构建完成:', {
    行数: result.length,
    列数: result[0]?.length || 0
  })

  // ==================== 新增：单表头模式也添加空白行和列 ====================
  // 在数据后面添加3行空白
  for (let i = 0; i < 3; i++) {
    const blankRow = new Array(result[0]?.length || 0).fill('')
    result.push(blankRow)
  }

  // 在每行后面添加3列空白
  result.forEach(row => {
    for (let i = 0; i < 3; i++) {
      row.push('')
    }
  })

  console.log('✅ 添加空白行列后:', {
    最终行数: result.length,
    最终列数: result[0]?.length || 0
  })
  // ==================== 结束新增 ====================

  return result
})



// 辅助函数：检查第一行是否包含实际数据
const checkIfFirstRowIsDataRow = (firstRow, orderedHeaders) => {
  // 如果第一行有大量的 __ 开头的属性，很可能是元数据行
  const metaKeys = Object.keys(firstRow).filter(key => key.startsWith('__')).length
  const totalKeys = Object.keys(firstRow).length

  console.log('🔍 检查第一行属性:', {
    元数据键数量: metaKeys,
    总键数量: totalKeys,
    元数据比例: metaKeys / totalKeys
  })

  // 如果大部分键都是元数据键，那么第一行很可能是元数据行
  if (metaKeys > 0 && metaKeys / totalKeys > 0.5) {
    return false
  }

  // 检查 orderedHeaders 是否与第一行的键匹配
  const firstRowKeys = Object.keys(firstRow).filter(key => !key.startsWith('__'))
  const isOrderedHeadersMatch = JSON.stringify(orderedHeaders) === JSON.stringify(firstRowKeys)

  console.log('🔍 列顺序匹配检查:', {
    第一行非元数据键: firstRowKeys,
    后端orderedHeaders: orderedHeaders,
    是否匹配: isOrderedHeadersMatch
  })

  return !isOrderedHeadersMatch
}

// 添加一个调试方法来检查后端原始数据
const debugBackendDataStructure = () => {
  if (!props.excelData || props.excelData.length === 0) {
    console.log('❌ 没有数据可调试')
    return
  }

  console.log('🔍 后端原始数据结构分析:')
  console.log('1. 数据总行数:', props.excelData.length)

  // 分析前几行
  for (let i = 0; i < Math.min(3, props.excelData.length); i++) {
    const row = props.excelData[i]
    console.log(`\n第 ${i} 行:`)
    console.log('- 键名列表:', Object.keys(row))

    // 如果有 orderedHeaders，特别检查
    if (row.__orderedHeaders) {
      console.log('- __orderedHeaders:', row.__orderedHeaders)

      // 检查列顺序
      const dataKeys = Object.keys(row).filter(key => !key.startsWith('__'))
      console.log('- 实际数据键名:', dataKeys)
      console.log('- 键名是否与 orderedHeaders 匹配:',
                 JSON.stringify(row.__orderedHeaders) === JSON.stringify(dataKeys))
    }

    // 显示前几个键值对
    const entries = Object.entries(row).slice(0, 5)
    console.log('- 前5个键值对:', entries.map(([k, v]) => `${k}: ${v}`))
  }

  // 检查列顺序问题
  console.log('\n🔍 列顺序问题分析:')
  const firstRow = props.excelData[0]
  if (firstRow.__orderedHeaders) {
    const expectedOrder = firstRow.__orderedHeaders
    const actualKeys = Object.keys(firstRow).filter(key => !key.startsWith('__'))

    console.log('- 期望顺序（orderedHeaders）:', expectedOrder)
    console.log('- 实际键名顺序:', actualKeys)

    // 检查是否是字母顺序
    const sortedKeys = [...actualKeys].sort()
    console.log('- 按字母排序后:', sortedKeys)
    console.log('- 是否是字母顺序:', JSON.stringify(actualKeys) === JSON.stringify(sortedKeys))

    // 检查是否与期望顺序匹配
    console.log('- 是否与期望顺序匹配:', JSON.stringify(expectedOrder) === JSON.stringify(actualKeys))

    if (JSON.stringify(expectedOrder) !== JSON.stringify(actualKeys)) {
      console.warn('⚠️ 警告：前端接收到的列顺序与后端声明的顺序不一致！')
      console.warn('这可能是后端数据处理的问题，或者是JSON序列化时键名重新排序了')
    }
  }
}




// 添加方法验证列顺序
const verifyColumnOrder = () => {
  if (props.excelData && props.excelData.length > 0) {
    const firstRow = props.excelData[0]
    console.log('🔍 验证列顺序:')
    console.log('- 原始键名:', Object.keys(firstRow))
    console.log('- 有序键名:', firstRow.__orderedHeaders || '未提供')
    console.log('- 最终显示顺序:', tableData.value[0] || [])
  }
}

// 在数据加载后验证顺序
watch(() => props.excelData, (newData) => {
  if (newData && newData.length > 0) {
    nextTick(() => {
      verifyColumnOrder()
    })
  }
}, { deep: true })


// 1. 修改固定行列的计算属性
const fixedRowsTop = computed(() => {
  const firstItem = props.excelData?.[0]
  return firstItem?.__metadata?.has_dual_headers ? 1 : 0  // 固定第一行（横向表头）
})

const fixedColumnsLeft = computed(() => {
  const firstItem = props.excelData?.[0]
  return firstItem?.__metadata?.has_dual_headers ? 1 : 0  // 固定第一列（纵向表头）
})


// 2. 修改列配置计算属性
const columns = computed(() => {
  if (!tableData.value || tableData.value.length === 0) {
    return []
  }

  const headers = tableData.value[0] || []
  console.log('🎯 生成列配置:', {
    列数: headers.length,
    表头样本: headers.slice(0, 3)
  })

  return headers.map((header, index) => ({
    data: index,
    type: 'text',
    width: 150,
    readOnly: !isEditMode.value,
    title: header || (index === 0 ? '' : `列${index}`),
    // 第一列特殊样式
    ...(index === 0 && {
      className: 'vertical-header-column',
      renderer: function(instance, td, row, col, prop, value) {
        Handsontable.renderers.TextRenderer.apply(this, arguments)
        td.style.background = '#f6ffed'
        td.style.fontWeight = '600'
      }
    })
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




// 修复：更严格的实例安全检查函数
const isHotInstanceValid = () => {
  if (!hotTable.value?.hotInstance) {
    return false
  }

  const hot = hotTable.value.hotInstance
  try {
    // 通过检查实例状态来验证是否有效
    return !hot.isDestroyed &&
           hot.rootElement !== null &&
           hot.rootElement.isConnected &&
           typeof hot.getSettings === 'function'
  } catch (error) {
    return false
  }
}


const getSafeHotInstance = () => {
  if (!isHotInstanceValid()) {
    return null
  }

  try {
    const hot = hotTable.value.hotInstance
    // 快速检查而不使用返回值
    const settings = hot.getSettings()
    return settings ? hot : null
  } catch (error) {
    return null
  }
}



// 修复：安全的异步操作包装器
const safeAsyncOperation = (callback) => {
  if (!isComponentActive.value || !isHotInstanceValid()) {
    console.log('ℹ️ 组件已卸载或实例无效，跳过操作')
    return
  }
  try {
    callback()
  } catch (error) {
    console.warn('⚠️ 异步操作失败:', error.message)
  }
}




// 修复：修改 setupEventListeners 中的重试逻辑
const setupEventListeners = () => {
  console.log('🔧 开始配置事件监听...', { retryCount })

  const hot = getSafeHotInstance()
  if (!hot) {
    retryCount++
    if (retryCount < MAX_RETRY_COUNT && isComponentActive.value) {
      console.log(`❌ 表格实例未准备好，延迟重试 (${retryCount}/${MAX_RETRY_COUNT})`)
      safeSetTimeout(() => {
          if (isComponentActive.value) {
            setupEventListeners()
          }
        }, 500)

    } else {
      console.error('❌ 表格实例初始化失败，停止重试')
    }
    return
  }

  console.log('✅ 表格实例已准备好，配置事件监听')

  try {
    // 清除可能存在的重复监听
    hot.removeHook('afterChange')
    console.log('✅ 已清除旧的 afterChange 监听')
  } catch (e) {
    console.log('ℹ️ 清除旧监听时出错:', e.message)
  }

  // 添加原生事件监听
  hot.addHook('afterChange', function(changes, source) {
    safeAsyncOperation(() => {
      console.log('🎯 afterChange 事件触发:', {
        changes: changes ? changes.length : 0,
        source: source,
        timestamp: new Date().toISOString()
      })

      // 调用我们的处理方法
      onDataChange(changes, source)
    })
  })

  console.log('✅ 事件监听配置完成')
  retryCount = 0 // 重置重试计数
}





// 修复：在 watch 中添加安全检查
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

    // 延迟执行以确保表格重新渲染
    nextTick(() => {
      calculateHeight()
      const hot = getSafeHotInstance()
      if (hot) {
        console.log('🔄 刷新表格实例')

        // 确保筛选功能重新启用
        const filterPlugin = hot.getPlugin('filters')
        if (filterPlugin && filtersEnabled.value) {
          filterPlugin.enablePlugin()
        }

        hot.updateSettings({
          height: tableHeight.value
        })
        hot.render()

        // 重置重试计数并重新设置事件监听
        retryCount = 0
        safeSetTimeout(setupEventListeners, 1000)

      }
    })
  }
}, { deep: true })




const toggleFilters = () => {
  filtersEnabled.value = !filtersEnabled.value
  ElMessage.info(filtersEnabled.value ? '筛选功能已启用' : '筛选功能已禁用')
}



// 添加筛选统计功能
const updateFilterStats = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  const filteredData = hot.getData()
  const originalCount = tableData.value.length
  const filteredCount = filteredData.filter(row => row.some(cell => cell !== '')).length

  console.log(`📊 筛选统计: ${filteredCount}/${originalCount} 行数据`)
}



// 添加清除筛选的方法
const clearAllFilters = () => {
  if (hotTable.value?.hotInstance) {
    const hot = hotTable.value.hotInstance
    const filterPlugin = hot.getPlugin('filters')
    if (filterPlugin) {
      filterPlugin.clearConditions()
      filterPlugin.filter()
      ElMessage.success('已清除所有筛选条件')
    }
  }
}




// 新增这个函数
const forceChineseLanguage = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  console.log('🔧 强制应用中文语言设置...')

  try {
    // 更新语言设置
    hot.updateSettings({
      language: 'zh-CN'
    })

    // 强制重新渲染
    safeSetTimeout(() => {
      if (isHotInstanceValid()) {
        hot.render()
        console.log('✅ 中文语言设置应用完成')
      }
    }, 100)
  } catch (error) {
    console.error('❌ 应用中文语言设置失败:', error)
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


// 使用 ResizeObserver 监听容器尺寸变化
const resizeObserver = ref(null)

watch(() => props.excelData, (newData, oldData) => {
  console.log('🔄 excelData 变化:', {
    新数据长度: newData?.length,
    旧数据长度: oldData?.length,
    新数据前3行: newData?.slice(0, 3).map(row => ({
      键名: Object.keys(row),
      是否数据行: row.__is_data_row,
      是否第一行: row.__is_first_row,
      元数据: row.__metadata ? '有' : '无'
    }))
  })
}, { deep: true, immediate: true })



// 新增：监听表格数据变化，在数据加载后配置事件监听
watch(() => props.excelData, (newData) => {
  if (newData && newData.length > 0) {
    console.log('📊 表格数据已加载，配置事件监听')

    // 延迟确保表格完全渲染
    nextTick(() => {
      safeSetTimeout(() => {
        setupEventListeners()  // 主要配置事件监听
      }, 100)
    })
  }
}, { immediate: true })




const excelViewerInstance = ref(null)


// 修复 verifyLanguageSetting 函数中的错误
const verifyLanguageSettingFixed = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    console.log('❌ 无法获取表格实例验证语言设置')
    return
  }

  const settings = hot.getSettings()
  console.log('🔍 验证语言设置:', {
    当前语言: settings.language,
    已注册中文: !!Handsontable.languages.getLanguageDictionary('zh-CN'),
    下拉菜单配置: settings.dropdownMenu
  })

  // 检查实际渲染的语言
  const headers = document.querySelectorAll('.ht_clone_top th')
  headers.forEach((header, index) => {
    const dropdownBtn = header.querySelector('.changeType')
    console.log(`表头 ${index}: 下拉按钮存在 = ${!!dropdownBtn}`)
  })

  // 调试语言包内容
  safeSetTimeout(debugLanguagePack, 1000)
}


// 在已有计算属性后添加
const hasDualHeaders = computed(() => {
  return props.excelData?.[0]?.__metadata?.has_dual_headers || false
})

const tableInfo = computed(() => {
  if (!hasDualHeaders.value) return null

  const metadata = props.excelData[0]?.__metadata || {}
  return {
    左上角: metadata.top_left_cell || '空',
    横向表头: metadata.horizontal_headers?.length || 0,
    纵向表头: metadata.vertical_headers?.length || 0,
    数据区域: `${metadata.vertical_headers?.length || 0}行 × ${metadata.horizontal_headers?.length || 0}列`
  }
})

// 添加调试验证函数
const verifyTableStructure = () => {
  if (!hasDualHeaders.value || !tableData.value.length) return

  console.log('🔍 验证表格结构:')
  console.log('1. 表格维度:', {
    总行数: tableData.value.length,
    总列数: tableData.value[0].length,
    固定行数: fixedRowsTop.value,
    固定列数: fixedColumnsLeft.value
  })

  console.log('2. 左上角单元格:', tableData.value[0][0])
  console.log('3. 横向表头行:', tableData.value[0].slice(1, 4))
  console.log('4. 纵向表头列:', tableData.value.slice(1, 4).map(row => row[0]))
  console.log('5. 数据区域起始:', `(1,1) = ${tableData.value[1]?.[1]}`)
}


// 修复：在 onUnmounted 中设置组件为非激活状态
onUnmounted(() => {
  console.log('🔧 开始清理组件资源...')

  // 首先设置组件为非激活状态
  isComponentActive.value = false

  // 清理所有定时器
  clearAllTimeouts()

  // 清理 ResizeObserver
  if (resizeObserver.value) {
    resizeObserver.value.disconnect()
    console.log('✅ ResizeObserver 已清理')
  }

  // 移除窗口大小变化监听器
  window.removeEventListener('resize', handleResize)
  console.log('✅ 窗口大小监听器已移除')

  // 清理全局实例
  if (window.excelViewerInstance) {
    delete window.excelViewerInstance
    console.log('✅ 全局实例已清理')
  }

  // 安全销毁 Handsontable 实例
  if (hotTable.value?.hotInstance && !hotTable.value.hotInstance.isDestroyed) {
    try {
      console.log('🔧 正在销毁 Handsontable 实例...')
      hotTable.value.hotInstance.destroy()
      console.log('✅ Handsontable 实例已安全销毁')
    } catch (error) {
      console.log('ℹ️ 清理 Handsontable 实例:', error.message)
    }
  } else {
    console.log('ℹ️ Handsontable 实例已销毁或不存在，跳过销毁操作')
  }

  console.log('✅ 组件资源清理完成')
})


// 单元格选择相关数据
const showCellContent = ref(false)
const selectedCell = ref({
  row: null,
  col: null,
  position: '',      // 如 "B3"
  content: '',
  type: '未知',
  charCount: 0,
  lineCount: 1
})

// 计算单元格位置（A1, B2 格式）
const calculateCellPosition = (row, col) => {
  if (row === null || col === null) return ''

  // 将列索引转换为字母（A, B, C...）
  let columnName = ''
  let columnIndex = col

  while (columnIndex >= 0) {
    columnName = String.fromCharCode(65 + (columnIndex % 26)) + columnName
    columnIndex = Math.floor(columnIndex / 26) - 1
  }

  // 行号从1开始（因为第0行可能是表头）
  const rowNumber = row + 1

  return `${columnName}${rowNumber}`
}


// 更新 getCellTypeTag 函数
const getCellTypeTag = (type) => {
  const typeMap = {
    '文本': '',           // 默认
    '数字': 'success',
    '日期': 'warning',    // 日期改为 warning 类型
    '公式': 'danger',
    '布尔': 'info',
    '错误': 'danger',
    '空值': 'info',
    '未知': 'info'
  }
  return typeMap[type] || 'info'
}



// 监听单元格选择变化
const setupCellSelectionListener = () => {
  const hot = getSafeHotInstance()
  if (!hot) return

  // 监听选择变化
  hot.addHook('afterSelection', (startRow, startCol, endRow, endCol) => {
    // 如果是单单元格选择
    if (startRow === endRow && startCol === endCol) {
      updateSelectedCellDisplay(startRow, startCol)
    } else {
      // 多单元格选择，隐藏显示栏
      showCellContent.value = false
    }
  })

  // 监听数据变化（当单元格内容被编辑时）
  hot.addHook('afterChange', (changes, source) => {
    if (changes && selectedCell.value.row !== null && selectedCell.value.col !== null) {
      // 检查当前选中的单元格是否被修改
      const isSelectedCellChanged = changes.some(([row, col]) =>
        row === selectedCell.value.row && col === selectedCell.value.col
      )

      if (isSelectedCellChanged) {
        updateSelectedCellDisplay(selectedCell.value.row, selectedCell.value.col)
      }
    }
  })

  console.log('✅ 单元格选择监听器已配置')
}


// 修改 updateSelectedCellDisplay 函数中的类型判断部分
const updateSelectedCellDisplay = (row, col) => {
  const hot = getSafeHotInstance()
  if (!hot) {
    showCellContent.value = false
    return
  }

  try {
    // 获取单元格内容
    const content = hot.getDataAtCell(row, col)
    const cellMeta = hot.getCellMeta(row, col)

    // 分析内容
    const contentStr = content !== null && content !== undefined ? String(content) : ''
    const charCount = contentStr.length
    const lineCount = contentStr.split('\n').length

    // 判断单元格类型
    let cellType = '未知'
    let dataFormat = '文本'
    let isNumeric = false
    let isFormula = false
    let isValidNumber = false
    let numberValidationMsg = ''
    let validationDetails = ''

    // 先进行字符串类型检查
    if (typeof content === 'string') {
      const trimmed = content.trim()

      // 检查是否为公式（最高优先级）
      if (trimmed.startsWith('=')) {
        cellType = '公式'
        isFormula = true
        dataFormat = '计算'
      }
      // 检查是否为布尔值
      else if (trimmed === 'TRUE' || trimmed === 'FALSE' || trimmed === 'true' || trimmed === 'false') {
        cellType = '布尔'
        dataFormat = '逻辑'
      }
      // 检查是否为空值
      else if (trimmed === '' || trimmed === null) {
        cellType = '空值'
        dataFormat = '空'
      }
      // 检查是否为日期格式
      else if (isDateString(trimmed)) {
        cellType = '日期'
        dataFormat = '日期'
      }
      // 检查是否为纯数字字符串（可能是年份或ID等）
      else {
        // 尝试解析为数字
        const numericValue = parseFloat(trimmed)
        const isNumericString = !isNaN(numericValue) && isFinite(numericValue)

        if (isNumericString) {
          // 特殊处理：判断是否为年份（4位数字）
          if (/^\d{4}$/.test(trimmed) && trimmed >= '1900' && trimmed <= '2100') {
            cellType = '日期'
            dataFormat = '年份'
          }
          // 特殊处理：判断是否为日期数字（如20241231）
          else if (/^\d{8}$/.test(trimmed)) {
            const year = trimmed.substring(0, 4)
            const month = trimmed.substring(4, 6)
            const day = trimmed.substring(6, 8)
            if (year >= '1900' && year <= '2100' && month >= '01' && month <= '12' && day >= '01' && day <= '31') {
              cellType = '日期'
              dataFormat = '日期数字'
            } else {
              // 不是合法日期，按数字处理
              cellType = '数字'
              dataFormat = '数值'
              isNumeric = true
              const validationResult = validateNumberFormat(trimmed)
              isValidNumber = validationResult.isValid
              numberValidationMsg = validationResult.message
              validationDetails = validationResult.details || ''
            }
          }
          // 普通数字字符串
          else {
            cellType = '数字'
            dataFormat = '数值'
            isNumeric = true
            const validationResult = validateNumberFormat(trimmed)
            isValidNumber = validationResult.isValid
            numberValidationMsg = validationResult.message
            validationDetails = validationResult.details || ''
          }
        } else {
          // 不是数字字符串
          cellType = '文本'
        }
      }
    }
    // 原生数字类型
    else if (typeof content === 'number' && !isNaN(content) && isFinite(content)) {
      // 特殊处理：判断是否为年份数字
      if (content >= 1900 && content <= 2100 && content % 1 === 0) {
        cellType = '日期'
        dataFormat = '年份'
      } else {
        cellType = '数字'
        dataFormat = '数值'
        isNumeric = true
        isValidNumber = true
        numberValidationMsg = '✅ 格式正确'
        validationDetails = '原生数字类型'
      }
    }
    // 日期对象
    else if (content instanceof Date) {
      cellType = '日期'
      dataFormat = '日期对象'
    }
    // 其他类型
    else if (content === null || content === undefined) {
      cellType = '空值'
      dataFormat = '空'
    }

    // 检查是否被修改过
    const cellKey = `${row},${col}`
    const isModified = modifiedCells.value.has(cellKey)

    // 获取格式信息（如果有的话）
    const formatInfo = cellMeta?.format || ''

    // 检查是否有数据验证
    const validation = cellMeta?.validator ? '有验证规则' : '无验证'

    // 检查是否为只读
    const isReadOnly = cellMeta?.readOnly || false

    // 更新选中单元格信息
    selectedCell.value = {
      row,
      col,
      position: calculateCellPosition(row, col),
      content: contentStr,
      type: cellType,
      charCount,
      lineCount,
      // 新增数据特性
      format: formatInfo,
      isModified,
      isReadOnly,
      validation,
      // 单元格在表格中的位置信息
      rowIndex: row + 1,  // 用户看到的行号（从1开始）
      colIndex: col + 1,  // 用户看到的列号（从1开始）
      // 数据类型标记
      isNumeric,
      isFormula,
      // 数字验证相关
      isValidNumber,
      numberValidationMsg,
      validationDetails,
      // 单元格在数据中的关系
      inDualHeader: hasDualHeaders.value,
      // 如果是双表头，添加表头信息
      ...(hasDualHeaders.value && {
        headerInfo: {
          isTopLeft: row === 0 && col === 0,
          isHorizontalHeader: row === 0 && col > 0,
          isVerticalHeader: row > 0 && col === 0
        }
      })
    }

    // 显示内容栏
    showCellContent.value = true

    console.log('🔍 选中单元格详情:', selectedCell.value)

    // 确保内容区域可见
    nextTick(() => {
      const contentDisplay = document.querySelector('.cell-content-display')
      if (contentDisplay) {
        contentDisplay.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }
    })

  } catch (error) {
    console.warn('⚠️ 获取单元格内容失败:', error)
    showCellContent.value = false
  }
}




// 更新：更全面的日期字符串检测函数
const isDateString = (str) => {
  // 移除首尾空格
  const trimmedStr = str.trim()

  // 常见日期格式检测
  const datePatterns = [
    // YYYY-MM-DD
    /^\d{4}-\d{2}-\d{2}$/,
    // YYYY/MM/DD
    /^\d{4}\/\d{2}\/\d{2}$/,
    // YYYY年MM月DD日
    /^\d{4}年\d{1,2}月\d{1,2}日$/,
    // YYYY年MM月
    /^\d{4}年\d{1,2}月$/,
    // YYYY年
    /^\d{4}年$/,
    // XX年XX月 (两位数年)
    /^\d{2}年\d{1,2}月$/,
    // XX年 (两位数年)
    /^\d{2}年$/,
    // MM/DD/YYYY
    /^\d{2}\/\d{2}\/\d{4}$/,
    // DD-MM-YYYY
    /^\d{2}-\d{2}-\d{4}$/,
    // YYYY-MM-DD HH:MM:SS
    /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/,
    // YYYY-MM-DD HH:MM
    /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/,
    // YYYY.MM.DD
    /^\d{4}\.\d{2}\.\d{2}$/,
    // 中文日期格式
    /^\d{4}年\d{1,2}月\d{1,2}日 \d{1,2}时\d{1,2}分\d{1,2}秒$/,
    // 中文日期格式（简写）
    /^\d{4}年\d{1,2}月\d{1,2}日 \d{1,2}:\d{1,2}$/,
    // 季度格式
    /^\d{4}年[第]?[一二三四1234][季季度]$/,
    // 上半年/下半年
    /^\d{4}年[上下]半年$/,
    // 中文月份
    /^\d{4}年[一二三四五六七八九十]+月$/
  ]

  // 先进行模式匹配
  const patternMatch = datePatterns.some(pattern => pattern.test(trimmedStr))

  // 如果不是模式匹配，再进行语义分析
  if (!patternMatch) {
    // 检查是否是"X年"格式
    if (trimmedStr.endsWith('年')) {
      const yearPart = trimmedStr.replace('年', '')
      // 可以是2位或4位数字
      if (/^\d{2}$/.test(yearPart) || /^\d{4}$/.test(yearPart)) {
        return true
      }
    }

    // 检查是否是"X年X月"格式
    if (trimmedStr.includes('年') && trimmedStr.endsWith('月')) {
      const parts = trimmedStr.split('年')
      if (parts.length === 2) {
        const yearPart = parts[0]
        const monthPart = parts[1].replace('月', '')
        // 年份可以是2位或4位数字
        const validYear = /^\d{2}$/.test(yearPart) || /^\d{4}$/.test(yearPart)
        // 月份可以是1-2位数字或中文数字
        const validMonth = /^\d{1,2}$/.test(monthPart) ||
                          /^[一二三四五六七八九十]+$/.test(monthPart)
        return validYear && validMonth
      }
    }
  }

  return patternMatch
}


// 完整的数字格式验证函数
const validateNumberFormat = (value) => {
  if (value === null || value === undefined) {
    return {
      isValid: false,
      message: '❌ 空值',
      details: '数值不能为空'
    }
  }

  const str = String(value).trim()

  // 特殊处理：空字符串
  if (str === '') {
    return {
      isValid: false,
      message: '❌ 空值',
      details: '数值不能为空字符串'
    }
  }




  // 特殊处理：日期格式检测（高优先级）
  // 1. "2024年" 格式
  if (str.endsWith('年')) {
    const yearPart = str.replace('年', '')
    if (/^\d{4}$/.test(yearPart)) {
      const yearNum = parseInt(yearPart, 10)
      if (yearNum >= 1900 && yearNum <= 2100) {
        return {
          isValid: true,
          message: '📅 年份',
          details: `识别为年份: ${yearNum}年`
        }
      }
    } else if (/^\d{2}$/.test(yearPart)) {
      // 2位数年份
      const yearNum = parseInt(yearPart, 10)
      const fullYear = yearNum < 50 ? 2000 + yearNum : 1900 + yearNum
      return {
        isValid: true,
        message: '📅 年份',
        details: `识别为年份: ${fullYear}年 (${yearPart}年)`
      }
    }
  }

  // 2. "2024年10月" 格式
  if (str.includes('年') && str.endsWith('月')) {
    const parts = str.split('年')
    if (parts.length === 2) {
      const yearPart = parts[0]
      const monthPart = parts[1].replace('月', '')

      // 验证年份
      const validYear = /^\d{4}$/.test(yearPart) || /^\d{2}$/.test(yearPart)

      // 验证月份
      const validMonth = /^\d{1,2}$/.test(monthPart)
      let monthNum = validMonth ? parseInt(monthPart, 10) : null

      if (validYear && validMonth && monthNum >= 1 && monthNum <= 12) {
        let fullYear = yearPart
        if (/^\d{2}$/.test(yearPart)) {
          const yearNum = parseInt(yearPart, 10)
          fullYear = yearNum < 50 ? 2000 + yearNum : 1900 + yearNum
        }
        return {
          isValid: true,
          message: '📅 年月',
          details: `识别为年月: ${fullYear}年${monthPart}月`
        }
      }
    }
  }

  // 3. "2024年10月15日" 格式
  if (str.includes('年') && str.includes('月') && str.includes('日')) {
    // 匹配类似 "2024年10月15日" 的格式
    const dateMatch = str.match(/^(\d{4}|\d{2})年(\d{1,2})月(\d{1,2})日$/)
    if (dateMatch) {
      let yearPart = dateMatch[1]
      const monthPart = dateMatch[2]
      const dayPart = dateMatch[3]

      let fullYear = yearPart
      if (/^\d{2}$/.test(yearPart)) {
        const yearNum = parseInt(yearPart, 10)
        fullYear = yearNum < 50 ? 2000 + yearNum : 1900 + yearNum
      }

      const monthNum = parseInt(monthPart, 10)
      const dayNum = parseInt(dayPart, 10)

      if (monthNum >= 1 && monthNum <= 12 && dayNum >= 1 && dayNum <= 31) {
        return {
          isValid: true,
          message: '📅 完整日期',
          details: `识别为完整日期: ${fullYear}年${monthPart}月${dayPart}日`
        }
      }
    }
  }

  // 4. 纯4位数字年份
  if (/^\d{4}$/.test(str)) {
    const yearNum = parseInt(str, 10)
    if (yearNum >= 1900 && yearNum <= 2100) {
      return {
        isValid: true,
        message: '📅 年份',
        details: `识别为年份: ${yearNum}`
      }
    }
  }

  // 5. 8位数字日期（YYYYMMDD）
  if (/^\d{8}$/.test(str)) {
    const year = str.substring(0, 4)
    const month = str.substring(4, 6)
    const day = str.substring(6, 8)
    const yearNum = parseInt(year, 10)
    const monthNum = parseInt(month, 10)
    const dayNum = parseInt(day, 10)

    if (yearNum >= 1900 && yearNum <= 2100 &&
        monthNum >= 1 && monthNum <= 12 &&
        dayNum >= 1 && dayNum <= 31) {
      return {
        isValid: true,
        message: '📅 日期数字',
        details: `识别为日期: ${year}-${month}-${day}`
      }
    }
  }

  // 6. "2024年第一季度" 或 "2024年Q1" 格式
  if (str.includes('年') && (str.includes('季度') || str.includes('季') || str.match(/Q[1-4]/))) {
    const quarterMatch = str.match(/^(\d{4})年(?:第)?([一二三四1234])[季季度]?$/)
    if (quarterMatch) {
      const yearPart = quarterMatch[1]
      const quarterPart = quarterMatch[2]
      const quarterNames = ['一', '二', '三', '四']
      const quarterNum = isNaN(quarterPart) ? quarterNames.indexOf(quarterPart) + 1 : parseInt(quarterPart)

      if (quarterNum >= 1 && quarterNum <= 4) {
        return {
          isValid: true,
          message: '📅 季度',
          details: `识别为季度: ${yearPart}年第${quarterNames[quarterNum-1]}季度`
        }
      }
    }

    // 检查 Q1, Q2, Q3, Q4 格式
    const qMatch = str.match(/^(\d{4})年Q([1-4])$/)
    if (qMatch) {
      return {
        isValid: true,
        message: '📅 季度',
        details: `识别为季度: ${qMatch[1]}年Q${qMatch[2]}`
      }
    }
  }

  // 7. "2024年上半年" 或 "2024年下半年" 格式
  if (str.includes('年') && (str.includes('上半年') || str.includes('下半年'))) {
    const halfMatch = str.match(/^(\d{4})年([上下])半年$/)
    if (halfMatch) {
      return {
        isValid: true,
        message: '📅 半年度',
        details: `识别为半年度: ${halfMatch[1]}年${halfMatch[2]}半年`
      }
    }
  }

  // 新规则：首位不能是0（除非是小数0.x或负数）
    if (!str.includes('.') && !str.startsWith('-') && !str.startsWith('+')) {
      // 检查整数部分（移除逗号）
      const integerPart = str.replace(/,/g, '')
      if (integerPart.length > 1 && integerPart.startsWith('0')) {
        return {
          isValid: false,
          message: '❌ 首位零',
          details: `整数首位不能是0，除非是0.xx的小数或带符号的数字。当前值: "${str}"`
        }
      }
    }

  // 以下是原有的数字格式验证逻辑...
  // 规则1：不能包含空格
  if (str.includes(' ')) {
    // 但如果是日期格式中的空格，特殊处理
    const dateKeywords = ['年', '月', '日', '季度', '季', '半年', 'H1', 'H2', 'Q1', 'Q2', 'Q3', 'Q4']
    const hasDateKeyword = dateKeywords.some(keyword => str.includes(keyword))

    if (!hasDateKeyword) {
      return {
        isValid: false,
        message: '❌ 包含空格',
        details: '数值中不应包含空格，请移除空格'
      }
    }
  }

  // 规则2：只能包含数字、小数点、正负号、逗号（千分位）
  // 扩展：允许日期相关字符
  const dateKeywordsPattern = /[年月日季度季上下HhQq]/
  const hasDateKeyword = dateKeywordsPattern.test(str)

  if (hasDateKeyword) {
    // 如果是日期相关格式，跳过严格的数字验证
    return {
      isValid: true,
      message: '📅 日期格式',
      details: '识别为日期相关格式，跳过数字验证'
    }
  }

  const validPattern = /^[-+]?[0-9,]*\.?[0-9]*$/
  if (!validPattern.test(str)) {
    const illegalChars = str.match(/[^0-9,.\-+]/g)
    return {
      isValid: false,
      message: '❌ 非法字符',
      details: illegalChars ? `包含非法字符: ${illegalChars.join(', ')}` : '包含非法字符'
    }
  }

  // 规则3：小数点最多一个
  const decimalCount = (str.match(/\./g) || []).length
  if (decimalCount > 1) {
    return {
      isValid: false,
      message: '❌ 多个小数点',
      details: `找到 ${decimalCount} 个小数点，数值只能有一个小数点`
    }
  }

  // 规则4：如果包含逗号，检查千分位格式
  if (str.includes(',')) {
    // 移除符号和小数部分
    const signedStr = str.replace(/^[-+]/, '')
    const parts = signedStr.split('.')
    const integerPart = parts[0]

    // 检查逗号是否在正确位置（每三位一个逗号）
    const groups = integerPart.split(',')

    // 第一位可以是1-3位数字
    if (groups[0].length < 1 || groups[0].length > 3) {
      return {
        isValid: false,
        message: '❌ 千分位格式错误',
        details: `第一组应为1-3位数字，实际为 ${groups[0].length} 位: "${groups[0]}"`
      }
    }

    // 后续每组必须为3位数字
    for (let i = 1; i < groups.length; i++) {
      if (groups[i].length !== 3) {
        return {
          isValid: false,
          message: '❌ 千分位格式错误',
          details: `第${i+1}组应为3位数字，实际为 ${groups[i].length} 位: "${groups[i]}"`
        }
      }
    }

    // 检查是否有连续逗号
    if (str.includes(',,')) {
      return {
        isValid: false,
        message: '❌ 连续逗号',
        details: '数值中包含连续逗号'
      }
    }

    // 检查逗号之间是否有空内容
    for (let i = 0; i < groups.length; i++) {
      if (groups[i] === '') {
        return {
          isValid: false,
          message: '❌ 空逗号段',
          details: '逗号之间不能为空'
        }
      }
    }
  }

  // 规则5：正负号只能在开头且只能有一个
  if (str.includes('-') && str.indexOf('-') > 0) {
    return {
      isValid: false,
      message: '❌ 负号位置错误',
      details: `负号必须在最前面，实际在第${str.indexOf('-') + 1}位`
    }
  }

  if (str.includes('+') && str.indexOf('+') > 0) {
    return {
      isValid: false,
      message: '❌ 正号位置错误',
      details: `正号必须在最前面，实际在第${str.indexOf('+') + 1}位`
    }
  }

  // 规则6：不能同时包含正负号
  if (str.includes('+') && str.includes('-')) {
    return {
      isValid: false,
      message: '❌ 符号冲突',
      details: '数值不能同时包含正号和负号'
    }
  }

  // 规则7：不能以小数点开头（除非前面有0）
  if (str.match(/^[-+]?\./)) {
    const suggested = str.replace(/^([-+]?)\./, '$10.')
    return {
      isValid: true,  // 技术上合法，但格式不规范
      message: '⚠️ 建议补0',
      details: `建议使用 "${suggested}" 格式`
    }
  }

  // 规则8：不能以逗号开头或结尾
  if (str.startsWith(',') || str.endsWith(',')) {
    return {
      isValid: false,
      message: '❌ 逗号位置错误',
      details: '逗号不能在数值的开头或结尾'
    }
  }

  // 规则9：小数点后不能有逗号
  if (str.includes('.') && str.split('.')[1].includes(',')) {
    return {
      isValid: false,
      message: '❌ 小数点后有逗号',
      details: '小数点后不能包含逗号'
    }
  }

  // 规则10：不能只有符号没有数字
  if (/^[-+]$/.test(str) || /^[-+],*$/.test(str)) {
    return {
      isValid: false,
      message: '❌ 缺少数字',
      details: '数值不能只有符号没有数字'
    }
  }

  // 规则11：逗号后不能直接跟小数点
  if (str.includes(',.')) {
    return {
      isValid: false,
      message: '❌ 逗号后直接小数点',
      details: '逗号后不能直接跟小数点'
    }
  }

  // 规则12：检查数值合理性（可选）
  if (str.includes('.')) {
    const parts = str.split('.')
    const integerPart = parts[0].replace(/[^0-9]/g, '') // 移除符号和逗号
    const decimalPart = parts[1]

    // 检查整数部分是否过大（可选，比如超过15位可能有问题）
    if (integerPart.length > 15) {
      return {
        isValid: true,  // 技术上合法，但可能有问题
        message: '⚠️ 数值过大',
        details: `整数部分有 ${integerPart.length} 位，可能超出精度范围`
      }
    }

    // 检查小数部分是否过长
    if (decimalPart.length > 6) {
      return {
        isValid: true,  // 技术上合法
        message: '⚠️ 小数位过多',
        details: `小数部分有 ${decimalPart.length} 位，建议保留2-4位`
      }
    }
  }

  // 规则13：检查连续多个0的情况（可能是错误输入）
  if (str.replace(/[^0]/g, '').length > 10) {
    return {
      isValid: true,  // 技术上合法
      message: '⚠️ 多零检查',
      details: '数值中包含多个连续的0，请检查是否正确'
    }
  }

  // 规则14：检查是否全是逗号
  if (/^[,]+$/.test(str)) {
    return {
      isValid: false,
      message: '❌ 全逗号',
      details: '数值不能全部由逗号组成'
    }
  }

  // 规则15：检查科学计数法（e/E）
  if (str.includes('e') || str.includes('E')) {
    // 科学计数法格式验证
    const scientificPattern = /^[-+]?[0-9]*\.?[0-9]+[eE][-+]?[0-9]+$/
    if (!scientificPattern.test(str)) {
      return {
        isValid: false,
        message: '❌ 科学计数法格式错误',
        details: '科学计数法格式应为: 数字e指数 或 数字E指数'
      }
    }
    return {
      isValid: true,
      message: '✅ 科学计数法',
      details: '科学计数法格式正确'
    }
  }

  // 规则16：检查是否为百分比
  if (str.endsWith('%')) {
    const numPart = str.slice(0, -1)
    // 递归验证去掉百分号的部分
    const numValidation = validateNumberFormat(numPart)
    if (!numValidation.isValid) {
      return {
        isValid: false,
        message: '❌ 百分比格式错误',
        details: `数值部分格式错误: ${numValidation.details}`
      }
    }
    return {
      isValid: true,
      message: '✅ 百分比',
      details: '百分比格式正确'
    }
  }

  // 规则17：检查是否为货币格式（¥、$、€开头）
  if (/^[¥$€]/.test(str)) {
    const numPart = str.slice(1)
    const numValidation = validateNumberFormat(numPart)
    if (!numValidation.isValid) {
      return {
        isValid: false,
        message: '❌ 货币格式错误',
        details: `数值部分格式错误: ${numValidation.details}`
      }
    }
    return {
      isValid: true,
      message: '💰 货币格式',
      details: '货币格式正确'
    }
  }

  // 规则18：检查是否为分数格式
  if (str.includes('/')) {
    const fractionParts = str.split('/')
    if (fractionParts.length === 2) {
      const numerator = fractionParts[0]
      const denominator = fractionParts[1]

      // 验证分子
      const numValidation = validateNumberFormat(numerator)
      if (!numValidation.isValid) {
        return {
          isValid: false,
          message: '❌ 分数格式错误',
          details: `分子格式错误: ${numValidation.details}`
        }
      }

      // 验证分母
      const denValidation = validateNumberFormat(denominator)
      if (!denValidation.isValid) {
        return {
          isValid: false,
          message: '❌ 分数格式错误',
          details: `分母格式错误: ${denValidation.details}`
        }
      }

      // 检查分母是否为0
      if (parseFloat(denominator.replace(/,/g, '')) === 0) {
        return {
          isValid: false,
          message: '❌ 分母为零',
          details: '分数分母不能为零'
        }
      }

      return {
        isValid: true,
        message: '🔢 分数',
        details: '分数格式正确'
      }
    }
  }

  // 规则19：检查是否为比例格式（如 1:2）
  if (str.includes(':')) {
    const ratioParts = str.split(':')
    if (ratioParts.length === 2) {
      const part1 = ratioParts[0]
      const part2 = ratioParts[1]

      // 验证第一部分
      const part1Validation = validateNumberFormat(part1)
      if (!part1Validation.isValid) {
        return {
          isValid: false,
          message: '❌ 比例格式错误',
          details: `第一部分格式错误: ${part1Validation.details}`
        }
      }

      // 验证第二部分
      const part2Validation = validateNumberFormat(part2)
      if (!part2Validation.isValid) {
        return {
          isValid: false,
          message: '❌ 比例格式错误',
          details: `第二部分格式错误: ${part2Validation.details}`
        }
      }

      return {
        isValid: true,
        message: '⚖️ 比例',
        details: '比例格式正确'
      }
    }
  }

  // 规则20：检查是否为范围格式（如 100-200）
  if (str.includes('-') && !str.startsWith('-')) {
    const rangeParts = str.split('-')
    if (rangeParts.length === 2) {
      const startPart = rangeParts[0]
      const endPart = rangeParts[1]

      // 验证起始值
      const startValidation = validateNumberFormat(startPart)
      if (!startValidation.isValid) {
        return {
          isValid: false,
          message: '❌ 范围格式错误',
          details: `起始值格式错误: ${startValidation.details}`
        }
      }

      // 验证结束值
      const endValidation = validateNumberFormat(endPart)
      if (!endValidation.isValid) {
        return {
          isValid: false,
          message: '❌ 范围格式错误',
          details: `结束值格式错误: ${endValidation.details}`
        }
      }

      // 检查起始值是否小于结束值
      const startValue = parseFloat(startPart.replace(/,/g, ''))
      const endValue = parseFloat(endPart.replace(/,/g, ''))
      if (startValue >= endValue) {
        return {
          isValid: true,  // 技术上合法，但逻辑可能有问题
          message: '⚠️ 范围顺序',
          details: `起始值(${startValue})不应大于等于结束值(${endValue})`
        }
      }

      return {
        isValid: true,
        message: '📏 范围',
        details: `数值范围: ${startValue} 到 ${endValue}`
      }
    }
  }

  // 所有验证通过
  const parsedValue = parseFloat(str.replace(/,/g, ''))
  let detailsMsg = '符合数值格式规范'

  if (!isNaN(parsedValue)) {
    if (parsedValue === 0) {
      detailsMsg += '，值为零'
    } else if (Math.abs(parsedValue) < 0.001) {
      detailsMsg += `，值为 ${parsedValue}（极小值）`
    } else if (Math.abs(parsedValue) > 1000000) {
      detailsMsg += `，值为 ${parsedValue.toExponential(2)}（大数值）`
    } else if (Math.abs(parsedValue) < 1 && parsedValue !== 0) {
      detailsMsg += `，值为 ${parsedValue}（小于1的小数）`
    } else {
      detailsMsg += `，解析值: ${parsedValue}`
    }

    // 检查是否为整数
    if (Number.isInteger(parsedValue)) {
      detailsMsg += '，整数'
    } else {
      const decimalPlaces = str.includes('.') ? str.split('.')[1].length : 0
      detailsMsg += `，小数位: ${decimalPlaces}`
    }

    // 检查数值是否在常见范围内
    if (parsedValue > 0 && parsedValue <= 100) {
      if (parsedValue <= 1) {
        detailsMsg += '，百分比范围'
      } else {
        detailsMsg += '，常规范围'
      }
    } else if (parsedValue > 100 && parsedValue <= 10000) {
      detailsMsg += '，较大数值'
    } else if (parsedValue > 10000) {
      detailsMsg += '，大数值'
    }
  } else {
    detailsMsg += '，无法解析为数值'
  }

  return {
    isValid: true,
    message: '✅ 格式正确',
    details: detailsMsg
  }
}



onMounted(() => {
  console.log('🎯 HandsontableExcelViewer onMounted 开始执行')

  // 1. 首先注册中文语言包
  const success = setupChineseLocalization()

  // 2. 立即设置当前语言
  if (success) {
    currentLanguage.value = 'zh-CN'
    langKey.value = 'zh-CN-' + Date.now() // 强制刷新
    console.log('✅ 中文语言包设置完成')
  } else {
    console.warn('⚠️ 中文语言包设置失败，使用英文')
    currentLanguage.value = 'en-US'
  }

  // 重置重试计数
  retryCount = 0

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
      setupEventListeners,

      // 添加表头紧急修复方法
      emergencyFixHeader: () => {
        const hot = getSafeHotInstance()
        if (!hot) return

        console.log('🚨 执行表头紧急修复')

        try {
          // 强制刷新表头
          hot.updateSettings({
            fixedRowsTop: fixedRowsTop.value,
            fixedColumnsLeft: fixedColumnsLeft.value
          })

          hot.render()

          // 直接操作DOM确保表头在正确位置
          const cloneTop = hot.rootElement.querySelector('.ht_clone_top')
          if (cloneTop) {
            cloneTop.style.position = 'absolute'
            cloneTop.style.top = '0px'
            cloneTop.style.left = '0px'
            cloneTop.style.zIndex = '100'
            cloneTop.style.visibility = 'visible'
            cloneTop.style.opacity = '1'
          }

          ElMessage.success('表头修复完成')
        } catch (error) {
          console.error('表头修复失败:', error)
        }
      },

      // 添加调试方法
      debugFilters: () => {
        if (hotTable.value?.hotInstance) {
          const hot = hotTable.value.hotInstance
          console.log('🔍 Handsontable 实例:', hot)

          // 兼容旧版本的插件检查方式
          let filterPlugin = null
          let allPlugins = []

          try {
            // 尝试新版本 API
            if (hot.getPluginsManager) {
              allPlugins = Object.keys(hot.getPluginsManager().plugins)
              filterPlugin = hot.getPlugin('filters')
            }
            // 尝试旧版本 API
            else if (hot.plugin) {
              filterPlugin = hot.plugin.filters
              allPlugins = Object.keys(hot.plugin).filter(key => hot.plugin[key])
            }
            // 最后尝试直接访问
            else if (hot.filters) {
              filterPlugin = hot.filters
              allPlugins = ['filters'] // 假设只有 filters 插件
            }
          } catch (error) {
            console.log('⚠️ 插件检查出错:', error)
          }

          console.log('🔍 筛选插件调试信息:', {
            实例: hot,
            筛选插件: filterPlugin,
            所有插件: allPlugins,
            版本: hot.version || '未知版本',
            表头元素: document.querySelectorAll('.ht_clone_top th')
          })

          // 检查配置
          console.log('⚙️ 当前配置:', {
            filters: hot.getSettings().filters,
            dropdownMenu: hot.getSettings().dropdownMenu,
            colHeaders: hot.getSettings().colHeaders
          })
        } else {
          console.log('❌ 表格实例未就绪')
        }
      },

      // 手动注册筛选插件
      registerFilterPlugin: () => {
        if (hotTable.value?.hotInstance) {
          const hot = hotTable.value.hotInstance
          try {
            // 尝试手动注册筛选插件
            const Filters = Handsontable.plugins.Filters
            if (Filters) {
              hot.getPluginsManager().addPlugin('filters', Filters)
              console.log('✅ 手动注册筛选插件成功')
            } else {
              console.log('❌ Filters 插件未找到，检查导入')
            }
          } catch (error) {
            console.error('❌ 注册筛选插件失败:', error)
          }
        }
      },

      // 添加测试方法
      testSelection: () => {
        const hot = getSafeHotInstance()
        if (hot) {
          console.log('🧪 测试选择功能')
          // 模拟选择一个区域（第2-4行，第1-2列）
          hot.selectCell(1, 0, 3, 1)
        }
      },

      // 显示当前选择状态
      debugSelection: () => {
        console.log('🔍 当前选择状态:', {
          显示统计面板: showStatsPanel.value,
          当前选择: currentSelection.value,
          统计信息: stats.value
        })
      }
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

  // ============================================
  // 新增：表头滚动保护机制
  // ============================================
  const protectTableHeader = () => {
    console.log('🛡️ 启动表头滚动保护')

    const checkHeaderPosition = () => {
      if (!isComponentActive.value) return

      const hot = getSafeHotInstance()
      if (!hot) return

      const cloneTop = hot.rootElement.querySelector('.ht_clone_top')
      if (!cloneTop) return

      // 强制表头保持在顶部
      cloneTop.style.position = 'absolute'
      cloneTop.style.top = '0px'
      cloneTop.style.left = '0px'
      cloneTop.style.zIndex = '100'
      cloneTop.style.visibility = 'visible'
      cloneTop.style.opacity = '1'

      // 监听滚动事件，实时修复
      if (excelContainer.value) {
        const handleScroll = () => {
          cloneTop.style.top = '0px'
        }

        excelContainer.value.addEventListener('scroll', handleScroll)

        // 保存清理函数
        window._headerScrollHandler = handleScroll
      }
    }

    // 延迟启动保护
    safeSetTimeout(() => {
      if (isComponentActive.value) {
        checkHeaderPosition()

        // 定期检查（每2秒一次）
        const intervalId = setInterval(() => {
          if (!isComponentActive.value) {
            clearInterval(intervalId)
            return
          }
          checkHeaderPosition()
        }, 2000)

        // 保存清理函数
        window._headerCheckInterval = intervalId
      }
    }, 1000)
  }

  // 启动表头保护
  protectTableHeader()

  // ============================================
  // 延迟初始化表格
  // ============================================
  safeSetTimeout(() => {
    console.log('⏰ 延迟初始化开始')

    if (!isComponentActive.value || !isHotInstanceValid()) {
      console.log('ℹ️ 组件已卸载或实例无效，跳过初始化')
      return
    }

    if (hotTable.value?.hotInstance) {
      const hot = hotTable.value.hotInstance
      console.log('✅ Handsontable 实例已加载，版本:', hot.version || '未知')

      // 检查插件可用性的兼容方法
      let filterPlugin = null
      try {
        filterPlugin = hot.getPlugin ? hot.getPlugin('filters') :
                       hot.plugin ? hot.plugin.filters :
                       hot.filters
      } catch (error) {
        console.log('⚠️ 获取筛选插件时出错:', error)
      }

      // 关键：确保语言设置正确应用
      const updateSettings = {
        language: currentLanguage.value, // 使用上面设置的当前语言
        filters: !!filterPlugin,
        dropdownMenu: [
          'filter_by_condition',
          'filter_by_value',
          'filter_action_bar',
          '---------',
          'filter_operators',
          '---------',
          'sort_asc',
          'sort_desc',
          '---------',
          'clear_column'
        ],
        // 添加表头固定配置
        fixedRowsTop: fixedRowsTop.value,
        fixedColumnsLeft: fixedColumnsLeft.value,
        // 防止表头被隐藏的额外配置
        viewportRowRenderingOffset: 50,
        viewportColumnRenderingOffset: 20
      }

      if (filterPlugin) {
        console.log('✅ 筛选插件已找到，启用完整功能')
        try {
          if (filterPlugin.enablePlugin) {
            filterPlugin.enablePlugin()
          }
        } catch (error) {
          console.error('❌ 启用筛选插件失败:', error)
        }
      } else {
        console.log('⚠️ 筛选插件未找到，使用 dropdownMenu 的基础筛选')
        updateSettings.filters = false
      }

      // 只更新可以修改的设置
      hot.updateSettings(updateSettings)

      // 强制重新渲染
      try {
        hot.render()
        console.log('🔄 表格重新渲染完成')
      } catch (error) {
        console.error('❌ 重新渲染失败:', error)
      }

      // 配置事件监听
      setupEventListeners()

      // 检查表头是否显示筛选图标和语言设置
      safeSetTimeout(() => {
        if (!isComponentActive.value || !isHotInstanceValid()) return

        const headers = document.querySelectorAll('.ht_clone_top th')
        console.log(`📊 表头数量: ${headers.length}`)
        headers.forEach((header, index) => {
          const hasDropdown = header.querySelector('.changeType')
          console.log(`表头 ${index}: 有下拉菜单 = ${!!hasDropdown}`)
        })

        console.log('🌐 验证中文设置:', {
          当前语言: hot.getSettings().language,
          筛选配置: hot.getSettings().filters,
          语言包状态: Handsontable.languages.getLanguageDictionary(currentLanguage.value) ? '已加载' : '未加载'
        })

        // 测试中文菜单显示（使用安全的方式）
        testActualDropdownContent() // 使用已有的函数
      }, 1000)

    } else {
      console.log('❌ Handsontable 实例仍未就绪')
    }

    // 配置列选择监听
    safeSetTimeout(() => {
      if (isComponentActive.value && isHotInstanceValid()) {
        setupCellSelectionListener()
        setupColumnSelectionListener()
      }
    }, 500)

  }, 2000)

  // 添加语言设置验证（修复 getLanguages 错误）
  safeSetTimeout(() => {
    verifyLanguageSettingFixed() // 使用修复后的函数
  }, 3500)

  // 添加快捷键支持
  setupKeyboardShortcuts()
})

// ============================================
// 修改 onUnmounted 函数，清理表头保护相关资源
// ============================================
onUnmounted(() => {
  console.log('🔧 开始清理组件资源...')

  // 首先设置组件为非激活状态
  isComponentActive.value = false

  // 清理表头保护相关资源
  if (window._headerScrollHandler && excelContainer.value) {
    excelContainer.value.removeEventListener('scroll', window._headerScrollHandler)
    delete window._headerScrollHandler
    console.log('✅ 表头滚动监听器已移除')
  }

  if (window._headerCheckInterval) {
    clearInterval(window._headerCheckInterval)
    delete window._headerCheckInterval
    console.log('✅ 表头检查定时器已清理')
  }

  // 清理所有定时器
  clearAllTimeouts()

  // 清理 ResizeObserver
  if (resizeObserver.value) {
    resizeObserver.value.disconnect()
    console.log('✅ ResizeObserver 已清理')
  }

  // 移除窗口大小变化监听器
  window.removeEventListener('resize', handleResize)
  console.log('✅ 窗口大小监听器已移除')

  // 清理全局实例
  if (window.excelViewerInstance) {
    delete window.excelViewerInstance
    console.log('✅ 全局实例已清理')
  }

  // 安全销毁 Handsontable 实例
  if (hotTable.value?.hotInstance && !hotTable.value.hotInstance.isDestroyed) {
    try {
      console.log('🔧 正在销毁 Handsontable 实例...')
      hotTable.value.hotInstance.destroy()
      console.log('✅ Handsontable 实例已安全销毁')
    } catch (error) {
      console.log('ℹ️ 清理 Handsontable 实例:', error.message)
    }
  } else {
    console.log('ℹ️ Handsontable 实例已销毁或不存在，跳过销毁操作')
  }

  console.log('✅ 组件资源清理完成')
})



// 在 onMounted 中添加表头保护
const protectHeaderFromHiding = () => {
  console.log('🛡️ 启动表头防隐藏保护')

  let lastScrollTop = 0
  let isDragging = false

  const checkAndFixHeader = () => {
    if (!isComponentActive.value) return

    const hot = getSafeHotInstance()
    if (!hot) return

    // 查找表头元素
    const headerClones = [
      hot.rootElement.querySelector('.ht_clone_top'),
      hot.rootElement.querySelector('.ht_clone_left_top')
    ].filter(Boolean)

    headerClones.forEach(header => {
      if (!header) return

      // 获取当前滚动位置
      const container = excelContainer.value
      const scrollTop = container?.scrollTop || 0
      const maxScroll = container?.scrollHeight - container?.clientHeight || 0

      // 如果接近底部，防止表头被隐藏
      if (scrollTop > lastScrollTop && scrollTop > maxScroll - 100) {
        console.log('⚠️ 检测到滚动到底部，保护表头')

        // 方法1：确保表头显示
        header.style.visibility = 'visible'
        header.style.opacity = '1'
        header.style.zIndex = '999'

        // 方法2：如果表头被隐藏，强制重新定位
        const headerRect = header.getBoundingClientRect()
        if (headerRect.top < 0 || header.style.display === 'none') {
          console.log('🔧 表头被隐藏，强制修复')

          // 显示表头
          header.style.display = 'block'
          header.style.visibility = 'visible'

          // 重新定位
          header.style.position = 'absolute'
          header.style.top = '0px'

          // 如果是固定列的表头，还需要特殊处理
          if (header.classList.contains('ht_clone_left_top')) {
            header.style.left = '0px'
          }
        }

        // 方法3：如果表头位置异常，滚动一点点回去
        if (scrollTop >= maxScroll - 50) {
          console.log('↩️ 滚动到底部边界，轻微回滚')
          container.scrollTop = Math.max(0, scrollTop - 10)
        }
      }

      lastScrollTop = scrollTop
    })
  }

  // 监听滚动事件
  const setupScrollListener = () => {
    const container = excelContainer.value
    if (!container) return

    const handleScroll = () => {
      checkAndFixHeader()
    }

    // 使用 passive: true 提高性能
    container.addEventListener('scroll', handleScroll, { passive: true })

    // 监听鼠标/触摸拖拽结束
    container.addEventListener('mouseup', () => {
      isDragging = false
      safeSetTimeout(checkAndFixHeader, 100)
    })

    container.addEventListener('touchend', () => {
      isDragging = false
      safeSetTimeout(checkAndFixHeader, 100)
    })

    container.addEventListener('mousedown', () => { isDragging = true })
    container.addEventListener('touchstart', () => { isDragging = true })

    // 保存清理函数
    window._headerScrollHandler = handleScroll
    window._headerScrollContainer = container
  }

  // 延迟设置监听器
  safeSetTimeout(() => {
    if (isComponentActive.value) {
      setupScrollListener()

      // 定期检查表头状态（每2秒）
      const checkInterval = setInterval(() => {
        if (!isComponentActive.value) {
          clearInterval(checkInterval)
          return
        }
        checkAndFixHeader()
      }, 2000)

      window._headerCheckInterval = checkInterval
    }
  }, 1500)
}

// 在 onMounted 中调用
protectHeaderFromHiding()

// 添加应急修复方法
const emergencyFixVanishingHeader = () => {
  const hot = getSafeHotInstance()
  if (!hot) {
    ElMessage.warning('表格实例未就绪')
    return
  }

  console.log('🚨 执行表头防消失应急修复')

  // 方法1：强制重新渲染表格
  hot.render()

  // 方法2：重置滚动位置
  const container = excelContainer.value
  if (container) {
    // 轻微回滚，避免触发表头隐藏
    const currentScroll = container.scrollTop
    if (currentScroll > container.scrollHeight - container.clientHeight - 100) {
      container.scrollTop = Math.max(0, currentScroll - 50)
    }
  }

  // 方法3：直接操作DOM修复表头
  safeSetTimeout(() => {
    const headerClones = [
      hot.rootElement.querySelector('.ht_clone_top'),
      hot.rootElement.querySelector('.ht_clone_left_top')
    ]

    headerClones.forEach(header => {
      if (!header) return

      // 确保表头可见
      header.style.display = 'block'
      header.style.visibility = 'visible'
      header.style.opacity = '1'
      header.style.zIndex = '999'
      header.style.position = '' // 重置position

      // 确保表头内容可见
      const cells = header.querySelectorAll('th, td')
      cells.forEach(cell => {
        cell.style.visibility = 'visible'
        cell.style.opacity = '1'
      })
    })

    ElMessage.success('表头修复完成')
  }, 100)
}

// 暴露到控制台
window.fixHeader = emergencyFixVanishingHeader

</script>


<style scoped>
/* 恢复正常的表头样式，移除所有 sticky 定位 */
.handsontable-excel-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
}

.excel-toolbar {
  flex-shrink: 0;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 60px;
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

/* ====================
   关键修复：恢复滚动功能
   ==================== */
.excel-container {
  flex: 1;
  min-height: 0;
  overflow: auto; /* 确保可以滚动 */
  position: relative;
  border: 1px solid #e0e0e0;
  background: white;
}

/* 给表格容器添加padding，避免内容被遮挡 */
.excel-container {
  padding-top: 1px !important; /* 微小padding避免边界问题 */
}


/* 确保 Handsontable 正常显示 */
:deep(.handsontable .wtHolder) {
  overflow: auto !important;
}

:deep(.handsontable) {
  position: relative;
}

/* ====================
   表头固定修复（不破坏滚动）
   ==================== */
/* 关键：不要修改表头的position，让Handsontable自己管理 */
:deep(.ht_clone_top) {
  z-index: 999 !important;
  overflow: visible !important;
}

/* 确保表头容器正常 */
:deep(.ht_clone_top .wtHolder) {
  overflow: hidden !important;
}

/* 主表格区域保持滚动 */
:deep(.ht_master .wtHolder) {
  overflow: auto !important;
  width: 100% !important;
}

/* 隐藏左侧表头的滚动条 */
:deep(.ht_clone_left::-webkit-scrollbar) {
  display: none !important;
}

/* ====================
   其他样式保持不变
   ==================== */
:deep(.modified-cell) {
  background-color: #ffebee !important;
  border: 1px solid #f44336 !important;
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

/* 确保表头文本可见 */
:deep(.ht_clone_top th) {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
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

.stats-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 12px;
  background: #f0f9ff;
  border: 1px solid #e1f5fe;
  border-radius: 6px;
  margin-right: 16px;
}

.stat-item {
  font-size: 12px;
  color: #1890ff;
  font-weight: 500;
}

.stat-item:not(:last-child)::after {
  content: "|";
  margin-left: 8px;
  color: #d9d9d9;
}

/* 确保统计面板在移动端也能正常显示 */
@media (max-width: 768px) {
  .stats-panel {
    flex-wrap: wrap;
    gap: 8px;
  }

  .stat-item::after {
    content: none !important;
  }
}

.stats-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 12px;
  background: #f0f9ff;
  border: 1px solid #e1f5fe;
  border-radius: 6px;
  margin-right: 16px;
  max-width: 600px;
  overflow: hidden;
}

.stat-item {
  font-size: 12px;
  color: #1890ff;
  font-weight: 500;
  white-space: nowrap;
}

.stat-item:not(:last-child)::after {
  content: "|";
  margin-left: 8px;
  color: #d9d9d9;
}

/* 选中区域统计的特殊样式 */
.stats-panel .el-tag[type="success"] {
  background: #f6ffed;
  border-color: #b7eb8f;
  color: #52c41a;
}

/* 清除选择按钮 */
.stats-panel .el-button {
  margin-left: 4px;
  padding: 0 4px;
}

/* 确保统计面板在移动端也能正常显示 */
@media (max-width: 768px) {
  .stats-panel {
    flex-wrap: wrap;
    gap: 8px;
    max-width: 300px;
  }

  .stat-item::after {
    content: none !important;
  }

  .stat-item {
    font-size: 11px;
  }
}

/* 双表头特殊样式 */
:deep(.vertical-header-column) {
  background-color: #f6ffed !important;
  font-weight: 600 !important;
  min-width: 120px !important;
}

/* 确保固定表头样式正确 */
:deep(.ht_clone_top) {
  z-index: 100 !important;
}

:deep(.ht_clone_left) {
  -ms-overflow-style: none !important;  /* IE and Edge */
  scrollbar-width: none !important;     /* Firefox */
}

:deep(.ht_clone_top th) {
  background-color: #f0f9ff !important;
  border-bottom: 2px solid #409eff !important;
}

/* 确保左侧表头与主表格对齐 */
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

.header-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: #f0f9ff;
  border-radius: 4px;
  margin-left: 12px;
}

.indicator-text {
  font-size: 12px;
  color: #1890ff;
  font-weight: 500;
}

/* ====================
   新增：防止表头被拉上去的特殊修复
   ==================== */
/* 防止表头行高变化 */
:deep(.ht_clone_top th) {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
  height: 20px !important; /* 减小高度 */
  min-height: 20px !important;
  line-height: 20px !important;
  box-sizing: border-box !important;
}

/* 确保表头背景不透明 */
:deep(.ht_clone_top) {
  background-color: #f8f9fa !important;
}


/* 在 <style scoped> 部分添加或检查 */
.cell-info-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;  /* 确保多行时正确换行 */
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.cell-content-area {
  padding: 12px;
}

.cell-content-text {
  min-height: 24px;
  padding: 8px;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  white-space: pre-wrap;  /* 保持换行 */
  word-break: break-word;  /* 长单词换行 */
}

/* 不同类型单元格的特殊样式 */
.cell-content-text.numeric-cell {
  font-family: 'Consolas', monospace;
  text-align: right;
}

.cell-content-text.formula-cell {
  font-style: italic;
  color: #409eff;
}

.cell-content-text.modified-cell {
  background-color: #fff2f0;
  border-color: #ffccc7;
}


/* 新增验证状态样式 */
.cell-info-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  min-height: 44px;
}

.cell-validation .el-tag {
  font-weight: bold;
  cursor: help;
  min-width: 100px;
  text-align: center;
}

/* 验证状态颜色 */
.cell-validation .el-tag.el-tag--success {
  background-color: #f6ffed;
  border-color: #b7eb8f;
  color: #52c41a;
}

.cell-validation .el-tag.el-tag--danger {
  background-color: #fff2f0;
  border-color: #ffccc7;
  color: #ff4d4f;
}

.cell-validation .el-tag.el-tag--warning {
  background-color: #fff7e6;
  border-color: #ffd591;
  color: #fa8c16;
}

/* 无效数字的特殊样式 */
.cell-content-text.invalid-number {
  background-color: #fff2f0 !important;
  border-color: #ffccc7 !important;
  color: #ff4d4f;
}

/* 内容区域样式 */
.cell-content-area {
  padding: 12px;
  background: white;
}

.cell-content-text {
  min-height: 24px;
  padding: 8px;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.cell-content-text.numeric-cell {
  text-align: right;
  font-family: 'Consolas', 'Monaco', monospace;
}

.cell-content-text.formula-cell {
  font-style: italic;
  color: #1677ff;
  background-color: #f0f6ff;
}

.cell-content-text.modified-cell {
  background-color: #fff7e6;
  border-color: #ffd591;
}

/* 统计信息样式 */
.cell-stats {
  margin-left: auto;
  display: flex;
  gap: 12px;
}

.stat-item {
  font-size: 12px;
  color: #666;
  padding: 2px 6px;
  background: #f0f0f0;
  border-radius: 3px;
  cursor: default;
}


/* 日期类型样式 */
.date-hint .el-tag {
  background-color: #fff7e6;
  border-color: #ffd591;
  color: #fa8c16;
}

.date-hint .el-tag .el-icon {
  margin-right: 2px;
}

/* 内容区域样式优化 */
.cell-content-text[data-type="date"] {
  color: #fa8c16;
  background-color: #fff7e6;
  border-color: #ffd591;
}

.cell-content-text[data-type="year"] {
  color: #d48806;
  font-weight: 500;
}

</style>

