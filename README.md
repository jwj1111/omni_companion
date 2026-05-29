# Omni Companion / 游戏 AI 陪聊

基于阿里云 Qwen-Omni 系列模型的网页端游戏 AI 陪聊应用。当前支持：

- **非沉浸文字模式**：文字聊天、自动附带当前屏幕帧、可选语音回复、清空当前会话。
- **沉浸实时模式**：浏览器麦克风实时语音、屏幕监控抽帧、云端 VAD、模型流式音频与转写。
- **多人会话隔离**：浏览器本地生成 `sessionId`，后端按会话隔离配置、聊天历史和截图缓存。
- **运行期设置**：设置页修改只影响当前浏览器会话；刷新后恢复 `config/` 与 `prompts/` 中的默认值。
- **Docker 基础部署**：已提供前后端镜像、Nginx 反代和 `docker-compose.yml`。

---

## 环境要求

| 依赖 | 版本要求 | 说明 |
|---|---|---|
| Python | >= 3.11 | 后端 FastAPI |
| Node.js | >= 18 | 前端开发与构建 |
| 浏览器 | Chrome / Edge | 需支持 `getDisplayMedia`、Web Audio、WebSocket |
| Docker | 可选 | 服务器部署推荐 |

---

## 快速启动：本地开发

### 1. 配置 API Key

复制示例环境变量：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
DASHSCOPE_API_KEY=sk-your-api-key
API_REGION=beijing

# 可选：Realtime 独立 Key；不填时复用 DASHSCOPE_API_KEY
# DASHSCOPE_API_KEY_REALTIME=sk-your-realtime-api-key
```

`API_REGION` 可选：

- `beijing`
- `singapore`

### 2. 启动后端

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
python run.py
```

后端地址：

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

前端开发服务器已通过 `vite.config.js` 代理：

- `/api/*` -> `http://localhost:8000/api/*`
- `/api/realtime/ws` -> 后端 WebSocket

因此前端默认走同域路径，不再硬编码 `localhost:8000`。

---

## Docker 基础部署

```bash
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY

docker compose up -d --build
```

默认访问：

- 前端：http://服务器IP 或 http://localhost
- 健康检查：http://服务器IP/health
- API 文档：http://服务器IP/docs

默认 compose 映射宿主机 80 端口；如果 80 已被占用，可改成 `8080:80` 后使用 `http://服务器IP:8080`。

更多说明见：`deploy/README.md`。

---

## 项目结构

```text
omni_companion/
├─ .env.example                  # 环境变量模板
├─ .dockerignore
├─ Dockerfile.backend
├─ Dockerfile.frontend
├─ docker-compose.yml
├─ deploy/
│  ├─ nginx.conf                 # 前端静态服务 + API/WS 反代
│  └─ README.md                  # Docker 部署说明
├─ config/
│  ├─ settings.yaml              # 默认技术配置
│  └─ personas/
│     └─ a001.yaml               # 当前角色人设
├─ prompts/
│  └─ interaction_rules.txt      # 通用行为规范
├─ backend/
│  ├─ run.py
│  ├─ requirements.txt
│  ├─ README.md
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ dependencies.py         # session 隔离、服务实例管理
│  │  ├─ routers/
│  │  │  ├─ chat.py
│  │  │  ├─ realtime.py
│  │  │  └─ settings.py
│  │  └─ services/
│  │     ├─ config_manager.py
│  │     ├─ omni_chat.py
│  │     ├─ omni_realtime.py
│  │     ├─ image_processor.py
│  │     └─ screen_capture.py
│  └─ tests/
├─ frontend/
│  ├─ package.json
│  ├─ vite.config.js
│  ├─ public/
│  │  └─ audio-worklet/
│  └─ src/
│     ├─ App.vue
│     ├─ services/
│     ├─ stores/
│     ├─ views/
│     └─ components/
├─ ARCHITECTURE.md               # 当前架构说明
├─ omni_realtime调用说明.md       # 官方 Realtime 参考快照
├─ omni_非实时调用说明.md         # 官方非实时参考快照
└─ omni音色列表.md                # 官方音色参考快照
```

---

## 两种模式

| 模式 | 入口 | 输入 | 输出 | 说明 |
|---|---|---|---|---|
| 非沉浸文字模式 | 右侧“文字对话” | 文本、手动图片、屏幕监控当前帧 | 流式文本、可选语音 | 适合打字、发截图、复盘游戏画面 |
| 沉浸实时模式 | 右侧“实时语音” | 16kHz PCM 麦克风流、屏幕抽帧 | 24kHz PCM 流式音频、转写文本 | 适合边玩边语音陪聊 |

---

## 会话隔离

前端在 `localStorage` 中生成 `omni_companion_session_id`，并通过：

- HTTP Header：`X-Session-Id`
- Realtime WebSocket Query：`?session_id=...`

传给后端。后端按 session 隔离：

- 非实时聊天历史
- 运行期设置覆盖
- 角色运行期覆盖
- 截图缓存

默认会话清理策略在 `config/settings.yaml`：

```yaml
session:
  ttl_seconds: 1800
  cleanup_interval_seconds: 600
  max_sessions: 100
```

---

## 配置原则

默认配置权威来源：

- `config/settings.yaml`
- `config/personas/*.yaml`
- `prompts/interaction_rules.txt`
- `.env`

设置页的修改是**当前会话运行期覆盖**：

- 刷新页面后前端会调用 `/api/settings/reset-runtime` 恢复默认配置。
- API Key 会写入 `.env`。
- `API_REGION` 只作为当前会话运行期覆盖。
- 角色、规则、技术参数默认不写回文件。

---

## 音频策略

- 麦克风输入：`16kHz / 16bit / mono PCM`。
- Realtime 输出：`24kHz / 16bit / mono PCM`。
- 非实时输出：API 返回音频 base64，前端保存完整音频，完成后可点击播放。
- 自动流式播放：前端使用 `AudioWorklet` 环形缓冲，浏览器不支持时回退到 `AudioBufferSource` 排队播放。
- 点击播放完整语音：使用完整 PCM 一次性构建 `AudioBuffer` 播放。

---

## 常见问题

### Q: 两个模式用同一个 API Key 吗？

默认共用 `DASHSCOPE_API_KEY`。Realtime 可单独配置：

```env
DASHSCOPE_API_KEY_REALTIME=sk-your-realtime-api-key
```

### Q: 设置页改了为什么刷新后恢复？

这是当前设计。默认值由文件配置维护，设置页只做当前浏览器会话的运行期覆盖，方便临时试参数且避免误改默认配置。

### Q: 屏幕监控怎么用？

点击左侧“开始采集”，选择游戏窗口或屏幕。非沉浸模式会在发送消息时自动取当前帧；沉浸模式会在用户说话期间按配置间隔推送画面帧。

### Q: 部署后 WebSocket 要注意什么？

如果使用 HTTPS，WebSocket 必须走 `wss://`。默认 Docker 部署通过同域 `/api/realtime/ws` 反代，外层 HTTPS 入口需要支持 WebSocket Upgrade。

---

## 参考文档

根目录中的以下文件是官方资料快照，不等同于项目实现文档：

- `omni_realtime调用说明.md`
- `omni_非实时调用说明.md`
- `omni音色列表.md`
