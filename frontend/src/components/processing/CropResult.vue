<template>
  <el-collapse
    v-if="images && images.length"
    style="margin-top: 10px"
  >
    <el-collapse-item title="查看切割子图">
      <div
        v-for="(img, idx) in images"
        :key="idx"
        class="slice"
      >
        <img
          :src="'data:image/png;base64,' + img"
          width="100%"
        >
      </div>
    </el-collapse-item>
  </el-collapse>
</template>

<script setup>
defineProps({
  images: { type: Array, default: () => [] }
})
</script>

<style scoped>
.slice {
  margin-bottom: 8px;
}
</style>