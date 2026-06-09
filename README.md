# 🚦 LicenseLight — 版权合规副驾驶

面向设计师和独立开发者的版权合规检测工具。上传设计图片，自动识别字体和图片来源的版权风险，提供清晰的红绿灯合规报告。

## 功能特性

- **🔍 OCR 文字提取** — 使用 PaddleOCR 提取图片中所有文字及其位置
- **🎨 字体识别** — 通过 Claude 3.5 Sonnet 视觉能力识别字体特征，匹配本地 300+ 字体授权数据库
- **🖼️ 图片来源溯源** — Google 反向图片搜索 + 主流图库授权解析
- **🚦 红绿灯报告** — Green/Yellow/Red 三级风险分类，清晰易懂
- **💡 替代建议** — 高风险字体自动推荐免费商用替代方案
- **📱 现代 UI** — Next.js + Tailwind CSS + shadcn/ui，支持拖放上传

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| 后端 | Python FastAPI, Pydantic v2 |
| 数据库 | PostgreSQL 15, SQLAlchemy 2.0 (async) |
| 任务队列 | Celery + Redis |
| AI | Anthropic Claude 3.5 Sonnet (图片分析 + 文本生成) |
| OCR | PaddleOCR (中英文) |
| 图片搜索 | Google Custom Search API |
| 部署 | Docker Compose |

## 快速开始

### 前置要求

- Docker & Docker Compose
- Anthropic Claude API Key ([获取地址](https://console.anthropic.com/))
- Google Custom Search API Key + CSE ID ([配置指南](#配置-google-custom-search))

### 1. 克隆并配置环境变量

```bash
git clone <repo-url> && cd LicenseLight
cp .env.example .env
# 编辑 .env，填入你的 API Keys
```

### 2. 启动所有服务

```bash
docker compose up -d
```

服务启动后：
- **前端**: http://localhost:3000
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

### 3. 初始化字体数据库

```bash
# 进入 API 容器执行种子脚本
docker compose exec api python scripts/seed_fonts.py
```

### 4. 开始使用

打开 http://localhost:3000，上传一张设计图片，等待分析完成即可查看版权合规报告。

## 环境变量说明

| 变量 | 说明 | 必需 |
|------|------|------|
| `CLAUDE_API_KEY` | Anthropic Claude API 密钥 | ✅ |
| `GOOGLE_API_KEY` | Google Cloud API 密钥 | ✅ |
| `GOOGLE_CSE_ID` | Google Custom Search Engine ID | ✅ |
| `DATABASE_URL` | PostgreSQL 连接字符串 | ✅ |
| `REDIS_URL` | Redis 连接字符串 | ✅ |
| `SECRET_KEY` | 应用密钥 | ✅ |
| `UPLOAD_DIR` | 图片上传目录 | ❌ (默认 ./uploads) |
| `MAX_UPLOAD_SIZE_MB` | 最大上传大小 | ❌ (默认 20MB) |

## 配置 Google Custom Search

1. 前往 [Google Cloud Console](https://console.cloud.google.com/apis/credentials) 创建 API 密钥
2. 启用 **Custom Search API**
3. 前往 [Programmable Search Engine](https://programmablesearchengine.google.com/) 创建搜索引擎
   - 搜索范围选择"搜索整个网络"
   - 在设置中启用**图片搜索**
4. 将 API Key 填入 `GOOGLE_API_KEY`，Search Engine ID 填入 `GOOGLE_CSE_ID`

> **注意**: Google CSE 免费额度为每天 100 次查询。生产环境建议升级。

## API 端点

### 上传图片进行分析
```bash
POST /api/v1/check/image
Content-Type: multipart/form-data

# 返回: { "task_id": "...", "status": "pending" }
```

### 查询分析状态
```bash
GET /api/v1/check/status/{task_id}

# 返回: { "task_id": "...", "status": "completed", "result": {...} }
```

### 搜索字体授权信息
```bash
GET /api/v1/fonts/search?q=方正黑体

# 返回: [{ "font": {...}, "match_type": "name", "score": 1.0 }]
```

### 健康检查
```bash
GET /api/health
```

## 报告结构

```json
{
  "overall_risk": "red",
  "fonts": [
    {
      "name": "方正黑体",
      "risk": "red",
      "explanation": "商业使用需购买方正字库授权...",
      "alternatives": ["思源黑体", "阿里巴巴普惠体"]
    }
  ],
  "image_source": {
    "source_url": "https://shutterstock.com/...",
    "risk": "yellow",
    "explanation": "Shutterstock 为付费图库...",
    "alternatives": ["https://unsplash.com"]
  },
  "summary": "检测到2项高风险...建议替换为..."
}
```

## 字体数据库

预置 **300+ 字体** 授权信息，涵盖：

- **中文字体** (200+): 方正字库、汉仪字库、华康字库、站酷、思源、阿里巴巴普惠体、造字工房、霞鹜文楷等
- **英文字体** (100+): Google Fonts、Adobe Fonts、Fontshare、系统字体等

每款字体包含：名称、厂商、授权类型、商业使用许可、署名要求、嵌入许可、价格参考等。

## 项目结构

```
LicenseLight/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # API 路由
│   │   ├── core/           # 配置、数据库
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic 验证
│   │   ├── services/       # 核心业务逻辑
│   │   │   ├── license_parsers/  # 图库授权解析器
│   │   ├── tasks/          # Celery 任务
│   │   └── main.py         # FastAPI 入口
│   ├── scripts/
│   │   └── seed_fonts.py   # 字体数据库种子脚本
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js 页面
│   │   ├── components/     # React 组件
│   │   ├── lib/            # API 客户端 + 工具
│   │   └── types/          # TypeScript 类型
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## 开发指南

### 仅启动后端

```bash
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 仅启动 Celery Worker

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

### 仅启动前端

```bash
cd frontend
npm install
npm run dev
```

### 运行测试

```bash
# 后端
cd backend
pytest tests/ -v

# 前端
cd frontend
npx vitest run
```

## 数据飞轮

每次用户反馈（误判/漏判）可通过以下方式记录：

1. 在 `AnalysisJob` 表中添加 `user_feedback` 字段
2. 收集误判案例的图片 URL、OCR 结果、实际字体/来源信息
3. 定期导出为微调数据集
4. 用于后续模型迭代升级准确率

## 许可证

MIT License
