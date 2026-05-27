"""
沉浸模式 - 交互式实时对话测试
通过麦克风和模型实时语音对话。

运行: cd backend && python tests/interactive_realtime.py

依赖: pip install pyaudio

命令（对话过程中输入）:
  /img 路径     → 发送一张图片给模型（模拟截屏）
  /stop        → 断开连接
  /quit        → 退出

注意:
  - 使用云端 semantic_vad，说完话模型会自动回复
  - 模型回复的音频会实时播放（需要扬声器/耳机）
"""
import asyncio
import base64
import json
import sys
import os
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.config_manager import ConfigManager
from app.services.omni_realtime import OmniRealtimeService

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 音频参数
INPUT_SAMPLE_RATE = 16000
INPUT_CHANNELS = 1
INPUT_FORMAT_WIDTH = 2  # 16bit = 2 bytes
OUTPUT_SAMPLE_RATE = 24000
CHUNK_SIZE = 3200  # 100ms at 16kHz 16bit mono


async def main():
    print("=" * 50)
    print("沉浸模式 - 交互式实时对话")
    print("=" * 50)

    # 检查 pyaudio
    try:
        import pyaudio
    except ImportError:
        print("✗ 需要安装 pyaudio: pip install pyaudio")
        return

    # 初始化配置
    cm = ConfigManager(PROJECT_ROOT)
    env = cm.load_env()
    settings = cm.load_settings()
    rt_config = settings.get("realtime", {})

    if not env["api_key"]:
        print("✗ 未配置 API Key，请在 .env 中设置 DASHSCOPE_API_KEY")
        return

    api_key = env.get("api_key_realtime") or env["api_key"]
    model = settings["models"]["realtime"]
    voice = cm.get_voice()
    system_prompt = cm.build_system_prompt()

    print(f"\n模型: {model}")
    print(f"角色: {cm.load_active_persona().get('name', 'N/A')}")
    print(f"音色: {voice}")
    print(f"VAD: {rt_config.get('vad_type', 'semantic_vad')}")
    print("\n命令: /img 路径, /stop, /quit")
    print("-" * 50)

    # 初始化音频
    pya = pyaudio.PyAudio()

    # 输出流（播放模型回复）
    output_stream = pya.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=OUTPUT_SAMPLE_RATE,
        output=True,
    )

    # 初始化 Realtime 服务
    realtime = OmniRealtimeService(
        api_key=api_key,
        model=model,
        base_url=cm.get_realtime_url(),
    )

    # 事件回调
    # 状态追踪
    user_transcript = ""
    assistant_transcript = ""

    async def on_event(event: dict):
        nonlocal user_transcript, assistant_transcript
        event_type = event.get("type", "")

        if event_type == "response.audio.delta":
            # 播放音频（静默，不打印）
            audio_b64 = event.get("delta", "")
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                output_stream.write(audio_bytes)

        elif event_type == "response.audio_transcript.delta":
            # 助手文字增量：直接追加输出（不覆盖，避免长文本重复）
            delta_text = event.get("delta", "")
            if delta_text:
                if not assistant_transcript:
                    print("  助手: ", end="", flush=True)
                assistant_transcript += delta_text
                print(delta_text, end="", flush=True)

        elif event_type == "response.audio_transcript.done":
            # 助手文字完成：换行
            assistant_transcript = ""
            print()

        elif event_type == "conversation.item.input_audio_transcription.completed":
            # 用户转写完成：打印最终结果
            user_transcript = event.get("transcript", "")
            print(f"  你: {user_transcript}")
            user_transcript = ""

        elif event_type == "conversation.item.input_audio_transcription.delta":
            # 用户转写增量：静默累积，不打印（等 completed 一次性显示）
            pass

        elif event_type == "input_audio_buffer.speech_started":
            # 清空上一轮残留
            user_transcript = ""
            assistant_transcript = ""
            print("\n  [语音开始]", flush=True)

        elif event_type == "input_audio_buffer.speech_stopped":
            print("\n  [语音结束，等待回复...]", flush=True)

        elif event_type == "response.done":
            print("  [回复完成]\n", flush=True)

        elif event_type == "session.created":
            print("✓ 会话已创建")

        elif event_type == "session.updated":
            print("✓ 会话配置已更新")

        elif event_type == "error":
            err = event.get("error", {})
            print(f"\n✗ 错误: {err.get('message', '未知错误')}")

    # 连接
    print("\n正在连接...")
    try:
        await realtime.connect()
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        pya.terminate()
        return

    # 配置会话
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

    # 开始监听
    await realtime.start_listening(on_event)

    # 开始麦克风采集
    is_recording = True

    async def mic_loop():
        """持续采集麦克风音频并发送"""
        input_stream = pya.open(
            format=pyaudio.paInt16,
            channels=INPUT_CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE // INPUT_FORMAT_WIDTH,
        )
        print("✓ 麦克风已打开，开始说话吧...\n")

        try:
            while is_recording and realtime.is_connected:
                # 读取音频帧
                audio_data = input_stream.read(
                    CHUNK_SIZE // INPUT_FORMAT_WIDTH,
                    exception_on_overflow=False,
                )
                # 发送
                audio_b64 = base64.b64encode(audio_data).decode()
                await realtime.append_audio(audio_b64)
                await asyncio.sleep(0.01)
        except Exception as e:
            if is_recording:
                print(f"麦克风错误: {e}")
        finally:
            input_stream.stop_stream()
            input_stream.close()

    # 启动麦克风任务
    mic_task = asyncio.create_task(mic_loop())

    # 命令输入循环（在另一个线程）
    def input_loop():
        nonlocal is_recording
        while is_recording:
            try:
                cmd = input().strip()
            except (EOFError, KeyboardInterrupt):
                is_recording = False
                break

            if cmd == "/quit" or cmd == "/stop":
                is_recording = False
                break
            elif cmd.startswith("/img"):
                img_path = cmd.replace("/img", "").strip()
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode()
                    # 通过事件循环发送图片
                    asyncio.run_coroutine_threadsafe(
                        realtime.append_image(img_b64),
                        loop
                    )
                    print(f"  [已发送图片: {os.path.basename(img_path)}]")
                else:
                    print("  ✗ 文件不存在或路径为空")

    loop = asyncio.get_event_loop()
    input_thread = threading.Thread(target=input_loop, daemon=True)
    input_thread.start()

    # 等待退出
    while is_recording and realtime.is_connected:
        await asyncio.sleep(0.5)

    # 清理
    print("\n正在断开...")
    is_recording = False
    mic_task.cancel()
    try:
        await mic_task
    except asyncio.CancelledError:
        pass

    await realtime.disconnect()
    output_stream.stop_stream()
    output_stream.close()
    pya.terminate()
    print("✓ 已断开，再见！")


if __name__ == "__main__":
    asyncio.run(main())
