# Company Agent

面向企业制度和内部资料问答的 RAG Agent 原型。项目用 FastAPI 提供流式问答接口，用 LangChain Agent 编排模型与检索工具，用 Chroma 保存向量，用本地 BM25 索引补充关键词召回，用 Ollama 生成 Embedding，用 Redis 保存浏览器会话历史。

当前版本适合学习、验证 RAG/Agent 链路和制作项目作品集，不是可直接用于生产环境的完整权限系统。企业制度内容仅作为测试资料，正式使用前应经过法务、合规和信息安全审核。

## 功能概览

已实现：

- 读取 UTF-8 TXT 制度文档，使用 `RecursiveCharacterTextSplitter` 递归切分。
- 使用 Ollama `nomic-embed-text` 生成向量并持久化到 Chroma。
- 使用轻量中文 BM25 索引进行关键词召回，索引持久化为 `Chroma_db/bm25_index.json`。
- 使用加权 Reciprocal Rank Fusion（RRF）融合向量和 BM25 排名，并按正文、来源和页码去重。
- 由 LangChain Agent 判断是否调用 `vector_search` 工具，再将检索资料交给 DeepSeek 生成回答。
- 通过 FastAPI `StreamingResponse` 流式返回回答。
- 使用 HttpOnly Cookie 维护浏览器会话，Redis 保存最近 10 条有效对话，默认 48 小时过期。
- 上传并校验 PNG、JPEG、WebP、PDF、DOCX、XLSX、TXT、MD、CSV 附件。
- 文本附件在请求时提取并拼接到用户上下文；图片以 Base64 发送给视觉模型，识别结果再交给主 Agent。
- 在工具、检索、入库和异常分支输出关键链路日志，包括工具调用、检索耗时、历史读写和失败信息。
- 提供附件、BM25、混合检索和接口测试，当前测试套件共 22 项。

## 系统流程

### 文档入库

```text
制度 TXT
  -> 文本加载
  -> 递归切分
  -> Ollama Embedding
  -> Chroma 持久化
  -> 从 Chroma 同步生成 BM25 JSON 索引
```

向量库和 BM25 索引使用同一批切分后的正文。BM25 不直接搜索文件路径，而是搜索保存到索引中的文本块；文本块元数据目前主要包含 `source`。

### 混合检索

```text
用户问题
  -> 向量召回 vector_k 个候选
  -> 相关性阈值过滤
  -> BM25 召回 bm25_k 个候选
  -> 加权 RRF 融合
  -> 正文/source/page 去重
  -> 返回 hybrid_k 个文本块
  -> Agent/LLM 生成回答
```

BM25 使用中文单字和二元词组，并保留英文、数字和下划线词。它适合补充制度编号、金额、产品名等精确词匹配；向量检索适合处理同义表达。RRF 只比较两路结果的名次，不直接比较向量分数和 BM25 分数，因此能减少不同分数尺度带来的影响。

### 附件问答

附件上传与知识库入库是两条独立链路：

```text
POST /attachments
  -> 文件名、扩展名、MIME、大小和基础文件结构校验
  -> 按 session_id 保存到 uploads/

POST /get_question
  -> 校验附件是否属于当前会话
  -> PDF/DOCX/XLSX/TXT/MD/CSV 提取文本
  -> 图片发送给视觉模型识别
  -> 附件上下文 + 历史对话交给 Agent
  -> Agent 按需调用混合检索
  -> DeepSeek 流式回答
```

附件内容不会自动写入 Chroma，也不会成为长期知识库语料。

## 目录结构

