# 游戏AI陪聊 - 后端

## 快速启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py
```

服务启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## API 概览

### 非沉浸模式（HTTP）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/chat/send | 发送消息（流式返回） |
| GET | /api/chat/history | 获取对话历史 |
| POST | /api/chat/clear | 清空对话历史 |

### 沉浸模式（WebSocket）

| 路径 | 说明 |
|---|---|
| WS /api/realtime/ws | 实时语音对话双向通道 |

### 设置管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/settings/all | 获取所有配置 |
| PUT | /api/settings/update | 更新 settings.yaml |
| PUT | /api/settings/env | 更新 .env 变量 |
| GET | /api/settings/personas | 列出所有角色 |
| GET | /api/settings/persona/{id} | 获取角色详情 |
| PUT | /api/settings/persona/{id} | 更新/创建角色 |
| DELETE | /api/settings/persona/{id} | 删除角色 |
| GET | /api/settings/voices | 获取可用音色列表 |

### 截屏

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/screenshot | 上传截屏到缓存池 |

## 测试

### 交互式测试（直接和模型聊天）

```bash
# 非沉浸模式：命令行打字聊天（支持发图片）
python tests/interactive_chat.py

# 沉浸模式：麦克风实时对话（需要 pyaudio）
pip install pyaudio
python tests/interactive_realtime.py
```

**非沉浸模式命令：**

| 命令 | 说明 |
|---|---|
| 直接输入文字 | 发送纯文本 |
| `/img` | 发送文本+图片（会提示输入文字和图片路径） |
| `/audio on` / `/audio off` | 开关音频输出 |
| `/clear` | 清空对话历史 |
| `/history` | 查看历史 |
| `/quit` | 退出 |

**沉浸模式命令（对话过程中输入）：**

| 命令 | 说明 |
|---|---|
| `/img 图片绝对路径` | 发送图片（模拟截屏） |
| `/stop` | 断开连接并退出 |
| `/quit` | 退出 |

---

### 离线测试（不需要启动服务，不消耗 token）

```bash
# 验证配置文件是否能正确加载、prompt 是否能正确组装
python tests/test_config_manager.py
```

### API 测试（需要先启动后端）

```bash
# 先启动后端
python run.py

# 新开一个终端，运行测试：

# 设置管理（不消耗 token）
python tests/test_settings_api.py

# 非沉浸模式聊天（会调用阿里云 API，消耗 token）
python tests/test_chat_api.py

# 沉浸模式 WebSocket（会尝试连接阿里云 Realtime，消耗 token）
python tests/test_realtime_api.py
```

### 用 pytest 批量运行

```bash
python -m pytest tests/ -v
```

### 测试文件说明

| 文件 | 测试内容 | 是否需要启动服务 | 是否消耗 token |
|---|---|---|---|
| test_config_manager.py | 配置加载、prompt 组装、角色管理 | ❌ | ❌ |
| test_settings_api.py | 设置读取、角色列表、音色列表 | ✅ | ❌ |
| test_chat_api.py | 发送消息、流式回复、历史管理 | ✅ | ✅ |
| test_realtime_api.py | WebSocket 连接、会话启停 | ✅ | ✅ |

> 建议顺序：先跑 `test_config_manager.py` 确认配置正确，再跑 `test_settings_api.py` 确认服务正常，最后跑消耗 token 的测试。

---

## 项目结构

```
backend/
├─ run.py                  # 启动脚本
├─ requirements.txt        # 依赖
├─ README.md
└─ app/
    ├─ __init__.py
    ├─ main.py             # FastAPI 入口
    ├─ dependencies.py     # 依赖注入
    ├─ routers/
    │   ├─ chat.py         # 非沉浸模式
    │   ├─ realtime.py     # 沉浸模式
    │   └─ settings.py     # 设置管理
    └─ services/
        ├─ config_manager.py    # 配置管理
        ├─ omni_chat.py         # 非实时 API
        ├─ omni_realtime.py     # Realtime API
        └─ screen_capture.py    # 截屏缓存
```
