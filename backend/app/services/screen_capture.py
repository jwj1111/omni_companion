"""
屏幕截图缓存服务
接收前端上传的截屏，管理缓存池，按需提供给沉浸模式
"""
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScreenFrame:
    """一帧截屏数据"""
    image_b64: str
    timestamp: float = field(default_factory=time.time)


class ScreenCaptureCache:
    """截屏缓存池"""

    def __init__(self, max_frames: int = 30, ttl_seconds: int = 60):
        """
        Args:
            max_frames: 最大缓存帧数
            ttl_seconds: 每帧存活时间（秒）
        """
        self.max_frames = max_frames
        self.ttl_seconds = ttl_seconds
        self.frames: deque[ScreenFrame] = deque(maxlen=max_frames)

    def add_frame(self, image_b64: str):
        """添加一帧截屏"""
        self.cleanup_expired()
        frame = ScreenFrame(image_b64=image_b64)
        self.frames.append(frame)

    def get_latest(self) -> Optional[ScreenFrame]:
        """获取最新一帧（未过期的）"""
        self.cleanup_expired()
        if self.frames:
            return self.frames[-1]
        return None

    def get_latest_b64(self) -> Optional[str]:
        """获取最新一帧的 base64 数据"""
        frame = self.get_latest()
        return frame.image_b64 if frame else None

    def get_frame_count(self) -> int:
        """当前缓存帧数"""
        return len(self.frames)

    def clear(self):
        """清空缓存"""
        self.frames.clear()

    def cleanup_expired(self):
        """清理过期帧"""
        now = time.time()
        while self.frames and (now - self.frames[0].timestamp) > self.ttl_seconds:
            self.frames.popleft()
