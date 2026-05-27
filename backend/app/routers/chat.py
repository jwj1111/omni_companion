"""
非沉浸模式 - 文字聊天路由
走非实时 Qwen-Omni API（OpenAI 兼容）
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.dependencies import get_chat_service, get_config_manager

router = APIRouter()


class SendMessageRequest(BaseModel):
    """发送消息请求体"""
    # 纯文本时为 str；多模态时为 list
    content: str | list
    # 是否输出音频
    output_audio: bool = True


@router.post("/send")
async def send_message(
    req: SendMessageRequest,
    chat_service=Depends(get_chat_service),
    config_manager=Depends(get_config_manager),
):
    """
    发送消息并通过 SSE 流式返回回复
    返回格式：每行一个 JSON，type 为 text/audio/done/error
    """
    settings = config_manager.load_settings()
    voice = config_manager.get_voice()
    enable_search = settings.get("non_realtime", {}).get("enable_search", False)

    modalities = ["text", "audio"] if req.output_audio else ["text"]

    async def event_stream():
        async for chunk in chat_service.send_message(
            content=req.content,
            modalities=modalities,
            voice=voice,
            enable_search=enable_search,
        ):
            yield json.dumps(chunk, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/plain; charset=utf-8",
    )


@router.get("/history")
async def get_history(chat_service=Depends(get_chat_service)):
    """获取当前会话的对话历史"""
    return {"messages": chat_service.get_history()}


@router.post("/clear")
async def clear_history(chat_service=Depends(get_chat_service)):
    """清空当前会话历史"""
    chat_service.clear_history()
    return {"status": "ok"}
