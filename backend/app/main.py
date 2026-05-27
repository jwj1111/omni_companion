"""
游戏AI陪聊 - 后端主入口
FastAPI 应用，提供非沉浸模式 HTTP API 和沉浸模式 WebSocket 接口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, realtime, settings
from app.dependencies import get_config_manager, get_screen_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：验证配置可加载
    cm = get_config_manager()
    s = cm.load_settings()
    print(f"[启动] 激活角色: {s.get('active_persona', 'unknown')}")
    print(f"[启动] 非实时模型: {s['models']['non_realtime']}")
    print(f"[启动] 实时模型: {s['models']['realtime']}")
    yield
    # 关闭时：清理（如有需要）
    print("[关闭] 后端服务已停止")


app = FastAPI(title="游戏AI陪聊", version="0.1.0", lifespan=lifespan)

# CORS（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(chat.router, prefix="/api/chat", tags=["非沉浸模式"])
app.include_router(realtime.router, prefix="/api/realtime", tags=["沉浸模式"])
app.include_router(settings.router, prefix="/api/settings", tags=["设置"])


# ==================== 通用端点 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


@app.post("/api/screenshot")
async def upload_screenshot(image_b64: str):
    """
    接收前端上传的截屏（base64 JPEG）
    存入全局截屏缓存池，供沉浸模式使用
    """
    cache = get_screen_cache()
    cache.add_frame(image_b64)
    return {"status": "ok", "frame_count": cache.get_frame_count()}
