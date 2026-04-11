<!-- frontend/src/views/AdminManagement.vue -->
<template>
  <div class="admin-management">
    <el-tabs v-model="activeTab" class="main-tabs">

      <!-- ============================= Tab1：子管理员管理 ============================= -->
      <el-tab-pane label="子管理员管理" name="admins">
        <div class="tab-header">
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            创建子管理员
          </el-button>
        </div>

        <el-alert
          title="子管理员说明"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px;"
        >
          子管理员由超级管理员创建，可分配以下权限：
          <strong>数据解析</strong> / <strong>数据审核</strong> / <strong>数据看板</strong>
        </el-alert>

        <el-table :data="adminList" stripe style="width: 100%">
          <el-table-column prop="username" label="用户名" width="180" />
          <el-table-column label="角色" width="120">
            <template #default>
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
              <el-button size="small" type="primary" @click="openEditDialog(row, $index)">编辑</el-button>
              <el-popconfirm title="确定删除该子管理员？" @confirm="handleDelete(row.username)">
                <template #reference>
                  <el-button size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ============================= Tab2：普通用户管理 ============================= -->
      <el-tab-pane name="users">
        <template #label>
          普通用户管理
        </template>

        <el-alert
          title="普通用户说明"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px;"
        >
          普通用户仅可访问数据看板页面，账号由用户自主注册申请并由超管审核通过后生效。
        </el-alert>

        <el-table :data="approvedUsers" stripe style="width: 100%">
          <el-table-column prop="username" label="用户名" width="180" />
          <el-table-column label="角色" width="120">
            <template #default>
              <el-tag type="info">普通用户</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="approvedAt" label="审核通过时间" min-width="200" />
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-popconfirm title="确定删除该用户？" @confirm="handleDeleteUser(row.username)">
                <template #reference>
                  <el-button size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="approvedUsers.length === 0" class="empty-tip">暂无普通用户</div>
      </el-tab-pane>

      <!-- ============================= Tab3：注册审核 ============================= -->
      <el-tab-pane name="register">
        <template #label>
          <span>
            注册审核
            <el-badge
              v-if="pendingCount > 0"
              :value="pendingCount"
              :max="99"
              style="margin-left: 4px;"
            />
          </span>
        </template>

        <el-alert
          v-if="pendingCount === 0 && rejectedRequests.length === 0"
          title="暂无注册申请"
          type="success"
          :closable="false"
          show-icon
          style="margin-bottom: 16px;"
        />

        <!-- 待审核 -->
        <template v-if="pendingRequests.length > 0">
          <div class="section-title">
            <el-icon><Clock /></el-icon>
            待审核申请（{{ pendingRequests.length }}）
          </div>
          <el-table :data="pendingRequests" stripe style="width: 100%; margin-bottom: 24px;">
            <el-table-column prop="username" label="用户名" width="180" />
            <el-table-column prop="remark" label="申请说明" min-width="200">
              <template #default="{ row }">
                <span style="color: #666;">{{ row.remark || '（无说明）' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="applyAt" label="申请时间" width="180" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" @click="handleApprove(row)">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button size="small" type="danger" @click="handleReject(row)">
                  <el-icon><Close /></el-icon> 拒绝
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <!-- 已拒绝（可清理） -->
        <template v-if="rejectedRequests.length > 0">
          <div class="section-title" style="color: #999;">
            <el-icon><CircleClose /></el-icon>
            已拒绝（{{ rejectedRequests.length }}）
            <el-button size="small" text type="danger" style="margin-left: 8px;" @click="clearRejected">清空</el-button>
          </div>
          <el-table :data="rejectedRequests" stripe style="width: 100%;" size="small">
            <el-table-column prop="username" label="用户名" width="180" />
            <el-table-column prop="remark" label="申请说明" min-width="200">
              <template #default="{ row }">
                <span style="color: #999;">{{ row.remark || '（无说明）' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="applyAt" label="申请时间" width="180" />
            <el-table-column prop="rejectedAt" label="拒绝时间" width="180" />
          </el-table>
        </template>
      </el-tab-pane>

    </el-tabs>

    <!-- ===== 创建/编辑子管理员弹窗 ===== -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑子管理员' : '创建子管理员'"
      width="500px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :disabled="isEdit" />
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
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Close, Clock, CircleClose } from '@element-plus/icons-vue'

// ===================== 通用状态 =====================
const activeTab = ref('admins')

// ===================== 权限映射 =====================
const PERM_MAP = {
  parse: { label: '数据解析', tagType: 'success' },
  review: { label: '数据审核', tagType: 'warning' },
  data: { label: '数据看板', tagType: 'primary' },
}
const getPermTagType = (perm) => PERM_MAP[perm]?.tagType || 'info'
const getPermLabel = (perm) => PERM_MAP[perm]?.label || perm

// ===================== Tab1：子管理员管理 =====================
const adminList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingIndex = ref(-1)
const submitting = ref(false)
const formRef = ref()

const form = ref({ username: '', password: '', permissions: [] })

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' },
  ],
  passwordOptional: [
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' },
  ],
  permissions: [
    {
      validator: (rule, value, callback) => {
        value.length === 0 ? callback(new Error('请至少选择一个权限')) : callback()
      },
      trigger: 'change',
    },
  ],
}

const loadAdmins = () => {
  const stored = localStorage.getItem('sub_admins')
  if (stored) {
    adminList.value = JSON.parse(stored)
  } else {
    adminList.value = [
      { username: 'manager1', password: '123456', role: 'admin', permissions: ['parse'] },
      { username: 'manager2', password: '123456', role: 'admin', permissions: ['review'] },
      { username: 'manager3', password: '123456', role: 'admin', permissions: ['data'] },
      { username: 'manager4', password: '123456', role: 'admin', permissions: ['parse', 'review'] },
    ]
    saveAdmins()
  }
}

const saveAdmins = () => localStorage.setItem('sub_admins', JSON.stringify(adminList.value))

const openCreateDialog = () => {
  isEdit.value = false
  editingIndex.value = -1
  form.value = { username: '', password: '', permissions: [] }
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

const openEditDialog = (row, index) => {
  isEdit.value = true
  editingIndex.value = index
  form.value = { username: row.username, password: '', permissions: [...row.permissions] }
  dialogVisible.value = true
  formRef.value?.clearValidate()
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true
    if (isEdit.value) {
      const admin = adminList.value[editingIndex.value]
      if (form.value.password) admin.password = form.value.password
      admin.permissions = [...form.value.permissions]
    } else {
      if (adminList.value.find(a => a.username === form.value.username)) {
        ElMessage.error('用户名已存在')
        return
      }
      adminList.value.push({
        username: form.value.username,
        password: form.value.password,
        role: 'admin',
        permissions: [...form.value.permissions],
      })
    }
    saveAdmins()
    dialogVisible.value = false
    ElMessage.success(isEdit.value ? '修改成功' : '创建成功')
  } catch (e) {
    // 验证失败
  } finally {
    submitting.value = false
  }
}

const handleDelete = (username) => {
  adminList.value = adminList.value.filter(a => a.username !== username)
  saveAdmins()
  ElMessage.success('删除成功')
}

// ===================== Tab2：普通用户管理 =====================
const approvedUsers = ref([])

const loadApprovedUsers = () => {
  try {
    approvedUsers.value = JSON.parse(localStorage.getItem('approved_users') || '[]')
  } catch {
    approvedUsers.value = []
  }
}

const saveApprovedUsers = () => {
  localStorage.setItem('approved_users', JSON.stringify(approvedUsers.value))
}

const handleDeleteUser = (username) => {
  approvedUsers.value = approvedUsers.value.filter(u => u.username !== username)
  saveApprovedUsers()
  ElMessage.success('用户已删除')
}

// ===================== Tab3：注册审核 =====================
const allRequests = ref([])

const pendingRequests = computed(() => allRequests.value.filter(r => r.status === 'pending'))
const rejectedRequests = computed(() => allRequests.value.filter(r => r.status === 'rejected'))
const pendingCount = computed(() => pendingRequests.value.length)

const loadRequests = () => {
  try {
    allRequests.value = JSON.parse(localStorage.getItem('register_requests') || '[]')
  } catch {
    allRequests.value = []
  }
}

const saveRequests = () => {
  localStorage.setItem('register_requests', JSON.stringify(allRequests.value))
}

/** 审核通过 */
const handleApprove = (row) => {
  // 1. 将用户加入已通过用户列表
  approvedUsers.value.push({
    username: row.username,
    password: row.password,
    role: 'user',
    permissions: ['data'],
    approvedAt: new Date().toLocaleString('zh-CN'),
  })
  saveApprovedUsers()

  // 2. 从申请队列中移除（直接删掉，保持列表整洁）
  allRequests.value = allRequests.value.filter(r => r.username !== row.username)
  saveRequests()

  ElMessage.success(`已通过 ${row.username} 的注册申请，账号已激活`)
}

/** 审核拒绝 */
const handleReject = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定拒绝 "${row.username}" 的注册申请？`,
      '拒绝确认',
      { confirmButtonText: '确定拒绝', cancelButtonText: '取消', type: 'warning' }
    )
    const target = allRequests.value.find(r => r.username === row.username)
    if (target) {
      target.status = 'rejected'
      target.rejectedAt = new Date().toLocaleString('zh-CN')
    }
    saveRequests()
    ElMessage.info(`已拒绝 ${row.username} 的注册申请`)
  } catch {
    // 取消操作
  }
}

/** 清空已拒绝记录 */
const clearRejected = () => {
  allRequests.value = allRequests.value.filter(r => r.status !== 'rejected')
  saveRequests()
  ElMessage.success('已清空拒绝记录')
}

// ===================== 初始化 =====================
onMounted(() => {
  loadAdmins()
  loadApprovedUsers()
  loadRequests()
})
</script>

<style scoped>
.admin-management {
  padding: 24px;
}

.tab-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.empty-tip {
  text-align: center;
  color: #999;
  padding: 32px 0;
  font-size: 14px;
}
</style>
