# Paper AI Enhanced - Arxiv 论文爬取与智能分析系统

一个自动化的 Arxiv 论文爬取、过滤、总结和推送系统，支持智能过滤、AI 总结和多种通知方式。

## 📋 目录

- [系统要求](#系统要求)
- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [安装配置](#安装配置)
- [配置说明](#配置说明)
- [使用方法](#使用方法)
- [API 接口](#api-接口)
- [模块说明](#模块说明)

## 🔧 系统要求

- **Python 版本**: Python 3.8 或更高版本
- **操作系统**: Linux / macOS / Windows
- **依赖包**: 见 `requirements.txt`

## ✨ 功能特性

### 核心功能

1. **论文爬取**
   - 自动从 Arxiv 爬取指定分类的最新论文
   - 支持自定义日期范围和分类筛选
   - 自动去重，避免重复处理

2. **智能过滤**
   - 关键词过滤：基于预定义关键词列表
   - 语义理解过滤：使用小模型进行语义匹配
   - 支持两种模式：仅关键词、仅语义、或两者结合

3. **AI 总结**
   - 使用大模型对论文进行结构化总结
   - 支持 PDF 内容提取和文本分析
   - 生成 Markdown 格式的详细总结

4. **数据存储**
   - 按日期组织存储论文数据
   - 支持 JSON、PDF、Markdown 等多种格式
   - 自动管理文件路径和元数据

5. **通知推送**
   - 网关数据推送
   - 支持自定义推送模板

6. **Web API 服务**
   - FastAPI 后端服务
   - 支持论文查询、筛选、搜索
   - 提供统计和文件下载接口

## 📁 项目结构

```
paper_ai_enhanced_1/
├── src/                    # 核心源代码
│   ├── crawler/           # 论文爬取模块
│   │   └── arxiv.py       # Arxiv API 封装
│   ├── core/              # 核心业务逻辑
│   │   ├── filter.py      # 论文过滤（关键词+语义）
│   │   ├── storage.py     # 数据存储管理
│   │   └── summarizer.py  # AI 论文总结
│   ├── notify/            # 通知推送模块
│   │   └── gateway.py     # 网关推送
│   ├── api/               # API 客户端
│   │   └── llm.py         # LLM API 封装
│   ├── config/            # 配置管理
│   ├── utils/             # 工具函数
│   └── main.py            # 主程序入口
├── server/                # Web API 服务器
│   └── main.py            # FastAPI 服务器
├── back/                  # 旧版代码（兼容保留）
├── config.yaml            # 配置文件
├── requirements.txt       # Python 依赖
├── main.py                # 入口脚本
├── start_server.sh        # 启动服务器脚本
└── start_frontend.sh      # 启动前端脚本（需前端项目）
```

## 🚀 安装配置

### 1. 克隆项目

```bash
git clone <repository-url>
cd paper_ai_enhanced
```

### 2. 创建虚拟环境（推荐）

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境

复制并编辑配置文件：

```bash
cp config.yaml config.yaml.local
# 编辑 config.yaml.local，填入你的 API 密钥和配置
```

## ⚙️ 配置说明

主要配置文件：`config.yaml`

### 1. Arxiv 配置

```yaml
arxiv:
  categories:          # 论文分类列表
    - "cs.AI"          # 人工智能
    - "cs.LG"          # 机器学习
    - "cs.CV"          # 计算机视觉
  max_results: 20      # 每次爬取的最大论文数
  days_back: 1         # 往前推多少天（默认1天，即昨天）
```

### 2. 论文过滤配置

```yaml
filter:
  enabled: true        # 是否启用过滤
  mode: "both"         # 过滤模式：keyword, semantic, both
  
  keyword:             # 关键词过滤
    enabled: true
    keywords:          # 关键词列表
      - "vulnerability"
      - "security"
    match_mode: "any"  # any: 匹配任意关键词, all: 匹配所有关键词
    case_sensitive: false  # 是否区分大小写
  
  semantic:            # 语义理解过滤
    enabled: true
    api_url: "https://open.bigmodel.cn/api/..."
    api_key: "your-api-key"
    model: "glm-4.5-flash"  # 小模型（用于快速过滤）
```

### 3. LLM 配置（论文总结）

```yaml
llm:
  enabled: true
  api_url: "https://open.bigmodel.cn/api/..."
  api_key: "your-api-key"
  model: "glm-4.5"     # 大模型（用于详细总结）
  timeout: 300         # 超时时间（秒）
```

### 4. 通知配置

```yaml
gateway:              # 网关推送
  enabled: false
  url: "http://your-gateway-url"
```

### 5. 路径配置

```yaml
paths:
  data_root: "./data"  # 数据存储根目录
```

### 6. 服务器配置

```yaml
server:
  api_prefix: "ai_paper"  # API 路径前缀
```

## 📖 使用方法

### 1. 运行论文爬取和总结

```bash
# 使用默认配置
python main.py

# 指定配置文件
python main.py --config config.yaml

# 自定义参数
python main.py --days 2 --max-results 50 --categories cs.AI cs.LG

# 禁用某些功能
python main.py --no-llm      # 禁用 AI 总结
python main.py --no-filter   # 禁用过滤
python main.py --no-push     # 禁用推送
```

### 2. 启动 Web API 服务器

```bash
# 方式1：使用启动脚本
./start_server.sh

# 方式2：直接使用 uvicorn
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

服务器启动后，访问：
- API 文档：http://localhost:8000/ai_paper/docs
- 根路径：http://localhost:8000/

### 3. 命令行参数

```bash
python main.py --help

选项：
  -c, --config PATH        配置文件路径（默认: config.yaml）
  -d, --days N             往前推多少天
  -m, --max-results N      最大结果数
  --categories CATS        论文分类（如: cs.AI cs.LG）
  --no-llm                 禁用大模型总结
  --no-filter              禁用论文过滤
  --no-push                禁用推送
```

## 🌐 API 接口

### 基础路径

所有 API 路径前缀为 `/ai_paper`（可在配置中修改）

### 主要接口

#### 1. 获取论文列表

```http
GET /ai_paper/api/papers
```

**查询参数：**
- `date` (可选): 日期筛选，格式：YYYY-MM-DD，为空时查询所有日期
- `category` (可选): 分类筛选，如：cs.CV
- `keyword` (可选): 关键词搜索（标题、摘要、llm_summary或content），忽略大小写
- `author` (可选): 作者筛选
- `limit` (默认: 50): 返回数量限制
- `offset` (默认: 0): 偏移量

**示例：**
```bash
curl "http://localhost:8000/ai_paper/api/papers?date=2026-01-14&keyword=AI"
```

#### 2. 获取所有论文

```http
GET /ai_paper/api/papers/all
```

**查询参数：**
- `category` (可选): 分类筛选
- `keyword` (可选): 关键词搜索
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期
- `limit` (默认: 100): 返回数量限制

#### 3. 获取论文详情

```http
GET /ai_paper/api/paper/{paper_id}
```

#### 4. 获取日期列表

```http
GET /ai_paper/api/dates
```

返回所有有论文数据的日期列表。

#### 5. 统计接口

```http
GET /ai_paper/api/stats          # 总体统计
GET /ai_paper/api/stats/daily    # 每日论文数量统计
```

#### 6. 文件下载

```http
GET /ai_paper/api/paper/{paper_id}/pdf        # 下载 PDF
GET /ai_paper/api/paper/{paper_id}/markdown   # 下载 Markdown
```

### API 特性

- **关键词搜索**：支持在标题、摘要、llm_summary 和 content 中搜索，忽略大小写
- **并发过滤**：使用多线程提升关键词搜索效率
- **日期查询**：支持单日期查询或查询所有日期
- **分页支持**：支持 limit 和 offset 参数

## 🔍 模块说明

### 1. 爬取模块 (`src/crawler/`)

**功能：**
- 封装 Arxiv API，支持按日期、分类爬取论文
- 自动处理 API 限制和错误重试
- 返回标准化的论文数据格式

**主要类：**
- `ArxivCrawler`: Arxiv 论文爬虫

### 2. 过滤模块 (`src/core/filter.py`)

**功能：**
- 关键词过滤：基于预定义关键词列表匹配
- 语义理解过滤：使用小模型进行语义匹配
- 支持多种匹配模式（any/all）

**主要类：**
- `PaperFilter`: 论文过滤器

### 3. 存储模块 (`src/core/storage.py`)

**功能：**
- 按日期组织存储论文数据
- 管理 JSON、PDF、Markdown 文件
- 支持论文去重和元数据管理

**主要类：**
- `PaperStorage`: 论文存储管理器

### 4. 总结模块 (`src/core/summarizer.py`)

**功能：**
- 使用大模型生成论文结构化总结
- 支持 PDF 内容提取
- 生成 Markdown 格式总结

**主要类：**
- `PaperSummarizer`: 论文总结器

### 5. 通知模块 (`src/notify/`)

**功能：**
- 网关数据推送
- 支持自定义推送模板

**主要函数：**
- `push_paper_to_gateway()`: 网关推送

### 6. API 服务器 (`server/main.py`)

**功能：**
- 提供 RESTful API 接口
- 支持论文查询、搜索、筛选
- 提供统计和文件下载功能

**主要接口：**
- `/api/papers`: 论文列表查询
- `/api/paper/{id}`: 论文详情
- `/api/stats`: 统计数据
- `/api/dates`: 日期列表

## 📝 数据存储结构

```
data/
├── 2026-01-14/          # 按日期组织
│   ├── json/            # JSON 文件
│   │   └── Paper_Title.json
│   ├── pdf/             # PDF 文件
│   │   └── Paper_Title.pdf
│   ├── markdown/        # Markdown 总结
│   │   └── Paper_Title.md
│   └── content/         # PDF 提取的文本内容
│       └── Paper_Title.txt
└── logs/                # 日志文件
```

## 🔧 常见问题

### 1. 如何修改 API 密钥？

编辑 `config.yaml` 文件，修改 `llm.api_key` 和 `filter.semantic.api_key`。

### 2. 如何添加新的论文分类？

在 `config.yaml` 的 `arxiv.categories` 中添加新的分类代码。

### 3. 如何自定义过滤关键词？

编辑 `config.yaml` 的 `filter.keyword.keywords` 列表。

### 4. 服务器启动失败？

- 检查端口 8000 是否被占用
- 确认已安装所有依赖：`pip install -r requirements.txt`
- 检查配置文件路径是否正确

### 5. 如何查看日志？

日志文件保存在 `data/logs/` 目录下，按日期组织。


## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

