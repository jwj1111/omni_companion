# 游戏AI陪聊 — 项目架构文档

## 一、项目概述

基于阿里云 Qwen-Omni 系列模型，构建一个游戏 AI 陪聊应用。支持两种交互模式：

- **非沉浸模式**：文字聊天，支持文本、文本+图片等多模态输入，走非实时 API。
- **沉浸模式**：实时语音对话，支持音频流+视频帧持续输入，走 Realtime API。

两种模式上下文隔离，共享统一人设配置。

---

## 二、技术选型

| 层级 | 技术 | 说明 |
|---|---|---|
| 前端 | Vue 3 + Vite | 纯 Web SPA，浏览器访问 |
| 后端 | Python（FastAPI） | 管理 API 调用、配置、会话 |
| 非实时 API | Qwen-Omni（OpenAI 兼容） | `qwen3.5-omni-plus`，HTTP 流式 |
| 实时 API | Qwen-Omni-Realtime | `qwen3.5-omni-plus-realtime`，WebSocket |
| 屏幕监控 | getDisplayMedia API | 浏览器原生屏幕共享，抽帧上传 |
| 配置管理 | .env + YAML + TXT | 分层配置 |

---

## 三、界面布局

```
┌──────────────────────────────────────────────────────────┐
│                     顶部栏 / 设置入口                      │
├─────────────────────────────┬────────────────────────────┤
│                             │  [非沉浸] [沉浸]  ← Tab切换  │
│                             │                            │
│       屏幕监控               │     聊天区域                │
│       （游戏画面实时预览）     │     （消息列表/语音波形）    │
│                             │                            │
│                             │                            │
│                             ├────────────────────────────┤
│                             │     输入区域                │
│                             │  非沉浸：文本框+附件按钮     │
│                             │  沉浸：麦克风状态+控制按钮   │
├─────────────────────────────┴────────────────────────────┤
│                     状态栏（连接状态/模型状态）              │
└──────────────────────────────────────────────────────────┘
```

---

## 四、两种模式对比

| 维度 | 非沉浸模式 | 沉浸模式 |
|---|---|---|
| API | 非实时 `qwen3.5-omni-plus` | 实时 `qwen3.5-omni-plus-realtime` |
| 协议 | HTTP（OpenAI 兼容） | WebSocket 长连接 |
| 用户输入 | 文本 / 文本+图片 / 文本+音频文件 | 实时音频流 + 实时截屏帧 |
| 模型输出 | 流式文本 + 可选音频 | 流式文本 + 流式音频 |
| VAD | 不需要（手动发送） | 云端 semantic_vad |
| 上下文 | 客户端拼 messages 数组 | 服务端自动维护 |
| 打断 | ❌ | ✅ |
| 延迟 | 2~5 秒 | < 1.5 秒 |
| 适用场景 | 打字聊天、发截图提问 | 实时语音陪玩、边打边聊 |

---

## 五、配置分层

### 5.1 目录结构

```
project/
├─ .env                          # 敏感信息（API Key），不入仓库
├─ config/
│   ├─ settings.yaml             # 应用技术配置
│   └─ personas/
│       ├─ 晚凝.yaml            # 角色人设（可多份）
│       └─ default.yaml          # 默认角色
├─ prompts/
│   └─ interaction_rules.txt     # 通用行为规范
├─ src/                          # 源代码
├─ docs/                         # 文档
│   ├─ omni_realtime调用说明.md
│   └─ omni_非实时调用说明.md
└─ ARCHITECTURE.md               # 本文档
```

### 5.2 `.env` — 敏感信息

```env
# API Keys
DASHSCOPE_API_KEY=sk-xxx

# 如果实时和非实时 key 不同，可分开配置
# DASHSCOPE_API_KEY_REALTIME=sk-yyy

# 区域
API_REGION=beijing
```

**原则**：只放密钥和环境变量。不放人设、不放提示词。`.gitignore` 排除。