```text
company_agent/
├── main.py                         # FastAPI 应用和 HTTP 接口
├── env.py                          # 文档路径、模型、检索和会话配置
├── requirements.txt                # Python 依赖
├── Attachment_Processing/
│   ├── storage.py                  # 附件校验、保存、删除和会话归属
│   ├── content.py                  # PDF、DOCX、XLSX、文本提取
│   └── vision.py                   # 图片多模态识别
├── Document_Processing/
│   ├── Document_Processing.py      # TXT 加载和文本切分
│   └── 金融公司制度与操作手册.txt    # 示例知识源
├── Vector_Processing/
│   ├── Vector_Processing.py         # Chroma、BM25 写入和混合检索
│   └── bm25.py                      # 中文分词和 BM25 实现
├── Rag/
│   ├── ai_answer.py                 # Agent、历史拼接和流式回答
│   └── chat_history.py              # Redis 会话历史
├── all_tools/all_tools.py           # Agent 工具封装
├── frontend/                        # HTML/CSS/JavaScript 对话页面
├── Chroma_db/                       # Chroma 数据和 BM25 JSON 索引
├── uploads/                         # 运行时附件目录，已被 Git 忽略
├── tests/                           # unittest 测试
└── docs/architecture.md             # 当前架构说明
```

## 环境要求

- Windows。
- Python 3.11 或更高版本。
- Redis，默认连接 `localhost:6379`。
- Ollama，并安装 `nomic-embed-text`。
- DeepSeek API Key。`ChatDeepSeek` 从环境变量读取密钥。

检查 Ollama：

```powershell
ollama pull nomic-embed-text
ollama list
```

启动 Redis 的方式取决于本机安装方式。启动应用前，确认 `localhost:6379` 可以连接。

## 安装

在 PowerShell 中执行：

```powershell
git clone <your-repository-url>
cd company_agent

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

设置 DeepSeek 密钥。当前代码不会自动加载 `.env` 文件，因此可在当前 PowerShell 会话中设置：

```powershell
$env:DEEPSEEK_API_KEY = "你的密钥"
```

如果 PowerShell 禁止激活脚本，可以直接使用虚拟环境解释器：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 配置

主要配置位于 `env.py`：

| 配置 | 作用 | 当前默认值 |
| --- | --- | --- |
| `text_Path` | 知识库源文档 | `Document_Processing/金融公司制度与操作手册.txt` |
| `encoding` | 源文档编码 | `utf-8` |
| `chunk_size` | 文本块目标长度 | `300` |
| `chunk_overlap` | 相邻文本块重叠长度 | `100` |
| `vector_path` | Chroma 和 BM25 存储目录 | `Chroma_db` |
| `k_top` | 向量和 BM25 候选数的兼容配置 | `20` |
| `vector_k` | 向量候选数量 | `20` |
| `bm25_k` | BM25 候选数量 | `20` |
| `hybrid_k` | 融合后返回数量 | `8` |
| `vector_weight` | 向量排名权重 | `0.5` |
| `bm25_weight` | BM25 排名权重 | `0.5` |
| `rrf_k` | RRF 平滑常数 | `60` |
| `relevance_threshold` | 向量相关性过滤阈值 | `0.3` |
| `MODEL` | 主回答模型 | `deepseek-v4-pro` |
| `IMAGE_MODEL` | 图片识别模型 | `deepseek-v4-flash-vision-exp` |
| `Expired_Time` | Redis 会话过期时间 | `172800` 秒（48 小时） |
| `COOKIE_NAME` | 会话 Cookie 名称 | `chat_session_id` |

注意：`text_Path` 和 `vector_path` 当前是本机绝对路径。迁移电脑前应改为项目根目录相对路径或环境变量。模型对象也在导入 `env.py` 时初始化，缺少 API Key 或网络不可用时，应用可能无法启动。

## 初始化知识库

1. 将源文档保存为 UTF-8 TXT。
2. 修改 `env.py` 中的 `text_Path`、切块参数和检索参数。
3. 启动 Ollama，确保 `nomic-embed-text` 可用。
4. 执行入库命令：

```powershell
.\.venv\Scripts\python.exe -c "from Vector_Processing.Vector_Processing import VectorProcessing; print(VectorProcessing().vector_storage())"
```

命令会依次完成文本切分、向量写入和 BM25 同步。重复入库前应先备份 `Chroma_db/`，因为当前使用顺序 ID（`0, 1, 2, ...`），没有内容哈希、版本号和完整幂等机制。正式系统应为每个文本块生成稳定 ID，并在更新时区分新增、修改和失效文档。

查看 BM25 索引块数：

```powershell
.\.venv\Scripts\python.exe -c "import json; print(len(json.load(open('Chroma_db/bm25_index.json', encoding='utf-8'))))"
```

## 启动应用

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

浏览器访问：

```text
http://127.0.0.1:8000/
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## HTTP 接口

