"""
FastAPI 依赖注入
按浏览器会话隔离运行期配置、文字聊天历史和截图缓存。
"""
import re
import time
from pathlib import Path
from functools import lru_cache
from typing import Optional

from fastapi import Depends, Header

from app.services.config_manager import ConfigManager
from app.services.omni_chat import OmniChatService
from app.services.omni_realtime import OmniRealtimeService
from app.services.screen_capture import ScreenCaptureCache


DEFAULT_SESSION_ID = "default"
_SESSION_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")


@lru_cache()
def get_project_root() -> Path:
    """项目根目录 = backend/ 的上级。"""
    return Path(__file__).resolve().parent.parent.parent


def normalize_session_id(session_id: Optional[str]) -> str:
    """规范化客户端会话 ID，避免空值和异常字符污染内存 key。"""
    if not session_id:
        return DEFAULT_SESSION_ID
    normalized = _SESSION_ID_PATTERN.sub("", session_id.strip())[:128]
    return normalized or DEFAULT_SESSION_ID


def get_session_id(x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id")) -> str:
    """从 HTTP Header 读取当前浏览器会话 ID，并刷新活跃时间。"""
    session_id = normalize_session_id(x_session_id)
    touch_session(session_id)
    return session_id


# ==================== 配置管理器 ====================

@lru_cache()
def get_config_manager() -> ConfigManager:
    """默认配置管理器，用于启动检查和无会话调用。"""
    return ConfigManager(get_project_root())


_config_managers: dict[str, ConfigManager] = {}
_session_last_active: dict[str, float] = {}


def get_session_limits() -> dict:
    """读取会话管理参数。"""
    session_config = get_config_manager().load_settings().get("session", {})
    ttl_seconds = int(session_config.get("ttl_seconds", 1800))
    cleanup_interval_seconds = int(session_config.get("cleanup_interval_seconds", 600))
    max_sessions = int(session_config.get("max_sessions", 100))
    return {
        "ttl_seconds": max(ttl_seconds, 0),
        "cleanup_interval_seconds": max(cleanup_interval_seconds, 60),
        "max_sessions": max(max_sessions, 1),
    }


def touch_session(session_id: str):
    """刷新会话活跃时间；只有新会话进入时检查最大会话数。"""
    sid = normalize_session_id(session_id)
    is_new_session = sid not in _session_last_active
    _session_last_active[sid] = time.time()
    if is_new_session:
        enforce_max_sessions(get_session_limits()["max_sessions"])


def drop_session(session_id: str):
    """删除指定会话的所有内存状态。"""
    sid = normalize_session_id(session_id)
    _chat_services.pop(sid, None)
    _config_managers.pop(sid, None)
    _screen_caches.pop(sid, None)
    _session_last_active.pop(sid, None)


def enforce_max_sessions(max_sessions: int):
    """超过最大会话数时，清理最久未活跃的会话。"""
    if max_sessions <= 0:
        return
    overflow = len(_session_last_active) - max_sessions
    if overflow <= 0:
        return
    stale_session_ids = sorted(_session_last_active, key=_session_last_active.get)[:overflow]
    for sid in stale_session_ids:
        drop_session(sid)


def cleanup_expired_sessions(ttl_seconds: Optional[int] = None, max_sessions: Optional[int] = None) -> int:
    """清理过期会话，返回清理数量。"""
    limits = get_session_limits()
    ttl = limits["ttl_seconds"] if ttl_seconds is None else ttl_seconds
    max_count = limits["max_sessions"] if max_sessions is None else max_sessions

    now = time.time()
    expired_session_ids = [
        sid for sid, last_active in list(_session_last_active.items())
        if ttl > 0 and now - last_active > ttl
    ]
    for sid in expired_session_ids:
        drop_session(sid)

    before_limit_count = len(_session_last_active)
    enforce_max_sessions(max_count)
    return len(expired_session_ids) + max(0, before_limit_count - len(_session_last_active))


def get_config_manager_for_session(session_id: str) -> ConfigManager:
    """获取当前会话的配置管理器，运行期微调按会话隔离。"""
    sid = normalize_session_id(session_id)
    if sid not in _config_managers:
        _config_managers[sid] = ConfigManager(get_project_root())
    return _config_managers[sid]


def get_request_config_manager(session_id: str = Depends(get_session_id)) -> ConfigManager:
    """FastAPI 依赖：获取当前请求所属会话的配置管理器。"""
    return get_config_manager_for_session(session_id)


# ==================== 非沉浸模式聊天服务 ====================

_chat_services: dict[str, OmniChatService] = {}


def get_chat_service(session_id: str = Depends(get_session_id)) -> OmniChatService:
    """获取当前会话的非沉浸聊天服务。"""
    sid = normalize_session_id(session_id)
    if sid not in _chat_services:
        cm = get_config_manager_for_session(sid)
        env = cm.load_env()
        settings = cm.load_settings()
        chat_service = OmniChatService(
            api_key=env["api_key"],
            model=settings["models"]["non_realtime"],
            base_url=cm.get_base_url(),
        )
        chat_service.set_system_prompt(cm.build_system_prompt())
        _chat_services[sid] = chat_service
    return _chat_services[sid]


# ==================== 沉浸模式实时服务 ====================

def create_realtime_service(session_id: str) -> OmniRealtimeService:
    """为单个 WebSocket 连接创建独立 Realtime 服务实例。"""
    cm = get_config_manager_for_session(session_id)
    env = cm.load_env()
    settings = cm.load_settings()
    return OmniRealtimeService(
        api_key=env.get("api_key_realtime") or env["api_key"],
        model=settings["models"]["realtime"],
        base_url=cm.get_realtime_url(),
    )


# ==================== 截屏缓存 ====================

_screen_caches: dict[str, ScreenCaptureCache] = {}


def get_screen_cache_for_session(session_id: str) -> ScreenCaptureCache:
    """获取当前会话的截屏缓存。"""
    sid = normalize_session_id(session_id)
    if sid not in _screen_caches:
        _screen_caches[sid] = ScreenCaptureCache()
    return _screen_caches[sid]


def get_screen_cache(session_id: str = Depends(get_session_id)) -> ScreenCaptureCache:
    """FastAPI 依赖：获取当前请求所属会话的截屏缓存。"""
    return get_screen_cache_for_session(session_id)


# ==================== 重置（用于设置更新后重新初始化） ====================

def reset_services(session_id: Optional[str] = None, clear_config: bool = False):
    """重置模型服务实例；传入 session_id 时只影响当前会话。"""
    if session_id is None:
        _chat_services.clear()
        if clear_config:
            _config_managers.clear()
            get_config_manager.cache_clear()
        return

    sid = normalize_session_id(session_id)
    _chat_services.pop(sid, None)
    if clear_config:
        _config_managers.pop(sid, None)
