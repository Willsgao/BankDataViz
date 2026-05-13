<template>
  <div
    ref="containerRef"
    class="area-selector"
  >
    <!-- 工具栏 -->
    <div
      v-if="enabled && imageLoaded"
      class="toolbar"
    >
      <el-button
        size="small"
        type="primary"
        plain
        @click="addManualBox"
      >
        <el-icon><Plus /></el-icon> 添加选区
      </el-button>
      <el-button
        size="small"
        :type="editMode ? 'warning' : 'default'"
        @click="editMode = !editMode"
      >
        <el-icon><Edit /></el-icon> {{ editMode ? '编辑中' : '已锁定' }}
      </el-button>
      <span class="box-count">
        共 {{ boxes.length }} 个选区
        <span
          v-if="confirmedIds.size < boxes.length"
          class="unconfirmed-tip"
        >
          （{{ boxes.length - confirmedIds.size }} 个待确认）
        </span>
      </span>
      <el-button
        size="small"
        type="success"
        :disabled="boxes.length === 0"
        @click="confirmAll"
      >
        <el-icon><Check /></el-icon> 确认本页
      </el-button>
      <el-button
        size="small"
        @click="clearAll"
      >
        清空全部
      </el-button>
    </div>

    <!-- 图片预览区域 -->
    <div
      ref="previewWrapperRef"
      class="preview-wrapper"
      @scroll="onPreviewScroll"
    >
      <img
        v-if="imageSrc"
        ref="imageRef"
        :src="imageSrc"
        class="preview-image"
        draggable="false"
        @load="onImageLoad"
      >

      <!-- 框选遮罩层 -->
      <div
        v-if="enabled && imageLoaded"
        ref="overlayRef"
        class="selector-overlay"
        @mousedown.prevent="onOverlayClick"
      >
        <!-- 已有框 -->
        <div
          v-for="(box, idx) in boxes"
          :key="box.id"
          class="box-rect"
          :class="{
            'box-selected': selectedBoxId === box.id,
            'box-confirmed': confirmedIds.has(box.id),
          }"
          :style="{
            left: box.x + 'px',
            top: box.y + 'px',
            width: box.w + 'px',
            height: box.h + 'px',
          }"
          @mousedown.prevent.stop="!confirmedIds.has(box.id) && editMode && onBoxMouseDown($event, idx)"
          @click.stop="selectBox(box.id)"
        >
          <!-- 框标签（未确认） -->
          <div
            v-if="!confirmedIds.has(box.id)"
            class="box-label label-editing"
            @mousedown.prevent.stop="editMode && onBoxLabelDown($event, idx)"
          >
            {{ box.label }}
            <el-icon
              class="action-icon confirm-icon"
              title="确认选区"
              @click.stop="confirmBox(idx)"
            >
              <Check />
            </el-icon>
            <el-icon
              class="action-icon delete-icon"
              title="删除"
              @click.stop="deleteBox(idx)"
            >
              <Close />
            </el-icon>
          </div>

          <!-- 框标签（已确认） -->
          <div
            v-else
            class="box-label label-confirmed"
            @mousedown.prevent.stop
            @click.stop="selectBox(box.id)"
          >
            <el-icon><Lock /></el-icon>
            {{ box.label }}
            <el-icon
              class="action-icon edit-icon"
              title="解锁编辑"
              @click.stop="editBox(idx)"
            >
              <Edit />
            </el-icon>
          </div>

          <!-- 八个缩放柄（仅编辑模式 + 未确认时显示） -->
          <template v-if="editMode && !confirmedIds.has(box.id)">
            <div
              v-for="handle in ['nw','ne','sw','se']"
              :key="'c-' + handle"
              class="resize-handle corner"
              :class="handle"
              @mousedown.prevent.stop="onResizeStart($event, idx, handle)"
            />
            <div
              v-for="handle in ['n','s','e','w']"
              :key="'e-' + handle"
              class="resize-handle edge"
              :class="handle"
              @mousedown.prevent.stop="onResizeStart($event, idx, handle)"
            />
          </template>
        </div>

        <!-- 正在绘制的框 -->
        <div
          v-if="drawing"
          class="box-rect drawing"
          :style="{
            left: drawRect.x + 'px',
            top: drawRect.y + 'px',
            width: drawRect.w + 'px',
            height: drawRect.h + 'px',
          }"
        />

        <!-- 提示 -->
        <div
          v-if="boxes.length === 0 && !drawing"
          class="hint-text"
        >
          点击「添加选区」手动框选，上传文件后系统会自动检测表格区域
        </div>
        <div
          v-if="showScrollTip"
          class="scroll-tip"
        >
          ⚠️ 表格较长，请滚动预览区域，确保选区包含完整表格
        </div>
      </div>

      <!-- 加载中遮罩 -->
      <div
        v-if="loading"
        class="loading-mask"
      >
        <el-icon
          class="is-loading"
          :size="32"
        >
          <Loading />
        </el-icon>
        <span>{{ loadingText }}</span>
      </div>
    </div>

    <!-- 已确认区域缩略图列表 -->
    <div
      v-if="confirmedItems.length > 0"
      class="confirmed-list"
    >
      <div class="confirmed-header">
        已确认的选区（共 {{ confirmedItems.length }} 个）
      </div>
      <div class="confirmed-items">
        <div
          v-for="item in confirmedItems"
          :key="item.id"
          class="confirmed-item"
        >
          <img
            :src="item.thumbnail"
            class="confirmed-thumb"
          >
          <span class="confirmed-label">{{ item.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Check, Close, Loading, Edit, Lock } from '@element-plus/icons-vue'

const props = defineProps({
  enabled: { type: Boolean, default: true },
  imageSrc: { type: String, default: '' },
  initialBoxes: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  loadingText: { type: String, default: '加载中...' },
})

const showScrollTip = ref(false)

const emit = defineEmits(['update:initialBoxes', 'boxes-change', 'confirm', 'box-add'])

// Refs
const containerRef = ref(null)
const previewWrapperRef = ref(null)
const imageRef = ref(null)
const overlayRef = ref(null)

// 状态
const boxes = ref([])
const selectedBoxId = ref(null)
const imageLoaded = ref(false)
const confirmedItems = ref([])

// ---- 监听 initialBoxes 变化（翻页时自动加载对应页的框） ----
watch(() => props.initialBoxes, (newBoxes) => {
  if (newBoxes && newBoxes.length > 0) {
    // 有检测框时初始化（翻页后 imageSrc 变化触发，替换为新页的检测框）
    initBoxesFromDetected(newBoxes)
  }
}, { immediate: true })
const editMode = ref(true)           // 编辑模式开关
const confirmedIds = ref(new Set()) // 已确认的框 ID 集合

// 绘制新框
const drawing = ref(false)
const drawRect = ref({ x: 0, y: 0, w: 0, h: 0 })
const drawStart = ref(null)

// 拖拽框
const dragBoxIdx = ref(null)
const dragOffset = ref({ x: 0, y: 0 })

// 缩放框
const resizeBoxIdx = ref(null)
const resizeHandle = ref('')
const resizeStartBox = ref(null)
const resizeStartMouse = ref(null)

let boxIdCounter = 1

// ---- 坐标转换 ----
function clientToOverlay(e) {
  const rect = overlayRef.value?.getBoundingClientRect()
  return {
    x: (e.clientX - (rect?.left || 0)),
    y: (e.clientY - (rect?.top || 0)),
  }
}

// ---- 图像加载 ----
function onImageLoad() {
  imageLoaded.value = true
  // 检查是否需要显示滚动提示
  nextTick(() => {
    const wrapper = previewWrapperRef.value
    const img = imageRef.value
    if (wrapper && img) {
      showScrollTip.value = img.naturalHeight > wrapper.clientHeight
    }
  })
}

// ---- 预览区域滚动 ----
function onPreviewScroll() {
  // 用户滚动后，隐藏滚动提示
  if (showScrollTip.value) {
    showScrollTip.value = false
  }
}

// ---- 初始化已有框（外部调用） ----
function initBoxesFromDetected(detectedBoxes) {
  confirmedIds.value = new Set()
  confirmedItems.value = []
  boxes.value = detectedBoxes.map((b, i) => ({
    id: `box-${boxIdCounter++}`,
    label: b.label || `选区 ${i + 1}`,
    x: b.x || 0,
    y: b.y || 0,
    w: b.w || 100,
    h: b.h || 60,
    bbox_pdf: b.bbox_pdf || null,
    bbox_pixel: b.bbox_pixel || null,
  }))
  emit('boxes-change', boxes.value)
}

// ---- 重排框序号 ----
function renumberBoxes() {
  boxes.value.forEach((box, i) => {
    box.label = `选区 ${i + 1}`
  })
}

// ---- 添加手动选区 ----
function addManualBox() {
  const wrapper = previewWrapperRef.value
  if (!wrapper) return
  const w = Math.round(wrapper.clientWidth * 0.4)
  const h = Math.round(wrapper.clientHeight * 0.25)
  const x = Math.round((wrapper.clientWidth - w) / 2)
  const y = Math.round((wrapper.clientHeight - h) / 2)

  const newBox = {
    id: `box-${boxIdCounter++}`,
    label: `选区 ${boxes.value.length + 1}`,
    x, y, w, h,
  }
  boxes.value.push(newBox)
  selectedBoxId.value = newBox.id
  emit('boxes-change', boxes.value)
  emit('box-add', newBox)
}

// ---- 点击 overlay 新建框 ----
function onOverlayClick(e) {
  if (e.target !== overlayRef.value) return
  if (dragBoxIdx.value !== null || resizeBoxIdx.value !== null) return

  const pos = clientToOverlay(e)
  drawStart.value = pos
  drawing.value = true
  drawRect.value = { x: pos.x, y: pos.y, w: 0, h: 0 }
}

// ---- 鼠标移动（全局） ----
function handleMouseMove(e) {
  if (drawing.value && drawStart.value) {
    const pos = clientToOverlay(e)
    drawRect.value = {
      x: Math.min(drawStart.value.x, pos.x),
      y: Math.min(drawStart.value.y, pos.y),
      w: Math.abs(pos.x - drawStart.value.x),
      h: Math.abs(pos.y - drawStart.value.y),
    }
    return
  }

  if (dragBoxIdx.value !== null) {
    const box = boxes.value[dragBoxIdx.value]
    if (confirmedIds.value.has(box.id)) return
    const pos = clientToOverlay(e)
    const overlayEl = overlayRef.value
    if (!overlayEl || !box) return
    box.x = Math.max(0, Math.min(pos.x - dragOffset.value.x, overlayEl.clientWidth - box.w))
    box.y = Math.max(0, Math.min(pos.y - dragOffset.value.y, overlayEl.clientHeight - box.h))
    return
  }

  if (resizeBoxIdx.value !== null) {
    const box = boxes.value[resizeBoxIdx.value]
    if (confirmedIds.value.has(box.id)) return
    const pos = clientToOverlay(e)
    const orig = resizeStartBox.value
    if (!box || !orig) return
    const dx = pos.x - resizeStartMouse.value.x
    const dy = pos.y - resizeStartMouse.value.y

    switch (resizeHandle.value) {
      case 'se':
        box.w = Math.max(20, orig.w + dx)
        box.h = Math.max(20, orig.h + dy)
        break
      case 'sw':
        box.x = Math.max(0, orig.x + dx)
        box.w = Math.max(20, orig.w - dx)
        box.h = Math.max(20, orig.h + dy)
        break
      case 'ne':
        box.y = Math.max(0, orig.y + dy)
        box.h = Math.max(20, orig.h - dy)
        box.w = Math.max(20, orig.w + dx)
        break
      case 'nw':
        box.x = Math.max(0, orig.x + dx)
        box.y = Math.max(0, orig.y + dy)
        box.w = Math.max(20, orig.w - dx)
        box.h = Math.max(20, orig.h - dy)
        break
      case 'e': box.w = Math.max(20, orig.w + dx); break
      case 'w':
        box.x = Math.max(0, orig.x + dx)
        box.w = Math.max(20, orig.w - dx)
        break
      case 's': box.h = Math.max(20, orig.h + dy); break
      case 'n':
        box.y = Math.max(0, orig.y + dy)
        box.h = Math.max(20, orig.h - dy)
        break
    }
  }
}

// ---- 鼠标释放（全局） ----
function handleMouseUp() {
  if (drawing.value) {
    drawing.value = false
    if (drawRect.value.w > 10 && drawRect.value.h > 10) {
      const newBox = {
        id: `box-${boxIdCounter++}`,
        label: `选区${boxes.value.length + 1}`,
        x: drawRect.value.x,
        y: drawRect.value.y,
        w: drawRect.value.w,
        h: drawRect.value.h,
      }
      boxes.value.push(newBox)
      selectedBoxId.value = newBox.id
      emit('boxes-change', boxes.value)
    }
    drawRect.value = { x: 0, y: 0, w: 0, h: 0 }
    drawStart.value = null
  }

  dragBoxIdx.value = null
  resizeBoxIdx.value = null
  resizeHandle.value = ''
  resizeStartBox.value = null
}

// 生命周期 - 全局事件
onMounted(() => {
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
})

// ---- 选择框 ----
function selectBox(id) {
  selectedBoxId.value = id
}

// ---- 拖拽框体（鼠标在框体上按下） ----
function onBoxMouseDown(e, idx) {
  const box = boxes.value[idx]
  if (confirmedIds.value.has(box.id)) return
  const pos = clientToOverlay(e)
  dragOffset.value = { x: pos.x - box.x, y: pos.y - box.y }
  dragBoxIdx.value = idx
}

// ---- 删除框 ----
function deleteBox(idx) {
  const box = boxes.value[idx]
  confirmedIds.value.delete(box.id)
  confirmedItems.value = confirmedItems.value.filter(item => item.id !== box.id)
  boxes.value.splice(idx, 1)
  selectedBoxId.value = null
  renumberBoxes()
  emit('boxes-change', boxes.value)
}

// ---- 单框确认截图 ----
async function confirmBox(idx) {
  const box = boxes.value[idx]
  if (!imageRef.value) return
  const img = imageRef.value
  const scale = img.naturalWidth / img.clientWidth

  const canvas = document.createElement('canvas')
  canvas.width = Math.round(box.w * scale)
  canvas.height = Math.round(box.h * scale)
  const ctx = canvas.getContext('2d')
  ctx.drawImage(img, box.x * scale, box.y * scale, box.w * scale, box.h * scale, 0, 0, canvas.width, canvas.height)

  confirmedIds.value.add(box.id)
  const item = {
    id: box.id,
    label: box.label,
    x: Math.round(box.x * scale),
    y: Math.round(box.y * scale),
    w: Math.round(box.w * scale),
    h: Math.round(box.h * scale),
    image_base64: canvas.toDataURL('image/png'),
    thumbnail: canvas.toDataURL('image/png'),
  }
  confirmedItems.value.push(item)
  emit('confirm', confirmedItems.value)
}

// ---- 解锁已确认的框，重新编辑 ----
function editBox(idx) {
  const box = boxes.value[idx]
  confirmedIds.value.delete(box.id)
  confirmedItems.value = confirmedItems.value.filter(item => item.id !== box.id)
  editMode.value = true
  emit('confirm', confirmedItems.value)
}

// ---- 拖拽框（标签栏） ----
function onBoxLabelDown(e, idx) {
  if (e.target.classList.contains('delete-icon')) return
  const box = boxes.value[idx]
  const pos = clientToOverlay(e)
  dragOffset.value = { x: pos.x - box.x, y: pos.y - box.y }
  dragBoxIdx.value = idx
}

// ---- 缩放框 ----
function onResizeStart(e, idx, handle) {
  resizeBoxIdx.value = idx
  resizeHandle.value = handle
  const box = boxes.value[idx]
  resizeStartBox.value = { x: box.x, y: box.y, w: box.w, h: box.h }
  resizeStartMouse.value = clientToOverlay(e)
}

// ---- 确认所有选区：截图 ----
async function confirmAll() {
  if (boxes.value.length === 0 || !imageRef.value) {
    ElMessage.warning('没有选区')
    return
  }

  const unconfirmed = boxes.value.filter(box => !confirmedIds.value.has(box.id))
  if (unconfirmed.length === 0) {
    ElMessage.info('所有选区已确认')
    return
  }

  const img = imageRef.value

  for (const box of unconfirmed) {
    try {
      const scale = img.naturalWidth / img.clientWidth
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(box.w * scale)
      canvas.height = Math.round(box.h * scale)
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, box.x * scale, box.y * scale, box.w * scale, box.h * scale, 0, 0, canvas.width, canvas.height)

      confirmedIds.value.add(box.id)
      confirmedItems.value.push({
        id: box.id,
        label: box.label,
        x: Math.round(box.x * scale),
        y: Math.round(box.y * scale),
        w: Math.round(box.w * scale),
        h: Math.round(box.h * scale),
        image_base64: canvas.toDataURL('image/png'),
        thumbnail: canvas.toDataURL('image/png'),
      })
    } catch (err) {
      console.error(`截图失败 [${box.label}]:`, err)
    }
  }

  emit('confirm', confirmedItems.value)
}

