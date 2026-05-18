<template>
  <div class="prompt-showcase-page">
    <div class="page-header">
      <h1>
        <el-icon :size="24"><Setting /></el-icon>
        Prompt 工程设计展示
      </h1>
      <p class="page-subtitle">5 种财务表格分析提示词 · 5 级复杂度评估体系 · 4 种 JSON 格式容错策略</p>
    </div>

    <div class="showcase-content">
      <!-- 复杂度评估体系 -->
      <el-card class="showcase-card">
        <template #header>
          <div class="card-title">
            <el-tag type="primary" effect="dark" size="large">核心能力</el-tag>
            <span>财务表格复杂度五级评估体系</span>
          </div>
        </template>
        <div class="complexity-grid">
          <div v-for="level in complexityLevels" :key="level.name" class="complexity-item" :class="level.className">
            <div class="level-badge">{{ level.name }}</div>
            <div class="level-desc">{{ level.desc }}</div>
            <div class="level-meta">
              <span>数据量：{{ level.dataRange }}</span>
              <span v-if="level.columns">列：{{ level.columns }}</span>
              <span v-if="level.rows">行：{{ level.rows }}</span>
            </div>
            <div class="level-example">{{ level.example }}</div>
          </div>
        </div>
        <div class="assessment-features">
          <h4>四维评估要素</h4>
          <el-row :gutter="16">
            <el-col :span="6" v-for="dim in dimensions" :key="dim.name">
              <div class="dim-item">
                <div class="dim-icon">{{ dim.icon }}</div>
                <div class="dim-name">{{ dim.name }}</div>
                <div class="dim-desc">{{ dim.desc }}</div>
              </div>
            </el-col>
          </el-row>
        </div>
      </el-card>

      <!-- Prompt 类型展示 -->
      <el-card class="showcase-card">
        <template #header>
          <div class="card-title">
            <el-tag type="success" effect="dark" size="large">提示词</el-tag>
            <span>4 种表格分析 Prompt 设计</span>
          </div>
        </template>
        <el-tabs v-model="activePrompt" type="border-card">
          <el-tab-pane label="复杂度评估" name="assessment">
            <div class="prompt-detail">
              <div class="prompt-meta">
                <el-tag>角色</el-tag> 财务表格复杂度五级评估专家
                <el-tag type="warning">特点</el-tag> 前置判定 + 四维评估 + 五级输出
              </div>
              <div class="prompt-highlight">
                <h4>设计亮点</h4>
                <ul>
                  <li><strong>两步前置判定</strong>：先判断整页截图是否存在银行财务表格（必须有金额/比率数值列），避免对非表格内容无效分析</li>
                  <li><strong>四维要素解耦</strong>：横向维度（指标数量/业务维度/维度类型）、纵向层级（层级数量/结构类型/汇总深度）、结构复杂度（合并单元格/汇总结构/非结构化元素）、数据量规模（单元格总数/明细项占比）</li>
                  <li><strong>五级分类</strong>：极简单→简单→中等-紧凑型(3A)→中等-扩展型(3B)→复杂→极复杂，Level 3 细分考虑数据量因素</li>
                  <li><strong>结构化输出</strong>：JSON 格式输出四维评估详情 + 综合等级判定，便于后续自动选择处理策略</li>
                </ul>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="标准表格 (STANDARD)" name="standard">
            <div class="prompt-detail">
              <div class="prompt-meta">
                <el-tag>适用</el-tag> 中等复杂度表格（50-120 单元格）
                <el-tag type="warning">处理模式</el-tag> 双维度解耦 + 11列CSV输出
              </div>
              <div class="prompt-highlight">
                <h4>设计亮点</h4>
                <ul>
                  <li><strong>分区块表格处理</strong>：自动识别资产负债表"资产/负债及所有者权益"双区块，独立提取后合并</li>
                  <li><strong>行列边界校验</strong>：垂直分隔线优先定位列边界 → 标题列宽度规则 → 数值列右对齐规则（三级降级）</li>
                  <li><strong>维度解耦架构</strong>：纵向层级路径（{父级}/{子级}/{明细}）+ 横向层级路径（{指标类型}/{时间维度}），支持笛卡尔积展开</li>
                  <li><strong>遮挡容错</strong>：被印章/水印遮挡的单元格 → 数值填"-"，单位/币种继承同列上方有效值</li>
                </ul>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="复杂表格 (COMPLEX)" name="complex">
            <div class="prompt-detail">
              <div class="prompt-meta">
                <el-tag>适用</el-tag> 复杂/极复杂表格（>120 单元格）
                <el-tag type="danger">处理模式</el-tag> 三维解析框架 + 笛卡尔积网格生成
              </div>
              <div class="prompt-highlight">
                <h4>设计亮点</h4>
                <ul>
                  <li><strong>三维解析框架</strong>：纵向科目维度(Y轴) × 横向指标维度(X轴) × 数据值维度(Z轴)，将复杂表格建模为三维矩阵</li>
                  <li><strong>笛卡尔积网格生成</strong>：基于纵向科目 × 横向指标的完整笛卡尔积生成数据点位，确保无遗漏</li>
                  <li><strong>完整性验证</strong>：预期单元格数=实际提取数验证 + 汇总值≈∑明细值（误差≤0.01元/0.01%）+ 层级合理性检查</li>
                  <li><strong>维度正交性</strong>：确保同一维度内元素互斥（如时间维度不含业务分类），防止维度混淆</li>
                </ul>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="非金融表格" name="non_financial">
            <div class="prompt-detail">
              <div class="prompt-meta">
                <el-tag>适用</el-tag> 通用非金融表格（产品清单、人员名单、统计报表等）
                <el-tag type="info">处理模式</el-tag> 直接提取 + 数据清洗
              </div>
              <div class="prompt-highlight">
                <h4>设计亮点</h4>
                <ul>
                  <li><strong>通用表格处理</strong>：不限定金融语义，适用于产品清单、人员名单、统计报表等多样化场景</li>
                  <li><strong>原样保留</strong>：文本内容原样保留不做金融术语转换，避免误处理非金融数据</li>
                  <li><strong>基础清洗</strong>：空白单元格→"-"，千位符删除，括号转负号，保持数据完整性</li>
                </ul>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- JSON 格式容错 -->
      <el-card class="showcase-card">
        <template #header>
          <div class="card-title">
            <el-tag type="danger" effect="dark" size="large">容错</el-tag>
            <span>LLM 响应 JSON 格式容错处理</span>
          </div>
        </template>
        <div class="fallback-strategies">
          <el-steps :active="4" align-center>
            <el-step title="数组格式" description="尝试解析为数组，直接遍历提取" />
            <el-step title="对象格式" description="尝试解析为对象，按 key 映射取值" />
            <el-step title="嵌套结构" description="递归搜索嵌套 JSON 中的数组数据" />
            <el-step title="深度搜索" description="遍历整棵 JSON 树，深度优先搜索表格数据" />
          </el-steps>
        </div>
        <el-divider />
        <div class="fallback-detail">
          <h4>为什么需要 4 种容错格式？</h4>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-alert title="LLM 输出不稳定" type="warning" :closable="false" show-icon>
                LLM 在不同 prompt/表格/模型版本下可能输出不同 JSON 结构，需要多级容错保证提取成功率
              </el-alert>
            </el-col>
            <el-col :span="8">
              <el-alert title="嵌套层级多变" type="info" :closable="false" show-icon>
                有些表格数据被包裹在多层嵌套的 JSON 中（如 {"data": {"tables": [...]}}），需要递归搜索
              </el-alert>
            </el-col>
            <el-col :span="8">
              <el-alert title="字段名不确定" type="success" :closable="false" show-icon>
                LLM 生成的字段名可能不一致（如 tables/table_data/data/result），需要深度搜索而非固定 key
              </el-alert>
            </el-col>
          </el-row>
        </div>
      </el-card>

      <!-- LLM 编排能力 -->
      <el-card class="showcase-card">
        <template #header>
          <div class="card-title">
            <el-tag type="" effect="dark" size="large">编排</el-tag>
            <span>LLM 调用编排与可靠性保障</span>
          </div>
        </template>
        <el-row :gutter="16">
          <el-col :span="8">
            <div class="orchestration-item">
              <el-icon :size="28" color="#409eff"><RefreshRight /></el-icon>
              <h4>指数退避重试</h4>
              <p>首次失败 2s 后重试 → 再次失败 4s 后重试，最多 3 次重试，防止瞬时错误导致整个管线失败</p>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="orchestration-item">
              <el-icon :size="28" color="#67c23a"><FolderOpened /></el-icon>
              <h4>复合缓存机制</h4>
              <p>MD5(图片) + model_name 复合主键，Redis(热)→SQLite(温)→磁盘(冷) 三级缓存，避免重复调用 LLM</p>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="orchestration-item">
              <el-icon :size="28" color="#e6a23c"><TrendCharts /></el-icon>
              <h4>5 级复杂度自适应</h4>
              <p>先评估再处理：根据四维评估结果自动选择最合适的 Prompt 模板和 max_tokens 配置，避免一刀切</p>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- 技术指标 -->
      <el-card class="showcase-card">
        <template #header>
          <div class="card-title">
            <el-tag type="primary" effect="dark" size="large">指标</el-tag>
            <span>Prompt 工程核心指标</span>
          </div>
        </template>
        <el-row :gutter="16">
          <el-col :span="6" v-for="metric in metrics" :key="metric.label">
            <el-statistic :title="metric.label" :value="metric.value" :suffix="metric.suffix" />
          </el-col>
        </el-row>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Setting, RefreshRight, FolderOpened, TrendCharts } from '@element-plus/icons-vue'

