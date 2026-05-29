# Omni Companion 后端

FastAPI 后端负责：

- 非实时 Qwen-Omni HTTP 流式聊天；
- Realtime WebSocket 代理；
- 配置、角色、行为规范加载；
- 按浏览器 session 隔离聊天历史、运行期设置和截图缓存；
- 图片预处理与截图缓存。

---

## 本地启动

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

访问：

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

生产容器启动使用：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 环境变量

项目根目录 `.env`：

```env
DASHSCOPE_API_KEY=sk-your-api-key
API_REGION=beijing

# 可选：Realtime 独立 Key；不填时复用 DASHSCOPE_API_KEY
# DASHSCOPE_API_KEY_REALTIME=sk-your-realtime-api-key
```

`API_REGION`：

- `beijing` -> `dashscope.aliyuncs.com`
- `singapore` -> `dashscope-intl.aliyuncs.com`

---

## Session 隔离

前端为每个浏览器生成 `sessionId`。

HTTP 请求：

```text
X-Session-Id: <sessionId>
```

Realtime WebSocket：

```text
/api/realtime/ws?session_id=<sessionId>
```

后端按 session 隔离：

- `ConfigManager`
- `OmniChatService`
- `ScreenCaptureCache`

默认清理策略来自 `config/settings.yaml`：

```yaml
session:
  ttl_seconds: 1800
  cleanup_interval_seconds: 600
  max_sessions: 100
```

---

## API 概览

### 非沉浸模式：`/api/chat`

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/chat/send` | 发送消息，逐行 JSON 流式返回 |
| `GET` | `/api/chat/history` | 获取当前 session 对话历史 |
| `POST` | `/api/chat/clear` | 清空当前 session 对话历史，保留 system prompt |

`POST /api/chat/send` 请求：

```json
{
  "content": "你好",
  "output_audio": true
}
```

或多模态：

```json
{
  "content": [
    {"type": "text", "text": "看下这张图"},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
  ],
  "output_audio": true
}
```

返回格式：每行一个 JSON：

```json
{"type":"text","data":"..."}
{"type":"audio","data":"base64..."}
{"type":"done","data":{}}
{"type":"error","data":"..."}
```

注意：后端保存 assistant 历史时只保存纯文本，符合非实时多轮格式要求。

---

### 沉浸模式：`/api/realtime`

| 路径 | 说明 |
|---|---|
| `WS /api/realtime/ws?session_id=...` | 浏览器和后端之间的 Realtime 代理通道 |

前端 -> 后端消息：

```json
{"type":"control","action":"start"}
{"type":"audio","data":"base64-pcm"}
{"type":"screenshot","data":"base64-jpeg"}
{"type":"control","action":"stop"}
```

后端 -> 前端消息：

```json
{"type":"status","event":"connected"}
{"type":"status","event":"input_audio_buffer.speech_started"}
{"type":"status","event":"input_audio_buffer.speech_stopped"}
{"type":"status","event":"response.done"}
{"type":"audio","data":"base64-pcm"}
{"type":"transcript","role":"user","text":"...","final":true}
{"type":"transcript","role":"assistant","text":"...","final":false}
{"type":"error","message":"..."}
```

后端保持 VAD 模式：

- 前端持续发送 16kHz PCM；
- 后端转发 `input_audio_buffer.append`；
- 云端返回 `speech_started` / `speech_stopped` / `committed` / `response.*`；
- 后端不主动发送 `input_audio_buffer.commit` 或 `response.create`。

---

### 设置管理：`/api/settings`

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/settings/all` | 获取当前 session 可见配置、角色、行为规范 |
| `PUT` | `/api/settings/update` | 应用当前 session 的 settings 运行期覆盖 |
| `POST` | `/api/settings/reset-runtime` | 清除当前 session 运行期覆盖 |
| `PUT` | `/api/settings/env` | 更新 API Key；区域作为当前 session 运行期覆盖 |
| `GET` | `/api/settings/personas` | 列出 persona 文件 |
| `GET` | `/api/settings/persona/{id}` | 获取 persona |
| `PUT` | `/api/settings/persona/{id}` | 应用当前 session 的 persona 运行期覆盖 |
| `DELETE` | `/api/settings/persona/{id}` | 删除 persona 文件 |
| `GET` | `/api/settings/rules` | 获取行为规范 |
| `PUT` | `/api/settings/rules` | 应用当前 session 的行为规范运行期覆盖 |
| `GET` | `/api/settings/voices` | 获取内置音色列表 |