// ---- 清空 ----
function clearAll() {
  boxes.value = []
  confirmedItems.value = []
  confirmedIds.value = new Set()
  selectedBoxId.value = null
  emit('boxes-change', [])
}

// ---- 获取当前框（供 FilePreview 保存） ----
function getCurrentBoxes() {
  return boxes.value.map(b => ({
    ...b,
    confirmed: confirmedIds.value.has(b.id),
  }))
}

// ---- 加载指定页的框（供 FilePreview 恢复） ----
function loadPageBoxes(savedBoxes) {
  confirmedIds.value = new Set(savedBoxes.filter(b => b.confirmed).map(b => b.id))
  boxes.value = savedBoxes.map(b => {
    const { confirmed, ...rest } = b
    return rest
  })
  emit('boxes-change', boxes.value)
}

// ---- 暴露：获取已确认截图 ----
function getConfirmedItems() {
  return confirmedItems.value
}

// ---- 自动滚动预览（供父组件调用）----
async function autoScrollPreview() {
  const wrapper = previewWrapperRef.value
  if (!wrapper) return
  const scrollHeight = wrapper.scrollHeight
  const clientHeight = wrapper.clientHeight
  if (scrollHeight <= clientHeight) return
  // 先滚回顶部
  wrapper.scrollTo({ top: 0, behavior: 'smooth' })
  await new Promise(r => setTimeout(r, 400))
  // 滚到底部
  wrapper.scrollTo({ top: scrollHeight, behavior: 'smooth' })
  await new Promise(r => setTimeout(r, 1500))
  // 滚回顶部
  wrapper.scrollTo({ top: 0, behavior: 'smooth' })
}