const activePrompt = ref('assessment')

const complexityLevels = [
  { name: 'Level 1', className: 'level-1', desc: '极简单', dataRange: '<30', columns: '1列', rows: '~10行', example: '现金日记账（日期/摘要/金额）' },
  { name: 'Level 2', className: 'level-2', desc: '简单', dataRange: '30-50', columns: '≤2列', rows: '~9行', example: '管理费用明细表' },
  { name: 'Level 3A', className: 'level-3a', desc: '中等-紧凑型', dataRange: '50-79', columns: '≤5列', rows: '~11行', example: '贷款五级分类简表' },
  { name: 'Level 3B', className: 'level-3b', desc: '中等-扩展型', dataRange: '80-120', columns: '6-8列', rows: '~19行', example: '贷款五级分类详表' },
  { name: 'Level 4', className: 'level-4', desc: '复杂', dataRange: '>120', columns: '≥9列', rows: '~30行', example: '预期信用减值准备表' },
  { name: 'Level 5', className: 'level-5', desc: '极复杂', dataRange: '>200', columns: '≥12列', rows: '≥30行', example: '集团合并金融资产减值表' }
]

const dimensions = [
  { icon: '📊', name: '横向维度', desc: '指标数量、业务维度、维度类型混合程度' },
  { icon: '🌲', name: '纵向层级', desc: '层级数量、结构类型、汇总深度' },
  { icon: '🧩', name: '结构复杂度', desc: '合并单元格、汇总结构、非结构化元素' },
  { icon: '📏', name: '数据量规模', desc: '单元格总数 × 明细项占比' }
]

