<template>
  <el-image
    :src="imgUrl"
    :preview-src-list="[imgUrl]"
    fit="contain"
    style="max-height:500px; width:100%; cursor:pointer;"
  />
</template>

<script setup>
import { getBackendUrl } from '@/utils/config'

const props = defineProps({ file: Object })
const imgUrl = getBackendUrl(`/file/${props.file.filename}`)
</script>