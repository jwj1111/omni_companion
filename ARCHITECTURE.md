# Omni Companion — 当前架构文档

## 1. 项目定位

`omni_companion` 是一个面向游戏场景的网页端 AI 陪聊应用，基于阿里云 Qwen-Omni 系列模型，提供两种交互模式：

- **非沉浸文字模式**：文字聊天，可附带屏幕画面，支持可选语音回复。
- **沉浸实时模式**：实时麦克风语音输入、屏幕画面抽帧、模型流式音频和转写输出。

项目当前是 Web 单页应用 + FastAPI 后端，不使用 Electron。

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|---|---|---|
| 前端 | Vue 3 + Vite + Pinia | SPA，深色 START 风格界面 |
| 后端 | FastAPI + Uvicorn | HTTP API、WebSocket、配置与服务实例管理 |
| 非实时模型 | `qwen3.5-omni-plus` | OpenAI 兼容 HTTP 流式接口 |
| 实时模型 | `qwen3.5-omni-plus-realtime` | DashScope Realtime WebSocket |
| 音频输入 | Web Audio API | 前端采集 16kHz 16bit mono PCM |
| 音频输出 | Web Audio API + AudioWorklet | 播放 24kHz 16bit mono PCM |
| 屏幕监控 | `getDisplayMedia` | 浏览器屏幕共享预览与抽帧 |
| 部署 | Docker + Nginx | 前端静态服务，后端 API/WS 反代 |

---

## 3. 界面结构

```text
┌──────────────────────────────────────────────────────────────┐
│ 顶部栏：Logo / Omni Companion / 设置入口                      │
├────────────────────────────────────┬─────────────────────────┤
│                                    │ 模式 Tab + 操作区        │
│ 屏幕监控主区域                      ├─────────────────────────┤
│ - 开始/停止采集                     │ 非沉浸：消息列表         │
│ - 实时预览                          │ 沉浸：实时转写           │
│ - 供两种模式取帧                     │                         │
│                                    ├─────────────────────────┤
│                                    │ 输入框或麦克风控制       │
└────────────────────────────────────┴─────────────────────────┘
```

当前没有独立底部 `StatusBar`；状态信息以内联方式显示在对应面板内。

布局比例由 `frontend/src/App.vue` 控制：左侧屏幕监控为主，右侧对话栏为辅助。

---

## 4. 会话隔离

### 4.1 前端 session id

`frontend/src/services/session.js` 在浏览器 `localStorage` 中维护：

```text
omni_companion_session_id
```

HTTP 请求通过 Header 传递：

```text
X-Session-Id: <sessionId>
```

Realtime WebSocket 通过 query 传递：

```text
/api/realtime/ws?session_id=<sessionId>
```

### 4.2 后端隔离对象

`backend/app/dependencies.py` 按 session 隔离：

- `ConfigManager`
- `OmniChatService`
- `ScreenCaptureCache`

Realtime 服务不复用全局单例；每条 WebSocket 连接创建独立 `OmniRealtimeService`。

### 4.3 清理策略

默认配置：

```yaml
session:
  ttl_seconds: 1800
  cleanup_interval_seconds: 600
  max_sessions: 100
```

含义：

- 30 分钟无活动清理；
- 每 10 分钟扫描一次；
- 最多保留 100 个会话，超出清理最久未活跃会话。

---

## 5. 配置系统

### 5.1 文件分层

```text
.env                         # API Key / 区域
config/settings.yaml          # 默认技术配置
config/personas/*.yaml        # 角色人设
prompts/interaction_rules.txt # 通用行为规范
```

### 5.2 加载顺序

```text
代码默认值 < 文件默认配置 < 当前 session 运行期覆盖
```

角色音色优先级：

```text
persona.voice > settings.voice
```

### 5.3 运行期覆盖

设置页修改默认不写回文件，而是保存在当前 session 的 `ConfigManager` 内存覆盖中：

- `save_settings()`：运行期覆盖 `settings`
- `save_persona()`：运行期覆盖角色
- `save_interaction_rules()`：运行期覆盖行为规范
- `reset_runtime_overrides()`：清空覆盖

前端每次加载会调用：

```text
POST /api/settings/reset-runtime
POST /api/chat/clear
```

因此刷新页面会恢复文件中的默认配置，并开始新文字会话。

例外：

