<template>
  <div class="image-screening-manager">
    <!-- 顶部工具栏 -->
    <div class="manager-toolbar">
      <div class="toolbar-left">
        <h2 class="manager-title">
          <i class="el-icon-folder-checked" />
          图片分类管理 - {{ pdfNameDisplay }}
        </h2>
        <div class="toolbar-info">
          <el-tag
            size="small"
            type="success"
          >
            <i class="el-icon-picture" />
            有表格: {{ stats.tables_count || 0 }}张
          </el-tag>
          <el-tag
            size="small"
            type="info"
          >
            <i class="el-icon-picture-outline" />
            无表格: {{ stats.no_tables_count || 0 }}张
          </el-tag>
          <el-tag
            v-if="stats.uncertain_count"
            size="small"
            type="warning"
          >
            <i class="el-icon-question" />
            不确定: {{ stats.uncertain_count }}张
          </el-tag>
        </div>
      </div>

      <div class="toolbar-right">
        <!-- 多选状态显示 -->
        <div
          v-if="isMultiSelectMode && selectedCount > 0"
          class="selection-info"
        >
          <el-tag
            type="primary"
            size="small"
          >
            <i class="el-icon-check" />
            已选择 {{ selectedCount }} 张图片
          </el-tag>
        </div>

        <!-- 批量操作按钮组 -->
        <div
          v-if="isMultiSelectMode && selectedCount > 0"
          class="batch-actions"
        >
          <!-- 当前在有表格分类：只显示移动到无表格 -->
          <el-button
            v-if="activeCategory === 'tables'"
            type="info"
            size="small"
            icon="el-icon-close"
            @click="batchMoveImages('no_tables')"
          >
            批量移动到无表格
          </el-button>

          <!-- 当前在无表格分类：只显示移动到有表格 -->
          <el-button
            v-if="activeCategory === 'no_tables'"
            type="success"
            size="small"
            icon="el-icon-check"
            @click="batchMoveImages('tables')"
          >
            批量移动到有表格
          </el-button>

          <!-- 当前在不确定分类：显示两个按钮 -->
          <template v-if="activeCategory === 'uncertain'">
            <el-button
              type="success"
              size="small"
              icon="el-icon-check"
              @click="batchMoveImages('tables')"
            >
              批量移动到有表格
            </el-button>
            <el-button
              type="info"
              size="small"
              icon="el-icon-close"
              @click="batchMoveImages('no_tables')"
            >
              批量移动到无表格
            </el-button>
          </template>

          <el-button
            type="text"
            size="small"
            icon="el-icon-delete"
            @click="clearSelection"
          >
            清空选择
          </el-button>
        </div>

        <!-- 多选模式开关按钮 -->
        <el-button
          :type="isMultiSelectMode ? 'primary' : 'default'"
          size="small"
          :icon="isMultiSelectMode ? 'el-icon-finished' : 'el-icon-select'"
          style="margin-right: 8px;"
          @click="toggleMultiSelectMode"
        >
          {{ isMultiSelectMode ? '退出多选' : '多选模式' }}
        </el-button>

        <el-button
          type="primary"
          size="small"
          icon="el-icon-refresh"
          :loading="refreshing"
          @click="refreshData"
        >
          刷新数据
        </el-button>
        <el-button
          type="success"
          size="small"
          icon="el-icon-finished"
          @click="handleFinish"
        >
          完成
        </el-button>
      </div>
    </div>

    <!-- 主内容区：分屏布局 -->
    <div
      class="split-layout"
      :class="{ 'multi-select-mode': isMultiSelectMode }"
    >
      <!-- 左侧：分类缩略图面板 -->
      <div
        class="left-panel"
        :class="{ 'full-width': isMultiSelectMode }"
      >
        <div class="category-tabs">
          <el-tabs
            v-model="activeCategory"
            type="card"
            @tab-click="handleTabChange"
          >
            <el-tab-pane
              label="有表格"
              name="tables"
            >
              <span slot="label">
                <i class="el-icon-check" />
                有表格
                <el-badge
                  :value="stats.tables_count"
                  :max="99"
                  class="tab-badge"
                />
              </span>
            </el-tab-pane>

            <el-tab-pane
              label="无表格"
              name="no_tables"
            >
              <span slot="label">
                <i class="el-icon-close" />
                无表格
                <el-badge
                  :value="stats.no_tables_count"
                  :max="99"
                  class="tab-badge"
                />
              </span>
            </el-tab-pane>

            <el-tab-pane
              v-if="stats.uncertain_count"
              label="不确定"
              name="uncertain"
            >
              <span slot="label">
                <i class="el-icon-question" />
                不确定
                <el-badge
                  :value="stats.uncertain_count"
                  :max="99"
                  class="tab-badge"
                />
              </span>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 缩略图网格 -->
        <div class="thumbnail-container">
          <div class="thumbnail-header">
            <div class="header-left">
              <span class="image-count">
                共 {{ currentImages.length }} 张图片
                <span
                  v-if="isMultiSelectMode && selectedCount > 0"
                  class="selected-count"
                >
                  (已选择 {{ selectedCount }} 张)
                </span>
              </span>
            </div>
            <div class="header-right">
              <el-button
                type="text"
                size="small"
                icon="el-icon-s-grid"
                :class="{ active: viewMode === 'grid' }"
                @click="viewMode = 'grid'"
              >
                网格
              </el-button>
              <el-button
                type="text"
                size="small"
                icon="el-icon-s-data"
                :class="{ active: viewMode === 'list' }"
                @click="viewMode = 'list'"
              >
                列表
              </el-button>
            </div>
          </div>

          <!-- 网格视图 -->
          <div
            v-if="viewMode === 'grid'"
            class="thumbnail-grid"
          >
            <div
              v-for="(image, index) in currentImages"
              :key="image.name"
              class="thumbnail-item"
              :class="{
                selected: !isMultiSelectMode && selectedImage?.name === image.name,
                'multi-selected': isMultiSelectMode && selectedImages.has(image.name)
              }"
              @click="selectImage(image, $event)"
            >
              <!-- 修改后的正确代码 -->
              <el-popover
                placement="right"
                :width="500"
                trigger="hover"
                popper-class="image-preview-popover"
              >
                <template #reference>
                  <div class="thumbnail-wrapper">
                    <!-- 图片元素 -->
                    <img
                      :src="getImageUrl(image)"
                      class="thumbnail-img"
                      loading="lazy"
                      @error="handleImageError(image, $event)"
                    >

                    <div class="thumbnail-overlay">
                      <el-tag
                        size="mini"
                        :type="getCategoryType(image.type)"
                        class="category-tag"
                      >
                        {{ getCategoryLabel(image.type) }}
                      </el-tag>
                    </div>
                    <!-- 多选模式下的选中标记 -->
                    <div
                      v-if="isMultiSelectMode && selectedImages.has(image.name)"
                      class="multi-select-checkmark"
                    >
                      <i class="el-icon-check" />
                    </div>
                  </div>
                </template>
                <!-- 悬停时显示完整大图 -->
                <div class="preview-image-container">
                  <img
                    :src="getImageUrl(image)"
                    class="preview-full-image"
                    loading="lazy"
                  >
                </div>
              </el-popover>


              <div class="thumbnail-info">
                <span
                  class="image-name"
                  :title="image.name"
                >
                  {{ image.name }}
                </span>
                <div class="thumbnail-actions">
                  <el-button
                    type="text"
                    size="mini"
                    icon="el-icon-view"
                    title="预览"
                    @click.stop="selectImage(image)"
                  />
                  <el-button
                    type="text"
                    size="mini"
                    icon="el-icon-right"
                    title="移动到..."
                    @click.stop="showMoveOptions(image)"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 列表视图 -->
          <div
            v-else
            class="thumbnail-list"
          >
            <el-table
              :data="currentImages"
              size="small"
              highlight-current-row
              style="width: 100%"
              @row-click="selectImage"
            >
              <el-table-column width="50">
                <template #default="scope">
                  <img
                    :src="getImageUrl(scope.row)"
                    class="list-thumbnail"
                    loading="lazy"
                  >
                </template>
              </el-table-column>

              <el-table-column
                prop="name"
                label="图片名称"
                min-width="150"
              >
                <template #default="scope">
                  <span class="list-image-name">{{ scope.row.name }}</span>
                </template>
              </el-table-column>

              <el-table-column
                prop="type"
                label="分类"
                width="100"
              >
                <template #default="scope">
                  <el-tag
                    size="small"
                    :type="getCategoryType(scope.row.type)"
                  >
                    {{ getCategoryLabel(scope.row.type) }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column
                label="操作"
                width="120"
              >
                <template #default="scope">
                  <el-button
                    type="text"
                    size="small"
                    icon="el-icon-view"
                    title="预览"
                    @click.stop="selectImage(scope.row)"
                  />
                  <el-button
                    type="text"
                    size="small"
                    icon="el-icon-right"
                    title="移动到..."
                    @click.stop="showMoveOptions(scope.row)"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 空状态 -->
          <div
            v-if="currentImages.length === 0 && !props.classifiedImages[activeCategory]?.length"
            class="empty-thumbnails"
          >
            <el-empty description="暂无图片">
              <p class="empty-tips">
                当前分类没有图片
              </p>
            </el-empty>
          </div>
        </div>
      </div>

      <!-- 右侧：大图预览和操作面板（多选模式下隐藏） -->
      <div
        v-if="!isMultiSelectMode"
        class="right-panel"
      >
        <div class="preview-header">
          <h3
            v-if="selectedImage"
            class="preview-title"
          >
            <i class="el-icon-picture-outline-round" />
            {{ selectedImage.name }}
          </h3>
          <h3
            v-else
            class="preview-title"
          >
            <i class="el-icon-picture-outline" />
            图片预览
          </h3>

          <div
            v-if="selectedImage"
            class="preview-nav"
          >
            <el-button
              size="small"
              icon="el-icon-arrow-left"
              :disabled="!hasPrevImage"
              @click="selectPrevImage"
            >
              上一张
            </el-button>
            <span class="nav-info">
              {{ currentImageIndex + 1 }} / {{ currentImages.length }}
            </span>
            <el-button
              size="small"
              icon="el-icon-arrow-right"
              :disabled="!hasNextImage"
              @click="selectNextImage"
            >
              下一张
            </el-button>
          </div>
        </div>

        <!-- 大图预览区域 -->
        <div class="preview-container">
          <div
            v-if="!selectedImage"
            class="empty-preview"
          >
            <el-empty description="请选择一张图片进行预览">
              <i
                class="el-icon-picture-outline"
                style="font-size: 80px; color: #dcdfe6;"
              />
            </el-empty>
          </div>

          <div
            v-else
            class="image-preview"
          >
            <div class="image-wrapper">
              <div
                v-if="previewLoading"
                class="image-loading"
              >
                <el-icon class="is-loading">
                  <Loading />
                </el-icon>
                <span>加载中...</span>
              </div>

              <!-- 这里应该有一个 img 标签 -->
              <img
                v-if="selectedImage"
                :src="getImageUrl(selectedImage, 'large')"
                class="preview-img"
                :class="{ loading: previewLoading }"
                @load="previewLoading = false"
                @error="handlePreviewError"
              >
            </div>

            <div class="image-info">
              <div class="info-row">
                <span class="info-label">文件名：</span>
                <span class="info-value">{{ selectedImage.name }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">当前分类：</span>
                <el-tag
                  :type="getCategoryType(selectedImage.type)"
                  size="small"
                >
                  {{ getCategoryLabel(selectedImage.type) }}
                </el-tag>
              </div>
              <div
                v-if="selectedImage.confidence"
                class="info-row"
              >
                <span class="info-label">置信度：</span>
                <span class="info-value">
                  {{ (selectedImage.confidence * 100).toFixed(1) }}%
                </span>
              </div>
              <div
                v-if="selectedImage.moved_at"
                class="info-row"
              >
                <span class="info-label">移动时间：</span>
                <span class="info-value">
                  {{ formatDate(selectedImage.moved_at) }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 操作面板 -->
        <div class="action-panel">
          <div class="action-section">
            <h4 class="action-title">
              <i class="el-icon-s-operation" />
              分类操作
            </h4>

            <div
              v-if="selectedImage"
              class="move-actions"
            >
              <el-button
                type="success"
                :disabled="selectedImage.type === 'tables'"
                @click="moveImage(selectedImage, 'tables')"
              >
                <i class="el-icon-check" />
                移动到有表格
              </el-button>

              <el-button
                type="info"
                :disabled="selectedImage.type === 'no_tables'"
                @click="moveImage(selectedImage, 'no_tables')"
              >
                <i class="el-icon-close" />
                移动到无表格
              </el-button>

              <el-button
                v-if="stats.uncertain_count"
                type="warning"
                :disabled="selectedImage.type === 'uncertain'"
                @click="moveImage(selectedImage, 'uncertain')"
              >
                <i class="el-icon-question" />
                移动到不确定
              </el-button>
            </div>

            <div
              v-else
              class="no-selection"
            >
              <p class="hint-text">
                请先选择一张图片
              </p>
            </div>
          </div>

          <div class="action-section">
            <h4 class="action-title">
              <i class="el-icon-magic-stick" />
              其他操作
            </h4>

            <div class="other-actions">
              <el-button
                type="primary"
                :disabled="!selectedImage"
                @click="redetectImage(selectedImage)"
              >
                <i class="el-icon-refresh" />
                重新检测
              </el-button>

              <el-button
                type="text"
                :disabled="!selectedImage"
                @click="downloadImage(selectedImage)"
              >
                <i class="el-icon-download" />
                下载图片
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 移动选项弹出框 -->
    <el-dialog
      v-model="showMoveDialog"
      title="移动图片"
      width="400px"
      destroy-on-close
    >
      <div
        v-if="imageToMove"
        class="move-dialog-content"
      >
        <p>将图片 <strong>{{ imageToMove.name }}</strong> 移动到：</p>

        <div class="move-options">
          <el-radio-group v-model="moveTargetType">
            <el-radio label="tables">
              <i class="el-icon-check" />
              有表格
            </el-radio>
            <el-radio label="no_tables">
              <i class="el-icon-close" />
              无表格
            </el-radio>
            <el-radio
              v-if="stats.uncertain_count"
              label="uncertain"
            >
              <i class="el-icon-question" />
              不确定
            </el-radio>
          </el-radio-group>
        </div>
      </div>

      <template #footer>
        <el-button @click="showMoveDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :disabled="!moveTargetType || imageToMove?.type === moveTargetType"
          @click="confirmMove"
        >
          确认移动
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>


<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { getBackendUrl } from '@/utils/config'

// 定义组件属性
const props = defineProps({
  pdfDiskName: {
    type: String,
    required: true
  },
  classifiedImages: {
    type: Object,
    default: () => ({
      tables: [],
      no_tables: [],
      uncertain: []
    })
  },
  stats: {
    type: Object,
    default: () => ({
      tables_count: 0,
      no_tables_count: 0,
      uncertain_count: 0,
      total: 0
    })
  },
  getImageUrlFn: {
    type: Function,
    default: null
  },
  onImageError: Function
})

// 定义事件
const emit = defineEmits([
  'close',
  'refresh',
  'move-image',
  'redetect-image',
  'finish'
])

// 响应式状态
const activeCategory = ref('tables')
const viewMode = ref('grid') // 'grid' 或 'list'
const selectedImage = ref(null)
const currentImageIndex = ref(-1)
const previewLoading = ref(false)
const refreshing = ref(false)


// === 第一步：添加多选状态管理（在 refreshing 之后添加）===
const selectedImages = ref(new Set()) // 使用Set存储选中的图片name
const isMultiSelectMode = ref(true) // 多选模式开关

// 计算选中的图片数量
const selectedCount = computed(() => selectedImages.value.size)

// 计算选中的图片对象数组
const selectedImageObjects = computed(() => {
  return currentImages.value.filter(img => selectedImages.value.has(img.name))
})
// === 第一步结束 ===


// === 第二步：添加切换多选模式的函数 ===
// 切换多选模式
const toggleMultiSelectMode = () => {
  isMultiSelectMode.value = !isMultiSelectMode.value
  if (!isMultiSelectMode.value) {
    selectedImages.value.clear() // 退出多选时清空选择
  }
  console.log('多选模式:', isMultiSelectMode.value ? '开启' : '关闭')
}
// === 第二步结束 ===


// === 第三步：添加图片选择切换函数 ===
// 切换图片选择状态
const toggleImageSelection = (image) => {
  if (selectedImages.value.has(image.name)) {
    selectedImages.value.delete(image.name)
  } else {
    selectedImages.value.add(image.name)
  }
  // 保持响应式更新
  selectedImages.value = new Set(selectedImages.value)
  console.log('当前选中图片:', Array.from(selectedImages.value))
}

// 修改现有的 selectImage 函数，支持多选模式
const selectImage = (image, event) => {
  if (isMultiSelectMode.value) {
    // 多选模式：切换选择状态
    toggleImageSelection(image)
  } else {
    // 单选模式：保持原有逻辑
    selectedImages.value.clear()
    selectedImage.value = image
    currentImageIndex.value = currentImages.value.findIndex(img => img.name === image.name)
    previewLoading.value = true
  }
}
// === 第三步结束 ===


// === 第五步：添加清空选择函数 ===
// 清除所有选择
const clearSelection = () => {
  selectedImages.value.clear()
  selectedImages.value = new Set(selectedImages.value)
  console.log('已清空选择')
}
// === 第五步结束 ===


// === 第七步：修复批量移动函数 ===
// 批量移动图片
const batchMoveImages = async (targetType) => {
  if (selectedImages.value.size === 0) {
    ElMessage.warning('请先选择要移动的图片')
    return
  }

  try {
    const selectedArray = Array.from(selectedImages.value)
    const movingCount = selectedArray.length

    // 确认对话框
    await ElMessageBox.confirm(
      `确定要将选中的 ${movingCount} 张图片移动到"${getCategoryLabel(targetType)}"分类吗？`,
      '批量移动确认',
      {
        confirmButtonText: '确定移动',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 显示批量操作进度 - 修复消息提示方式
    let loadingMessage = null
    try {
      loadingMessage = ElMessage.info({
        message: `正在移动图片... (0/${movingCount})`,
        duration: 0
      })
    } catch (e) {
      console.warn('消息提示创建失败，继续执行移动操作', e)
    }

    let successCount = 0
    let errorCount = 0

    // 逐个移动图片
    for (let i = 0; i < selectedArray.length; i++) {
      const imageName = selectedArray[i]
      const image = currentImages.value.find(img => img.name === imageName)

      if (!image) continue

      try {
        // 调用父组件的移动图片函数
        emit('move-image', {
          imageName: image.name,
          fromType: image.type,
          toType: targetType,
          pdfDiskName: props.pdfDiskName
        })
        successCount++
      } catch (error) {
        console.error(`移动图片 ${imageName} 失败:`, error)
        errorCount++
      }

      // 更新进度 - 修复消息更新方式
      if (loadingMessage) {
        try {
          loadingMessage.close()
          loadingMessage = ElMessage.info({
            message: `正在移动图片... (${i + 1}/${movingCount})`,
            duration: 0
          })
        } catch (e) {
          console.warn('消息更新失败', e)
        }
      }
    }

    // 关闭消息提示
    if (loadingMessage) {
      loadingMessage.close()
    }

    // 显示结果
    if (errorCount === 0) {
      ElMessage.success(`成功移动 ${successCount} 张图片到${getCategoryLabel(targetType)}`)
    } else {
      ElMessage.warning(`移动完成：成功 ${successCount} 张，失败 ${errorCount} 张`)
    }

    // 清空选择
    clearSelection()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量移动失败:', error)
      ElMessage.error('批量移动操作失败')
    }
  }
}
// === 第七步结束 ===


// 移动相关状态
const showMoveDialog = ref(false)
const imageToMove = ref(null)
const moveTargetType = ref('')

// 计算属性
const pdfNameDisplay = computed(() => {
  return props.pdfDiskName.replace('.pdf', '')
})

const currentImages = computed(() => {
  return props.classifiedImages[activeCategory.value] || []
})

const hasPrevImage = computed(() => {
  return selectedImage.value && currentImageIndex.value > 0
})

const hasNextImage = computed(() => {
  return selectedImage.value && currentImageIndex.value < currentImages.value.length - 1
})

// 方法
const getCategoryLabel = (type) => {
  const labels = {
    'tables': '有表格',
    'no_tables': '无表格',
    'uncertain': '不确定'
  }
  return labels[type] || type
}

const getCategoryType = (type) => {
  const types = {
    'tables': 'success',
    'no_tables': 'info',
    'uncertain': 'warning'
  }
  return types[type] || 'default'
}


const getImageUrl = (image, size = 'thumb') => {
  console.log('🖼️ getImageUrl 输入:', {
    image,
    hasGetImageUrlFn: !!props.getImageUrlFn,
    getImageUrlFnType: typeof props.getImageUrlFn,
    pdfDiskName: props.pdfDiskName
  })

  // 如果有父组件提供的URL生成函数，优先使用
  if (props.getImageUrlFn && typeof props.getImageUrlFn === 'function') {
    console.log('✅ 使用父组件函数')
    const url = props.getImageUrlFn(image, props.pdfDiskName.replace('.pdf', ''))
    console.log('生成的URL:', url)
    return url
  } else {
    console.log('❌ 父组件函数不存在，使用内部逻辑')
  }

  console.log('🔍 检查image字段:', {
    hasUrl: !!image.url,
    hasPath: !!image.path,
    pathValue: image.path,
    hasRelativePath: !!image.relative_path
  })


  // 如果有父组件提供的URL生成函数，优先使用
  if (props.getImageUrlFn && typeof props.getImageUrlFn === 'function') {
    return props.getImageUrlFn(image, props.pdfDiskName.replace('.pdf', ''))
  }

  // 根据图片数据生成URL
  if (image.url) return image.url

  if (image.path) {
    // 简单处理路径，实际应根据项目配置调整
    if (image.path.startsWith('http')) return image.path
    if (image.path.startsWith('/')) return image.path

    // 对于相对路径，构建完整URL
    const baseUrl = getBackendUrl('')
    const pdfFolder = props.pdfDiskName.replace('.pdf', '')

    // 检查是否是筛选后的图片
    if (image.path.includes('filtered_tables') || image.path.includes('tables/') || image.path.includes('no_tables/')) {
      return `${baseUrl}/api/${image.path}`
    } else {
      // 普通PNG图片
      return `${baseUrl}/api/png/${pdfFolder}/${image.name}`
    }
  }

  // 默认返回占位符或基于名称构建URL
  const baseUrl = getBackendUrl('')
  const pdfFolder = props.pdfDiskName.replace('.pdf', '')

  // 尝试几种可能的URL模式
  const possibleUrls = [
    `${baseUrl}/api/png/${pdfFolder}/${image.name}`,
    `${baseUrl}/api/filtered-tables/${pdfFolder}/tables/${image.name}`,
    `${baseUrl}/api/filtered-tables/${pdfFolder}/no_tables/${image.name}`,
    `${baseUrl}/static/png_output/${pdfFolder}/${image.name}`
  ]

  // 返回第一个URL，实际加载时会处理404
  return possibleUrls[0]
}



const selectImage000 = (image) => {
  selectedImage.value = image
  currentImageIndex.value = currentImages.value.findIndex(img => img.name === image.name)
  previewLoading.value = true

  console.log('选择图片:', image)
}

const selectPrevImage = () => {
  if (hasPrevImage.value && currentImageIndex.value > 0) {
    const prevIndex = currentImageIndex.value - 1
    selectImage(currentImages.value[prevIndex])
  }
}

const selectNextImage = () => {
  if (hasNextImage.value && currentImageIndex.value < currentImages.value.length - 1) {
    const nextIndex = currentImageIndex.value + 1
    selectImage(currentImages.value[nextIndex])
  }
}

const showMoveOptions = (image) => {
  imageToMove.value = image
  moveTargetType.value = ''
  showMoveDialog.value = true
}

const confirmMove = async () => {
  if (!imageToMove.value || !moveTargetType.value) return

  try {
    await emit('move-image', {
      imageName: imageToMove.value.name,
      fromType: imageToMove.value.type,
      toType: moveTargetType.value,
      pdfDiskName: props.pdfDiskName
    })

    showMoveDialog.value = false
    ElMessage.success('移动成功')

    // 如果移动的是当前选中的图片，更新选中状态
    if (selectedImage.value?.name === imageToMove.value.name) {
      selectedImage.value = { ...selectedImage.value, type: moveTargetType.value }
    }

  } catch (error) {
    console.error('移动失败:', error)
    ElMessage.error('移动失败')
  }
}

const moveImage = async (image, targetType) => {
  if (image.type === targetType) {
    ElMessage.warning('图片已在目标分类中')
    return
  }

  try {
    await emit('move-image', {
      imageName: image.name,
      fromType: image.type,
      toType: targetType,
      pdfDiskName: props.pdfDiskName
    })

    ElMessage.success(`已移动到${getCategoryLabel(targetType)}`)

  } catch (error) {
    console.error('移动失败:', error)
    ElMessage.error('移动失败')
  }
}

const redetectImage = async (image) => {
  if (!image) return

  try {
    await ElMessageBox.confirm(
      `确定要重新检测图片 "${image.name}" 吗？`,
      '重新检测确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await emit('redetect-image', {
      imageName: image.name,
      currentType: image.type,
      pdfDiskName: props.pdfDiskName
    })

    ElMessage.success('已提交重新检测')

  } catch (error) {
    if (error !== 'cancel') {
      console.error('重新检测失败:', error)
      ElMessage.error('重新检测失败')
    }
  }
}

const downloadImage = (image) => {
  if (!image) return

  const imageUrl = getImageUrl(image, 'large')
  const link = document.createElement('a')
  link.href = imageUrl
  link.download = image.name
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  ElMessage.success('开始下载图片')
}

const refreshData = async () => {
  refreshing.value = true
  try {
    await emit('refresh', props.pdfDiskName)
    ElMessage.success('数据已刷新')
  } catch (error) {
    console.error('刷新失败:', error)
    ElMessage.error('刷新失败')
  } finally {
    refreshing.value = false
  }
}

const handleFinish = () => {
  emit('finish')
  emit('close')
}

// 修改图片加载错误处理：
const handleImageError = (image, event) => {
  console.error('图片加载失败:', image.name, event)

  // 尝试其他可能的URL
  const imgElement = event.target
  const currentSrc = imgElement.src

  const baseUrl = getBackendUrl('')
  const pdfFolder = props.pdfDiskName.replace('.pdf', '')

  // 备选URL列表
  const fallbackUrls = [
    `${baseUrl}/api/png/${pdfFolder}/${image.name}`,
    `${baseUrl}/api/filtered-tables/${pdfFolder}/tables/${image.name}`,
    `${baseUrl}/api/filtered-tables/${pdfFolder}/no_tables/${image.name}`,
    `${baseUrl}/static/png_output/${pdfFolder}/${image.name}`,
    // 占位符图片
    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="%23f5f5f5"/><text x="50" y="50" font-family="Arial" font-size="12" text-anchor="middle" fill="%23999">图片加载失败</text></svg>'
  ]

  // 尝试下一个URL
  const currentIndex = fallbackUrls.indexOf(currentSrc)
  if (currentIndex >= 0 && currentIndex < fallbackUrls.length - 1) {
    imgElement.src = fallbackUrls[currentIndex + 1]
  } else if (currentIndex === -1 && fallbackUrls.length > 0) {
    // 如果当前URL不在列表中，尝试第一个备选URL
    imgElement.src = fallbackUrls[0]
  }
}

const handlePreviewError = () => {
  previewLoading.value = false
  ElMessage.error('图片加载失败')
}

const handleTabChange = () => {
  console.log('切换标签页到:', activeCategory.value)

  // 切换标签页时清除所有选择
  selectedImage.value = null
  currentImageIndex.value = -1

  // 清除多选选择
  selectedImages.value.clear()

  // 如果需要，可以更新Set的响应式
  selectedImages.value = new Set(selectedImages.value)

  console.log('已清空所有选择状态')
}

const formatDate = (dateString) => {
  if (!dateString) return '未知'
  try {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN')
  } catch {
    return dateString
  }
}

// 监听分类数据变化
watch(
  () => props.classifiedImages,
  () => {
    // 数据更新后，如果当前选中的图片不在当前分类中，清除选中
    if (selectedImage.value && activeCategory.value !== selectedImage.value.type) {
      selectedImage.value = null
      currentImageIndex.value = -1
    }
  },
  { deep: true }
)

// 组件挂载时自动选择第一张图片（如果有）
nextTick(() => {
  if (currentImages.value.length > 0) {
    selectImage(currentImages.value[0])
  }
})
</script>

<style scoped lang="scss">
.image-screening-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;

  .manager-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    background: #f5f7fa;
    border-bottom: 1px solid #e4e7ed;
    flex-shrink: 0;

    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 16px;

      .manager-title {
        margin: 0;
        font-size: 18px;
        color: #303133;
        font-weight: 600;

        i {
          margin-right: 8px;
          color: #409eff;
        }
      }

      .toolbar-info {
        display: flex;
        gap: 8px;
      }
    }

    .toolbar-right {
      display: flex;
      gap: 8px;
    }
  }

  .split-layout {
    flex: 1;
    display: flex;
    min-height: 0;
    overflow: hidden;

    .left-panel {
      flex: 0 0 65%;
      display: flex;
      flex-direction: column;
      border-right: 1px solid #e4e7ed;
      background: #fafafa;

      .category-tabs {
        flex-shrink: 0;
        background: #fff;
        padding: 0 20px;

        :deep(.el-tabs__header) {
          margin: 0;
        }

        :deep(.el-tabs__item) {
          height: 36px;
          line-height: 36px;
          font-size: 14px;

          i {
            margin-right: 4px;
          }

          .tab-badge {
            margin-left: 4px;

            :deep(.el-badge__content) {
              transform: translateY(-50%) translateX(100%);
            }
          }
        }
      }

      .thumbnail-container {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-height: 0;

        .thumbnail-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 20px;
          background: #fff;
          border-bottom: 1px solid #e4e7ed;
          flex-shrink: 0;

          .header-left {
            .image-count {
              color: #606266;
              font-size: 14px;
            }
          }

          .header-right {
            display: flex;
            gap: 4px;

            .el-button {
              color: #909399;
              padding: 4px 8px;

              &.active {
                color: #409eff;
                background: #ecf5ff;
              }

              &:hover {
                color: #409eff;
              }
            }
          }
        }

        .thumbnail-grid {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
          gap: 16px;

          .thumbnail-item {
            border: 1px solid #e4e7ed;
            border-radius: 4px;
            overflow: hidden;
            background: #fff;
            transition: all 0.2s;
            cursor: pointer;

            &:hover {
              border-color: #409eff;
              box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
              transform: translateY(-2px);

              /* 悬停时图片放大 */
              .thumbnail-wrapper .thumbnail-img {
                transform: scale(5);
              }
            }

            &.selected {
              border-color: #409eff;
              border-width: 2px;
              box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
            }

            .thumbnail-wrapper {
              position: relative;
              height: 120px;
              overflow: hidden;
              background: #f5f7fa;

              .thumbnail-img {
                  width: 100%;
                  height: 100%;
                  object-fit: contain;
                  transition: transform 0.3s ease;
                }

              .thumbnail-overlay {
                position: absolute;
                top: 4px;
                right: 4px;

                .category-tag {
                  font-size: 10px;
                  padding: 0 6px;
                  height: 20px;
                  line-height: 20px;
                }
              }
            }

            .thumbnail-info {
              padding: 8px;

              .image-name {
                display: block;
                font-size: 12px;
                color: #606266;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                margin-bottom: 4px;
              }

              .thumbnail-actions {
                display: flex;
                justify-content: flex-end;
                gap: 4px;

                .el-button {
                  padding: 2px;
                  min-height: auto;

                  i {
                    font-size: 12px;
                  }
                }
              }
            }
          }
        }

        .thumbnail-list {
          flex: 1;
          overflow-y: auto;

          :deep(.el-table) {
            .list-thumbnail {
              width: 40px;
              height: 40px;
              object-fit: contain;
              border-radius: 2px;
            }

            .list-image-name {
              font-size: 13px;
              color: #606266;
            }
          }
        }

        .empty-thumbnails {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #fff;

          .empty-tips {
            color: #909399;
            font-size: 14px;
            margin-top: 8px;
          }
        }
      }
    }

    .right-panel {
      flex: 0 0 35%;
      display: flex;
      flex-direction: column;
      background: #fff;

      .preview-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 20px;
        border-bottom: 1px solid #e4e7ed;
        flex-shrink: 0;

        .preview-title {
          margin: 0;
          font-size: 16px;
          color: #303133;
          font-weight: 600;

          i {
            margin-right: 8px;
            color: #409eff;
          }
        }

        .preview-nav {
          display: flex;
          align-items: center;
          gap: 12px;

          .nav-info {
            color: #606266;
            font-size: 14px;
            min-width: 60px;
            text-align: center;
          }
        }
      }

      .preview-container {
        flex: 1;
        padding: 20px;
        display: flex;
        flex-direction: column;
        min-height: 0;

        .empty-preview {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #fafafa;
          border-radius: 4px;
        }

        .image-preview {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 20px;

          .image-wrapper {
            flex: 1;
            position: relative;
            background: #f5f7fa;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;

            .preview-img {
              max-width: 100%;
              max-height: 100%;
              object-fit: contain;

              &.loading {
                opacity: 0;
              }
            }

            .image-loading {
              position: absolute;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
              text-align: center;
              color: #909399;

              i {
                font-size: 24px;
                display: block;
                margin-bottom: 8px;
              }
            }
          }

          .image-info {
            background: #f8f9fa;
            border-radius: 4px;
            padding: 16px;
            border: 1px solid #e4e7ed;

            .info-row {
              display: flex;
              align-items: center;
              margin-bottom: 8px;

              &:last-child {
                margin-bottom: 0;
              }

              .info-label {
                width: 80px;
                color: #606266;
                font-size: 13px;
                flex-shrink: 0;
              }

              .info-value {
                color: #303133;
                font-size: 13px;
                word-break: break-all;
              }
            }
          }
        }
      }

      .action-panel {
        padding: 20px;
        border-top: 1px solid #e4e7ed;
        flex-shrink: 0;

        .action-section {
          margin-bottom: 20px;

          &:last-child {
            margin-bottom: 0;
          }

          .action-title {
            font-size: 14px;
            color: #303133;
            margin: 0 0 12px 0;
            font-weight: 600;

            i {
              margin-right: 8px;
              color: #409eff;
            }
          }

          .move-actions {
            display: flex;
            flex-direction: column;
            gap: 8px;

            .el-button {
              justify-content: flex-start;
              text-align: left;

              i {
                margin-right: 8px;
              }
            }
          }

          .other-actions {
            display: flex;
            gap: 8px;
          }

          .no-selection {
            text-align: center;
            color: #909399;
            padding: 20px;

            .hint-text {
              margin: 0;
              font-size: 14px;
            }
          }
        }
      }
    }
  }

  .move-dialog-content {
    p {
      margin: 0 0 16px 0;
      color: #606266;
    }

    .move-options {
      .el-radio-group {
        display: flex;
        flex-direction: column;
        gap: 12px;

        .el-radio {
          margin: 0;
          padding: 8px 12px;
          border: 1px solid #e4e7ed;
          border-radius: 4px;
          transition: all 0.2s;

          &:hover {
            border-color: #409eff;
            background: #ecf5ff;
          }

          :deep(.el-radio__label) {
            i {
              margin-right: 8px;
            }
          }
        }
      }
    }
  }
}