### 上传附件 `POST /attachments`

请求类型为 `multipart/form-data`，字段名必须是 `files`。一次最多 5 个文件，单个文件最大 10 MB。

支持：`PNG`、`JPEG`、`WebP`、`PDF`、`DOCX`、`XLSX`、`TXT`、`MD`、`CSV`。

PowerShell 示例：

```powershell
curl.exe -X POST http://127.0.0.1:8000/attachments `
  -F "files=@报销单.png"
```

成功返回附件元数据，并设置 HttpOnly Cookie：

```json
{
  "attachments": [
    {
      "id": "32位随机附件ID",
      "name": "报销单.png",
      "content_type": "image/png",
      "size": 102400,
      "extension": ".png"
    }
  ]
}
```

### 删除附件 `DELETE /attachments/{attachment_id}`

只能删除当前会话拥有的附件。成功返回 `204 No Content`；附件不存在、格式无效或不属于当前会话时返回 `404`。

```powershell
curl.exe -X DELETE http://127.0.0.1:8000/attachments/<attachment_id>
```

### 提问 `POST /get_question`

请求体：

```json
{
  "question": "请帮我核对这张报销单是否缺少审批材料",
  "attachment_ids": ["32位随机附件ID"]
}
```

`attachment_ids` 可以省略。接口会：

- 验证附件 ID 和当前 Cookie 的会话归属。
- 提取 PDF、DOCX、XLSX、TXT、MD、CSV 文本，并限制单个附件 20,000 字符、所有附件合计 60,000 字符。
- 将图片编码为 Base64 Data URL，交给 `IMAGE_MODEL` 识别。
- 将附件资料、识别结果和最近有效对话交给 Agent。
- 返回 `text/plain; charset=utf-8` 的流式响应。

示例：

```powershell
curl.exe -X POST http://127.0.0.1:8000/get_question `
  -H "Content-Type: application/json" `
  -d '{"question":"报销需要哪些材料？","attachment_ids":[]}'
```

### 新建会话 `POST /new_chat`

删除当前浏览器的会话 Cookie，返回 `204 No Content`。当前实现不会立即删除 Redis 中的旧键，旧历史会在过期后清理。

```powershell
curl.exe -X POST http://127.0.0.1:8000/new_chat
```

## 测试

项目使用标准库 `unittest`，不依赖 pytest。执行全部测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

当前测试覆盖：

- BM25 中文分词、关键词排序、JSON 持久化和 RRF 去重。
- 混合检索同时包含向量路和 BM25 路的结果。
- 上传文件类型、文件头、大小、Office 容器和会话归属校验。
- PDF/DOCX/XLSX/文本提取上下文拼接。
- 图片发送、视觉识别失败和接口错误映射。
- 附件上传、删除、提问和跨会话访问接口。

## 检索评估

检索指标必须基于固定测试集，不应把主观体验或 LLM 最终回答直接当成召回率。建议为每个问题标记正确的文档、章节或文本块，并固定以下指标：

- `Top1`：正确文本块是否排在第 1 位。
- `Hit@3`：正确文本块是否出现在前 3 位。
- `Recall@K`：正确文本块是否出现在前 K 位。
- `MRR@K`：正确结果排名越靠前得分越高。
- 无答案拒答率：知识库没有依据的问题，系统是否能够拒绝编造。

评测时应保持题集、目标标注、切块策略、候选数和阈值一致，分别比较纯向量、纯 BM25 和混合检索。还应单独评测最终答案的事实一致性、引用正确性和响应延迟。