- `DASHSCOPE_API_KEY`、`DASHSCOPE_API_KEY_REALTIME` 会写入 `.env`。
- `API_REGION` 作为当前 session 运行期覆盖。
- `DELETE /api/settings/persona/{id}` 会删除对应 persona 文件。

---

## 6. System Prompt 组装

`ConfigManager.build_system_prompt()` 将当前角色和通用规则拼接：

```text
# 角色：<name>

## 性格
<personality>

## 背景身份
<background>

## 说话风格
<speaking_style>

## 与用户的关系
<relationship>

## 口癖
<quirks>

---

<prompts/interaction_rules.txt>
```

注入位置：

| 模式 | 注入方式 |
|---|---|
| 非实时 | `messages[0] = {role: "system", content: system_prompt}` |
| Realtime | `session.update.session.instructions = system_prompt` |

---

## 7. 非沉浸文字模式

### 7.1 数据流

```text
用户输入文本 / 图片
  ↓
frontend/src/views/NonImmersiveChat.vue
  ↓
frontend/src/stores/chat.js
  ↓
POST /api/chat/send
  ↓
backend/app/routers/chat.py
  ↓
backend/app/services/omni_chat.py
  ↓
Qwen-Omni 非实时 OpenAI-compatible stream
  ↓
逐行 JSON 返回 text/audio/done/error
  ↓
前端更新消息、播放语音
```

### 7.2 多模态输入

非沉浸模式支持：

- 纯文本；
- 用户手动上传图片；
- 屏幕监控开启时自动取当前帧。

前端会展示用户原话，并以紧凑附件标记“已附带画面”。

### 7.3 历史格式

后端只把 assistant 历史保存为纯文本：

```json
{"role": "assistant", "content": "..."}
```

这是为了符合非实时 OpenAI-compatible 多轮格式要求。

### 7.4 清空会话

文字模式有“清空会话”按钮，调用：

```text
POST /api/chat/clear
```

只清当前 `X-Session-Id` 对应的聊天历史。

---

## 8. 沉浸 Realtime 模式

### 8.1 数据流

```text
前端麦克风 16kHz PCM
  ↓
WebSocket /api/realtime/ws?session_id=...
  ↓
后端 input_audio_buffer.append
  ↓
DashScope Realtime API

前端屏幕帧 JPEG base64
  ↓
后端 input_image_buffer.append
  ↓
DashScope Realtime API

DashScope response.audio.delta
  ↓
后端转发 {type:"audio", data:"..."}
  ↓
前端播放 24kHz PCM

DashScope response.audio_transcript.* / input_audio_transcription.*
  ↓
后端转发 {type:"transcript", role, text, final}
  ↓
前端转写显示
```

### 8.2 session.update

由 `backend/app/services/omni_realtime.py::build_session_config()` 构造：

```json
{
  "modalities": ["text", "audio"],
  "voice": "persona 或 settings 读取",
  "instructions": "拼接后的 system prompt",
  "input_audio_format": "pcm",
  "output_audio_format": "pcm",
  "turn_detection": {
    "type": "semantic_vad",
    "threshold": 0.5,
    "silence_duration_ms": 800
  },
  "input_audio_transcription": {
    "model": "qwen3-asr-flash-realtime"
  },
  "enable_search": true
}
```

`enable_search` 由 `config/settings.yaml` 控制。

### 8.3 VAD 交互流程

官方 VAD 预期流程：

```text
1. 前端持续发送 input_audio_buffer.append
2. 云端检测 speech_started
3. 云端检测 speech_stopped
4. 云端自动 committed
5. 云端 response.created
6. 返回 response.audio.delta / response.audio_transcript.delta
7. response.done
```

项目当前不主动发送 `input_audio_buffer.commit` 或 `response.create`，保持 VAD 模式。

### 8.4 截图输入

- 前端只在用户说话期间推送截图，避免 image before audio。
- 后端 `image_processor.py` 会将图片转为 JPEG 并压缩到 Realtime 限制内。
- Realtime 单帧限制：base64 后 ≤ 256KB，推荐 480p/720p。

---

## 9. 音频架构

### 9.1 输入

`MicRecorder`：

- `getUserMedia()` 获取麦克风；
- `AudioContext({ sampleRate: 16000 })`；
- `ScriptProcessor` 转 `Float32` -> `Int16 PCM`；
- base64 后发送。

