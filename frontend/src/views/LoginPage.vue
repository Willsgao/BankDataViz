<!-- frontend/src/views/LoginPage.vue -->
<template>
  <div class="login-page">
    <!-- ===================== 左侧品牌区 ===================== -->
    <div class="brand-panel">
      <!-- 背景层 -->
      <div class="bg-layer">
        <div class="bg-grid"></div>
        <div class="bg-glow bg-glow--top"></div>
        <div class="bg-glow bg-glow--mid"></div>
        <div class="bg-glow bg-glow--bottom"></div>
        <div class="bg-line bg-line--1"></div>
        <div class="bg-line bg-line--2"></div>
      </div>

      <div class="brand-content">
        <!-- Logo + 标题 -->
        <div class="brand-header">
          <div class="logo-box">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="40" height="40" rx="10" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
              <path d="M10 30V16L20 11L30 16V30L20 25L10 30Z" fill="rgba(184,134,11,0.7)" stroke="rgba(212,175,55,0.8)" stroke-width="1" stroke-linejoin="round"/>
              <path d="M20 11V25" stroke="rgba(10,22,40,0.5)" stroke-width="1"/>
              <path d="M10 16L20 21L30 16" stroke="rgba(212,175,55,0.8)" stroke-width="1" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="header-text">
            <h1 class="system-title">BankData</h1>
            <p class="system-desc">上市银行数据库管理系统</p>
          </div>
        </div>

        <!-- 团队标识 -->
        <div class="team-section">
          <div class="team-tag">
            <span class="tag-dot"></span>
            专属研究平台
          </div>
          <div class="team-title">银行与货币金融研究</div>
          <div class="team-name">王先爽团队</div>
        </div>

        <!-- 分割线 -->
        <div class="divider"></div>

        <!-- 数据库模块列表 -->
        <div class="modules-section">
          <div class="modules-label">覆盖数据库（部分展示）</div>
          <div class="modules-grid">
            <div
              v-for="(db, i) in databases"
              :key="i"
              class="module-item"
            >
              <span class="module-num">{{ String(i + 1).padStart(2, '0') }}</span>
              <span class="module-text">{{ db }}</span>
            </div>
          </div>
        </div>

        <!-- 底部统计 -->
        <div class="brand-stats">
          <div class="stats-group">
            <span class="stats-value">50+</span>
            <span class="stats-key">专业数据库</span>
          </div>
          <div class="stats-sep"></div>
          <div class="stats-group">
            <span class="stats-value">AI</span>
            <span class="stats-key">智能解析引擎</span>
          </div>
          <div class="stats-sep"></div>
          <div class="stats-group">
            <span class="stats-value">100%</span>
            <span class="stats-key">上市银行覆盖</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===================== 右侧登录区 ===================== -->
    <div class="form-panel">
      <div class="form-wrapper">
        <!-- 顶部装饰 -->
        <div class="form-accent"></div>

        <!-- 表单卡片 -->
        <div class="form-card">
          <div class="form-header">
            <h2 class="form-title">欢迎访问</h2>
            <p class="form-subtitle">请登录以使用数据库系统</p>
          </div>

          <el-tabs v-model="activeTab" class="auth-tabs">
            <!-- ===== 登录 Tab ===== -->
            <el-tab-pane label="账号登录" name="login">
              <el-form
                ref="loginForm"
                :model="form"
                :rules="rules"
                class="auth-form"
              >
                <el-form-item prop="username">
                  <el-input
                    v-model="form.username"
                    placeholder="用户名"
                    prefix-icon="User"
                    size="large"
                  />
                </el-form-item>

                <el-form-item prop="password">
                  <el-input
                    v-model="form.password"
                    type="password"
                    placeholder="密码"
                    prefix-icon="Lock"
                    size="large"
                    @keyup.enter="handleLogin"
                  />
                </el-form-item>

                <el-form-item>
                  <el-button
                    type="primary"
                    @click="handleLogin"
                    :loading="loading"
                    class="submit-btn"
                    size="large"
                  >
                    登 录
                  </el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>

            <!-- ===== 注册 Tab ===== -->
            <el-tab-pane label="申请注册" name="register">
              <el-form
                ref="registerForm"
                :model="regForm"
                :rules="regRules"
                class="auth-form"
              >
                <el-form-item prop="username">
                  <el-input
                    v-model="regForm.username"
                    placeholder="用户名（3-20个字符）"
                    prefix-icon="User"
                    size="large"
                  />
                </el-form-item>

                <el-form-item prop="password">
                  <el-input
                    v-model="regForm.password"
                    type="password"
                    placeholder="密码（6-20个字符）"
                    prefix-icon="Lock"
                    size="large"
                    show-password
                  />
                </el-form-item>

                <el-form-item prop="confirmPassword">
                  <el-input
                    v-model="regForm.confirmPassword"
                    type="password"
                    placeholder="确认密码"
                    prefix-icon="Lock"
                    size="large"
                    show-password
                    @keyup.enter="handleRegister"
                  />
                </el-form-item>

                <el-form-item prop="remark">
                  <el-input
                    v-model="regForm.remark"
                    placeholder="申请说明（选填）"
                    prefix-icon="ChatDotRound"
                    size="large"
                  />
                </el-form-item>

                <el-form-item>
                  <el-button
                    type="primary"
                    @click="handleRegister"
                    :loading="regLoading"
                    class="submit-btn"
                    size="large"
                  >
                    提交注册申请
                  </el-button>
                </el-form-item>

                <div class="reg-tip">
                  <el-icon><InfoFilled /></el-icon>
                  <span>提交后需等待管理员审核通过方可登录</span>
                </div>
              </el-form>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 底部版权 -->
        <div class="form-footer">
          &copy; {{ new Date().getFullYear() }} BankData &middot; 银行与货币金融研究
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import { ref, reactive, inject } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const regLoading = ref(false)
const loginForm = ref()
const registerForm = ref()
const reloadUserInfo = inject('reloadUserInfo', () => {})
const activeTab = ref('login')

