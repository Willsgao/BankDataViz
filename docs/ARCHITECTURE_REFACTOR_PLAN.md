# BankDataViz 工业级 Agent 平台架构改造方案

> **文档性质**：技术方案  
> **版本**：v1.0  
> **日期**：2026-06-13  
> **原则**：渐进式演进，不推倒重来，在当前工作代码上逐层加固

---

## 目录

- [一、总体架构：8 层分层设计](#一总体架构8-层分层设计)
- [二、L1 基础设施层](#二l1-基础设施层)
- [三、L2 数据处理管线层](#三l2-数据处理管线层)
- [四、L3 知识引擎层](#四l3-知识引擎层)
- [五、L4 Agent 框架核心层](#五l4-agent-框架核心层)
- [六、L5 编排与工作流层](#六l5-编排与工作流层)
- [七、L6 安全与治理层](#七l6-安全与治理层)
- [八、L7 API 网关层](#八l7-api-网关层)
- [九、L8 用户界面层](#九l8-用户界面层)
- [十、分阶段实施路线图](#十分阶段实施路线图)
- [十一、最终目录结构总览](#十一最终目录结构总览)
- [十二、关键技术决策总结](#十二关键技术决策总结)
- [十三、风险与应对](#十三风险与应对)

---

## 一、总体架构：8 层分层设计

```
┌─────────────────────────────────────────────────────────────┐
│  L8  用户界面层                                              │
│  Vue 3 SPA — Agent Playground / 管理控制台 / 监控大盘        │
├─────────────────────────────────────────────────────────────┤
│  L7  API 网关层                                              │
│  REST + SSE + WebSocket — 认证鉴权 / 限流 / 路由 / 审计      │
├─────────────────────────────────────────────────────────────┤
│  L6  安全与治理层                                            │
│  Tool RBAC 权限引擎 / 输入净化 / 速率限制 / 审计追踪 / 脱敏   │
├─────────────────────────────────────────────────────────────┤
│  L5  编排与工作流层                                          │
│  DAG 工作流引擎 / 多Agent并行调度 / 条件路由 / 子任务委派     │
├─────────────────────────────────────────────────────────────┤
│  L4  Agent 框架核心层                                        │
│  Tool / Agent / ReActAgent / PlanAgent                      │
│  LLM Provider 抽象 / Memory 系统 / 熔断降级                  │
├─────────────────────────────────────────────────────────────┤
│  L3  知识引擎层                                              │
│  混合检索 (向量+BM25+重排序) / FAISS→Milvus 多级索引         │
├─────────────────────────────────────────────────────────────┤
│  L2  数据处理管线层                                          │
│  文档加载 → 文本清洗 → 结构感知分块 → 元数据提取 → OCR 反哺   │
├─────────────────────────────────────────────────────────────┤
│  L1  基础设施层                                              │
│  异步任务队列 / 结构化日志 / 配置中心 / Metrics+Tracing       │
└─────────────────────────────────────────────────────────────┘
```

**数据流向**：L1（基础设施）→ L2（数据管线处理）→ L3（知识引擎索引）→ 被 L4（Agent 框架）消费 → 经 L5（编排）调度 → 通过 L6（安全）守卫 → 由 L7（API 网关）暴露 → 在 L8（前端界面）呈现。

---

## 二、L1：基础设施层

> **定位**：所有上层模块的运行底座，必须优先建设。

### 目录结构

```
backend/infrastructure/
├── config/
│   ├── settings.py          # Pydantic Settings 统一配置中心
│   ├── agent_settings.py    # Agent 行为配置（超时/重试/max_steps）
│   └── model_settings.py    # LLM 模型注册表（多模型配置）
├── logging/
│   ├── logger.py            # structlog 结构化日志
│   ├── middleware.py         # Flask 中间件：每请求自动注入 trace_id
│   └── formatters.py        # JSON/Console 双格式
├── async_tasks/
│   ├── celery_app.py        # Celery 实例 + Redis broker 配置
│   ├── tasks.py             # Agent 任务定义（parse_task/analyze_task）
│   └── progress.py          # 进度追踪 + SSE 推送
├── metrics/
│   ├── collector.py         # Prometheus metrics（tool调用量/延迟/成功率）
│   └── health.py            # 健康检查端点 /health /ready
└── connection_pool.py       # DB/Redis 连接池管理
```

### 技术选型

| 组件 | 选型 | 理由 |
|---|---|---|
| 配置中心 | **Pydantic Settings** | 支持 `.env` / 环境变量 / YAML，类型安全，多环境切换 |
| 日志系统 | **structlog** | 结构化 JSON，自动绑定 trace_id，无缝对接 ELK |
| 异步任务 | **Celery + Redis** | 已有 Redis 基础设施，社区最成熟的 Python 任务队列 |
| 指标采集 | **prometheus_client** | Prometheus 标准格式，Grafana 直接消费 |
| 链路追踪 | **OpenTelemetry** | 跨服务追踪标准，轻量 SDK，自动采集 |

### 关键设计

**Pydantic Settings 配置中心**：

```python
# settings.py — 环境差异化配置，类型安全
class Settings(BaseSettings):
    # 环境
    ENV: str = "development"

    # 数据库
    DATABASE_URL: str = "sqlite:///bank_data.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Agent 默认配置
    AGENT_MAX_STEPS: int = 8
    AGENT_TIMEOUT_SECONDS: int = 120
    AGENT_MAX_RETRIES: int = 3
    AGENT_VERBOSE: bool = False

    # LLM 配置
    LLM_DEFAULT_MODEL: str = "deepseek-chat"
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.0

    # 安全
    JWT_SECRET_KEY: str = "change-me-in-production"
    RATE_LIMIT_PER_MINUTE: int = 60

    # 可观测性
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | console

    class Config:
        env_file = ".env"
        env_prefix = "APP_"
```

**structlog 结构化日志**：

```python
# logger.py — 无侵入式迁移，渐进替换所有 print()
class StructLogger:
    """结构化日志，每请求自动绑定 trace_id"""
    def __init__(self):
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        self.logger = structlog.get_logger(__name__)

    def bind(self, **kwargs):
        return self.logger.bind(**kwargs)

logger = StructLogger()
```

**Celery 异步任务封装**：

```python
# tasks.py — Agent 长耗时任务异步化
@celery_app.task(bind=True, max_retries=3)
def run_agent_parse(self, task_id: str, image_path: str, options: dict):
    self.update_state(state="PROGRESS", meta={"step": "ocr", "progress": 20})
    # ... 执行 Agent 解析流程
```

---

## 三、L2：数据处理管线层

> **定位**：RAG 质量的根基。解决当前"原始文本→直接分块→直接向量化"无清洗的致命缺陷。

### 目录结构

```
backend/data_pipeline/
├── ingestion/
│   ├── loader.py            # 统一文档加载器（PDF/图片/文本/Excel）
│   ├── pdf_extractor.py     # PyMuPDF 文字型提取
│   ├── ocr_extractor.py     # 扫描件 OCR → 文本反哺给 RAG
│   └── type_detector.py     # 文档类型自动检测（文字型/扫描件/混合）
├── cleaning/
│   ├── normalizer.py        # 全角→半角、空白统一、特殊字符清理
│   ├── noise_filter.py      # 页眉/页脚/页码/水印过滤
│   ├── table_dedup.py       # 表格区域文本去重
│   └── pipeline.py          # 清洗管线：可插拔的 Processor 链
├── chunking/
│   ├── semantic_chunker.py  # 语义边界分块（现有，升级）
│   ├── structural_chunker.py # 按文档结构分块（章节/表格/段落）
│   ├── hybrid_chunker.py    # 混合策略：结构优先→语义兜底
│   └── overlap_manager.py   # 智能重叠：表格区域高重叠，正文低重叠
└── metadata/
    ├── extractor.py         # 提取文档元数据（银行名/年份/报表类型）
    └── enricher.py          # 元数据增强（关联数据库中的银行信息）
```

### 关键设计

**可插拔的清洗管线**：

```python
class CleaningPipeline:
    """职责链模式的文本清洗管线"""
    def __init__(self, processors: List[TextProcessor] = None):
        self.processors = processors or [
            WhitespaceNormalizer(),     # 空白符归一化（连续空行→单空行）
            FullwidthConverter(),       # 全角字母/数字→半角
            PageNumberFilter(),         # 页码/页眉/页脚过滤
            HeaderFooterFilter(),       # 基于频率的页眉页脚检测
            TableDedupProcessor(),      # 表格文本去重（与纯文本重复的内容）
            SpecialCharCleaner(),       # PDF 提取常见乱码字符清理
            FinancialNumberNormalizer() # 金融数字格式统一
        ]

    def clean(self, text: str, metadata: dict = None) -> str:
        for processor in self.processors:
            text = processor.process(text, metadata or {})
        return text

class TextProcessor(ABC):
    """清洗处理器抽象基类"""
    @abstractmethod
    def process(self, text: str, metadata: dict) -> str: ...
```

**扫描件 OCR 文本反哺 RAG**：

> 核心问题：当前扫描件 PDF 通过 OCR 表格管线（TableParsingAgent）处理后，OCR 结果没有反哺到 RAG 索引，导致扫描件内容不可检索。
>
> 解决方案：OCR 完成后，自动将识别的文本通过 `CleaningPipeline` 清洗后流入 RAG 索引。

**结构感知混合分块器**：

```python
class HybridChunker:
    """混合分块：结构优先→语义兜底"""

    def chunk(self, text: str, doc_structure: dict) -> List[Chunk]:
        # 1. 按文档结构边界切分（章节标题、表格、段落）
        structural_chunks = self.structural_chunker.split(text, doc_structure)

        # 2. 对过大块再用语义边界拆分
        final_chunks = []
        for chunk in structural_chunks:
            if len(chunk.text) > self.max_chunk_size:
                sub_chunks = self.semantic_chunker.split(chunk.text)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        # 3. 根据内容类型调整重叠（表格区域更高重叠）
        for chunk in final_chunks:
            chunk.overlap = self.calculate_overlap(chunk.content_type)

        return final_chunks
```

---

## 四、L3：知识引擎层

> **定位**：统一管理向量化、索引、检索全流程。当前 FAISS 可行但需要增强混合检索和增量更新能力。

### 目录结构

```
backend/knowledge_engine/
├── embedding/
│   ├── bge_embedder.py      # BGE-large-zh（现有，封装为标准接口）
│   ├── embedder_registry.py # 多 Embedding 模型注册
│   └── batch_encoder.py     # 大批量异步编码
├── vector_store/
│   ├── base.py              # 统一 VectorStore 抽象接口
│   ├── faiss_store.py       # FAISS IndexIVFFlat（现有，升级）
│   └── milvus_store.py      # Milvus 迁移适配器（Phase 3）
├── retrieval/
│   ├── vector_searcher.py   # 纯向量检索
│   ├── bm25_searcher.py     # BM25 关键词检索
│   ├── hybrid_searcher.py   # 混合检索 + RRF 融合排序
│   └── reranker.py          # Cross-Encoder 重排序（BGE-Reranker）
├── index_manager.py         # 索引生命周期（构建/增量更新/版本管理）
└── knowledge_graph/         # 知识图谱（Phase 5，银行→指标→年份关系）
    ├── entity_extractor.py
    └── graph_builder.py
```

### 关键设计

**统一 VectorStore 接口**（为 FAISS→Milvus 平滑迁移做准备）：

```python
class BaseVectorStore(ABC):
    """统一向量存储接口，FAISS 和 Milvus 均实现此接口"""

    @abstractmethod
    def add_vectors(self, vectors: np.ndarray, metadata: List[dict]) -> None: ...

    @abstractmethod
    def search(self, query_vector: np.ndarray, top_k: int = 10,
               filters: dict = None) -> List[SearchResult]: ...

    @abstractmethod
    def delete(self, doc_id: str) -> None: ...

    @abstractmethod
    def save(self, path: str) -> None: ...

    @abstractmethod
    def load(self, path: str) -> None: ...
```

**混合检索（向量 + BM25 + RRF 融合）**：

```python
class HybridSearcher:
    """向量检索 + BM25 关键词检索 → RRF 融合 → 重排序"""

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        # 1. 向量检索（语义匹配）
        query_vec = self.embedder.encode_query(query)
        vec_results = self.vector_store.search(query_vec, k=top_k * 2)

        # 2. BM25 关键词检索（精确匹配，金融数字查询至关重要）
        bm25_results = self.bm25_index.search(query, k=top_k * 2)

        # 3. RRF (Reciprocal Rank Fusion) 融合
        merged = self._rrf_fusion(vec_results, bm25_results, k=60)

        # 4. Cross-Encoder 重排序（可选，高精度场景）
        if self.reranker:
            merged = self.reranker.rerank(query, merged[:top_k * 2])

        return merged[:top_k]

    def _rrf_fusion(self, results_a: list, results_b: list, k: int = 60) -> list:
        """RRF 算法：对来自不同检索器的结果进行公平融合"""
        scores = {}
        for rank, item in enumerate(results_a, start=1):
            scores[item.id] = scores.get(item.id, 0) + 1 / (k + rank)
        for rank, item in enumerate(results_b, start=1):
            scores[item.id] = scores.get(item.id, 0) + 1 / (k + rank)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

> **为什么需要 BM25**：金融场景大量查询是数值/代码查询（如"2023 年工商银行净利润"），纯向量语义检索对此类精确匹配效果差。BM25 可精准命中关键词，向量检索补全语义，两者是互补关系。

**增量索引更新**：

> 当前：每次新文档需要全量重建索引。  
> 改进：新文档追加向量到 FAISS 索引，元数据追加到 SQLite，无需重建已有数据。  
> 实现方式：FAISS 的 `IndexIVFFlat` 支持 `add()` 增量插入，同时维护 `doc_id → vector_ids` 映射表，支持按文档删除。

---

## 五、L4：Agent 框架核心层

> **定位**：在现有 `backend/harness/` 基础上硬化。保持接口不变，增加 LLM Provider、Memory、Resilience 三大模块。

### 目录结构

```
backend/agent_framework/
├── core/
│   ├── tool.py              # Tool / ToolResult（现有增强：版本号/健康检查/成本标记）
│   ├── agent.py             # Agent / ReActAgent（现有增强：PlanAgent）
│   ├── action.py            # Action / Observation（现有）
│   └── registry.py          # ToolRegistry（现有增强：动态加载/热启用禁用）
├── providers/               # ★ 新增：LLM Provider 抽象层
│   ├── base.py              # BaseLLMProvider 抽象接口
│   ├── deepseek.py          # DeepSeek Provider
│   ├── doubao.py            # 豆包 Vision Provider
│   ├── openai_compat.py     # OpenAI 兼容通用 Provider
│   └── router.py            # 模型路由器：按任务类型/成本自动选模型
├── memory/                  # ★ 新增：记忆系统
│   ├── base.py              # Memory 抽象
│   ├── short_term.py        # 短期记忆（当前会话上下文窗口）
│   ├── long_term.py         # 长期记忆（向量化存储历史交互）
│   ├── episodic.py          # 情景记忆（完整任务执行记录）
│   └── manager.py           # 记忆管理器（协调三种记忆）
├── resilience/              # ★ 新增：韧性机制
│   ├── circuit_breaker.py   # 熔断器（外部服务连续失败→快速失败）
│   ├── retry_policy.py      # 可配置重试策略（指数退避/抖动）
│   ├── fallback_chain.py    # 降级链（主→备→兜底）
│   └── dead_letter.py       # 死信队列（持久化失败任务供排查）
├── verification/            # 现有，增强
│   ├── engine.py            # RuleEngine（现有）
│   ├── rules.py             # 内置规则（现有增强：自动修复规则）
│   └── auto_fix.py          # ★ 新增：验证失败→自动修复策略
├── plan_agent.py            # ★ 新增：Plan-Execute Agent（先规划再执行）
└── agent_factory.py         # ★ 新增：Agent 工厂（声明式配置构建 Agent 实例）
```

### 关键设计

**LLM Provider 抽象接口**：

```python
@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    cost: float
    latency_ms: float

class BaseLLMProvider(ABC):
    """统一 LLM 调用接口，所有模型 Provider 实现此接口"""

    @abstractmethod
    async def chat(self, messages: List[dict], **kwargs) -> LLMResponse:
        """同步对话，返回完整响应 + 用量成本"""
        ...

    @abstractmethod
    async def chat_stream(self, messages: List[dict], **kwargs) -> AsyncIterator[str]:
        """流式对话，yield token"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def cost_per_1k_tokens(self) -> float: ...

class ModelRouter:
    """智能模型路由：
    - 简单意图（格式转换、命名）→ 便宜模型 (e.g. deepseek-chat)
    - 复杂推理（数据分析）→ 强模型 (e.g. deepseek-reasoner)
    - 视觉任务 → 豆包 Vision
    - 预算受限 → 自动降级到更便宜的模型
    """

    def route(self, task_type: str, complexity: str = "medium",
              max_cost: float = 0.01) -> BaseLLMProvider:
        candidates = self.registry.filter(task_type=task_type)
        # 按 budget 排序，选满足需求且最低成本的
        return min(
            (p for p in candidates if p.cost_per_1k_tokens <= max_cost),
            key=lambda p: p.cost_per_1k_tokens,
            default=candidates[0]
        )
```

**三级记忆系统**：

```python
class MemoryManager:
    """三级记忆协调器"""

    def __init__(self):
        self.short_term = ShortTermMemory(max_tokens=8000)   # 当前对话窗口
        self.long_term = LongTermMemory(vector_store)         # 向量化历史
        self.episodic = EpisodicMemory(sqlite)               # 完整任务记录

    def retrieve_context(self, task: str, user_id: str) -> str:
        """构建 Agent 的完整上下文"""
        parts = []

        # 1. 短期：最近 N 轮对话
        recent = self.short_term.get_recent(user_id, n=5)
        if recent:
            parts.append(f"[近期对话]\n{recent}")

        # 2. 长期：相似历史任务的结论
        similar = self.long_term.search(task, top_k=3)
        if similar:
            parts.append(f"[历史相关经验]\n{similar}")

        # 3. 情景：上次同类任务的成功执行链
        episode = self.episodic.find_similar(task_type="analysis", user_id=user_id)
        if episode:
            parts.append(f"[上次成功策略]\n工具调用链: {episode.action_chain}")

        return "\n---\n".join(parts)

    def commit(self, task: str, result: str, actions: list, user_id: str):
        """任务完成后，持久化到短期、长期、情景记忆"""
        self.short_term.add(user_id, task, result)
        self.long_term.index(task, result)         # 向量化存入
        self.episodic.save(user_id, task, actions)  # 完整执行链
```

**熔断器（Circuit Breaker）**：

```python
@dataclass
class CircuitBreaker:
    """熔断器：外部服务连续失败超过阈值→快速失败，避免雪崩"""
    name: str
    failure_threshold: int = 5      # 连续失败 N 次后熔断
    recovery_timeout: float = 60.0  # 熔断后 N 秒尝试半开
    half_open_max: int = 3          # 半开状态最多尝试 N 次

    state: str = "CLOSED"           # CLOSED | OPEN | HALF_OPEN
    failure_count: int = 0
    last_failure_time: float = 0.0

    def call(self, func: Callable, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"  # 尝试恢复
            else:
                raise CircuitBreakerOpenError(f"熔断器 {self.name} 已打开")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"     # 恢复成功
                self.failure_count = 0
            return result
        except Exception:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise
```

**Tool 增强（版本 & 健康检查）**：

```python
class Tool(ABC):
    """增强版 Tool 基类"""
    name: str
    version: str = "1.0.0"          # ★ 新增：版本号
    estimated_cost: float = 0.0      # ★ 新增：预估成本
    required_permissions: List[str] = []  # ★ 新增：所需权限

    def health_check(self) -> bool:
        """★ 新增：工具健康检查（OCR 服务是否可用等）"""
        try:
            return self._do_health_check()
        except:
            return False

    @abstractmethod
    def _do_health_check(self) -> bool: ...
```

**Plan-Execute Agent**：

```python
class PlanAgent(Agent):
    """Plan-Execute 模式：先生成完整执行计划，再逐步执行。
    适用于复杂多步骤任务，比 ReAct 更可控。

    流程：
    1. Plan：LLM 生成结构化执行计划 [{"step": 1, "tool": "...", "purpose": "..."}, ...]
    2. Verify Plan：RuleEngine 检查计划合理性
    3. Execute：按计划逐步调用 Tool
    4. Verify Each Step：每步完成后验证中间结果
    5. Adapt：如果某步失败，重新规划剩余步骤
    """

    def plan(self, task: str, context: dict) -> List[PlanStep]:
        """生成执行计划"""
        ...

    def execute_plan(self, plan: List[PlanStep]) -> PlanResult:
        """按计划执行，支持动态调整"""
        ...
```

---

## 六、L5：编排与工作流层

> **定位**：从当前的串行 Orchestrator 升级为声明式 DAG 工作流引擎，支持并行执行和条件路由。

### 目录结构

```
backend/orchestration/
├── workflow/
│   ├── dag_engine.py        # DAG 工作流引擎（有向无环图）
│   ├── node.py              # 工作流节点抽象
│   ├── conditions.py        # 条件分支（if/then/else）
│   ├── parallel.py          # 并行执行（asyncio/ThreadPool）
│   └── state_machine.py     # 任务状态机
├── orchestrator.py          # 多Agent编排器（现有，升级为支持 DAG 模式）
├── scheduler.py             # 任务调度器（优先级队列/定时任务）
├── context_bus.py           # 上下文总线（Agent间数据共享）
└── delegation.py            # Agent 委派（主Agent→子Agent任务分发）
```

### 关键设计

**DAG 工作流声明**：

```python
@dataclass
class WorkflowNode:
    id: str
    agent_type: str                # Agent 类型标识
    tool_chain: List[str]          # 要执行的 Tool 序列
    depends_on: List[str] = []     # 依赖的前置节点 ID
    condition: Optional[Callable] = None   # 条件执行判断
    on_failure: str = "abort"      # abort | skip | retry | fallback
    max_retries: int = 1
    timeout_seconds: int = 120

class DAGWorkflow:
    """声明式 DAG 工作流引擎"""

    def __init__(self, nodes: List[WorkflowNode]):
        self.nodes = nodes
        self._validate_dag()  # 拓扑排序 + 环检测

    async def execute(self, task: str, context: dict) -> WorkflowResult:
        # 1. 拓扑排序 → 确定执行层级
        levels = self._topological_sort()

        # 2. 按层级并行执行（同层无依赖的节点可并行）
        for level_batch in levels:
            tasks = [
                self._run_node(node, task, context)
                for node in level_batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 3. 处理各节点结果，合并上下文
            for node, result in zip(level_batch, results):
                if isinstance(result, Exception):
                    self._handle_failure(node, result)
                else:
                    context[f"node_{node.id}"] = result

        return WorkflowResult(success=True, context=context)
```

**任务状态机**：

```
QUEUED → RUNNING → VERIFYING → COMPLETED
                     ↓             ↑
                 RETRYING ────────┘
                     ↓
                  FAILED
                     ↓
              DEAD_LETTER（死信队列）
```

---

## 七、L6：安全与治理层

> **定位**：当前 Agent 没有任何权限控制。在金融行业场景，这是不可接受的安全缺陷。

### 目录结构

```
backend/security/
├── auth/
│   ├── jwt_handler.py       # JWT 签发/验证（增强现有）
│   └── session_manager.py   # Agent 会话管理
├── permissions/
│   ├── rbac_engine.py       # 基于 Casbin 的 RBAC 引擎
│   ├── tool_policy.py       # Tool 级权限策略定义
│   └── policy_loader.py     # 策略加载（文件/数据库/远程）
├── guard/
│   ├── input_sanitizer.py   # 输入净化（防注入/防越权路径）
│   ├── output_filter.py     # 输出过滤（敏感数据脱敏）
│   └── rate_limiter.py      # 速率限制（用户级/Tool级/API级）
└── audit/
    ├── trail.py             # 审计追踪（谁+何时+调了什么Tool+结果）
    └── store.py             # 审计日志持久化（独立于业务DB）
```

### 关键设计

**Tool 级 RBAC 权限控制**：

```csv
# tool_policy.csv — Casbin RBAC 策略定义
# Format: p, role, tool, action
p, super_admin, *, execute          # 超级管理员可调用所有 Tool
p, admin, data_query, execute       # 管理员可查询数据
p, admin, rag, execute              # 管理员可用 RAG
p, admin, chart, execute            # 管理员可生成图表
p, admin, ocr, execute              # 管理员可用 OCR
p, admin, rebuild, execute          # 管理员可生成 Excel
p, user, rag, execute               # 普通用户只能用 RAG
p, user, chart, execute             # 普通用户可看图表
```

```python
class ToolPermissionGuard:
    """Agent 每次调用 Tool 前必须通过此守卫"""

    def __init__(self, enforcer: casbin.Enforcer):
        self.enforcer = enforcer
        self.audit = AuditTrail()

    def check(self, user: User, tool_name: str) -> bool:
        allowed = self.enforcer.enforce(user.role, tool_name, "execute")
        if not allowed:
            self.audit.log(
                event="tool_access_denied",
                user=user.id, user_role=user.role,
                tool=tool_name,
                timestamp=datetime.now()
            )
        return allowed
```

**输入净化器**：

```python
class InputSanitizer:
    """Agent 输入安全净化：
    1. 文件路径：校验白名单路径，防止路径遍历攻击
    2. SQL 片段：拦截可能被注入的字符
    3. Shell 命令：拦截命令注入
    """

    ALLOWED_PATHS = ["/data/pdf/", "/data/images/", "/data/uploads/"]

    def sanitize_path(self, path: str) -> str:
        """校验文件路径是否在允许的目录内"""
        real_path = os.path.realpath(path)
        if not any(real_path.startswith(p) for p in self.ALLOWED_PATHS):
            raise SecurityError(f"路径不在允许范围: {path}")
        return real_path

    def sanitize_query(self, query: str) -> str:
        """过滤可能用于注入的特殊字符"""
        dangerous = [";--", "DROP ", "DELETE ", "INSERT ", "UPDATE ", "';"]
        for pattern in dangerous:
            if pattern.lower() in query.lower():
                raise SecurityError(f"查询包含危险模式: {pattern}")
        return query
```

**速率限制**：

```python
class RateLimiter:
    """三级速率限制：
    - 用户级：每用户每分钟最多 N 次请求
    - Tool级：每 Tool 每分钟最多 M 次调用（保护 LLM API 不被刷爆）
    - API级：整个 API 网关总速率限制
    """
    def check_user_limit(self, user_id: str) -> bool: ...
    def check_tool_limit(self, tool_name: str) -> bool: ...
    def check_api_limit(self) -> bool: ...
```

**审计追踪**：

```python
@dataclass
class AuditRecord:
    """每次 Tool 调用记录完整的审计追踪"""
    id: str
    timestamp: datetime
    user_id: str
    user_role: str
    session_id: str
    agent_type: str
    tool_name: str
    tool_version: str
    input_summary: str         # 输入摘要（不存完整敏感数据）
    result: str                # SUCCESS | FAILED | DENIED
    error: Optional[str]
    tokens_used: int
    cost: float
    latency_ms: float
```

---

## 八、L7：API 网关层

> **定位**：统一的入口管理。核心变化是 Agent API 从同步阻塞改为异步任务模式。

### 目录结构

```
backend/api/
├── gateway/
│   ├── auth_middleware.py    # 认证中间件（JWT 验证）
│   ├── cors_handler.py       # CORS 配置（现有，增强）
│   ├── error_handler.py      # 统一错误响应格式
│   └── request_validator.py  # 请求参数校验
├── agent_routes.py           # Agent 核心 API（重构 harness_routes）
│   # POST   /api/agent/parse           → 提交异步解析任务
│   # GET    /api/agent/parse/{task_id}/stream → SSE 流式进度
│   # POST   /api/agent/analyze         → 提交 ReAct 分析任务
│   # GET    /api/agent/analyze/{task_id}/stream → SSE 推理链
│   # GET    /api/agent/tasks/{id}      → 任务状态查询
│   # POST   /api/agent/tasks/{id}/cancel → 取消任务
│   # GET    /api/agent/tools           → 列出当前用户可用的 Tool
├── rag_routes.py             # RAG API（现有，增强 SSE）
├── admin_routes.py           # 管理端 API
│   # GET    /api/admin/metrics           → 平台运行指标
│   # GET    /api/admin/audit             → 审计日志查询
│   # POST   /api/admin/tools/{name}/toggle → Tool 启用/禁用
│   # GET    /api/admin/llm/usage         → LLM Token 用量统计
│   # GET    /api/admin/health            → 全系统健康检查
├── playground_routes.py      # Agent Playground API
│   # POST   /api/playground/test         → 单 Tool 测试
│   # POST   /api/playground/dryrun       → Agent 干跑（不实际执行 Tool）
│   # POST   /api/playground/trace        → 重放历史执行链
└── streaming/
    ├── sse_manager.py        # SSE 连接管理器（连接池/心跳/自动清理）
    └── ws_manager.py         # WebSocket 连接池（Phase 3）
```

### 关键设计

**Agent API — 异步任务模式**：

```python
# POST /api/agent/analyze — 请求示例
# Request:
{
    "task": "分析工商银行 2024 年资产负债表中资产项的变化趋势",
    "context": {"bank": "工商银行", "year": 2024},
    "mode": "react",           # react | pipeline | plan
    "stream": true             # 是否启用 SSE 流式推送
}
# Response (202 Accepted):
{
    "task_id": "task_abc123",
    "status": "queued",
    "stream_url": "/api/agent/analyze/task_abc123/stream"
}

# GET /api/agent/analyze/{task_id}/stream — SSE 事件流
# event: progress
# data: {"step": 1, "action": "think", "content": "需要先查询资产负债表数据..."}

# event: tool_call
# data: {"tool": "data_query", "args": {...}, "start_time": "..."}

# event: tool_result
# data: {"tool": "data_query", "success": true, "rows": 42, "latency_ms": 120}

# event: complete
# data: {"result": "...", "total_tokens": 4200, "cost": 0.0084}
```

**统一错误响应格式**：

```python
# 所有 API 的错误响应统一为：
{
    "error": {
        "code": "TOOL_ACCESS_DENIED",
        "message": "当前用户无权调用 data_query 工具",
        "request_id": "req_xyz789",
        "trace_id": "trace_abc123",
        "timestamp": "2026-06-13T23:00:00Z"
    }
}
```

---

## 九、L8：用户界面层

> **定位**：在现有 Vue 3 前端基础上新增 Agent Playground、管理控制台、监控大盘三个关键页面。

### 目录结构

```
frontend/src/
├── views/
│   ├── AgentWorkflow.vue    # Agent 工作流可视化（现有，升级）
│   ├── AgentPlayground.vue  # ★ 新增：Agent 实验场
│   ├── AdminDashboard.vue   # ★ 新增：管理控制台
│   ├── MonitorDashboard.vue # ★ 新增：监控大盘
│   └── ... (现有 8+ 页面保留)
├── components/agent/        # Agent 相关组件
│   ├── ThinkChain.vue       # ReAct 推理链可视化（Think→Act→Observe→Answer）
│   ├── ToolInvocation.vue   # Tool 调用详情卡片（输入/输出/耗时/成本）
│   ├── MemoryViewer.vue     # Agent 记忆查看器
│   ├── DAGGraph.vue         # 工作流 DAG 图（使用 ECharts 力导向图）
│   └── CostTracker.vue      # Token 成本追踪（实时累计）
├── composables/
│   ├── useAgentStream.js    # Agent SSE 流式消费 Hook
│   └── useAgentPlayground.js # Playground 交互 Hook
└── stores/
    └── agentStore.js         # Agent 状态管理（现有，增强）
```

### Agent Playground 核心交互

| 功能 | 说明 |
|---|---|
| **任务输入** | 自由输入自然语言任务描述 |
| **Agent 选择** | 下拉选择 Pipeline / ReAct / Plan 模式 |
| **Tool 可见性** | 列出当前用户可用的所有 Tool 及说明 |
| **干跑模式** | Agent 走完整推理流程但不实际执行 Tool，输出计划 |
| **推理链可视化** | 实时展示 Think → Act → Observe 循环，每个 Action 的输入输出 |
| **成本核算** | 实时显示当前对话累计 Token 用量和费用 |
| **历史回放** | 选择历史任务记录，回放完整执行过程 |
| **记忆管理** | 查看/清除 Agent 短期记忆，搜索长期记忆 |

---

## 十、分阶段实施路线图

### Phase 1：基础设施（约 3 周）

| 序号 | 任务 | 产出 | 依赖 |
|---|---|---|---|
| 1.1 | Pydantic Settings 配置中心 | 替代散落的 config 文件，统一多环境配置 | 无 |
| 1.2 | structlog 结构化日志 | 替代所有 `print()`，每请求自动注入 `trace_id` | 无 |
| 1.3 | Celery + Redis 异步任务队列 | Agent 任务不再阻塞 Flask WSGI worker | 配置中心 |
| 1.4 | Prometheus metrics 采集 | Tool 调用量/延迟/成功率指标暴露 | 配置中心 |
| 1.5 | 健康检查端点 | `/health`（存活）+ `/ready`（就绪） | 无 |
| 1.6 | Docker 容器化 | `Dockerfile` + `docker-compose.yml` | 无 |

**Phase 1 完成后效果**：日志可检索、任务异步不阻塞、指标可采集、可容器化部署。

### Phase 2：数据管线升级（约 3 周）

| 序号 | 任务 | 产出 | 依赖 |
|---|---|---|---|
| 2.1 | 文本清洗管线 | Normalizer / Filter / Dedup 处理器链 | Phase 1 日志 |
| 2.2 | 扫描件 OCR 文本反哺 RAG | OCR 结果自动流入 RAG 索引，扫描件可检索 | 现有 OCR 服务 |
| 2.3 | 结构感知分块 | 章节/表格边界感知的混合分块器 | 文本清洗 |
| 2.4 | 混合检索（BM25 + 向量） | 召回率提升 20-30% | 现有 FAISS |
| 2.5 | 增量索引更新 | 新文档追加索引，不需全量重建 | 现有索引管理器 |
| 2.6 | 向量索引版本管理 | 每次构建带时间戳版本，支持回滚 | 增量索引 |

**Phase 2 完成后效果**：RAG 检索质量显著提升，金融数字查询命中率提高，扫描件 PDF 也能被检索到。

### Phase 3：Agent 框架硬化（约 4 周）

| 序号 | 任务 | 产出 | 依赖 |
|---|---|---|---|
| 3.1 | LLM Provider 抽象层 | 多模型统一接口 + 智能路由 | 配置中心（1.1） |
| 3.2 | Memory 系统 | 短期/长期/情景三级记忆 | 向量存储（2.4） |
| 3.3 | Circuit Breaker 熔断器 | 外部服务异常时快速失败，防止雪崩 | 无 |
| 3.4 | 死信队列 | 失败任务持久化 + 手动重试 | Celery（1.3） |
| 3.5 | Plan-Execute Agent | 先规划再执行的新 Agent 模式 | Agent 核心 |
| 3.6 | Agent Factory | 声明式配置即可构建 Agent 实例 | 配置中心（1.1） |
| 3.7 | Tool 版本化 + 健康检查 | Tool 启用/禁用 + 可用性探测 | 无 |

**Phase 3 完成后效果**：Agent 具备工业级韧性，支持多模型调度，具有长期记忆，外部依赖故障不影响核心流程。

### Phase 4：编排 + 安全（约 2 周）

| 序号 | 任务 | 产出 | 依赖 |
|---|---|---|---|
| 4.1 | DAG 工作流引擎 | 声明式工作流 + 并行执行 | Agent 框架（Phase 3） |
| 4.2 | Tool RBAC 权限引擎 | Casbin + 策略文件，Tool 级权限控制 | 现有用户体系 |
| 4.3 | 输入净化 + 输出脱敏 | 防注入 + 金融数据脱敏 | 权限引擎 |
| 4.4 | 审计日志 | 所有 Tool 调用全量记录 | 结构化日志（1.2） |
| 4.5 | 速率限制 | 用户/Tool/API 三级限流 | 无 |

**Phase 4 完成后效果**：安全的 Agent 平台，满足金融行业合规要求。

### Phase 5：运营 + 上线（约 2 周）

| 序号 | 任务 | 产出 | 依赖 |
|---|---|---|---|
| 5.1 | RAG 评估框架 | 检索精度/答案质量自动化评测 | Phase 2 数据管线 |
| 5.2 | Agent 实验场（前端） | 前端 Playground 界面 | Phase 3 |
| 5.3 | 监控大盘 | Grafana Dashboard | Phase 1 metrics |
| 5.4 | 管理控制台（前端） | Admin 界面（工具管理/审计/用量） | Phase 4 安全 |
| 5.5 | 生产部署 | Gunicorn + Nginx + Docker Compose | Phase 1 Docker |

---

## 十一、最终目录结构总览

```
BankDataViz/                           # 项目根目录
│
├── backend/                           # Python 后端
│   │
│   ├── infrastructure/                # [NEW] L1 基础设施
│   │   ├── config/                    # Pydantic Settings 配置中心
│   │   │   ├── settings.py
│   │   │   ├── agent_settings.py
│   │   │   └── model_settings.py
│   │   ├── logging/                   # structlog 结构化日志
│   │   │   ├── logger.py
│   │   │   ├── middleware.py
│   │   │   └── formatters.py
│   │   ├── async_tasks/               # Celery 异步任务
│   │   │   ├── celery_app.py
│   │   │   ├── tasks.py
│   │   │   └── progress.py
│   │   ├── metrics/                   # Prometheus 指标
│   │   │   ├── collector.py
│   │   │   └── health.py
│   │   └── connection_pool.py
│   │
│   ├── data_pipeline/                 # [NEW] L2 数据处理管线
│   │   ├── ingestion/                 # 文档加载
│   │   │   ├── loader.py
│   │   │   ├── pdf_extractor.py
│   │   │   ├── ocr_extractor.py
│   │   │   └── type_detector.py
│   │   ├── cleaning/                  # 文本清洗管线
│   │   │   ├── normalizer.py
│   │   │   ├── noise_filter.py
│   │   │   ├── table_dedup.py
│   │   │   └── pipeline.py
│   │   ├── chunking/                  # 混合分块策略
│   │   │   ├── semantic_chunker.py
│   │   │   ├── structural_chunker.py
│   │   │   ├── hybrid_chunker.py
│   │   │   └── overlap_manager.py
│   │   └── metadata/
│   │       ├── extractor.py
│   │       └── enricher.py
│   │
│   ├── knowledge_engine/              # [NEW] L3 知识引擎
│   │   ├── embedding/
│   │   │   ├── bge_embedder.py
│   │   │   ├── embedder_registry.py
│   │   │   └── batch_encoder.py
│   │   ├── vector_store/
│   │   │   ├── base.py
│   │   │   ├── faiss_store.py
│   │   │   └── milvus_store.py
│   │   ├── retrieval/
│   │   │   ├── vector_searcher.py
│   │   │   ├── bm25_searcher.py
│   │   │   ├── hybrid_searcher.py
│   │   │   └── reranker.py
│   │   └── index_manager.py
│   │
│   ├── agent_framework/               # [REFACTOR] L4 Agent 核心
│   │   ├── core/
│   │   │   ├── tool.py                # Tool / ToolResult（增强）
│   │   │   ├── agent.py               # Agent / ReActAgent（增强）
│   │   │   ├── action.py              # Action / Observation
│   │   │   └── registry.py            # ToolRegistry（增强）
│   │   ├── providers/                 # LLM Provider 抽象
│   │   │   ├── base.py
│   │   │   ├── deepseek.py
│   │   │   ├── doubao.py
│   │   │   ├── openai_compat.py
│   │   │   └── router.py
│   │   ├── memory/                    # 三级记忆系统
│   │   │   ├── base.py
│   │   │   ├── short_term.py
│   │   │   ├── long_term.py
│   │   │   ├── episodic.py
│   │   │   └── manager.py
│   │   ├── resilience/                # 韧性机制
│   │   │   ├── circuit_breaker.py
│   │   │   ├── retry_policy.py
│   │   │   ├── fallback_chain.py
│   │   │   └── dead_letter.py
│   │   ├── verification/              # 规则引擎
│   │   │   ├── engine.py
│   │   │   ├── rules.py
│   │   │   └── auto_fix.py
│   │   ├── plan_agent.py
│   │   └── agent_factory.py
│   │
│   ├── orchestration/                 # [NEW] L5 编排
│   │   ├── workflow/
│   │   │   ├── dag_engine.py
│   │   │   ├── node.py
│   │   │   ├── conditions.py
│   │   │   ├── parallel.py
│   │   │   └── state_machine.py
│   │   ├── orchestrator.py
│   │   ├── scheduler.py
│   │   ├── context_bus.py
│   │   └── delegation.py
│   │
│   ├── security/                      # [NEW] L6 安全
│   │   ├── permissions/
│   │   │   ├── rbac_engine.py
│   │   │   ├── tool_policy.py
│   │   │   └── tool_policy.csv        # Casbin 策略文件
│   │   ├── guard/
│   │   │   ├── input_sanitizer.py
│   │   │   ├── output_filter.py
│   │   │   └── rate_limiter.py
│   │   └── audit/
│   │       ├── trail.py
│   │       └── store.py
│   │
│   ├── api/                           # [REFACTOR] L7 API
│   │   ├── gateway/
│   │   │   ├── auth_middleware.py
│   │   │   ├── cors_handler.py
│   │   │   ├── error_handler.py
│   │   │   └── request_validator.py
│   │   ├── agent_routes.py            # Agent 异步 API（重构）
│   │   ├── playground_routes.py       # Agent Playground
│   │   ├── admin_routes.py            # 管理控制台 API
│   │   ├── rag_api.py                 # RAG API（保持，增强）
│   │   └── streaming/
│   │       ├── sse_manager.py
│   │       └── ws_manager.py
│   │
│   ├── services/                      # 现有业务服务层（保留）
│   ├── core/                          # 现有核心管线（保留）
│   ├── database/                      # 现有数据库层（保留）
│   ├── models/                        # 现有数据模型（保留）
│   └── harness/                       # 现有 Agent 框架（逐步迁移到 agent_framework/）
│
├── frontend/                          # Vue 3 前端
│   └── src/
│       ├── views/
│       │   ├── AgentPlayground.vue    # [NEW] Agent 实验场
│       │   ├── AdminDashboard.vue     # [NEW] 管理控制台
│       │   ├── MonitorDashboard.vue   # [NEW] 监控大盘
│       │   └── ... (现有页面保留)
│       ├── components/agent/          # [NEW] Agent 组件
│       └── composables/               # [NEW] Agent 交互 Hooks
│
├── docker-compose.yml                 # [NEW] 一键部署
├── Dockerfile                         # [NEW] 容器构建
├── prometheus.yml                     # [NEW] 监控配置
├── .env.example                       # [NEW] 环境变量模板
└── README.md
```

---

## 十二、关键技术决策总结

| 决策点 | 选择 | 为什么不选别的 |
|---|---|---|
| Agent 框架 | **自研** | 不做 LangChain 的附属品。当前 harness 骨架设计好，只需加固而非重写 |
| 异步任务 | **Celery + Redis** | 已有 Redis 基础设施，社区最成熟，文档最全 |
| 日志系统 | **structlog** | 结构化 JSON，无侵入式迁移（渐进替换 print，不破坏现有代码） |
| 配置中心 | **Pydantic Settings** | 类型安全、支持多环境、运行时可校验 |
| 权限框架 | **Casbin** | 策略与代码分离，支持 RBAC/ABAC，轻量零依赖 |
| 向量数据库 | **FAISS → Milvus 平滑迁移** | 先用 FAISS（够用+零部署），数据量上百万后开启 Milvus adapter |
| 检索策略 | **混合检索（向量 + BM25）** | 金融场景大量数值/代码查询，纯向量语义检索命中率低，BM25 不可缺 |
| 部署方式 | **Docker + Gunicorn** | 替换当前 nohup 裸启动，Nginx 反向代理，支持水平扩展 |
| Web 框架 | **Flask（保持）** | FastAPI 更好但迁移成本高，优先加固当前架构，不做无谓的技术重写 |
| 前端框架 | **Vue 3（保持）** | 已在用，组件成熟 |

---

## 十三、风险与应对

| 风险 | 影响 | 应对策略 |
|---|---|---|
| Celery 引入复杂度 | 增加运维成本 | Phase 1 可先用 Redis Queue 简化版，Phase 3 再切 Celery |
| SQLite 并发瓶颈 | 多用户并发写锁定 | 表处理仍用 SQLite（单机够用），会话/审计用 Redis |
| BGE 模型大（1.3GB）加载慢 | 首次请求等待 10s+ | 已实现预热+单例，后续支持 ONNX 量化（模型缩小 4x） |
| 自研框架可维护性 | 人走代码凉 | 接口优先设计，每层独立测试，不变更现有 Tool 接口，编写框架使用文档 |
| LLM 成本不可控 | Agent 自动循环消耗大量 Token | ModelRouter 预算控制 + MaxSteps 硬限制 + 用量告警 |
| 金融数据泄露 | 合规风险 | 输出脱敏 + 审计日志 + 权限最小化 + 数据不上云（本地部署） |

---

## 附录：改造前后对比

| 维度 | 当前状态 | Phase 5 完成后 |
|---|---|---|
| 日志 | 118 个 `print()`，不可检索 | structlog 结构化日志，trace_id 全链路追踪 |
| 任务执行 | Flask 同步阻塞 14s+ | Celery 异步队列，SSE 进度推送 |
| Agent 记忆 | 单次请求生命周期 | 短期/长期/情景三级记忆，跨会话复用 |
| LLM 调用 | 直接 hardcode API | Provider 抽象，多模型智能路由 + 成本控制 |
| RAG 检索 | 纯向量（FAISS IVF） | 混合检索（向量+BM25+RRF+重排序） |
| 文本质量 | 无清洗，原始 PDF 文本 | 6 步清洗管线，半角/去噪/去重 |
| 权限控制 | 无，任何人可调任何 Tool | Casbin RBAC，Tool 级别权限 |
| 安全防护 | 无输入校验、无限流 | 输入净化 + 速率限制 + 输出脱敏 |
| 可观测性 | 无指标无追踪 | Prometheus + Grafana + 审计日志 |
| 部署方式 | `nohup python start_backend.bat` | Docker Compose 一键部署 |
| 分块策略 | 固定 512 字符 | 结构感知 + 智能重叠 |

---

> **核心原则**：不做推倒重来，在现有工作代码上 **逐层加固**。每个 Phase 都有明确的交付物和可感知的效果提升，不需要等到全部做完才能用。现有的 `backend/harness/` 目录在迁移过程中保持向后兼容，新旧 Agent 可同时运行。
