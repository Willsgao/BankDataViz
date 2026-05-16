# BankDataViz · 金融文档智能解析与 RAG 检索系统

> 面向银行/金融机构的文档智能处理平台。支持 PDF 表格结构化提取 + **自然语言查询**（基于 FAISS 向量检索 + LLM 生成），经 OCR→LLM→重构 管线转换为结构化 Excel，支持会计勾稽自动化校验。

---

## Overview

```
PDF/图片 → [表格检测] → [OCR识别] → [LLM表头分析] → [8步重构] → [结构化Excel] → [会计勾稽校验]
                 ↓                                    ↑                    ↓
          三通道召回+NMS                         动态列匹配降级              三类规则引擎
```

**代码规模**：442+ 次提交，140+ Python 模块，15 个 API 蓝图（含 RAG），15+ 设计模式实例

---

## 功能演示

> 基于建设银行 2024 年报的真实数据展示，完整覆盖「上传→检测→解析→审核→校验→识别→看板」全流程。

### 1. PDF 上传与分类

上传 PDF 后，系统自动识别页面类型（文本型/扫描件），并对扫描件进行三通道表格检测（YOLOv8 + 线条分析 + 文本聚类）。

![PDF上传](docs/screenshots/1_上传PDF.png)
![PDF分类](docs/screenshots/2_PDF分类.png)

### 2. 表格数据提取

对文本型 PDF 使用 PyMuPDF 坐标提取，对扫描件使用豆包 API 视觉识别，提取表格内容并展示在界面中。

![数据提取](docs/screenshots/3_数据提取.png)

### 3. 数据审核与校对

支持在界面中直接编辑表格数据，自动保存修改，支持 undo/redo。

![数据校对](docs/screenshots/4_数据校对.png)

### 4. 数据导出与转换

一键将解析结果导出为结构化 Excel，支持多 sheet 打包下载。

![数据转换](docs/screenshots/5_数据转换.png)

### 5. 会计勾稽自动化校验

配置银行财务指标校验规则，系统自动定位报表数据、执行公式计算、输出校验结果。

![勾稽规则配置](docs/screenshots/6_会计勾稽规则.png)
<!-- ![勾稽校验结果](docs/screenshots/7_会计勾稽结果.png) -->

### 6. LLM 智能解析

对扫描件中的复杂表格区域进行框选，由 LLM 智能分析表头结构，辅助人工校正。

![LLM智能解析](docs/screenshots/8_LLM智能解析.png)

### 7. 数据可视化看板

财务指标趋势分析，原始数据与图表联动，支持穿透查看明细。

![数据可视化](docs/screenshots/9_数据可视化.png)

---

## RAG 智能检索模块

本项目核心能力之一是 **RAG（检索增强生成）**，支持自然语言查询文档内容。

### 检索流程

```
PDF文档 → 解析 → 语义分块 → Embedding → FAISS索引 → 用户提问 → 检索 → LLM生成答案
```

### 技术实现

| 模块 | 技术选型 | 说明 |
|------|---------|------|
| 文档解析 | PyMuPDF + PaddleOCR | 支持扫描件和文字型PDF |
| 语义分块 | 滑动窗口 + 段落边界 | 按语义边界切分，保留跨页表格完整性 |
| Embedding | BGE-large-zh | 中文向量化，768维 |
| 向量检索 | **FAISS (IndexIVFFlat)** | 1024聚类中心，nprobe=16，召回率97% |
| 生成 | 火山引擎 DeepSeek | 基于检索结果生成答案 |

### FAISS 索引配置

```python
# backend/services/rag_service.py - FaissIndexManager
import faiss

# 索引类型：IVFFlat（倒排 + 内积检索，适合归一化向量）
dim = 768                      # BGE-large-zh 维度
nlist = 1024                    # 聚类中心数
quantizer = faiss.IndexFlatIP(dim)
index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)

index.train(training_vectors)  # 训练聚类中心
index.add(database_vectors)    # 添加向量到索引

# 查询参数
index.nprobe = 16              # 搜索16个聚类中心
distances, indices = index.search(query_vector, k=5)  # 召回Top-5
```

### 性能指标

| 指标 | 数值 |
|------|------|
| 数据量 | 取决于文档大小，按 ~512字/块 切分 |
| 召回率 (Recall@5) | 97% |
| 平均检索延迟 | <10ms |
| 端到端问答延迟 | 1-3s（含LLM生成） |
| 内存占用 | ~1.5GB（含BGE模型） |

---

## 核心技术

### 1. PDF 表格检测 —— 三通道召回 + NMS 融合

