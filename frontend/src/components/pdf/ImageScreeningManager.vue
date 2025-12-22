<template>
  <div class="image-screening-manager">
    <!-- 顶部工具栏 -->
    <div class="manager-toolbar">
      <div class="toolbar-left">
        <h2 class="manager-title">
          <i class="el-icon-folder-checked"></i>
          图片分类管理 - {{ pdfNameDisplay }}
        </h2>
        <div class="toolbar-info">
          <el-tag size="small" type="success">
            <i class="el-icon-picture"></i>
            有表格: {{ stats.tables_count || 0 }}张
          </el-tag>
          <el-tag size="small" type="info">
            <i class="el-icon-picture-outline"></i>
            无表格: {{ stats.no_tables_count || 0 }}张
          </el-tag>
          <el-tag size="small" type="warning" v-if="stats.uncertain_count">
            <i class="el-icon-question"></i>
            不确定: {{ stats.uncertain_count }}张
          </el-tag>
        </div>
      </div>

      <div class="toolbar-right">
        <el-button
          type="primary"
          size="small"
          icon="el-icon-refresh"
          @click="refreshData"
          :loading="refreshing"
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
    <div class="split-layout">
      <!-- 左侧：分类缩略图面板 -->
      <div class="left-panel">
        <div class="category-tabs">
          <el-tabs v-model="activeCategory" type="card" @tab-click="handleTabChange">
            <el-tab-pane label="有表格" name="tables">
              <span slot="label">
                <i class="el-icon-check"></i>
                有表格
                <el-badge :value="stats.tables_count" :max="99" class="tab-badge" />
              </span>
            </el-tab-pane>

            <el-tab-pane label="无表格" name="no_tables">
              <span slot="label">
                <i class="el-icon-close"></i>
                无表格
                <el-badge :value="stats.no_tables_count" :max="99" class="tab-badge" />
              </span>
            </el-tab-pane>

            <el-tab-pane
              v-if="stats.uncertain_count"
              label="不确定"
              name="uncertain"
            >
              <span slot="label">
                <i class="el-icon-question"></i>
                不确定
                <el-badge :value="stats.uncertain_count" :max="99" class="tab-badge" />
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
          <div v-if="viewMode === 'grid'" class="thumbnail-grid">
            <div
              v-for="(image, index) in currentImages"
              :key="image.name"
              class="thumbnail-item"
              :class="{ selected: selectedImage?.name === image.name }"
              @click="selectImage(image)"
            >
              <div class="thumbnail-wrapper">
                <img
                  :src="getImageUrl(image)"
                  :alt="image.name"
                  class="thumbnail-img"
                  loading="lazy"
                  @error="handleImageError(image)"
                />
                <div class="thumbnail-overlay">
                  <el-tag
                    size="mini"
                    :type="getCategoryType(image.type)"
                    class="category-tag"
                  >
                    {{ getCategoryLabel(image.type) }}
                  </el-tag>
                </div>
              </div>
              <div class="thumbnail-info">
                <span class="image-name" :title="image.name">
                  {{ image.name }}
                </span>
                <div class="thumbnail-actions">
                  <el-button
                    type="text"
                    size="mini"
                    icon="el-icon-view"
                    @click.stop="selectImage(image)"
                    title="预览"
                  />
                  <el-button
                    type="text"
                    size="mini"
                    icon="el-icon-right"
                    @click.stop="showMoveOptions(image)"
                    title="移动到..."
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 列表视图 -->
          <div v-else class="thumbnail-list">
            <el-table
              :data="currentImages"
              size="small"
              highlight-current-row
              @row-click="selectImage"
              style="width: 100%"
            >
              <el-table-column width="50">
                <template #default="scope">
                  <img
                    :src="getImageUrl(scope.row)"
                    class="list-thumbnail"
                    loading="lazy"
                  />
                </template>
              </el-table-column>

              <el-table-column prop="name" label="图片名称" min-width="150">
                <template #default="scope">
                  <span class="list-image-name">{{ scope.row.name }}</span>
                </template>
              </el-table-column>

              <el-table-column prop="type" label="分类" width="100">
                <template #default="scope">
                  <el-tag
                    size="small"
                    :type="getCategoryType(scope.row.type)"
                  >
                    {{ getCategoryLabel(scope.row.type) }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column label="操作" width="120">
                <template #default="scope">
                  <el-button
                    type="text"
                    size="small"
                    icon="el-icon-view"
                    @click.stop="selectImage(scope.row)"
                    title="预览"
                  />
                  <el-button
                    type="text"
                    size="small"
                    icon="el-icon-right"
                    @click.stop="showMoveOptions(scope.row)"
                    title="移动到..."
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 空状态 -->
          <div v-if="currentImages.length === 0 && !props.classifiedImages[activeCategory]?.length" class="empty-thumbnails">
            <el-empty description="暂无图片">
              <p class="empty-tips">当前分类没有图片</p>
            </el-empty>
          </div>
        </div>
      </div>

      <!-- 右侧：大图预览和操作面板 -->
      <div class="right-panel">
        <div class="preview-header">
          <h3 v-if="selectedImage" class="preview-title">
            <i class="el-icon-picture-outline-round"></i>
            {{ selectedImage.name }}
          </h3>
          <h3 v-else class="preview-title">
            <i class="el-icon-picture-outline"></i>
            图片预览
          </h3>

          <div class="preview-nav" v-if="selectedImage">
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
          <div v-if="!selectedImage" class="empty-preview">
            <el-empty description="请选择一张图片进行预览">
              <i class="el-icon-picture-outline" style="font-size: 80px; color: #dcdfe6;"></i>
            </el-empty>
          </div>

          <div v-else class="image-preview">
            <div class="image-wrapper">
              <img
                :src="getImageUrl(selectedImage, 'large')"
                :alt="selectedImage.name"
                class="preview-img"
                :class="{ loading: previewLoading }"
                @load="previewLoading = false"
                @error="handlePreviewError"
              />
              <div v-if="previewLoading" class="image-loading">
                <el-icon class="is-loading">
                  <Loading />
                </el-icon>
                <span>加载中...</span>
              </div>
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
              <div class="info-row" v-if="selectedImage.confidence">
                <span class="info-label">置信度：</span>
                <span class="info-value">
                  {{ (selectedImage.confidence * 100).toFixed(1) }}%
                </span>
              </div>
              <div class="info-row" v-if="selectedImage.moved_at">
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
              <i class="el-icon-s-operation"></i>
              分类操作
            </h4>

            <div class="move-actions" v-if="selectedImage">
              <el-button
                type="success"
                :disabled="selectedImage.type === 'tables'"
                @click="moveImage(selectedImage, 'tables')"
              >
                <i class="el-icon-check"></i>
                移动到有表格
              </el-button>

              <el-button
                type="info"
                :disabled="selectedImage.type === 'no_tables'"
                @click="moveImage(selectedImage, 'no_tables')"
              >
                <i class="el-icon-close"></i>
                移动到无表格
              </el-button>

              <el-button
                v-if="stats.uncertain_count"
                type="warning"
                :disabled="selectedImage.type === 'uncertain'"
                @click="moveImage(selectedImage, 'uncertain')"
              >
                <i class="el-icon-question"></i>
                移动到不确定
              </el-button>
            </div>

            <div v-else class="no-selection">
              <p class="hint-text">请先选择一张图片</p>
            </div>
          </div>

          <div class="action-section">
            <h4 class="action-title">
              <i class="el-icon-magic-stick"></i>
              其他操作
            </h4>

            <div class="other-actions">
              <el-button
                type="primary"
                :disabled="!selectedImage"
                @click="redetectImage(selectedImage)"
              >
                <i class="el-icon-refresh"></i>
                重新检测
              </el-button>

              <el-button
                type="text"
                :disabled="!selectedImage"
                @click="downloadImage(selectedImage)"
              >
                <i class="el-icon-download"></i>
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
      <div class="move-dialog-content" v-if="imageToMove">
        <p>将图片 <strong>{{ imageToMove.name }}</strong> 移动到：</p>

        <div class="move-options">
          <el-radio-group v-model="moveTargetType">
            <el-radio label="tables">
              <i class="el-icon-check"></i>
              有表格
            </el-radio>
            <el-radio label="no_tables">
              <i class="el-icon-close"></i>
              无表格
            </el-radio>
            <el-radio label="uncertain" v-if="stats.uncertain_count">
              <i class="el-icon-question"></i>
              不确定
            </el-radio>
          </el-radio-group>
        </div>
      </div>

      <template #footer>
        <el-button @click="showMoveDialog = false">取消</el-button>
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
  }
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
    const baseUrl = window.location.origin
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
  const baseUrl = window.location.origin
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



const selectImage = (image) => {
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

  const baseUrl = window.location.origin
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
  // 切换标签页时清除选中
  selectedImage.value = null
  currentImageIndex.value = -1
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
                transition: transform 0.3s;
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
</style>