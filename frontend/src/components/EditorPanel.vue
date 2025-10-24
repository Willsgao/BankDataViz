<template>
  <div class="editor-panel">
    <div class="editor-container">
      <!-- 用 modelValue + emit 代替 v-model:content 避免突变 prop -->
      <quill-editor
        :modelValue="modelValue"
        @update:modelValue="emit('update:modelValue', $event)"
        :options="editorOptions"
        contentType="html"
      />
    </div>
    <el-button type="primary" @click="emit('save')" class="save-btn">保存</el-button>
  </div>
</template>

<script setup>
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css'

defineProps({ modelValue: String })
defineEmits(['update:modelValue', 'save'])

const editorOptions = {
  modules: {
    toolbar: [
      ['bold', 'italic', 'underline', 'strike'],
      ['blockquote', 'code-block'],
      [{ header: 1 }, { header: 2 }],
      [{ list: 'ordered' }, { list: 'bullet' }],
      [{ color: [] }, { background: [] }],
      ['link', 'image']
    ]
  },
  placeholder: '请输入内容...',
  theme: 'snow'
}
</script>

<style scoped>
.editor-panel {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
}
.editor-container {
  flex: 1;
  margin-bottom: 20px;
  height: calc(100% - 60px);
}
.save-btn {
  align-self: flex-end;
  margin-top: 20px;
}
</style>