// 响应式调整
@media (max-width: 1200px) {
  .split-layout {
    flex-direction: column;

    .left-panel,
    .right-panel {
      flex: none;
      height: 50%;
    }

    .left-panel {
      border-right: none;
      border-bottom: 1px solid #e4e7ed;
    }
  }
}



/* === 第四步：添加多选选中状态的样式 === */
.thumbnail-item.multi-selected {
  border: 2px solid #409eff !important;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
  background: #f0f9ff;
  transform: translateY(-2px);
}

.thumbnail-item.multi-selected .thumbnail-wrapper::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(64, 158, 255, 0.1);
  z-index: 1;
}
/* === 第四步结束 === */


/* === 第五步：添加工具栏布局样式 === */
.selection-info {
  margin-right: 12px;
}

.batch-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-right: 12px;
}
/* === 第五步结束 === */


/* 多选模式面板样式 */
.multi-select-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
  border-left: 1px solid #e4e7ed;
}

.multi-select-content {
  text-align: center;
  padding: 40px;
  max-width: 300px;
}

.multi-select-icon {
  font-size: 64px;
  color: #409eff;
  margin-bottom: 16px;
}

.multi-select-title {
  font-size: 20px;
  color: #303133;
  margin: 0 0 12px 0;
}

.multi-select-desc {
  color: #606266;
  font-size: 14px;
  margin-bottom: 20px;
}

