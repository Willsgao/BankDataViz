<template>
  <el-dialog
    :model-value="visible"
    title="转图进度"
    width="400px"
    :close-on-click-modal="false"
    :show-close="false"
    @update:model-value="emit('update:visible', $event)"
  >
    <div style="text-align:center">
      <el-progress
        :percentage="percent"
        :status="status"
        :stroke-width="12"
      />
      <div style="margin-top:10px;color:#999">
        {{ msg }}
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
const emit = defineEmits(['update:visible'])
defineProps({
  visible: Boolean,
  percent: Number,
  status: String,
  msg: String
})

</script>