# ✈️ AeroRegQA — 适航法规智能问答系统

<p align="center">
  <em>基于 Agentic RAG 的航空器适航规章检索、条款溯源与问答工具</em>
</p>

<p align="center">
  <a href="https://aeroregai.streamlit.app/"><strong>🌐 在线体验 Demo</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/LLM-DeepSeek-green" alt="DeepSeek"/>
  <img src="https://img.shields.io/badge/VectorDB-ChromaDB-orange" alt="ChromaDB"/>
  <img src="https://img.shields.io/badge/UI-Streamlit-red?logo=streamlit" alt="Streamlit"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License"/>
</p>

---

## 内置规章与部署（2026-10 更新）

本次同步本地完整低空适航版本，包含混合检索、重排序、意图路由、专项问答 Skills、引用检查、反馈记录和 FastAPI。网站首次启动自动恢复 **17 个来源、4,235 个文本块**，无需访客先上传资料。

原项目 19 个资料文件存放于 `knowledge/documents/`，未入库候选单独保留。具体入库边界见 [知识库说明](knowledge/README.md) 与 [来源清单](knowledge/manifest.json)。这些是收集时的版本快照，不代表全部或最新有效法规。

Streamlit Community Cloud 的入口仍为 `ui/app.py`，Python 使用 3.11。保留已有 Secrets，至少配置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_NAME`、`EMBEDDING_API_KEY`；向量模型必须是 `BAAI/bge-m3`，默认接口为 `https://api.siliconflow.cn/v1`。未配置的 Judge、Lite、Router 模型自动复用主模型名，支持第三方服务商的模型命名。

`knowledge/seed.zip` 内置文本和向量，启动恢复不调用外部模型。运行时数据库、密钥、对话与日志仍排除在 Git 之外。云端运行目录丢失后会恢复内置知识库；访客后来上传的文件和对话不保证永久保存。当前版本仍是共享演示实例，未实现访客数据隔离。

默认依赖使用 PyMuPDF 解析文本 PDF，避免云端安装大型 OCR 模型；本地扫描件 OCR 可选安装 `pip install -r requirements-ocr.txt`。Redis 不可用时自动禁用缓存，统计数据库默认使用 SQLite，无需单独部署 MySQL。

验证：`python -m pytest -q`。知识库测试会在临时目录恢复完整索引并验证向量检索、重复启动及模型兼容性，不调用付费接口。

---

## 📌 项目简介

**AeroRegQA** 面向适航工程师、审定人员和航空产品研发团队，提供可本地部署的**适航法规检索与问答系统**。用户可上传适航规章、咨询通告（AC）、管理程序（AP）及相关审定资料，构建自己的法规知识库。

适航审定涉及审定程序、航空器类别适用标准和具体条款。相关文件篇幅较长且版本持续更新，人工定位依据耗时；通用大模型若脱离原文回答，也容易误引或编造条款。

本系统通过 **Agentic RAG（检索增强生成）** 架构解析并索引用户上传的法规文档，要求大模型依据检索到的原文条款回答，并通过 **LLM-as-a-Judge** 检查答复质量与引用。回答用于辅助法规检索与研读；具体适用性仍需以现行文件和正式审定意见为准。

---

## 🎯 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **Agentic RAG** | 多轮迭代检索-生成-评估，自动优化检索策略直至答案达标 |
| ⚖️ **LLM-as-a-Judge** | 内置裁判模型对生成答案进行事实性评估，不合格自动重试 |
| 📎 **强制溯源标注** | 每条回答强制附带文献来源编号与章节定位 |
| 📄 **多格式支持** | 支持 PDF（含双栏排版）、Word (DOCX)、纯文本 (TXT) |
| 🔒 **完全本地化** | 文档解析与向量存储全部本地运行，仅 LLM 推理调用 API |
| 💬 **多轮对话** | 支持上下文记忆、指代消解、历史对话管理 |
| 🚀 **一键启动** | 双击 `start.bat` 即可运行，无需任何命令行操作 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Web UI                       │
├─────────────────────────────────────────────────────────┤
│                  Agentic RAG Controller                   │
│  ┌───────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │Query      │  │Draft      │  │LLM-as-a-Judge      │  │
│  │Rewriter   │→ │Generator  │→ │(质量评估 & 事实核查)│  │
│  └───────────┘  └───────────┘  └────────────────────┘  │
│         ↑                              │ 不合格则重试    │
│         └──────────────────────────────┘                │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Semantic      │  │ChromaDB      │  │Hybrid        │  │
│  │Chunker       │  │Vector Store  │  │Retriever     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Document Parser (PDF / DOCX / TXT)                      │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
AeroRegQA/
├── config/                 # 配置管理
│   ├── settings.py         # 全局参数配置（从 .env 加载）
│   └── prompts.py          # 提示词模板
├── core/                   # 核心业务逻辑
│   ├── chunker/            # 语义分块器（按标题层级 + 递归分割）
│   ├── conversation/       # 对话管理（历史记录、标题生成）
│   ├── parser/             # 文档解析器（PDF / DOCX / TXT）
│   ├── rag/                # RAG 智能体
│   │   ├── agent.py        # 核心控制循环（检索→生成→裁判→优化）
│   │   ├── judge.py        # LLM-as-a-Judge 裁判模块
│   │   ├── llm_client.py   # LLM API 客户端封装
│   │   └── query_rewriter.py  # 查询重写与指代消解
│   └── vectorstore/        # 向量数据库层
│       ├── chroma_store.py # ChromaDB 封装
│       ├── embedder.py     # Embedding 服务
│       └── retriever.py    # 混合检索器
├── ui/                     # Streamlit 前端界面
│   ├── app.py              # 主应用入口
│   ├── components/         # UI 组件（聊天区、侧边栏、上传器）
│   ├── state.py            # 状态管理
│   └── styles.py           # 样式定义
├── data/                   # 运行时数据（已 gitignore）
├── tests/                  # 测试套件
├── .env.example            # 环境变量模板
├── requirements.txt        # Python 依赖
├── start.bat               # Windows 一键启动
└── start.sh                # Linux/macOS 一键启动
```

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Miniconda 或 Anaconda
- DeepSeek API 密钥（用于 LLM 推理）
- 硅基流动 API 密钥（用于 Embedding 向量化）

### 安装步骤

**1. 克隆仓库**

```bash
git clone https://github.com/StarwardAero/AeroRegQA.git
cd AeroRegQA
```

**2. 创建虚拟环境**

```bash
conda create -n academic-rag python=3.11 -y
conda activate academic-rag
```

**3. 安装依赖**

```bash
pip install -r requirements.txt
```

**4. 配置 API 密钥**

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入您的 API 密钥：

```properties
# DeepSeek LLM
LLM_API_KEY=sk-your-deepseek-key

