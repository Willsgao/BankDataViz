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
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
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
          <p>• 普通用户：只能访问三栏布局页面</p>
          <p>• 管理员：可以访问两栏和三栏布局页面</p>
        </div>
      </el-form>
    </div>
  </div>
</template>


<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const loginForm = ref()

// 定义测试账户
const testAccounts = {
  // 普通用户账户
  user: [
    { username: 'user1', password: '123456', role: 'user' },
    { username: 'zhangsan', password: '123456', role: 'user' },
    { username: 'lisi', password: '123456', role: 'user' }
  ],
  // 管理员账户
  admin: [
    { username: 'admin', password: 'admin123', role: 'admin' },
    { username: 'root', password: 'root123', role: 'admin' },
    { username: 'superadmin', password: 'super123', role: 'admin' }
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

// 模拟登录验证
const mockLogin = (username, password, role) => {
  const accounts = testAccounts[role] || []
  return accounts.find(acc => acc.username === username && acc.password === password)
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

        ElMessage.success(`登录成功！欢迎 ${account.username}`)

        // 根据角色重定向
        router.push('/three-column')
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