// ===================== 数据库列表 =====================
const databases = [
  '上市银行业绩变化一览',
  '上市银行财报综述',
  '上市银行关键指标数据库',
  '上市银行ROE拆分数据库',
  '上市银行业绩驱动拆分',
  '上市银行息差数据库',
  '上市银行自由现金流数据库',
  '上市银行资产质量指标数据库',
  '对公零售贷款资产质量数据库',
  'A+H资产三阶段数据库',
  '银行超额拨备数据库',
  '上市银行金融投资数据库',
  '资产负债结构数据库',
  '上市银行主要指标市占率数据库',
]

// ===================== 超级管理员账户（硬编码，不可变） =====================
const SUPER_ADMINS = [
  { username: 'admin', password: 'admin123321', role: 'super_admin', permissions: ['parse', 'review', 'data'] },
  { username: '15618421568', password: 'wangxianshuang', role: 'super_admin', permissions: ['parse', 'review', 'data'] },
]

// ===================== localStorage 工具函数 =====================

/** 读取子管理员列表 */
const getSubAdmins = () => {
  try {
    return JSON.parse(localStorage.getItem('sub_admins') || '[]')
  } catch { return [] }
}

/** 读取已审核通过的普通用户列表 */
const getApprovedUsers = () => {
  try {
    return JSON.parse(localStorage.getItem('approved_users') || '[]')
  } catch { return [] }
}

/** 读取内置兜底普通用户（保留旧账号兼容性） */
const getBuiltinUsers = () => [
  { username: 'user1', password: '123456', role: 'user', permissions: ['data'] },
  { username: 'zhangsan', password: '123456', role: 'user', permissions: ['data'] },
  { username: 'lisi', password: '123456', role: 'user', permissions: ['data'] },
]

