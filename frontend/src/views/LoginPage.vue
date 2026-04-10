<!-- frontend/src/views/LoginPage.vue -->
<template>
  <div class="login-container">
    <div class="login-card">
      <h2>系统登录</h2>
      <el-form
        ref="loginForm"
        :model="form"
        :rules="rules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item prop="role">
          <el-select v-model="form.role" placeholder="选择权限角色" style="width: 100%">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="子管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="handleLogin"
            :loading="loading"
            style="width: 100%"
          >
            登录
          </el-button>
        </el-form-item>

        <div class="login-tips">
          <p><strong>权限说明：</strong></p>
          <p>• 超级管理员 ：拥有所有权限</p>
          <p>• 普通用户：仅可访问数据看板</p>
          <p>• 子管理员：由超管创建，可分配解析/审核/数据权限</p>
        </div>
      </el-form>
    </div>
  </div>
</template>


<script setup>
import { ref, reactive, inject  } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const loginForm = ref()
const reloadUserInfo = inject('reloadUserInfo', () => {})


// 定义测试账户
const testAccounts = {
  // 超级管理员账户（拥有所有权限）
  // { username: 'admin', password: 'admin123', role: 'super_admin', permissions: ['parse', 'review', 'data'] },
  super_admin: [
    { username: 'admin', password: 'admin123321', role: 'super_admin', permissions: ['parse', 'review', 'data'] },
    { username: '15618421568', password: 'wangxianshuang', role: 'super_admin', permissions: ['parse', 'review', 'data'] },
  ],
  // 普通用户账户
  user: [
    { username: 'user1', password: '123456', role: 'user', permissions: ['data'] },
    { username: 'zhangsan', password: '123456', role: 'user', permissions: ['data'] },
    { username: 'lisi', password: '123456', role: 'user', permissions: ['data'] }
  ],
  // 子管理员账户（由超管创建，权限可配置）
  // { username: '13161130322', password: 'wenxueyang', role: 'admin', permissions: ['data'] },
  //  { username: '15358866605', password: 'hanjiao', role: 'admin', permissions: ['data'] }
  admin: [
    { username: 'manager1', password: '123456', role: 'admin', permissions: ['parse'] },  // 仅解析权限
    { username: 'manager2', password: '123456', role: 'admin', permissions: ['review'] }, // 仅审核权限
    { username: 'manager3', password: '123456', role: 'admin', permissions: ['data'] },  // 仅数据权限
    { username: 'manager4', password: '123456', role: 'admin', permissions: ['parse', 'review'] }, // 解析+审核
    // 旧账户兼容（默认拥有数据权限）

  ]
}

const form = reactive({
  username: '',
  password: '',
  role: 'user' // 默认选择普通用户
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

// 获取子管理员数据（优先从 localStorage 读取，兼容旧代码）
const getSubAdmins = () => {
  const stored = localStorage.getItem('sub_admins')
  if (stored) {
    return JSON.parse(stored)
  }
  // 返回默认数据（兼容旧逻辑）
  return [
    { username: 'manager1', password: '123456', role: 'admin', permissions: ['parse'] },
    { username: 'manager2', password: '123456', role: 'admin', permissions: ['review'] },
    { username: 'manager3', password: '123456', role: 'admin', permissions: ['data'] },
    { username: 'manager4', password: '123456', role: 'admin', permissions: ['parse', 'review'] },
    { username: '15618421568', password: 'wangxianshuang', role: 'admin', permissions: ['data'] },
    { username: '13161130322', password: 'wenxueyang', role: 'admin', permissions: ['data'] },
    { username: '15358866605', password: 'hanjiao', role: 'admin', permissions: ['data'] }
  ]
}

// 模拟登录验证
const mockLogin = (username, password, role) => {
  // 1. 先检查超级管理员
  const superAdmin = testAccounts.super_admin.find(acc => acc.username === username && acc.password === password)
  if (superAdmin) {
    return superAdmin
  }

  // 2. 检查子管理员（优先从 localStorage 读取）
  const subAdmins = getSubAdmins()
  const subAdmin = subAdmins.find(acc => acc.username === username && acc.password === password)
  if (subAdmin) {
    return subAdmin
  }

  // 3. 检查普通用户
  const userAccount = (testAccounts.user || []).find(acc => acc.username === username && acc.password === password)
  if (userAccount) {
    return userAccount
  }

  // 4. 如果没找到任何账户，返回 null
  return null
}

const handleLogin = async () => {
  try {
    await loginForm.value.validate()
    loading.value = true

    // 模拟API请求延迟
    setTimeout(() => {
      // 验证用户名和密码
      const account = mockLogin(form.username, form.password, form.role)

      if (account) {
        // 登录成功，存储用户信息
        localStorage.setItem('token', 'jwt-token-' + Date.now())
        localStorage.setItem('user_role', account.role)
        localStorage.setItem('username', account.username)
        // 存储权限列表
        localStorage.setItem('permissions', JSON.stringify(account.permissions || []))

        // 2. 立即通知 App.vue 更新
        reloadUserInfo()

        ElMessage.success(`登录成功！欢迎 ${account.username}`)

        // 超级管理员重定向到数据解析，其他根据权限重定向
        if (account.role === 'super_admin') {
          router.push('/two-column')
        } else if (account.permissions?.includes('review')) {
          router.push('/three-column')
        } else {
          router.push('/bank-data')
        }
      } else {
        // 登录失败
        ElMessage.error('用户名或密码错误，或角色不匹配')
      }

    }, 1000)
  } catch (error) {
    console.error('登录失败:', error)
    ElMessage.error('请正确填写所有字段')
  } finally {
    loading.value = false
  }
}


</script>



<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.login-card h2 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

.login-form {
  margin-top: 20px;
}

.login-tips {
  margin-top: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  line-height: 1.6;
}

.login-tips p {
  margin: 5px 0;
}

.login-tips strong {
  color: #333;
}
</style>