"""
游戏AI陪聊 - 后端主入口
FastAPI 应用，提供非沉浸模式 HTTP API 和沉浸模式 WebSocket 接口
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.routers import chat, realtime, settings

from app.dependencies import cleanup_expired_sessions, get_config_manager, get_screen_cache, get_session_limits



async def session_cleanup_loop():
    """按配置定时清理过期会话。"""
    while True:
        limits = get_session_limits()
        await asyncio.sleep(limits["cleanup_interval_seconds"])
        removed = cleanup_expired_sessions(
            ttl_seconds=limits["ttl_seconds"],
            max_sessions=limits["max_sessions"],
        )
        if removed:
            print(f"[会话清理] 已清理 {removed} 个过期/超限会话")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：验证配置可加载
    cm = get_config_manager()
    s = cm.load_settings()
    session_config = s.get("session", {})
    print(f"[启动] 激活角色: {s.get('active_persona', 'unknown')}")
    print(f"[启动] 非实时模型: {s['models']['non_realtime']}")
    print(f"[启动] 实时模型: {s['models']['realtime']}")
    print(
        "[启动] 会话清理: "
        f"TTL={session_config.get('ttl_seconds')}s, "
        f"interval={session_config.get('cleanup_interval_seconds')}s, "
        f"max={session_config.get('max_sessions')}"
    )
    cleanup_task = asyncio.create_task(session_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        print("[关闭] 后端服务已停止")



app = FastAPI(title="游戏AI陪聊", version="0.1.0", lifespan=lifespan)


class ScreenshotRequest(BaseModel):
    image_b64: str


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
async def upload_screenshot(req: ScreenshotRequest, cache=Depends(get_screen_cache)):
    """
    接收前端上传的截屏（base64 JPEG）
    存入当前会话的截屏缓存池，供沉浸模式使用
    """
    cache.add_frame(req.image_b64)
    return {"status": "ok", "frame_count": cache.get_frame_count()}