// ===================== 登录逻辑 =====================
const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const mockLogin = (username, password) => {
  // 1. 超级管理员
  const superAdmin = SUPER_ADMINS.find(a => a.username === username && a.password === password)
  if (superAdmin) return superAdmin

  // 2. 子管理员
  const subAdmin = getSubAdmins().find(a => a.username === username && a.password === password)
  if (subAdmin) return subAdmin

  // 3. 审核通过的普通用户
  const approvedUser = getApprovedUsers().find(a => a.username === username && a.password === password)
  if (approvedUser) return approvedUser

  // 4. 内置兜底用户（兼容旧账号）
  const builtinUser = getBuiltinUsers().find(a => a.username === username && a.password === password)
  if (builtinUser) return builtinUser

  return null
}

const handleLogin = async () => {
  try {
    await loginForm.value.validate()
    loading.value = true

    setTimeout(() => {
      const account = mockLogin(form.username, form.password)

      if (account) {
        localStorage.setItem('token', 'jwt-token-' + Date.now())
        localStorage.setItem('user_role', account.role)
        localStorage.setItem('username', account.username)
        localStorage.setItem('permissions', JSON.stringify(account.permissions || []))

        reloadUserInfo()
        ElMessage.success(`登录成功！欢迎 ${account.username}`)

        if (account.role === 'super_admin') {
          router.push('/two-column')
        } else if (account.permissions?.includes('parse')) {
          router.push('/two-column')
        } else if (account.permissions?.includes('review')) {
          router.push('/three-column')
        } else {
          router.push('/bank-data')
        }
      } else {
        // 检查是否是待审核账号
        const pending = getPendingRequests().find(r => r.username === form.username)
        if (pending) {
          ElMessage.warning('您的账号正在等待管理员审核，请耐心等待')
        } else {
          ElMessage.error('用户名或密码错误')
        }
      }

      loading.value = false
    }, 800)
  } catch (error) {
    console.error('登录失败:', error)
  }
}

// ===================== 注册逻辑 =====================
const regForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  remark: '',
})

const validateConfirmPwd = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请确认密码'))
  } else if (value !== regForm.password) {
    callback(new Error('两次密码不一致'))
  } else {
    callback()
  }
}

const regRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPwd, trigger: 'blur' },
  ],
}

/** 读取注册申请队列 */
const getPendingRequests = () => {
  try {
    return JSON.parse(localStorage.getItem('register_requests') || '[]')
  } catch { return [] }
}

/** 检查用户名是否已被占用 */
const isUsernameTaken = (username) => {
  const allUsernames = [
    ...SUPER_ADMINS.map(a => a.username),
    ...getSubAdmins().map(a => a.username),
    ...getApprovedUsers().map(a => a.username),
    ...getBuiltinUsers().map(a => a.username),
    ...getPendingRequests().map(r => r.username),
  ]
  return allUsernames.includes(username)
}

const handleRegister = async () => {
  try {
    await registerForm.value.validate()
    regLoading.value = true

    setTimeout(() => {
      // 检查用户名重复
      if (isUsernameTaken(regForm.username)) {
        ElMessage.error('该用户名已存在或已有人申请，请换一个')
        regLoading.value = false
        return
      }

      // 写入待审核队列
      const requests = getPendingRequests()
      requests.push({
        username: regForm.username,
        password: regForm.password,
        remark: regForm.remark || '',
        applyAt: new Date().toLocaleString('zh-CN'),
        status: 'pending',
      })
      localStorage.setItem('register_requests', JSON.stringify(requests))

      ElMessage.success('注册申请已提交，请等待管理员审核')

      // 重置表单，切回登录 Tab
      regForm.username = ''
      regForm.password = ''
      regForm.confirmPassword = ''
      regForm.remark = ''
      registerForm.value?.clearValidate()
      activeTab.value = 'login'

      regLoading.value = false
    }, 800)
  } catch (error) {
    console.error('注册失败:', error)
  }
}
</script>



