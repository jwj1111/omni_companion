"""
FastAPI 依赖注入
管理全局单例服务实例
"""
from pathlib import Path
from functools import lru_cache

from app.services.config_manager import ConfigManager
from app.services.omni_chat import OmniChatService
from app.services.omni_realtime import OmniRealtimeService
from app.services.screen_capture import ScreenCaptureCache


# ==================== 配置管理器（单例） ====================

@lru_cache()
def get_config_manager() -> ConfigManager:
    """获取配置管理器单例"""
    # 项目根目录 = backend/ 的上级
    project_root = Path(__file__).resolve().parent.parent.parent
    return ConfigManager(project_root)


# ==================== 非沉浸模式聊天服务 ====================

_chat_service: OmniChatService | None = None


def get_chat_service() -> OmniChatService:
    """获取非沉浸模式聊天服务（懒初始化）"""
    global _chat_service
    if _chat_service is None:
        cm = get_config_manager()
        env = cm.load_env()
        settings = cm.load_settings()
        _chat_service = OmniChatService(
            api_key=env["api_key"],
            model=settings["models"]["non_realtime"],
            base_url=cm.get_base_url(),
        )
        # 设置 system prompt
        system_prompt = cm.build_system_prompt()
        _chat_service.set_system_prompt(system_prompt)
    return _chat_service


# ==================== 沉浸模式实时服务 ====================

_realtime_service: OmniRealtimeService | None = None


def get_realtime_service() -> OmniRealtimeService:
    """获取沉浸模式实时服务（懒初始化）"""
    global _realtime_service
    if _realtime_service is None:
        cm = get_config_manager()
        env = cm.load_env()
        settings = cm.load_settings()
        _realtime_service = OmniRealtimeService(
            api_key=env.get("api_key_realtime") or env["api_key"],
            model=settings["models"]["realtime"],
            base_url=cm.get_realtime_url(),
        )
    return _realtime_service


# ==================== 截屏缓存 ====================

_screen_cache: ScreenCaptureCache | None = None


def get_screen_cache() -> ScreenCaptureCache:
    """获取截屏缓存单例"""
    global _screen_cache
    if _screen_cache is None:
        _screen_cache = ScreenCaptureCache()
    return _screen_cache


# ==================== 重置（用于设置更新后重新初始化） ====================

def reset_services(clear_config: bool = False):
    """重置模型服务实例；默认保留运行期配置微调。"""
    global _chat_service, _realtime_service
    _chat_service = None
    _realtime_service = None
    if clear_config:
        get_config_manager.cache_clear()
