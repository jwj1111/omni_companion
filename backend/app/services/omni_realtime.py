"""
Qwen-Omni-Realtime 服务
负责管理与阿里云 Realtime API 的 WebSocket 长连接
"""
import json
import time
import asyncio
from typing import Callable, Optional

import websockets


class OmniRealtimeService:
    """沉浸模式 - 实时语音对话服务"""

    # 心跳间隔（秒）：每隔这么久发一次静音保活
    KEEPALIVE_INTERVAL = 60
    # 静音 PCM：200ms 的 16kHz 16bit 单声道全零音频
    SILENCE_PCM_B64 = __import__("base64").b64encode(b'\x00' * 6400).decode()

    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url  # wss://dashscope.aliyuncs.com/api-ws/v1/realtime
        self.ws = None
        self.is_connected = False
        self._event_callback: Optional[Callable] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._last_send_time: float = 0

    async def connect(self):
        """建立与阿里云 Realtime API 的 WebSocket 连接"""
        url = f"{self.base_url}?model={self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        self.ws = await websockets.connect(url, additional_headers=headers)
        self.is_connected = True

    async def disconnect(self):
        """断开连接"""
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            await self.ws.close()
            self.ws = None
        self.is_connected = False

    async def update_session(self, config: dict):
        """
        发送 session.update 事件配置会话

        config 示例:
        {
            "modalities": ["text", "audio"],
            "voice": "Ethan",
            "instructions": "...",
            "input_audio_format": "pcm",
            "output_audio_format": "pcm",
            "turn_detection": {"type": "semantic_vad", "threshold": 0.5, "silence_duration_ms": 800},
            "input_audio_transcription": {"model": "qwen3-asr-flash-realtime"}
        }
        """
        event = {
            "event_id": self._gen_event_id(),
            "type": "session.update",
            "session": config,
        }
        await self._send(event)

    async def append_audio(self, audio_b64: str):
        """向音频缓冲区追加 PCM 音频帧（Base64 编码）"""
        event = {
            "event_id": self._gen_event_id(),
            "type": "input_audio_buffer.append",
            "audio": audio_b64,
        }
        await self._send(event)

    async def append_image(self, image_b64: str):
        """
        向图像缓冲区追加截屏帧（Base64 编码）
        自动进行格式转换和压缩以满足限制：
        - 格式转为 JPEG
        - Base64 编码后 ≤ 256KB
        - 分辨率不超过 720p
        - 必须在发送过音频之后才能发送图片
        """
        from app.services.image_processor import process_image_from_b64, TargetAPI

        # 自动压缩转换
        processed_b64 = process_image_from_b64(image_b64, target=TargetAPI.REALTIME)

        event = {
            "event_id": self._gen_event_id(),
            "type": "input_image_buffer.append",
            "image": processed_b64,
        }
        await self._send(event)

    async def commit_audio_buffer(self):
        """提交音频缓冲区（Manual 模式下使用）"""
        event = {
            "event_id": self._gen_event_id(),
            "type": "input_audio_buffer.commit",
        }
        await self._send(event)

    async def create_response(self):
        """请求模型生成回复（Manual 模式下使用）"""
        event = {
            "event_id": self._gen_event_id(),
            "type": "response.create",
        }
        await self._send(event)

    async def cancel_response(self):
        """取消当前回复（用于打断）"""
        event = {
            "event_id": self._gen_event_id(),
            "type": "response.cancel",
        }
        await self._send(event)

    async def clear_audio_buffer(self):
        """清除音频缓冲区"""
        event = {
            "event_id": self._gen_event_id(),
            "type": "input_audio_buffer.clear",
        }
        await self._send(event)

    # ==================== 事件监听 ====================

    async def start_listening(self, callback: Callable):
        """
        开始监听服务端事件并回调

        callback: async def callback(event: dict) -> None
        """
        self._event_callback = callback
        self._listen_task = asyncio.create_task(self._listen_loop())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def _listen_loop(self):
        """持续监听 WebSocket 消息"""
        try:
            async for message in self.ws:
                event = json.loads(message)
                if self._event_callback:
                    await self._event_callback(event)
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
        except asyncio.CancelledError:
            pass

    async def _keepalive_loop(self):
        """心跳保活：定期发送静音音频防止空闲超时（300秒）"""
        try:
            while self.is_connected:
                await asyncio.sleep(self.KEEPALIVE_INTERVAL)
                # 如果最近没有发过任何数据，发一段静音
                elapsed = time.time() - self._last_send_time
                if elapsed >= self.KEEPALIVE_INTERVAL and self.is_connected:
                    await self.append_audio(self.SILENCE_PCM_B64)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    # ==================== 内部工具 ====================

    async def _send(self, event: dict):
        """发送事件到阿里云"""
        if not self.ws:
            raise RuntimeError("WebSocket 未连接")
        await self.ws.send(json.dumps(event))
        self._last_send_time = time.time()

    @staticmethod
    def _gen_event_id() -> str:
        """生成唯一事件 ID"""
        return f"evt_{int(time.time() * 1000)}"

    # ==================== 便捷方法 ====================

    def build_session_config(
        self,
        instructions: str,
        voice: str = "Tina",
        modalities: list = None,
        vad_type: str = "semantic_vad",
        vad_threshold: float = 0.5,
        silence_duration_ms: int = 800,
        enable_transcription: bool = True,
        transcription_model: str = "qwen3-asr-flash-realtime",
        enable_search: bool = False,
    ) -> dict:
        """
        构建 session.update 的 config 对象
        基于 settings 和 persona 生成
        """
        if modalities is None:
            modalities = ["text", "audio"]

        config = {
            "modalities": modalities,
            "voice": voice,
            "instructions": instructions,
            "input_audio_format": "pcm",
            "output_audio_format": "pcm",
            "turn_detection": {
                "type": vad_type,
                "threshold": vad_threshold,
                "silence_duration_ms": silence_duration_ms,
            },
        }

        if enable_transcription:
            config["input_audio_transcription"] = {
                "model": transcription_model,
            }

        if enable_search:
            config["enable_search"] = True

        return config