<style scoped>
/* ========================================================
   全局变量
   ======================================================== */
.login-page {
  --deep-1: #070e1a;
  --deep-2: #0c1a30;
  --deep-3: #122640;
  --deep-4: #1a3a5c;
  --gold-1: #b8860b;
  --gold-2: #d4a940;
  --gold-3: #f0d060;
  --text-1: #ffffff;
  --text-2: rgba(255, 255, 255, 0.78);
  --text-3: rgba(255, 255, 255, 0.45);
  --text-4: rgba(255, 255, 255, 0.25);
  --surface: #f0f2f5;
  --card-bg: #ffffff;
  --input-border: #d9d9d9;
  --input-focus: var(--deep-3);
  --accent: var(--deep-3);

  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: var(--deep-1);
}

/* ========================================================
   左侧品牌面板
   ======================================================== */
.brand-panel {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(165deg, var(--deep-1) 0%, var(--deep-2) 30%, var(--deep-3) 60%, var(--deep-4) 100%);
  overflow: hidden;
}

/* ---- 背景装饰 ---- */
.bg-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(64, 169, 255, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(64, 169, 255, 0.025) 1px, transparent 1px);
  background-size: 80px 80px;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
}

.bg-glow--top {
  width: 500px;
  height: 500px;
  top: -180px;
  right: -120px;
  background: rgba(26, 58, 92, 0.45);
}

.bg-glow--mid {
  width: 350px;
  height: 350px;
  top: 40%;
  left: -80px;
  background: rgba(184, 134, 11, 0.08);
}

.bg-glow--bottom {
  width: 400px;
  height: 400px;
  bottom: -150px;
  left: 30%;
  background: rgba(46, 139, 87, 0.08);
}

.bg-line {
  position: absolute;
  border-radius: 50%;
  border: 1px solid;
}

.bg-line--1 {
  width: 700px;
  height: 700px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-color: rgba(64, 169, 255, 0.04);
}

.bg-line--2 {
  width: 450px;
  height: 450px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-color: rgba(212, 169, 64, 0.04);
}

/* ---- 品牌内容容器 ---- */
.brand-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 600px;
  padding: 48px 52px;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-sizing: border-box;
  justify-content: center;
}

/* ---- Logo + 系统标题 ---- */
.brand-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 36px;
}

.logo-box {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.35));
}

.logo-box svg {
  width: 100%;
  height: 100%;
}

.system-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-1);
  margin: 0 0 4px;
  letter-spacing: 3px;
}

.system-desc {
  font-size: 14px;
  color: var(--text-3);
  margin: 0;
  letter-spacing: 1px;
}

/* ---- 团队标识 ---- */
.team-section {
  margin-bottom: 0;
}

.team-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 16px;
  background: rgba(184, 134, 11, 0.12);
  border: 1px solid rgba(184, 134, 11, 0.28);
  border-radius: 20px;
  font-size: 12px;
  color: var(--gold-2);
  letter-spacing: 2px;
  margin-bottom: 16px;
  text-transform: uppercase;
}

.tag-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--gold-2);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.team-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-2);
  margin: 0 0 5px;
  letter-spacing: 1px;
}

.team-name {
  font-size: 15px;
  color: var(--text-3);
  margin: 0;
  letter-spacing: 0.5px;
}

/* ---- 分割线 ---- */
.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(184, 134, 11, 0.2), rgba(64, 169, 255, 0.1), transparent);
  margin: 28px 0;
}

/* ---- 数据库模块 ---- */
.modules-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.modules-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-4);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 14px;
}

.modules-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px 20px;
}

.module-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 6px;
  transition: background 0.2s ease;
}

.module-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.module-num {
  font-size: 11px;
  font-weight: 600;
  color: rgba(64, 169, 255, 0.45);
  font-family: 'Courier New', monospace;
  min-width: 18px;
  flex-shrink: 0;
}