.multi-select-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.multi-select-tips {
  text-align: left;
  background: #f0f9ff;
  border: 1px solid #d1e9ff;
  border-radius: 4px;
  padding: 12px;

  p {
    margin: 0 0 8px 0;
    font-weight: 600;
    color: #409eff;
  }

  ul {
    margin: 0;
    padding-left: 16px;

    li {
      color: #606266;
      font-size: 12px;
      line-height: 1.5;
      margin-bottom: 4px;
    }
  }
}

/* 多选模式下左侧面板占据更多空间 */
.split-layout .left-panel {
  transition: flex 0.3s ease;
}

.split-layout:has(.multi-select-panel) .left-panel {
  flex: 1;
}


/* 多选模式下左侧面板占据全宽 */
.left-panel.full-width {
  flex: 1 !important;
  width: 100%;
}

.split-layout.multi-select-mode .left-panel {
  border-right: none;
}

/* 多选模式下的选中标记 */
.multi-select-checkmark {
  position: absolute;
  top: 4px;
  left: 4px;
  background: #409eff;
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  z-index: 2;
}

/* 已选择数量显示 */
.selected-count {
  color: #409eff;
  font-weight: 600;
  margin-left: 8px;
}

/* 悬停预览浮层样式 */
.preview-image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  max-height: 70vh;
  overflow: auto;
}

.preview-full-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

/* 调整 popover 样式 */
:deep(.image-preview-popover) {
  padding: 8px;
}

</style>