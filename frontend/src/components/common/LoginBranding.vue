<!-- components/common/LoginBranding.vue - 登录页品牌装饰组件 -->
<template>
  <div class="brand-panel">
    <!-- 背景层 -->
    <div class="bg-layer">
      <div class="bg-grid" />
      <div class="bg-glow bg-glow--top" />
      <div class="bg-glow bg-glow--mid" />
      <div class="bg-glow bg-glow--bottom" />
      <div class="bg-line bg-line--1" />
      <div class="bg-line bg-line--2" />

      <!-- 数据可视化装饰 SVG -->
      <svg
        class="data-viz data-viz--chart1"
        viewBox="0 0 320 180"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <polyline
          points="0,140 40,120 80,130 120,80 160,90 200,50 240,60 280,30 320,20"
          stroke="rgba(64,169,255,0.22)"
          stroke-width="2"
          fill="none"
        />
        <polyline
          points="0,160 50,140 100,150 150,110 200,120 250,80 300,70 320,60"
          stroke="rgba(212,169,64,0.14)"
          stroke-width="1.5"
          fill="none"
        />
        <circle cx="120" cy="80" r="3" fill="rgba(64,169,255,0.35)" />
        <circle cx="200" cy="50" r="3.5" fill="rgba(64,169,255,0.4)" />
        <circle cx="280" cy="30" r="3.5" fill="rgba(64,169,255,0.45)" />
        <path
          d="M0,140 L40,120 L80,130 L120,80 L160,90 L200,50 L240,60 L280,30 L320,20 L320,180 L0,180 Z"
          fill="url(#chartGrad1)"
          opacity="0.2"
        />
        <defs>
          <linearGradient id="chartGrad1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="rgba(64,169,255,0.7)" />
            <stop offset="100%" stop-color="rgba(64,169,255,0)" />
          </linearGradient>
        </defs>
      </svg>

      <svg
        class="data-viz data-viz--bars"
        viewBox="0 0 200 160"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="10" y="90" width="18" height="70" rx="3" fill="rgba(64,169,255,0.14)" />
        <rect x="38" y="60" width="18" height="100" rx="3" fill="rgba(64,169,255,0.18)" />
        <rect x="66" y="40" width="18" height="120" rx="3" fill="rgba(64,169,255,0.22)" />
        <rect x="94" y="70" width="18" height="90" rx="3" fill="rgba(64,169,255,0.16)" />
        <rect x="122" y="30" width="18" height="130" rx="3" fill="rgba(64,169,255,0.25)" />
        <rect x="150" y="50" width="18" height="110" rx="3" fill="rgba(64,169,255,0.2)" />
        <rect x="122" y="30" width="18" height="4" rx="2" fill="rgba(212,169,64,0.45)" />
        <rect x="66" y="40" width="18" height="4" rx="2" fill="rgba(212,169,64,0.35)" />
      </svg>

      <svg
        class="data-viz data-viz--particles"
        viewBox="0 0 300 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="50" cy="40" r="2.5" fill="rgba(64,169,255,0.4)">
          <animate attributeName="opacity" values="0.4;0.9;0.4" dur="3s" repeatCount="indefinite" />
        </circle>
        <circle cx="120" cy="80" r="2" fill="rgba(212,169,64,0.5)">
          <animate attributeName="opacity" values="0.5;1;0.5" dur="2.5s" repeatCount="indefinite" />
        </circle>
        <circle cx="200" cy="50" r="3" fill="rgba(64,169,255,0.35)">
          <animate attributeName="opacity" values="0.35;0.85;0.35" dur="4s" repeatCount="indefinite" />
        </circle>
        <circle cx="80" cy="130" r="2" fill="rgba(64,169,255,0.45)">
          <animate attributeName="opacity" values="0.45;0.9;0.45" dur="3.5s" repeatCount="indefinite" />
        </circle>
        <circle cx="250" cy="100" r="2.5" fill="rgba(212,169,64,0.4)">
          <animate attributeName="opacity" values="0.4;0.85;0.4" dur="2.8s" repeatCount="indefinite" />
        </circle>
        <circle cx="170" cy="150" r="2" fill="rgba(64,169,255,0.4)">
          <animate attributeName="opacity" values="0.4;0.9;0.4" dur="3.2s" repeatCount="indefinite" />
        </circle>
        <circle cx="30" cy="170" r="2.5" fill="rgba(212,169,64,0.35)">
          <animate attributeName="opacity" values="0.35;0.8;0.35" dur="2.2s" repeatCount="indefinite" />
        </circle>
        <circle cx="280" cy="170" r="2" fill="rgba(64,169,255,0.38)">
          <animate attributeName="opacity" values="0.38;0.82;0.38" dur="3.8s" repeatCount="indefinite" />
        </circle>
        <line x1="50" y1="40" x2="120" y2="80" stroke="rgba(64,169,255,0.1)" stroke-width="1" />
        <line x1="120" y1="80" x2="200" y2="50" stroke="rgba(64,169,255,0.1)" stroke-width="1" />
        <line x1="200" y1="50" x2="250" y2="100" stroke="rgba(64,169,255,0.08)" stroke-width="1" />
      </svg>

      <svg
        class="data-viz data-viz--donut"
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="60" cy="60" r="45" stroke="rgba(64,169,255,0.12)" stroke-width="12" fill="none" />
        <circle cx="60" cy="60" r="45" stroke="rgba(64,169,255,0.22)" stroke-width="12" fill="none"
          stroke-dasharray="180 283" stroke-linecap="round" transform="rotate(-90 60 60)" />
        <circle cx="60" cy="60" r="45" stroke="rgba(212,169,64,0.18)" stroke-width="12" fill="none"
          stroke-dasharray="60 283" stroke-dashoffset="-180" stroke-linecap="round" transform="rotate(-90 60 60)" />
        <circle cx="60" cy="60" r="4" fill="rgba(64,169,255,0.25)" />
      </svg>

      <!-- 浮动数字装饰 -->
      <div class="data-float data-float--1">98.6</div>
      <div class="data-float data-float--2">▲ 12.4%</div>
      <div class="data-float data-float--3">2,847</div>
      <div class="data-float data-float--4">¥3.2T</div>
    </div>


    <!-- 演示项目标识 -->
    <div class="qrcode-corner">
      <span class="qrcode-label">Open Source</span>
    </div>

    <div class="brand-content">
      <!-- Logo + 标题 -->
      <div class="brand-header">
        <div class="logo-box">
          <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="40" height="40" rx="10" fill="rgba(255,255,255,0.08)"
              stroke="rgba(255,255,255,0.12)" stroke-width="1" />
            <path d="M10 30V16L20 11L30 16V30L20 25L10 30Z" fill="rgba(184,134,11,0.7)"
              stroke="rgba(212,175,55,0.8)" stroke-width="1" stroke-linejoin="round" />
            <path d="M20 11V25" stroke="rgba(10,22,40,0.5)" stroke-width="1" />
            <path d="M10 16L20 21L30 16" stroke="rgba(212,175,55,0.8)" stroke-width="1"
              stroke-linejoin="round" />
          </svg>
        </div>
        <div class="header-text">
          <h1 class="system-title">DocBrain</h1>
          <p class="system-desc">智能文档解析与数据洞察平台</p>
        </div>
      </div>

      <!-- 作者标识 -->
      <div class="team-section">
        <div class="team-tag">
          <span class="tag-dot" />
          全栈项目作品
        </div>
        <div class="team-title">文档智能 + 数据分析</div>
        <div class="team-name">高玉伟</div>
      </div>

      <!-- 分割线 -->
      <div class="divider" />

      <!-- 功能模块列表 -->
      <div class="modules-section">
        <div class="modules-label">系统功能</div>
        <div class="modules-grid">
          <div v-for="(db, i) in databases" :key="i" class="module-item">
            <span class="module-num">{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="module-text">{{ db }}</span>
          </div>
        </div>
      </div>

      <!-- 底部统计 -->
      <div class="brand-stats">
        <div class="stats-group">
          <span class="stats-value">140+</span>
          <span class="stats-key">Python 模块</span>
        </div>
        <div class="stats-sep" />
        <div class="stats-group">
          <span class="stats-value">48+</span>
          <span class="stats-key">Vue 组件</span>
        </div>
        <div class="stats-sep" />
        <div class="stats-group">
          <span class="stats-value">14</span>
          <span class="stats-key">API 蓝图</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  databases: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
/* CSS 变量（从 LoginPage 继承） */
.brand-panel {
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
  width: 500px; height: 500px; top: -180px; right: -120px;
  background: rgba(26, 58, 92, 0.45);
}

.bg-glow--mid {
  width: 350px; height: 350px; top: 40%; left: -80px;
  background: rgba(184, 134, 11, 0.08);
}

.bg-glow--bottom {
  width: 400px; height: 400px; bottom: -150px; left: 30%;
  background: rgba(46, 139, 87, 0.08);
}

.bg-line {
  position: absolute;
  border-radius: 50%;
  border: 1px solid;
}

.bg-line--1 {
  width: 700px; height: 700px; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  border-color: rgba(64, 169, 255, 0.04);
}

.bg-line--2 {
  width: 450px; height: 450px; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  border-color: rgba(212, 169, 64, 0.04);
}

/* ---- 数据可视化 SVG 装饰 ---- */
.data-viz {
  position: absolute;
  pointer-events: none;
}

.data-viz--chart1 { left: 2%; top: 15%; width: 36%; opacity: 1; }
.data-viz--bars { left: 4%; bottom: 20%; width: 24%; opacity: 0.95; }
.data-viz--particles { left: 6%; top: 48%; width: 32%; opacity: 0.9; }
.data-viz--donut { left: 22%; bottom: 10%; width: 13%; opacity: 0.85; }

/* ---- 浮动数字装饰 ---- */
.data-float {
  position: absolute;
  font-family: 'Courier New', 'SF Mono', monospace;
  font-weight: 600;
  pointer-events: none;
  letter-spacing: 1px;
}

.data-float--1 { left: 5%; top: 8%; font-size: 24px; color: rgba(64, 169, 255, 0.22); animation: dataFloat 6s ease-in-out infinite; }
.data-float--2 { left: 10%; top: 36%; font-size: 15px; color: rgba(46, 139, 87, 0.35); animation: dataFloat 5s ease-in-out infinite 1s; }
.data-float--3 { left: 6%; bottom: 32%; font-size: 20px; color: rgba(212, 169, 64, 0.22); animation: dataFloat 7s ease-in-out infinite 2s; }
.data-float--4 { left: 16%; top: 24%; font-size: 16px; color: rgba(64, 169, 255, 0.18); animation: dataFloat 5.5s ease-in-out infinite 0.5s; }

@keyframes dataFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

/* ---- 品牌内容容器 ---- */
.brand-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 580px;
  padding: 44px 48px 44px 36px;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-sizing: border-box;
  justify-content: center;
}