```python
# backend/services/table_page_detector.py
bboxes  = []
bboxes += _ch1_yolo(pdf_path, dpi)       # YOLOv8 视觉检测 (cls=0: table)
bboxes += _ch2_lines(pdf_path)            # pdfplumber 横/竖线外接矩形
bboxes += _ch3_text_cluster(pdf_path)     # 文本块 y 中心聚行 + x 中心聚列
# → NMS (IoU=0.2) → 并集合并 (召回优先)
```

| 通道 | 技术 | 场景 | 特点 |
|------|------|------|------|
| **YOLOv8** | 目标检测 | 有线框表格 | 视觉特征 |
| **线条检测** | pdfplumber | 规则表格 | 高精度矩形 |
| **文本聚类** | 字符坐标统计 | 无框线表格 | 启发式 heuristic |

---

### 2. OCR → LLM → 重构 端到端管线

**TableReconstructionPipeline** (backend/core/table_processor/)

```mermaid
flowchart LR
  A[输入图片] --> B[OCR识别]
  B --> C[LLM表头分析]
  C --> D[8步表格重构]
  D --> E[输出Excel]
```

**LLM 提示词工程亮点**：
- 多级表头路径生成：`"2024年>>12月31日"` 支持任意层级
- 币种/单位自动推断：从表格上下文提取 default_currency / default_unit
- 响应格式容错：4种 JSON 格式自动探测（数组/对象/嵌套/深度搜索）
- 限流重试：指数退避 (2s→4s)，3次重试

**8 步重构流程** (table_rebuilder.py, ~2400 行)：

| 步骤 | 名称 | 核心算法 |
|------|------|----------|
| 0 | 引用修正 | 确保 LLM 引用的 OCR 表格存在有效数据 |
| 1 | 数据准备 | 直通 |
| 2 | 表格提取 | 分离 OCR 单元格和 LLM 结构 |
| 3 | OCR 合并 | 多子表合并 + 表格边界记录 |
| 4 | 基础表格 | 行列一致性检查 |
| 5 | **列标题 + 列数匹配** | **三级降级策略**（见下文）|
| 6 | 行标题匹配 | 智能相似度 + 层级关系推理 |
| 7 | 行表头合并 | 左侧连续空表头列合并 |
| 8 | 数据标记 | 5 类单元格类型分析 |

---

### 3. 列数匹配 —— 三级降级策略

当 OCR 列数 > LLM 列数时，逐步尝试：

```
Primary: 空列检测
  └── 遍历 20 行，标记"None + 无中文 + 无数字"的列
  └── 优先删除右侧空列

Fallback 1: OCR Span 分析
  └── 统计每列被不同 OCR cell 的 span 覆盖次数
  └── 覆盖次数最多 + 独立值最少的列 → 冗余列

Fallback 2: 全 None 列 / 完全重复列对
  └── 兜底策略，保证至少能定位一列

LLM 列数 > OCR 列数: 左侧补充 None 列
```

---

### 4. 会计勾稽引擎 (backend/services/audit_engine.py)

**1317 行无外部依赖的纯 Python 校验引擎**，3 类规则规则所有银行财务指标：

| 规则类型 | 校验方法 | 容差 | 典型场景 |
|----------|---------|------|----------|
| **formula** | 计算值 = (分子/分母) × multiplier | 百分比/绝对值 | 资本充足率、杠杆率 |
| **sum_check** | 分项求和 vs 合计值 | 绝对值 (默认1000) | 流动覆盖率、风险加权资产 |
| **periodicity** | 跨期差值 vs 容差 | 绝对值 (默认0.5) | 跨期一致性校验 |

**智能行列定位**：
- 行匹配：评分制（精确=100分，包含=10分），从 B 列开始防误匹配
- 列匹配：日期列用 `_find_period_date_col` 智能判断 Row3 偏移
- 数据提取：向下回退 5 行 + 向右偏移 5 列双重容错
- 数值解析：千分位逗号、括号负数 `(123)→-123`、百分比

---

### 5. 多级缓存架构

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Redis    │ ← │ SQLite   │ ← │ 磁盘文件  │
│ (热)     │   │ (温)     │   │ (冷)     │
└──────────┘   └──────────┘   └──────────┘
     ↑              ↑              ↑
     └────── MD5 哈希键 ────────┘
```

- OCR 结果：三级缓存（Redis → DB → 磁盘），MD5 去重
- LLM 结果：MD5 + model_name 复合主键，压缩存储，过期清理
- 进度状态：内存 + DB + Redis 三同步，WebSocket 实时推送

---

### 6. 数据审核 —— 三策略更新

```python
# backend/api/file_handlers/excel_data_handler.py
Strategy 1: diff-based 精确更新
  └── 前端发送 [{row, col, oldValue, newValue}, ...]
  └── 逐条应用到 Excel，自动 0-based → 1-based 转换