# 硅基流动 Embedding
EMBEDDING_API_KEY=sk-your-siliconflow-key
```

**5. 启动系统**

```bash
# Windows - 双击 start.bat 或：
streamlit run ui/app.py --server.port 8501

# Linux / macOS
bash start.sh
```

浏览器将自动打开 `http://localhost:8501`。

---

## 📖 使用指南

### 1️⃣ 构建知识库

在界面的“添加文献资料”区域，拖入适航法规文件（PDF / DOCX / TXT / Markdown / CSV），点击“开始解析并入库”。系统将自动完成：

- 文档解析（支持双栏 PDF、含公式文档）
- 语义分块（按标题层级智能切分）
- 向量化（调用 BGE-M3 模型生成 1024 维向量）
- 入库存储（写入本地 ChromaDB）

### 2️⃣ 智能问答

在输入框中提出问题，例如：

> "CCAR-23 部对小型飞机的结构设计有哪些适航要求？"

系统将执行完整的 Agentic RAG 流程：

1. **查询重写** — 将口语化问题转化为精确检索语句
2. **向量检索** — 从知识库中召回最相关的法规片段
3. **草稿生成** — 基于检索内容生成初步回答
4. **裁判评估** — 内置裁判模型进行事实性打分
5. **迭代优化** — 若未达标则优化检索条件重试（最多 3 轮）
6. **流式输出** — 最终答案逐字流式展示，附带文献溯源标注

### 3️⃣ 对话管理

- 支持创建多个独立对话
- 自动生成对话标题
- 历史对话可随时恢复或删除

---

## ⚙️ 配置说明

所有配置项均在 `.env` 文件中管理：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_API_KEY` | DeepSeek API 密钥 | — |
| `LLM_BASE_URL` | LLM API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL_NAME` | 主模型名称 | `deepseek-chat` |
| `LLM_JUDGE_MODEL_NAME` | 裁判模型名称 | `deepseek-chat` |
| `LLM_LITE_MODEL_NAME` | 轻量模型（查询重写） | `deepseek-chat` |
| `EMBEDDING_API_KEY` | 硅基流动 API 密钥 | — |
| `EMBEDDING_BASE_URL` | Embedding API 地址 | `https://api.siliconflow.cn/v1` |
| `EMBEDDING_MODEL_NAME` | Embedding 模型 | `BAAI/bge-m3` |
| `RAG_TOP_K` | 每次检索返回的文档块数 | `5` |
| `RAG_MAX_ITERATIONS` | 最大迭代轮数 | `3` |
| `RAG_JUDGE_THRESHOLD` | 裁判通过阈值 (0-1) | `0.7` |
| `CHUNK_SIZE` | 文本块大小（字符） | `1500` |
| `CHUNK_OVERLAP` | 块间重叠（字符） | `200` |

---

## 🧪 运行测试

```bash
conda activate academic-rag
pytest tests/ -v
```

---

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 前端框架 | Streamlit |
| 大语言模型 | DeepSeek (OpenAI 兼容 API) |
| 向量化模型 | BAAI/bge-m3 (硅基流动) |
| 向量数据库 | ChromaDB |
| 文档解析 | marker-pdf, PyMuPDF, python-docx |
| 文本分块 | LangChain RecursiveCharacterTextSplitter |
| 运行环境 | Python 3.11, Conda |

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

---

## 📄 License

本项目基于 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) — 提供高质量中文大语言模型服务
- [硅基流动 SiliconFlow](https://siliconflow.cn/) — 提供高性能 Embedding 推理服务
- [ChromaDB](https://www.trychroma.com/) — 轻量级开源向量数据库
- [Streamlit](https://streamlit.io/) — 快速构建数据应用的 Python 框架