// ---- 暴露 ----
defineExpose({
  initBoxesFromDetected,
  getCurrentBoxes,
  loadPageBoxes,
  getConfirmedBoxes: () => confirmedItems.value,
  clearAll,
  confirmAll,
  autoScrollPreview,
})
</script>

<style scoped>
.area-selector {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 8px;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: #f0f2f5;
  border-radius: 6px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.box-count {
  font-size: 12px;
  color: #606266;
  flex: 1;
}

/* 预览区域 */
.preview-wrapper {
  flex: 1;
  position: relative;
  overflow: auto;
  background: #f5f5f5;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  min-height: 0;
}

.preview-image {
  display: block;
  max-width: 100%;
  user-select: none;
}

/* 遮罩层 */
.selector-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
}

/* 框 */
.box-rect {
  position: absolute;
  border: 2px solid #1890ff;
  background: rgba(24, 144, 255, 0.08);
  cursor: move;
  user-select: none;
}

.box-rect:hover,
.box-rect.box-selected {
  border-color: #0050b3;
  background: rgba(24, 144, 255, 0.15);
}

.box-rect.box-confirmed {
  border-color: #67c23a;
  background: rgba(103, 194, 58, 0.08);
  cursor: default;
}

.box-rect.box-confirmed:hover,
.box-rect.box-confirmed.box-selected {
  border-color: #5a8f2f;
  background: rgba(103, 194, 58, 0.15);
}