### 9.2 输出

`frontend/src/services/audio.js` 提供：

- `PcmStreamPlayer`：流式 PCM 播放，优先 `AudioWorklet` 环形缓冲；不支持时回退到 `AudioBufferSource` 排队。
- `AudioPlayer`：`PcmStreamPlayer` 的兼容别名，沉浸模式使用。
- `playPcmAudio()`：完整 PCM 音频一次性播放，用于“播放语音”按钮。
- `stopAllAudio()`：全局停止，避免两种模式串音。

音频规格：

| 方向 | 采样率 | 位深 | 声道 | 格式 |
|---|---:|---:|---:|---|
| 前端 -> Realtime | 16kHz | 16bit | mono | PCM base64 |
| Realtime -> 前端 | 24kHz | 16bit | mono | PCM base64 |
| 非实时音频 | 24kHz | 16bit | mono | API 返回 base64 PCM，前端按 PCM 播放 |

---

## 10. 前端服务地址

生产默认走同域反代：

- HTTP：`/api/...`
- WebSocket：根据页面协议自动推导 `ws://host/api/realtime/ws` 或 `wss://host/api/realtime/ws`

可通过 Vite 构建变量覆盖：

```env
VITE_API_BASE_URL=https://api.example.com
VITE_WS_BASE_URL=wss://api.example.com/api/realtime/ws
```

本地开发由 `frontend/vite.config.js` 代理到 `localhost:8000`。

---

## 11. Docker 部署架构

```text
Browser
  ↓ HTTP / WebSocket
Nginx frontend container
  ├─ /               -> Vue dist
  ├─ /api/*          -> backend:8000
  ├─ /api/realtime/ws -> backend WebSocket
  ├─ /health         -> backend health
  └─ /docs           -> backend docs

Backend container
  ├─ FastAPI / Uvicorn
  ├─ /app/config  <- host ./config readonly
  └─ /app/prompts <- host ./prompts readonly
```

入口文件：

- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker-compose.yml`
- `deploy/nginx.conf`

详细说明：`deploy/README.md`。

---

## 12. 后端 API 概览

| 模块 | 路径 | 说明 |
|---|---|---|
| Chat | `POST /api/chat/send` | 非实时流式聊天 |
| Chat | `GET /api/chat/history` | 当前 session 历史 |
| Chat | `POST /api/chat/clear` | 清空当前 session 历史 |
| Realtime | `WS /api/realtime/ws` | 实时语音 WebSocket |
| Settings | `GET /api/settings/all` | 当前 session 配置视图 |
| Settings | `PUT /api/settings/update` | 当前 session settings 覆盖 |
| Settings | `POST /api/settings/reset-runtime` | 清除当前 session 运行期覆盖 |
| Settings | `PUT /api/settings/env` | API Key 持久化 / 区域运行期覆盖 |
| Settings | `GET/PUT /api/settings/rules` | 行为规范读取/运行期覆盖 |
| Screenshot | `POST /api/screenshot` | 上传当前 session 截图缓存 |

---

## 13. 关键约束

1. 非实时 API 必须 `stream=True`。
2. 非实时多轮 assistant message 只保存纯文本。
3. Realtime 输入音频必须是 `16kHz / 16bit / mono PCM`。
4. Realtime 输出音频是 `24kHz / 16bit / mono PCM`。
5. Realtime 图片必须是 JPEG，base64 后不超过 256KB。
6. 联网搜索与工具调用不兼容；当前项目只暴露联网搜索开关。
7. `.env` 不入仓库；使用 `.env.example` 作为模板。
8. 设置页修改默认只影响当前浏览器 session，刷新恢复默认。

---

## 14. 后续演进建议

| 优先级 | 方向 | 说明 |
|---|---|---|
| P0 | 生产 HTTPS/WSS 入口 | Docker 外层接 Caddy/Nginx/云 LB |
| P1 | 文档拆分 | 将官方参考文档迁入 `docs/reference/` |
| P1 | 日志与错误上报 | Realtime 事件链、API 错误、前端播放错误可观测 |
| P2 | 历史持久化 | 当前会话历史在内存中，重启即丢 |
| P2 | Realtime 专用播放器 | 若需要更低延迟，可拆出专用 PCM 播放器 |
| P3 | 用户认证 | 多用户公网部署时需要登录态与配额控制 |
