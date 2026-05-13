# DocuVista · 金融文档智能解析平台

> 面向银行/金融机构的文档智能处理平台，从年报/募集说明书中自动提取财务表格，支持勾稽关系校验，输出结构化 Excel 数据。
>
> *由银行数据分析团队的**真实业务需求**驱动开发*

---

## 🏗️ 平台全景

```
┌──────────────────────────────────────────────────────────────────┐
│                         DocuVista                               │
├──────────┬──────────┬──────────┬──────────┬─────────────────────┤
│  数据解析  │  数据审核  │  会计勾稽  │  智能识别  │     数据看板       │
│ (PDF→Excel)│ (表格校正) │ (合规校验) │ (框选识别) │ (图表/文档检索)    │
└──────────┴──────────┴──────────┴──────────┴─────────────────────┘
```

---

## ✨ 核心功能

### 🔍 会计勾稽验证（Audit）

银行财务合规检查工具，支持自定义校验规则与自动字段匹配。

```mermaid
flowchart LR
  A[选择档案] --> B[勾选规则]
  B --> C[自动匹配Sheet字段]
  C --> D[执行勾稽校验]
  D --> E[通过/警告/失败]
```

- **预置规则**：资本充足率、杠杆率、风险加权资产、流动性覆盖率、净稳定资金比例、跨期一致性等
- **规则类型**：`公式校验`（=）、`汇总验证`（Σ）、`跨期对比`（↔）
- **自动映射**：智能分析 Sheet 表头与规则字段的对应关系，自动推荐匹配
- **字段确认**：自动检测不确定的字段映射，提示人工确认后再执行
- **结果展示**：通过率统计 + 逐条明细，支持按状态筛选（通过/警告/失败）
- **详情追溯**：每条校验结果可查看实际值、理论值、差值及详细说明

### 🖼️ 智能识别（Smart Recognize）

面向扫描件/复杂表格的人工辅助识别工具。

- 上传文件 → 自动检测表格区域
- 拖拽调整区域边界 → 框选确认
- 批量发送至 DeepSeek 识别
- 识别结果确认后保存为 Excel

### 📄 数据解析（PDF → Excel）

从金融文档 PDF 中提取表格数据的两套技术路线：

| 方案 | 适用场景 | 技术栈 | 特点 |
|------|---------|--------|------|
| **桌面版** | 文字型PDF | PyMuPDF + pdfplumber | 纯CPU，5秒100页，零依赖 |
| **Web版** | 扫描件/复杂表格 | OCR + DeepSeek LLM | 高精度，支持复杂格式 |

### ✅ 数据审核（表格校正）

- 逐页/逐表浏览提取结果
- 人工修正表格行列错误
- 确认后写入数据库

### 📊 数据看板

- **图表看板**：提取结果的可视化统计
- **文档检索**：按 Excel 内容搜索已处理的文档

---

## 🧩 模块架构

```
DocuVista/
├── frontend/                          # Vue.js 前端
│   └── src/
│       ├── views/
│       │   ├── TwoColumnPage.vue      # 数据解析
│       │   ├── ThreeColumnPage.vue    # 数据审核
│       │   ├── AuditPage.vue          # 会计勾稽 ← 核心模块
│       │   ├── SmartRecognizePage.vue # 智能识别 ← 核心模块
│       │   ├── BankDashboardPage.vue  # 数据看板-图表
│       │   ├── BankDataPage.vue       # 数据看板-文档
│       │   ├── LoginPage.vue          # 登录
│       │   └── AdminManagement.vue    # 管理员管理
│       └── router/index.js            # 路由 & 权限守卫
│
├── backend/                           # Flask 后端
│   ├── app.py                         # 应用入口
│   ├── api/
│   │   ├── audit.py                   # 会计勾稽 API
│   │   ├── smart_recognize.py         # 智能识别 API
│   │   ├── convert_apis.py            # PDF解析 API
│   │   ├── bank_data_api.py           # 数据看板 API
│   │   └── ...
│   ├── services/
│   │   ├── audit_engine.py            # 勾稽校验引擎
│   │   ├── dal/                       # 数据访问层
│   │   ├── llm/                       # LLM 服务
│   │   └── ...
│   ├── core/
│   │   ├── table_processor/           # 表格处理管线
│   │   │   ├── end_to_end_pipeline.py # OCR→LLM→重构 端到端管线
│   │   │   ├── table_rebuilder.py     # 表格重构（7步流程）
│   │   │   ├── llm_table_structure_parser.py  # LLM表头解析
│   │   │   └── ...
│   │   └── incremental_processor/     # 增量处理
│   ├── configs/                       # 配置文件
│   ├── database/                      # 数据库模型
│   └── utils/                         # 工具函数
│
└── docs/                              # 文档
    └── screenshots/                   # 效果截图
```

---

## 🛠️ 技术栈

| 层 | 技术 |
|------|------|
| **前端** | Vue 3 + Element Plus + Vue Router |
| **后端** | Python + Flask + SQLAlchemy |
| **数据库** | SQLite |
| **PDF解析** | PyMuPDF / pdfplumber / PyPDF2 |
| **OCR** | PaddleOCR |
| **LLM** | DeepSeek API |
| **任务队列** | Redis |
| **桌面版** | PyQt5 |

---

## ⚙️ 快速启动

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 前端启动

```bash
cd frontend
npm install
npm run serve
```

### 桌面版启动

```bash
# 独立仓库: pdf_table_extractor
pip install -r requirements.txt
python main.py
```

---

## 📸 效果截图

> *（你的截图放这里，建议截取「会计勾稽」结果页的统计卡片+明细列表）*

```
screenshots/
├── audit-result.png       # 勾稽验证结果
├── smart-recognize.png    # 智能识别界面
└── upload-pipeline.png    # 整体工作流
```

---

## 📬 关于

独立开发，全栈交付。由银行数据分析团队的真实需求驱动，从桌面原型到 Web 服务两阶段演进。

- **作者**：高玉伟
- **邮箱**：willsgao@163.com
- **场景**：银行年报 / 募集说明书 / 监管问询函等资本市场文档的智能解析
