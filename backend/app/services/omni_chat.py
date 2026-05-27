"""
非实时 Qwen-Omni 服务
负责调用 OpenAI 兼容的 chat.completions API（流式）
"""
import asyncio
from typing import AsyncGenerator, Optional

from openai import AsyncOpenAI


class OmniChatService:
    """非沉浸模式 - 非实时多模态聊天服务"""

    def __init__(self, api_key: str, model: str, base_url: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.messages: list = []

    def set_system_prompt(self, prompt: str):
        """设置/更新 system prompt"""
        # 如果已有 system message，替换；否则插入
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0] = {"role": "system", "content": prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    async def send_message(
        self,
        content,
        modalities: Optional[list] = None,
        voice: str = "Tina",
        enable_search: bool = False,
    ) -> AsyncGenerator[dict, None]:
        """
        发送消息并流式返回回复

        content: str 或 list（OpenAI 格式的 content）
            - 纯文本: "你好"
            - 多模态: [{"type": "text", "text": "..."}, {"type": "image_url", ...}]

        yields: {"type": "text", "data": "..."} 或 {"type": "audio", "data": "base64..."}
                 或 {"type": "done"} 或 {"type": "error", "data": "..."}
        """
        if modalities is None:
            modalities = ["text", "audio"]

        # 构造 user message
        user_message = {"role": "user", "content": content}
        self.messages.append(user_message)

        # 构造请求参数
        kwargs = {
            "model": self.model,
            "messages": self.messages,
            "modalities": modalities,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        # 音频输出配置
        if "audio" in modalities:
            kwargs["audio"] = {"voice": voice, "format": "wav"}

        # 联网搜索
        if enable_search:
            kwargs["extra_body"] = {"enable_search": True}

        try:
            completion = await self.client.chat.completions.create(**kwargs)

            assistant_text = ""
            audio_data = ""
            usage_info = None

            async for chunk in completion:
                if not chunk.choices:
                    # 最后一个 chunk 可能只有 usage（无 choices）
                    if hasattr(chunk, "usage") and chunk.usage:
                        usage_info = chunk.usage
                    continue

                delta = chunk.choices[0].delta

                # 文本部分
                if delta.content:
                    assistant_text += delta.content
                    yield {"type": "text", "data": delta.content}

                # 音频部分
                if hasattr(delta, "audio") and delta.audio:
                    audio_chunk = delta.audio.get("data", "")
                    if audio_chunk:
                        audio_data += audio_chunk
                        yield {"type": "audio", "data": audio_chunk}

            # 将 assistant 回复存入历史（只存文本，文档要求）
            if assistant_text:
                self.messages.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": assistant_text}]
                })

            # 返回 done 事件，附带 usage 信息
            done_data = {}
            if usage_info:
                done_data["usage"] = {
                    "prompt_tokens": getattr(usage_info, "prompt_tokens", None),
                    "completion_tokens": getattr(usage_info, "completion_tokens", None),
                    "total_tokens": getattr(usage_info, "total_tokens", None),
                }
                # 联网搜索插件信息
                if hasattr(usage_info, "plugins"):
                    done_data["plugins"] = usage_info.plugins

            yield {"type": "done", "data": done_data}

        except Exception as e:
            yield {"type": "error", "data": str(e)}

    def get_history(self) -> list:
        """获取对话历史"""
        return self.messages

    def clear_history(self):
        """清空对话历史（保留 system prompt）"""
        if self.messages and self.messages[0].get("role") == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []
