<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    title="PDF 分页预览"
    width="85vw"
    top="5vh"
    :close-on-click-modal="false"
  >
    <!-- 分页控制器 -->
    <div style="display:flex;align-items:center;justify-content:center;margin-bottom:10px;gap:12px;">
      <el-button :disabled="page === 1" size="small" @click="page--">上一页</el-button>
      <span>第 {{ page }} / {{ pngs.length }} 页</span>
      <el-button :disabled="page === pngs.length" size="small" @click="page++">下一页</el-button>
    </div>

    <!-- 仅当前页大图 -->
    <div style="height:70vh;overflow-y:auto;text-align:center">
      <img
        :src="`http://127.0.0.1:5000/api/png/${folder}/${pngs[page-1]}`"
        style="max-width:100%;max-height:80vh;box-shadow:0 0 8px rgba(0,0,0,.2)"
      />
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, watch, toRef } from 'vue'

const props = defineProps({
  visible: Boolean,
  folder: String,
  pngs: Array
})
const emit = defineEmits(['update:visible'])

const page = ref(1)
const pngsRef = toRef(props, 'pngs')

watch(pngsRef, () => { page.value = 1 })
</script>