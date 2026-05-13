<template>
  <div class="empty-state">
    <div class="empty-text">
      暂无文件，请上传PDF或图片文件
    </div>
  </div>
</template>

<script setup>
// 空状态组件，不需要逻辑
</script>

<style scoped>
.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-text {
  font-size: 16px;
}
</style>