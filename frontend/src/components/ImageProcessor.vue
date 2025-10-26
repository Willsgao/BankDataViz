<template>
  <div class="image-processor">
    <a-card title="表格识别处理">
      <a-tabs v-model:activeKey="activeTab">
        <!-- 单张图片处理 -->
        <a-tab-pane key="single" tab="单张处理">
          <single-image-processor />
        </a-tab-pane>

        <!-- 批量处理 -->
        <a-tab-pane key="batch" tab="批量处理">
          <batch-image-processor />
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SingleImageProcessor from './components/SingleImageProcessor.vue'
import BatchImageProcessor from './components/BatchImageProcessor.vue'

const activeTab = ref('single')
</script>

<style scoped>
.image-processor {
  padding: 20px;
}
</style>