/* ---- Logo + 系统标题 ---- */
.brand-header { display: flex; align-items: center; gap: 14px; margin-bottom: 28px; }

.logo-box {
  width: 44px; height: 44px; flex-shrink: 0;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.35));
}

.logo-box svg { width: 100%; height: 100%; }

.system-title { font-size: 28px; font-weight: 700; color: var(--text-1); margin: 0 0 4px; letter-spacing: 3px; }
.system-desc { font-size: 14px; color: var(--text-3); margin: 0; letter-spacing: 1px; }

/* ---- 团队标识 ---- */
.team-section { margin-bottom: 0; }

.team-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 16px;
  background: rgba(184, 134, 11, 0.12);
  border: 1px solid rgba(184, 134, 11, 0.28);
  border-radius: 20px;
  font-size: 12px; color: var(--gold-2); letter-spacing: 2px;
  margin-bottom: 14px; text-transform: uppercase;
}

.tag-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--gold-2); animation: pulse 2s ease-in-out infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.team-title { font-size: 20px; font-weight: 600; color: var(--text-2); margin: 0 0 5px; letter-spacing: 1px; }
.team-name { font-size: 18px; font-weight: 600; color: var(--text-2); margin: 0; letter-spacing: 1px; }

/* ---- 分割线 ---- */
.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(184, 134, 11, 0.2), rgba(64, 169, 255, 0.1), transparent);
  margin: 22px 0;
}

