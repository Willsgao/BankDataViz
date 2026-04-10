<!-- frontend/src/views/AdminManagement.vue -->
<template>
  <div class="admin-management">
    <div class="page-header">
      <h2>子管理员管理</h2>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        创建子管理员
      </el-button>
    </div>

    <!-- 提示信息 -->
    <el-alert
      title="子管理员说明"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 20px;"
    >
      子管理员由超级管理员创建，可分配以下权限：<br>
      <strong>数据解析</strong> - 访问数据解析页面，上传和解析文档<br>
      <strong>数据审核</strong> - 访问数据审核页面，审核表格内容<br>
      <strong>数据看板</strong> - 访问数据看板页面，查看和下载数据
    </el-alert>

    <!-- 子管理员列表 -->
    <el-table :data="adminList" stripe style="width: 100%">
      <el-table-column prop="username" label="用户名" width="180" />
      <el-table-column prop="role" label="角色" width="120">
        <template #default="{ row }">
          <el-tag type="warning">子管理员</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="权限" min-width="300">
        <template #default="{ row }">
          <el-tag
            v-for="perm in row.permissions"
            :key="perm"
            :type="getPermTagType(perm)"
            size="small"
            style="margin-right: 4px;"
          >
            {{ getPermLabel(perm) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row, $index }">
          <el-button size="small" type="primary" @click="openEditDialog(row, $index)">
            编辑
          </el-button>
          <el-popconfirm
            title="确定删除该子管理员？"
            @confirm="handleDelete(row.username)"
          >
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑子管理员' : '创建子管理员'"
      width="500px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :disabled="isEdit"
          />
        </el-form-item>

        <el-form-item label="密码" :prop="isEdit ? 'passwordOptional' : 'password'">
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="isEdit ? '留空则不修改密码' : '请输入密码'"
            show-password
          />
        </el-form-item>

        <el-form-item label="权限分配" prop="permissions">
          <el-checkbox-group v-model="form.permissions">
            <el-checkbox label="parse">数据解析</el-checkbox>
            <el-checkbox label="review">数据审核</el-checkbox>
            <el-checkbox label="data">数据看板</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const adminList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingIndex = ref(-1)
const submitting = ref(false)
const formRef = ref()

const form = ref({
  username: '',
  password: '',
  permissions: []
})

// 超级管理员硬编码账户（不参与列表显示）
const SUPER_ADMIN = {
  username: 'admin',
  password: 'admin123'
}

// 权限映射
const PERM_MAP = {
  parse: { label: '数据解析', tagType: 'success' },
  review: { label: '数据审核', tagType: 'warning' },
  data: { label: '数据看板', tagType: 'primary' }
}

// 表单验证规则
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' }
  ],
  passwordOptional: [
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' }
  ],
  permissions: [
    {
      validator: (rule, value, callback) => {
        if (value.length === 0) {
          callback(new Error('请至少选择一个权限'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

// 权限标签类型
const getPermTagType = (perm) => {
  return PERM_MAP[perm]?.tagType || 'info'
}

// 权限标签文字
const getPermLabel = (perm) => {
  return PERM_MAP[perm]?.label || perm
}

// 从 localStorage 加载子管理员数据
const loadAdmins = () => {
  const stored = localStorage.getItem('sub_admins')
  if (stored) {
    adminList.value = JSON.parse(stored)
  } else {
    // 初始化默认数据
    adminList.value = [
      { username: 'manager1', password: '123456', role: 'admin', permissions: ['parse'] },
      { username: 'manager2', password: '123456', role: 'admin', permissions: ['review'] },
      { username: 'manager3', password: '123456', role: 'admin', permissions: ['data'] },
      { username: 'manager4', password: '123456', role: 'admin', permissions: ['parse', 'review'] }
    ]
    saveAdmins()
  }
}

// 保存子管理员数据到 localStorage
const saveAdmins = () => {
  localStorage.setItem('sub_admins', JSON.stringify(adminList.value))
}

// 同步更新 LoginPage 的测试账户
const syncToLoginPage = () => {
  // 将子管理员数据同步到全局，供 LoginPage 使用
  localStorage.setItem('sub_admins_for_login', JSON.stringify(adminList.value))
}

// 打开创建弹窗
const openCreateDialog = () => {
  isEdit.value = false
  editingIndex.value = -1
  form.value = {
    username: '',
    password: '',
    permissions: []
  }
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

// 打开编辑弹窗
const openEditDialog = (row, index) => {
  isEdit.value = true
  editingIndex.value = index
  form.value = {
    username: row.username,
    password: '', // 密码不显示
    permissions: [...row.permissions]
  }
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

// 提交表单
const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true

    if (isEdit.value) {
      // 编辑模式：更新指定索引的数据
      const admin = adminList.value[editingIndex.value]
      if (form.value.password) {
        admin.password = form.value.password
      }
      admin.permissions = [...form.value.permissions]
    } else {
      // 创建模式：检查用户名是否已存在
      const exists = adminList.value.find(a => a.username === form.value.username)
      if (exists) {
        ElMessage.error('用户名已存在')
        return
      }

      adminList.value.push({
        username: form.value.username,
        password: form.value.password,
        role: 'admin',
        permissions: [...form.value.permissions]
      })
    }

    saveAdmins()
    syncToLoginPage()
    dialogVisible.value = false
    ElMessage.success(isEdit.value ? '修改成功' : '创建成功')
  } catch (e) {
    // 验证失败
  } finally {
    submitting.value = false
  }
}

// 删除子管理员
const handleDelete = (username) => {
  adminList.value = adminList.value.filter(a => a.username !== username)
  saveAdmins()
  syncToLoginPage()
  ElMessage.success('删除成功')
}

onMounted(() => {
  loadAdmins()
  syncToLoginPage()
})
</script>

<style scoped>
.admin-management {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
</style>