当前代码没有把评测题集和脚本固化到仓库，因此历史实验结果只能作为临时参考。一次小样本实验中，混合检索在 `25` 个有答案问题上明显优于纯向量，但无答案拒答率为 `0%`；这说明检索融合有效，但拒答阈值仍未解决，不能将该实验结果称为生产准确率。

## 常见问题

### 启动时报 Ollama 连接失败

确认 Ollama 服务已启动并检查：

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

如果没有 `nomic-embed-text`，执行 `ollama pull nomic-embed-text`。

### 启动时报 Redis 连接失败

确认 Redis 正在监听 `localhost:6379`。当前 `ChatHistory` 使用默认连接参数，没有在 `env.py` 暴露 Redis 主机、端口和密码配置。

### 改了 `chunk_size`，检索结果没有变化

修改配置只会影响下一次入库，不会自动重建现有 Chroma 数据。需要备份当前 `Chroma_db/`，再按“初始化知识库”执行入库，并核对 BM25 索引块数。

### 图片识别结果不准确

视觉模型对模糊、遮挡、低分辨率和复杂表格可能识别错误。金额、日期、发票号、审批结论等关键字段必须人工核对；图片中的文字也不会被当作系统指令执行。

### 为什么无关问题仍然返回资料

当前 BM25 只返回有词法匹配的候选，向量路也可能对语义相近但实际无关的问题给出结果；融合层没有最终的拒答阈值或 Rerank。正式使用前应增加无答案分类、融合分数校准、Rerank 或人工确认。

## 当前限制

- 知识库入库只读取 TXT；PDF、Word、Excel 和图片目前是对话附件能力，不会自动入库。
- 文本切块以固定长度为主，还没有按章节、条款、页码和表格结构化切块。
- Chroma 元数据目前主要是 `source`，尚未完整保存章节、版本、生效日期、权限和内容哈希。
- 现有入库使用顺序 ID，重复执行可能产生重复或覆盖风险，尚未实现稳定 ID 和版本化更新。
- Agent 当前只有 `vector_search` 工具，没有数据库查询、计算、审批系统或文件管理工具。
- HTTP 接口返回纯文本流，没有单独的结构化 `sources` 字段。
- 没有认证、细粒度文档权限、速率限制、审计日志和生产部署配置。
- Redis 只保留最近 10 条记录，且会话默认 48 小时过期。
- 流式响应中途断开时可能写入 `completed=false` 记录；尚未实现取消、重试和幂等处理。
- 前端图标依赖 CDN，离线环境可能无法显示。

## 后续路线

建议按以下顺序演进：

1. 用环境变量替代绝对路径、模型和 Redis 配置，并加入 `.env.example` 和启动健康检查。
2. 支持 PDF、Word、Excel 和扫描件 OCR 的知识库入库，保留页码和表格结构。
3. 使用内容哈希、文档版本、生效状态和稳定文本块 ID，实现幂等更新和旧版本隔离。
4. 将切块从固定长度扩展为章节/条款感知切块，补充标题、章节、页码等元数据过滤。
5. 增加查询改写、Rerank、无答案检测、引用结构化返回和固定评测集。
6. 为 Agent 工具增加参数校验、超时、重试、错误协议和调用链观测。
7. 增加认证、权限过滤、恶意文件扫描、附件清理、审计、Docker、CI、监控和备份恢复。

## 安全注意事项

- 不要提交 `.env`、API Key、Redis 密码、真实企业文档或客户附件。
- 当前附件校验是基础校验，生产环境还需要恶意文件扫描、配额、过期清理和访问审计。
- 生产环境应启用 HTTPS，并将 Cookie 的 `secure` 设置为 `True`。
- 企业制度问答只能作为工作辅助，不能替代法定审批、合规判断、客户适当性判断或重大风险决策。
- 对外部模型发送资料前，应确认数据脱敏、传输范围和供应商合规要求。

## 许可证

当前未指定许可证。如需公开发布，请补充许可证、第三方依赖声明和文档版权说明。