.box-rect.drawing {
  border-style: dashed;
  cursor: crosshair;
}

/* 框标签 */
.box-label {
  position: absolute;
  top: -24px;
  left: -2px;
  background: #1890ff;
  color: white;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px 3px 0 0;
  white-space: nowrap;
  cursor: move;
  display: flex;
  align-items: center;
  gap: 3px;
  z-index: 2;
}

.box-rect:hover .box-label,
.box-rect.box-selected .box-label {
  background: #0050b3;
}

/* 已确认标签 */
.box-label.label-confirmed {
  background: #67c23a;
  cursor: default;
  gap: 3px;
}

.box-rect:hover .box-label.label-confirmed,
.box-rect.box-selected .box-label.label-confirmed {
  background: #5a8f2f;
}

/* 标签内图标 */
.action-icon {
  cursor: pointer;
  font-size: 11px;
  opacity: 0.85;
  line-height: 1;
}

.action-icon:hover {
  opacity: 1;
}

.confirm-icon { color: #fff; }
.confirm-icon:hover { color: #b9f5b0; }

.delete-icon { color: #fff; }
.delete-icon:hover { color: #ff7875; }

.edit-icon { color: #fff; }
.edit-icon:hover { color: #ffd591; }

.unconfirmed-tip {
  color: #e6a23c;
}

/* 缩放柄 */
.resize-handle {
  position: absolute;
  background: white;
  border: 1.5px solid #1890ff;
  border-radius: 2px;
  z-index: 1;
}

.resize-handle.corner {
  width: 10px;
  height: 10px;
}

.resize-handle.edge {
  background: #1890ff;
  border: none;
  border-radius: 0;
  opacity: 0.6;
}

.resize-handle.nw { top: -5px; left: -5px; cursor: nw-resize; }
.resize-handle.ne { top: -5px; right: -5px; cursor: ne-resize; }
.resize-handle.sw { bottom: -5px; left: -5px; cursor: sw-resize; }
.resize-handle.se { bottom: -5px; right: -5px; cursor: se-resize; }
.resize-handle.n  { top: -4px; left: 10px; right: 10px; height: 6px; cursor: n-resize; }
.resize-handle.s  { bottom: -4px; left: 10px; right: 10px; height: 6px; cursor: s-resize; }
.resize-handle.e  { right: -4px; top: 10px; bottom: 10px; width: 6px; cursor: e-resize; }
.resize-handle.w  { left: -4px; top: 10px; bottom: 10px; width: 6px; cursor: w-resize; }

/* 提示 */
.hint-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #909399;
  font-size: 14px;
  pointer-events: none;
  background: rgba(255, 255, 255, 0.85);
  padding: 10px 20px;
  border-radius: 6px;
  text-align: center;
  white-space: nowrap;
}

/* 滚动提示 */
.scroll-tip {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  background: #fdf6ec;
  color: #e6a23c;
  font-size: 13px;
  padding: 6px 16px;
  border-radius: 4px;
  border: 1px solid #e6a23c;
  z-index: 15;
  pointer-events: none;
  white-space: nowrap;
}

/* 加载遮罩 */
.loading-mask {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 14px;
  color: #606266;
  z-index: 20;
}

/* 已确认选区列表 */
.confirmed-list {
  flex-shrink: 0;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 8px;
  background: white;
  max-height: 120px;
  overflow-y: auto;
}

.confirmed-header {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.confirmed-items {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.confirmed-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.confirmed-thumb {
  width: 64px;
  height: 44px;
  object-fit: cover;
  border: 1px solid #e4e7ed;
  border-radius: 3px;
}

.confirmed-label {
  font-size: 11px;
  color: #303133;
  max-width: 64px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}
</style>