const metrics = [
  { label: 'Prompt 模板数', value: '5', suffix: '种' },
  { label: '复杂度等级', value: '5', suffix: '级' },
  { label: 'JSON 容错策略', value: '4', suffix: '种' },
  { label: 'LLM 重试次数', value: '3', suffix: '次（指数退避）' }
]
</script>

<style scoped>
.prompt-showcase-page {
  height: calc(100vh - 50px);
  overflow-y: auto;
  background: #f0f2f5;
  padding: 20px 24px;
}

.page-header {
  text-align: center;
  padding: 24px 0 32px;
}
.page-header h1 {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin: 0 0 8px;
  font-size: 24px;
  color: #303133;
}
.page-subtitle {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.showcase-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.showcase-card {
  border-radius: 12px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

/* Complexity Grid */
.complexity-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.complexity-item {
  padding: 14px 10px;
  border-radius: 10px;
  text-align: center;
  border: 2px solid transparent;
  transition: transform 0.2s;
}
.complexity-item:hover {
  transform: translateY(-2px);
}
.level-badge {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 4px;
}
.level-desc {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}
.level-meta {
  font-size: 11px;
  color: #606266;
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 6px;
}
.level-example {
  font-size: 11px;
  color: #909399;
  font-style: italic;
}

.level-1 { background: #e8f5e9; border-color: #a5d6a7; }
.level-2 { background: #e3f2fd; border-color: #90caf9; }
.level-3a { background: #fff3e0; border-color: #ffcc80; }
.level-3b { background: #fce4ec; border-color: #f48fb1; }
.level-4 { background: #f3e5f5; border-color: #ce93d8; }
.level-5 { background: #ffebee; border-color: #ef9a9a; }

/* Assessment Features */
.assessment-features {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}
.assessment-features h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #303133;
}
.dim-item {
  text-align: center;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}
.dim-icon { font-size: 28px; margin-bottom: 6px; }
.dim-name { font-size: 13px; font-weight: 600; color: #303133; margin-bottom: 4px; }
.dim-desc { font-size: 11px; color: #909399; line-height: 1.4; }

/* Prompt Detail */
.prompt-detail {
  padding: 8px 0;
}
.prompt-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #606266;
}
.prompt-highlight h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #303133;
}
.prompt-highlight ul {
  margin: 0;
  padding-left: 20px;
}
.prompt-highlight li {
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

/* Fallback */
.fallback-strategies {
  padding: 0 40px;
}
.fallback-detail h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #303133;
}

/* Orchestration */
.orchestration-item {
  text-align: center;
  padding: 20px 16px;
  background: #f5f7fa;
  border-radius: 10px;
  height: 100%;
}
.orchestration-item h4 {
  margin: 10px 0 8px;
  font-size: 14px;
  color: #303133;
}
.orchestration-item p {
  margin: 0;
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

/* Responsive */
@media (max-width: 900px) {
  .complexity-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
