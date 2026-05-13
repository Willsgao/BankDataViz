<template>
  <div class="table-list">
    <h3>表格列表</h3>
    <div class="table-items">
      <!-- 这里显示提取到的表格列表 -->
      <div
        v-for="table in tables"
        :key="table.id"
        class="table-item"
      >
        {{ table.name }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TableList',
  props: {
    tables: {
      type: Array,
      default: () => []
    }
  }
}
</script>

<style scoped>
.table-list {
  padding: 16px;
}
.table-item {
  padding: 8px;
  border: 1px solid #e0e0e0;
  margin-bottom: 8px;
  cursor: pointer;
}
.table-item:hover {
  background-color: #f5f5f5;
}
</style>