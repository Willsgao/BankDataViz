<template>
  <el-image
    :src="imgUrl"
    :preview-src-list="[imgUrl]"
    fit="contain"
    style="max-height:500px; width:100%; cursor:pointer;"
  />
</template>

<script setup>
const props = defineProps({ file: Object })
const imgUrl = `http://127.0.0.1:5000/file/${props.file.filename}`
</script>