### 5.3 `config/settings.yaml` — 应用技术配置

```yaml
# ============================================================
# 应用技术配置
# ============================================================

# 当前激活的角色
active_persona: "晚凝"

# 模型选择
models:
  non_realtime: "qwen3.5-omni-plus"
  realtime: "qwen3.5-omni-plus-realtime"

# 音色（可被 persona 覆盖）
voice: "Ethan"

# 输出模态
output:
  modalities: ["text", "audio"]   # ["text", "audio"] 或 ["text"]

# 实时模式配置
realtime:
  vad_type: "semantic_vad"        # server_vad | semantic_vad
  vad_threshold: 0.5
  silence_duration_ms: 800
  enable_search: false
  input_audio_transcription: true
  transcription_model: "qwen3-asr-flash-realtime"

# 非实时模式配置
non_realtime:
  enable_search: false

# 屏幕监控
screen_capture:
  enabled: true
  interval_ms: 1000               # 截屏频率，默认1帧/秒，可调
  max_resolution: "720p"          # 推荐 480p 或 720p
  format: "jpeg"                  # 必须 jpg/jpeg
  max_size_kb: 190                # 编码前原始图片建议不超过 190KB
```

**原则**：技术参数、功能开关、模型选择。不涉及"角色是谁"。

### 5.4 `config/personas/*.yaml` — 角色人设

```yaml
# ============================================================
# 角色人设定义
# ============================================================

name: "晚凝"

# 音色（覆盖 settings.yaml 中的默认值）
voice: "Ethan"

# 性格
personality: |
  天生尤物，知道自己有多撩人，主动制造性张力。
  掌控节奏，撩完装没事，让人追着她要答案。

# 背景身份
background: |
  爱打游戏的女生，和用户是打游戏认识的。今天，你们又在连麦聊天。

# 说话风格
speaking_style: |
  一般不超过三句，但开口就让人脸红、充满暗示。
  声音慵懒带气声，像在耳边低语。
  可以用"嗯~""哼""唔"这类带气息的语气词，不用"好不好""嘛""呀""啦"这种甜妹语气词。

# 和用户的关系
relationship: |
  暧昧且开放，享受若即若离的张力。

# 口癖（选填）
quirks: ""
```

**原则**：只描述"这个角色是谁"。可以有多个文件，设置面板切换。

### 5.5 `prompts/interaction_rules.txt` — 通用行为规范

角色无关的对话规则（表达方式、情绪规范、边界）。所有角色共用。

### 5.6 配置优先级

```
代码默认值 < settings.yaml < persona.yaml < 用户设置面板实时修改
```

