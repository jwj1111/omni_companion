# 游戏AI陪聊

基于阿里云 Qwen-Omni 系列模型的游戏 AI 陪聊应用。支持非沉浸（文字聊天）和沉浸（实时语音）两种模式。

---

## 环境要求

| 依赖 | 版本要求 |
|---|---|
| Python | >= 3.11 |
| Node.js | >= 18（前端开发用） |
| 浏览器 | Chrome / Edge（需支持 `getDisplayMedia`） |
| 操作系统 | Windows / macOS / Linux |

---

## 快速启动

### 1. 配置 API Key

在项目根目录创建 `.env` 文件（已有的话直接编辑）：

```env
DASHSCOPE_API_KEY=sk-你的apikey
API_REGION=beijing
```

> 获取 API Key：https://help.aliyun.com/zh/model-studio/get-api-key  
> 区域可选：`beijing`（北京）或 `singapore`（新加坡）

### 2. 启动后端

```bash
cd backend

# 创建虚拟环境（首次）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# 安装依赖（首次）
pip install -r requirements.txt

# 启动服务
python run.py
```

启动后：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 3. 启动前端

```bash
cd frontend

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

启动后浏览器访问：http://localhost:5173

---

## 项目结构

```
project/
├─ .env                          # API Key（敏感，不入仓库）
├─ .gitignore
├─ README.md                     # 本文件
├─ ARCHITECTURE.md               # 架构设计文档
│
├─ config/
│   ├─ settings.yaml             # 应用技术配置
│   └─ personas/
│       └─ a001.yaml             # 角色人设
│
├─ prompts/
│   └─ interaction_rules.txt     # 通用行为规范
│
├─ backend/                      # Python 后端（FastAPI）
│   ├─ run.py                    # 启动入口
│   ├─ requirements.txt
│   ├─ README.md                 # 后端API详细文档
│   └─ app/
│       ├─ main.py
│       ├─ dependencies.py
│       ├─ routers/
│       │   ├─ chat.py           # 非沉浸模式
│       │   ├─ realtime.py       # 沉浸模式
│       │   └─ settings.py       # 设置管理
│       └─ services/
│           ├─ config_manager.py
│           ├─ omni_chat.py
│           ├─ omni_realtime.py
│           └─ screen_capture.py
│
├─ frontend/                     # Vue 3 前端
│   ├─ package.json
│   ├─ vite.config.js
│   ├─ index.html
│   └─ src/
│       ├─ main.js
│       ├─ App.vue
│       ├─ router/
│       ├─ views/
│       ├─ components/
│       └─ stores/
│
└─ docs/                         # 参考文档
    ├─ omni_realtime调用说明.md
    └─ omni_非实时调用说明.md
```

---

## 两种模式

| 模式 | 交互方式 | 特点 |
|---|---|---|
| 非沉浸 | 打字聊天 + 可附截图 | 支持文本/图片多模态，延迟 2~5s |
| 沉浸 | 实时语音 + 持续画面 | 亚秒延迟，支持打断，像打电话 |

---

## 常见问题

### Q: 两个模式用的同一个 API Key 吗？

默认共用 `DASHSCOPE_API_KEY`。如果实时和非实时需要不同 Key，在 `.env` 中加：

```env
DASHSCOPE_API_KEY_REALTIME=sk-另一个key
```

### Q: 怎么切换角色？

在设置面板中切换，或直接编辑 `config/settings.yaml` 的 `active_persona` 字段。

### Q: 屏幕监控怎么用？

点击左侧面板的"开始采集"，浏览器会弹出屏幕共享选择窗口。选择游戏窗口后即开始实时预览和采集。

### Q: 后端端口被占用了？

编辑 `backend/run.py` 修改 `port=8000` 为其他端口。