.module-text {
  font-size: 13.5px;
  color: var(--text-2);
  line-height: 1.8;
  letter-spacing: 0.3px;
}

.module-item:hover .module-text {
  color: var(--text-1);
}

/* ---- 底部统计 ---- */
.brand-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  padding-top: 24px;
}

.stats-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.stats-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: 1px;
}

.stats-key {
  font-size: 11px;
  color: var(--text-4);
  letter-spacing: 1px;
  white-space: nowrap;
}

.stats-sep {
  width: 1px;
  height: 32px;
  background: rgba(255, 255, 255, 0.08);
}

/* ========================================================
   右侧登录面板
   ======================================================== */
.form-panel {
  width: 460px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  position: relative;
}

.form-wrapper {
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 顶部装饰线 */
.form-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--deep-3) 0%, #2e8b57 50%, var(--gold-1) 100%);
}

/* ---- 表单卡片 ---- */
.form-card {
  width: 100%;
  background: var(--card-bg);
  border-radius: 12px;
  padding: 40px 32px 32px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.form-header {
  text-align: center;
  margin-bottom: 28px;
}

.form-title {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 6px;
}

.form-subtitle {
  font-size: 13px;
  color: #8c8c8c;
  margin: 0;
}

/* ---- Tab ---- */
.auth-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
  color: #8c8c8c;
  padding: 0 16px;
  height: 40px;
  line-height: 40px;
}

.auth-tabs :deep(.el-tabs__item.is-active) {
  color: var(--deep-3);
  font-weight: 600;
}

.auth-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--deep-3);
}

.auth-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}

/* ---- 表单 ---- */
.auth-form {
  margin-top: 16px;
}

.auth-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.auth-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--input-border) inset;
  transition: box-shadow 0.25s ease;
  padding: 4px 11px;
}

.auth-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #b0bec5 inset;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--input-focus) inset, 0 0 0 3px rgba(18, 38, 64, 0.08);
}

/* ---- 提交按钮 ---- */
.submit-btn {
  width: 100%;
  height: 42px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 6px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--deep-3) 0%, var(--deep-4) 100%);
  border: none;
  transition: all 0.25s ease;
}

.submit-btn:hover {
  background: linear-gradient(135deg, var(--deep-4) 0%, #1f4f78 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(18, 38, 64, 0.3);
}

.submit-btn:active {
  transform: translateY(0);
  box-shadow: none;
}

/* ---- 注册提示 ---- */
.reg-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #fffbe6;
  border-radius: 8px;
  font-size: 12px;
  color: #ad6800;
  line-height: 1.5;
}

/* ---- 底部版权 ---- */
.form-footer {
  margin-top: 28px;
  font-size: 12px;
  color: #bfbfbf;
  letter-spacing: 0.5px;
}

/* ========================================================
   响应式
   ======================================================== */
@media (max-width: 1100px) {
  .brand-content {
    padding: 36px 40px;
  }

  .modules-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
}

@media (max-width: 900px) {
  .login-page {
    flex-direction: column;
  }

  .brand-panel {
    flex: none;
    min-height: auto;
    padding: 28px 24px;
  }

  .brand-content {
    padding: 0;
    max-width: 100%;
    height: auto;
    justify-content: flex-start;
  }

  .brand-stats {
    display: none;
  }

  .form-panel {
    width: 100%;
    flex: 1;
    padding: 20px;
  }

  .form-wrapper {
    max-width: 400px;
  }

  .form-card {
    padding: 32px 24px 28px;
  }

  .modules-grid {
    grid-template-columns: 1fr 1fr;
    gap: 2px 16px;
  }
}

@media (max-width: 520px) {
  .modules-grid {
    grid-template-columns: 1fr;
  }

  .brand-header {
    margin-bottom: 24px;
  }

  .system-title {
    font-size: 22px;
  }
}
</style>