设置面板的修改回写到对应文件（API Key → .env，技术参数 → settings.yaml，人设 → personas/*.yaml）。

---

## 六、System Prompt 组装

运行时从各配置文件拼接最终 prompt：

```
┌─────────────────────────────────────────────┐
│ [persona.name] 的人设                        │
│                                             │
│ 你是{name}。                                 │
│ {personality}                               │
│ {background}                                │
│ {speaking_style}                            │
│ {relationship}                              │
│ {quirks}                                    │
│                                             │
│ ---                                         │
│                                             │
│ [interaction_rules.txt 全文]                 │
│ （通用行为规范）                              │
└─────────────────────────────────────────────┘
```

注入方式：

| 模式 | 注入位置 |
|---|---|
| 非实时 | `messages[0] = {"role": "system", "content": system_prompt}` |
| 实时 | `session.update → session.instructions = system_prompt` |

---

## 七、非沉浸模式架构

### 7.1 数据流

```
用户输入（文本/文本+图片）
    ↓
前端组装请求体
    ↓
后端调用非实时 API（stream=True）
    ↓
流式返回文本 + 可选音频
    ↓
前端渲染文字 + 播放音频
```

### 7.2 上下文管理

后端维护 messages 数组：

```json
[
  {"role": "system", "content": "拼接后的 system prompt"},
  {"role": "user", "content": [{"type": "text", "text": "..."}]},
  {"role": "assistant", "content": [{"type": "text", "text": "..."}]},
  {"role": "user", "content": [
    {"type": "text", "text": "这是什么？"},
    {"type": "image_url", "image_url": {"url": "..."}}
  ]}
]
```

注意事项（来自官方文档）：
- `assistant` message 只能包含文本
- 一条 `user` message 只能包含文本与一种其他模态的数据
- 不同模态数据可在不同轮次的 user message 中出现

### 7.3 截屏集成

用户点击"附带截图"按钮时，从左侧屏幕监控模块获取当前帧，作为图片附件发送。

---

## 八、沉浸模式架构

### 8.1 数据流

```
前端麦克风 PCM 帧 ──→ 后端 ──→ input_audio_buffer.append ──→ 阿里云 Realtime
前端截屏帧        ──→ 后端 ──→ input_image_buffer.append ──→ 阿里云 Realtime

阿里云 Realtime ──→ response.audio.delta ──→ 后端 ──→ 前端播放
阿里云 Realtime ──→ response.audio_transcript.delta ──→ 后端 ──→ 前端渲染文字
```

### 8.2 会话初始化

```json
{
  "type": "session.update",
  "session": {
    "modalities": ["text", "audio"],
    "voice": "从 persona 或 settings 读取",
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
    }
  }
}
```

### 8.3 交互流程（云端 VAD 模式）

```
1. 前端持续推送麦克风 PCM 帧 → 后端 → input_audio_buffer.append
2. 前端持续推送截屏帧（1帧/秒）→ 后端 → input_image_buffer.append
3. 云端 VAD 检测到语音开始 → speech_started
4. 云端 VAD 检测到语音结束 → speech_stopped
5. 云端自动 commit（音频+图片一起提交）→ committed
6. 云端自动触发模型回复 → response.created
7. 模型流式返回音频+文字 → 前端播放+渲染
8. 回复完成 → response.done
```

### 8.4 关键约束

- 图片必须在 `speech_stopped` 之前已 append 到缓冲区
- 持续以固定频率推送截屏即可满足此要求
- 截屏格式：JPEG，推荐 480p/720p，Base64 编码后 ≤ 256KB
- 音频格式：16kHz 16bit 单声道 PCM

### 8.5 使用限制

| 模型 | 音频最大轮次 | 视频最大轮次 | 音频最大时长 | 视频最大时长 |
|---|---|---|---|---|
| qwen3.5-omni-plus-realtime | 100 轮 | 50 轮 | 600 秒 | 240 秒 |
| qwen3.5-omni-flash-realtime | 80 轮 | 50 轮 | 480 秒 | 120 秒 |

单次会话最长 120 分钟。超时需重连。

---

## 九、屏幕监控模块

### 职责

- 实时采集游戏画面
- 为两种模式提供截屏服务

### 两种模式的消费方式

| 模式 | 如何使用截屏 |
|---|---|
| 非沉浸 | 用户手动点击"附带截图"，取当前帧作为图片附件 |
| 沉浸 | 按 `screen_capture.interval_ms` 持续推送到 Realtime |

### 技术要求

- 输出格式：JPEG
- 分辨率：推荐 720p（可配置）
- 单帧大小：原始 ≤ 190KB，Base64 编码后 ≤ 256KB
- 帧率：可配置（默认 1帧/秒）

---

## 十、设置面板

### 结构

```
设置
├─ API 配置
│   ├─ API Key                   [输入框] [测试连接]
│   ├─ 实时 API Key（可选）       [输入框] [测试连接]
│   └─ 区域                      [北京 / 新加坡]
│
├─ 角色管理
│   ├─ 当前角色                   [下拉选择 persona 文件]
│   ├─ 角色名称                   [输入框]
│   ├─ 性格描述                   [文本域]
│   ├─ 背景身份                   [文本域]
│   ├─ 说话风格                   [文本域]
│   ├─ 关系设定                   [文本域]
│   └─ 音色                      [下拉选择]
│
├─ 功能开关
│   ├─ 非实时联网搜索             [开/关]
│   └─ 实时联网搜索               [开/关]
│
├─ 实时模式
│   ├─ VAD 类型                   [semantic_vad / server_vad]
│   ├─ VAD 阈值                   [滑块 0.1~0.9]
│   ├─ 静默时长                   [滑块 500~1500ms]
│   └─ 截屏频率                   [滑块 500~10000ms]
│
└─ 高级
    ├─ 输出模态                   [文本+语音 / 仅文本]
    └─ 截屏分辨率                 [480p / 720p / 1080p]
```

### 保存逻辑

| 用户操作 | 写入目标 |
|---|---|
| 修改 API Key | `.env` |
| 修改技术参数 | `config/settings.yaml` |
| 修改角色人设 | `config/personas/{name}.yaml` |
| 新建角色 | 创建新 persona 文件 |

---

## 十一、开发阶段规划

### Phase 1：基础框架

- [ ] 项目脚手架搭建（Electron + 前端框架）
- [ ] 配置加载系统（.env / settings.yaml / persona / prompts）
- [ ] 设置面板 UI

### Phase 2：非沉浸模式

- [ ] 文本聊天功能
- [ ] 文本 + 图片输入
- [ ] 流式文本输出渲染
- [ ] 可选音频输出播放
- [ ] 多轮对话上下文管理

### Phase 3：屏幕监控

- [ ] 游戏画面采集
- [ ] 截屏预览展示
- [ ] 非沉浸模式截图附件集成

### Phase 4：沉浸模式

- [ ] WebSocket 长连接管理
- [ ] 麦克风 PCM 采集与流式推送
- [ ] 云端 VAD（semantic_vad）
- [ ] 截屏持续推送（input_image_buffer）
- [ ] 模型音频流接收与播放
- [ ] 模型文字转写展示
- [ ] 打断处理

### Phase 5：完善

- [ ] 断线重连
- [ ] 会话超时处理（120 分钟限制）
- [ ] 错误处理与用户提示
- [ ] 联网搜索开关集成
- [ ] 多角色切换

---

## 十二、关键约束与红线

### API 层面

1. 非实时 API 所有请求必须 `stream=True`
2. 非实时多轮中 assistant message 只能包含文本
3. Realtime API 没有原生文本输入通道，输入只能是音频流
4. Realtime 图片必须在音频之后 append（即先 append 过音频才能 append 图片）
5. 联网搜索和工具调用不兼容，不可同时开启

### 架构层面

1. 两种模式上下文完全隔离，互不干扰
2. 人设配置统一管理，两种模式从同一份 persona + interaction_rules 组装 prompt
3. 屏幕监控模块独立，两种模式按需消费
4. `.env` 不入版本控制

### 音频规格

| 参数 | 值 |
|---|---|
| 采样率 | 输入 16kHz，输出 24kHz |
| 位深 | 16bit |
| 声道 | 单声道 |
| 格式 | PCM（Realtime） / WAV（非实时） |

### 图片规格

| 参数 | 值 |
|---|---|
| 格式 | JPEG |
| 分辨率 | 推荐 480p / 720p，最高 1080p |
| 大小 | 原始 ≤ 190KB，Base64 ≤ 256KB |

---

## 十三、后续升级路径

| 版本 | 目标 |
|---|---|
| V1 | 两种模式独立可用，上下文隔离 |
| V2 | 统一会话列表 UI，历史记录可查看 |
| V3 | 文本模式摘要单向注入实时模式（进入沉浸时带上近期文字聊天摘要） |
| V4 | 双向上下文共享（语音转写回流文字历史） |
| V5 | 本地 VAD 替代云端（应对高噪音游戏环境） |