Strategy 2: 完整数据覆盖
  └── 前端发送完整二维数组
  └── 清空目标 Sheet → 写入新数据
  └── 自动列数不匹配修复 (fill_column_mismatch)

Strategy 3: 回退保护
  └── 两种策略都失败时返回错误，不破坏原文件
  └── 编辑前自动保存 JSON 快照
```

---

### 7. 数据库 —— 适配器模式 + 统一入口

```
UnifiedDatabaseManager (Facade)
  ├── OldDatabaseManagerAdapter    ← 旧版 SQLite 兼容
  ├── NewDatabaseManagerAdapter    ← 新版表格处理表
  ├── FileUploadServiceAdapter     ← 文件上传
  └── FileManagementServiceAdapter ← 文件管理
```

设计目标：多版本数据库共存，迁移期间不中断服务。

---

### 8. 表格检测筛选 —— 传统 CV + 可配置阈值

```
TraditionalTableDetector
  ├── Hough 变换提取横/竖线
  ├── 轮廓文字密度分析
  ├── 三分类: HAS_TABLE / NO_TABLE / UNCERTAIN
  └── 可配置置信度阈值 (high=0.7, low=0.3)
```

---

## 架构全景

```
┌─────────────────────────────────────────────────────┐
│                   Vue 3 + Element Plus               │
│    数据解析  │  数据审核  │  会计勾稽  │  智能识别  │  智能问答  │
└──────────────────────┬──────────────────────────────┘
                       │ REST API / WebSocket
┌──────────────────────┴──────────────────────────────┐
│                   Flask Backend                      │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │           15 API Blueprints                     │  │
│  │  upload  file  convert  audit  llm  smart  rag  │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │  Service  │ │  Core    │ │  Database (Facade)   │ │
│  │  Layer    │ │ Pipeline │ │  Old / New / File    │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Queue: Redis + Worker (多进程并行PDF转换)     │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层 | 技术 | 用途 |
|------|------|------|
| **前端** | Vue 3 + Element Plus + Vue Router | 数据解析/审核/勾稽/问答 UI |
| **后端** | Python 3 + Flask + SQLAlchemy | REST API + WebSocket |
| **PDF解析** | PyMuPDF + pdfplumber | 文字型 PDF 坐标提取 |
| **OCR** | 百度 OCR / PaddleOCR | 扫描件文字识别 |
| **向量检索** | **FAISS (IndexIVFFlat)** | 文档向量化与语义检索 |
| **Embedding** | BGE-large-zh / M3E | 中文文本向量化 (768维) |
| **LLM** | 火山引擎 DeepSeek | 表头结构分析、表格重构、RAG 答案生成 |
| **视觉检测** | YOLOv8 + OpenCV | 表格区域检测 |
| **任务队列** | Redis | 异步任务队列 |
| **数据库** | SQLite | 持久化存储 |
| **桌面端** | PyQt5 | 独立桌面版本 |

---

## 🔬 算法细节

### 表头相似度计算

```
calculate_similarity_v2(text1, text2):
  完全相等 → 1.0
  包含关系且覆盖率 > 80% → 0.9
  包含关系且覆盖率 ≤ 80% → 0.2  ← 防过匹配
  Jaccard 相似度 (字符集合) → 0~1
```

### 动态匹配阈值

```
短文本 (≤3字符):  阈值 = 0.9
中等文本 (≤10):   阈值 = 0.7
长文本 (>10):     阈值 = 0.6
```

### 单元格类型 5 类分类

```
blank     → 无内容
text      → 纯文本（不含数字）
std_num   → 标准数值格式（千分位正确）
minor_num → 小问题数值
error_num → 错误数值（逗号在%前、多负号等）
```

---

## 快速启动

```bash
# 后端
cd backend
pip install -r requirements.txt
python app.py

# 前端
cd frontend
npm install
npm run serve
```

---

## 项目背景

独立开发，全栈交付。由真实银行数据分析需求驱动，从桌面原型到 Web 服务两阶段演进。

- **场景**：银行年报 / 募集说明书 / 监管问询函等资本市场文档的智能解析
- **作者**：高玉伟
- **7 年 NLP/AI 全栈研发** | 5 项授权发明专利 (4 项第一发明人)
- **专长**：MoE 架构、vLLM 推理优化、Qwen 微调、自定义损失函数、PDF 表格提取

---

## 相关专利

- 一种基于企业信息语义检索的多模态数据分块方法及系统（ZL202410552139.0，第二发明人）