/* ---- 数据库模块 ---- */
.modules-section { flex: 1; min-height: 0; display: flex; flex-direction: column; }

.modules-label {
  font-size: 12px; font-weight: 600; color: var(--text-4);
  letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px;
}

.modules-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1px 20px; }

.module-item { display: flex; align-items: baseline; gap: 10px; padding: 6px 10px; border-radius: 6px; transition: background 0.2s ease; }
.module-item:hover { background: rgba(255, 255, 255, 0.04); }

.module-num { font-size: 11px; font-weight: 600; color: rgba(64, 169, 255, 0.45); font-family: 'Courier New', monospace; min-width: 18px; flex-shrink: 0; }
.module-text { font-size: 13px; color: var(--text-2); }

/* ---- 底部统计 ---- */
.brand-stats { display: flex; align-items: center; gap: 6px; margin-top: auto; padding-top: 18px; }

.stats-group { display: flex; flex-direction: column; align-items: flex-start; }
.stats-value { font-size: 22px; font-weight: 700; color: var(--text-1); }
.stats-key { font-size: 11px; color: var(--text-4); }

.stats-sep { width: 1px; height: 32px; background: rgba(255, 255, 255, 0.08); flex-shrink: 0; }

/* ---- 二维码 ---- */
.qrcode-corner { position: absolute; bottom: 24px; right: 32px; z-index: 2; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.qrcode-img { width: 72px; height: 72px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1); }
.qrcode-label { font-size: 10px; color: rgba(255, 255, 255, 0.25); white-space: nowrap; }
</style>
