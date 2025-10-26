<template>
  <el-dialog
    :model-value="visible"
    :title="`表格预览 (${index + 1}/${total})`"
    width="80%"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="preview-content">
      <img :src="image" class="preview-image" />
      <div class="preview-nav">
        <el-button @click="$emit('prev')" :disabled="index === 0">上一张</el-button>
        <span class="preview-position">{{ index + 1 }} / {{ total }}</span>
        <el-button @click="$emit('next')" :disabled="index === total - 1">下一张</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  image: {
    type: String,
    default: ''
  },
  index: {
    type: Number,
    default: 0
  },
  total: {
    type: Number,
    default: 0
  }
})

defineEmits(['update:visible', 'prev', 'next'])
</script>

<style scoped>
.preview-content {
  text-align: center;
}

.preview-image {
  max-width: 100%;
  max-height: 60vh;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
}

.preview-nav {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

.preview-position {
  color: #666;
  font-size: 14px;
}
</style>