运行期覆盖说明：

- `settings`、`persona`、`rules` 默认不写回文件；
- 页面刷新会调用 `/api/settings/reset-runtime` 恢复默认；
- API Key 会写入 `.env`；
- `API_REGION` 是当前 session 运行期覆盖。

---

### 截屏：根路径

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/screenshot` | 上传当前 session 截图缓存 |

请求：

```json
{"image_b64":"..."}
```

---

## 配置与模型

默认配置文件：`config/settings.yaml`

```yaml
models:
  non_realtime: "qwen3.5-omni-plus"
  realtime: "qwen3.5-omni-plus-realtime"

output:
  modalities: ["text", "audio"]

realtime:
  vad_type: "semantic_vad"
  vad_threshold: 0.5
  silence_duration_ms: 800
  enable_search: true
  input_audio_transcription: true
  transcription_model: "qwen3-asr-flash-realtime"

non_realtime:
  enable_search: true
```

角色与行为规范：

- `config/personas/a001.yaml`
- `prompts/interaction_rules.txt`

System prompt 由 `ConfigManager.build_system_prompt()` 拼接，并同时用于非实时和 Realtime。

---

## 图片与音频处理

### 图片

`image_processor.py` 对 Realtime 截图做兜底处理：

- 输出 JPEG；
- 分辨率不超过 720p；
- base64 后不超过 256KB。

### 音频

- 输入 Realtime：16kHz / 16bit / mono PCM；
- 输出 Realtime：24kHz / 16bit / mono PCM；
- 非实时音频：按 24kHz PCM 在前端播放。

后端不播放音频，只转发给前端。

---

## 测试

### 离线测试

```bash
python tests/test_config_manager.py
```

### 交互式测试

```bash
# 非实时：文字聊天，可发图片
python tests/interactive_chat.py

# Realtime：麦克风实时对话，需要 pyaudio
pip install pyaudio
python tests/interactive_realtime.py
```

### API 测试

需要先启动后端：

```bash
python run.py
```

再运行：

```bash
python tests/test_settings_api.py
python tests/test_chat_api.py
python tests/test_realtime_api.py
```

### 批量运行

```bash
python -m pytest tests/ -v
```

测试说明：

| 文件 | 内容 | 是否需要后端 | 是否消耗 token |
|---|---|---|---|
| `test_config_manager.py` | 配置加载、prompt 组装 | 否 | 否 |
| `test_settings_api.py` | 设置 API | 是 | 否 |
| `test_chat_api.py` | 非实时聊天 | 是 | 是 |
| `test_realtime_api.py` | Realtime WS 启停 | 是 | 是 |
| `interactive_chat.py` | 命令行非实时聊天 | 否 | 是 |
| `interactive_realtime.py` | 命令行实时语音 | 否 | 是 |

---

## Docker 部署

根目录已提供：

- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker-compose.yml`
- `deploy/nginx.conf`
- `deploy/README.md`

启动：

```bash
cd ..
cp .env.example .env
# 编辑 .env

docker compose up -d --build
```

默认访问：http://localhost:8080

---

## 后端项目结构

```text
backend/
├─ run.py
├─ requirements.txt
├─ README.md
├─ app/
│  ├─ main.py
│  ├─ dependencies.py
│  ├─ routers/
│  │  ├─ chat.py
│  │  ├─ realtime.py
│  │  └─ settings.py
│  └─ services/
│     ├─ config_manager.py
│     ├─ image_processor.py
│     ├─ omni_chat.py
│     ├─ omni_realtime.py
│     └─ screen_capture.py
└─ tests/
```
