# LangGraph 智能旅行助手

基于 LangGraph 与 MCP 的多智能体旅行规划助手。用户输入目的地、日期、交通方式、住宿偏好和旅行兴趣后，系统会调用地图、天气、POI 等工具，并生成结构化的多日旅行计划。

## 技术栈

后端：

- FastAPI
- LangChain
- LangGraph
- langchain-mcp-adapters
- 高德地图 MCP Server
- PostgreSQL / pgvector
- OpenAI-compatible LLM，如 DeepSeek
- Pydantic

前端：

- Vue 3
- TypeScript
- Vite
- Ant Design Vue
- Axios

## 后端主流程

```text
POST /api/trip/plan
  -> trip.py 接收 TripRequest
  -> get_trip_planner_agent()
  -> LangGraphTripPlanner.plan_trip()
  -> retrieve_knowledge
  -> search_attractions
  -> query_weather
  -> search_hotels
  -> plan_itinerary
  -> TripPlanResponse
```

核心文件：

- `backend/app/api/main.py`：FastAPI 应用入口与路由注册
- `backend/app/api/routes/trip.py`：旅行规划接口
- `backend/app/agents/trip_planner_agent.py`：LangGraph 多节点规划流程
- `backend/app/services/amap_service.py`：高德地图 MCP 工具封装
- `backend/app/services/rag_service.py`：PostgreSQL/pgvector RAG 检索增强
- `backend/app/services/llm_service.py`：LLM 客户端初始化
- `backend/app/models/schemas.py`：请求、响应与行程结构定义
- `backend/scripts/ingest_travel_guides.py`：旅行知识库入库脚本

## RAG 知识库

项目使用 `backend/data/travel_guides/*.md` 作为旅行知识库来源。入库流程：

```text
markdown攻略
  -> 文本切分
  -> embedding向量化
  -> PostgreSQL/pgvector存储
  -> 按用户城市和偏好相似度检索
  -> 注入最终行程规划prompt
```

首次使用 RAG 前，需要 PostgreSQL 已安装 `pgvector` 扩展，然后执行：

```bash
cd backend
python scripts/ingest_travel_guides.py
```

本地开发可以使用 Homebrew 安装并启动数据库：

```bash
brew install postgresql@17 pgvector
brew services start postgresql@17
/opt/homebrew/opt/postgresql@17/bin/createdb travel_planner
```

如果未配置 `DATABASE_URL`，系统会自动跳过 RAG 节点，保留原有 MCP 工具规划流程。默认 `RAG_EMBEDDING_PROVIDER=sentence_transformer`，使用本地下载的 `BAAI/bge-small-zh-v1.5` 中文 embedding 模型；如切换到 `openai`，再配置 `EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL`。

## 快速启动

后端：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

需要在 `.env` 中配置：

```text
AMAP_API_KEY=
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL_ID=
DATABASE_URL=
RAG_EMBEDDING_PROVIDER=sentence_transformer
RAG_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
RAG_EMBEDDING_DIMENSIONS=512
```
