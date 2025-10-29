<!-- EditableCell.vue -->
<template>
  <div class="editable-cell">
    <div v-if="!editing" class="cell-content" @dblclick="startEditing">
      {{ value || ' ' }}
    </div>
    <el-input
      v-else
      ref="inputRef"
      v-model="editValue"
      size="small"
      @blur="finishEditing"
      @keyup.enter="finishEditing"
      @keyup.esc="cancelEditing"
    />
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  value: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:value'])

const editing = ref(false)
const editValue = ref('')
const inputRef = ref()

const startEditing = () => {
  editing.value = true
  editValue.value = props.value
  nextTick(() => {
    inputRef.value?.focus()
  })
}

const finishEditing = () => {
  editing.value = false
  emit('update:value', editValue.value)
}

const cancelEditing = () => {
  editing.value = false
  editValue.value = props.value
}
</script>

<style scoped>
.editable-cell {
  min-height: 32px;
  display: flex;
  align-items: center;
}

.cell-content {
  width: 100%;
  padding: 4px 8px;
  cursor: text;
  min-height: 24px;
  display: flex;
  align-items: center;
}

.cell-content:hover {
  background: #f5f7fa;
}
</style>