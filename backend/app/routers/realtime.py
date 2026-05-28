"""
沉浸模式 - 实时语音对话路由
前端 ←WebSocket→ 后端 ←WebSocket→ 阿里云 Realtime API
"""
import json
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.dependencies import (
    create_realtime_service,
    get_config_manager_for_session,
    get_screen_cache_for_session,
    normalize_session_id,
    touch_session,
)



router = APIRouter()


@router.websocket("/ws")
async def realtime_session(websocket: WebSocket):
    """
    沉浸模式 WebSocket 端点

    前端发送的消息格式（JSON）：
    - {"type": "audio", "data": "base64pcm..."}        音频帧
    - {"type": "screenshot", "data": "base64jpeg..."}   截屏帧
    - {"type": "control", "action": "start"}            开始会话
    - {"type": "control", "action": "stop"}             结束会话

    后端发回前端的消息格式（JSON）：
    - {"type": "audio", "data": "base64pcm..."}         模型音频回复
    - {"type": "transcript", "text": "...", "role": "assistant"}  模型文字
    - {"type": "transcript", "text": "...", "role": "user"}      用户语音转写
    - {"type": "status", "event": "..."}                状态事件
    - {"type": "error", "message": "..."}               错误
    """
    await websocket.accept()

    session_id = normalize_session_id(websocket.query_params.get("session_id"))
    touch_session(session_id)
    cm = get_config_manager_for_session(session_id)

    realtime = create_realtime_service(session_id)
    screen_cache = get_screen_cache_for_session(session_id)

    async def on_server_event(event: dict):

        """处理阿里云返回的事件，转发给前端"""
        event_type = event.get("type", "")

        try:
            if event_type == "response.audio.delta":
                # 模型音频增量
                await websocket.send_json({
                    "type": "audio",
                    "data": event.get("delta", ""),
                })

            elif event_type == "response.audio_transcript.delta":
                # 模型文字转写增量
                await websocket.send_json({
                    "type": "transcript",
                    "text": event.get("delta", ""),
                    "role": "assistant",
                    "final": False,
                })

            elif event_type == "response.audio_transcript.done":
                # 模型文字转写完成
                await websocket.send_json({
                    "type": "transcript",
                    "text": event.get("transcript", ""),
                    "role": "assistant",
                    "final": True,
                })

            elif event_type == "conversation.item.input_audio_transcription.completed":
                # 用户语音转写完成
                await websocket.send_json({
                    "type": "transcript",
                    "text": event.get("transcript", ""),
                    "role": "user",
                    "final": True,
                })

            elif event_type == "conversation.item.input_audio_transcription.delta":
                # 用户语音转写增量
                preview = event.get("text", "") + event.get("stash", "")
                await websocket.send_json({
                    "type": "transcript",
                    "text": preview,
                    "role": "user",
                    "final": False,
                })

            elif event_type in (
                "session.created", "session.updated",
                "input_audio_buffer.speech_started",
                "input_audio_buffer.speech_stopped",
                "input_audio_buffer.committed",
                "response.created", "response.done",
            ):
                # 状态事件，转发给前端做 UI 更新
                await websocket.send_json({
                    "type": "status",
                    "event": event_type,
                })

            elif event_type == "error":
                await websocket.send_json({
                    "type": "error",
                    "message": event.get("error", {}).get("message", "未知错误"),
                })

        except Exception:
            # 前端已断开，忽略发送错误
            pass

    try:
        while True:
            raw = await websocket.receive_text()
            touch_session(session_id)
            msg = json.loads(raw)
            msg_type = msg.get("type", "")


            if msg_type == "control":
                action = msg.get("action", "")

                if action == "start":
                    # 建立与阿里云的连接
                    await realtime.connect()

                    # 构建 session 配置
                    settings = cm.load_settings()
                    rt_config = settings.get("realtime", {})
                    system_prompt = cm.build_system_prompt()
                    voice = cm.get_voice()

                    session_config = realtime.build_session_config(
                        instructions=system_prompt,
                        voice=voice,
                        modalities=settings.get("output", {}).get("modalities", ["text", "audio"]),
                        vad_type=rt_config.get("vad_type", "semantic_vad"),
                        vad_threshold=rt_config.get("vad_threshold", 0.5),
                        silence_duration_ms=rt_config.get("silence_duration_ms", 800),
                        enable_transcription=rt_config.get("input_audio_transcription", True),
                        transcription_model=rt_config.get("transcription_model", "qwen3-asr-flash-realtime"),
                        enable_search=rt_config.get("enable_search", False),
                    )

                    await realtime.update_session(session_config)

                    # 开始监听服务端事件
                    await realtime.start_listening(on_server_event)

                    await websocket.send_json({"type": "status", "event": "connected"})

                elif action == "stop":
                    await realtime.disconnect()
                    await websocket.send_json({"type": "status", "event": "disconnected"})

            elif msg_type == "audio":
                # 转发音频帧到阿里云
                audio_b64 = msg.get("data", "")
                if audio_b64 and realtime.is_connected:
                    await realtime.append_audio(audio_b64)

            elif msg_type == "screenshot":
                # 转发截屏到阿里云
                image_b64 = msg.get("data", "")
                if image_b64 and realtime.is_connected:
                    await realtime.append_image(image_b64)
                    # 同时存入缓存池
                    screen_cache.add_frame(image_b64)

    except WebSocketDisconnect:
        # 前端断开，清理阿里云连接
        if realtime.is_connected:
            await realtime.disconnect()
    except Exception as e:
        # 异常断开 — 打印完整错误便于调试
        import traceback
        print(f"\n[Realtime WS Error] {type(e).__name__}: {e}")
        traceback.print_exc()

        # 尝试将错误原因发给前端
        error_msg = str(e)
        try:
            await websocket.send_json({"type": "error", "message": error_msg})
        except Exception:
            pass

        # 清理阿里云连接
        if realtime.is_connected:
            await realtime.disconnect()

        # 显式关闭前端 WS，带上 reason（前端 onclose 可读取）
        try:
            await websocket.close(code=1011, reason=error_msg[:120])
        except Exception:
            pass
