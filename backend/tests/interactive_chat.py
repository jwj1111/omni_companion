"""
非沉浸模式 - 交互式聊天测试
直接在命令行和模型对话，支持发送图片。

运行: cd backend && python tests/interactive_chat.py

命令:
  直接输入文字 → 发送文本消息
  /img 图片路径  → 发送文本+图片（先输文字再输路径）
  /audio on/off → 开关音频输出
  /clear        → 清空对话历史
  /history      → 查看对话历史
  /quit         → 退出
"""
import asyncio
import base64
import sys
import os
from pathlib import Path

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

# 确保可以导入 app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.config_manager import ConfigManager
from app.services.omni_chat import OmniChatService

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def main():
    print("=" * 50)
    print("非沉浸模式 - 交互式聊天")
    print("=" * 50)

    # 初始化
    cm = ConfigManager(PROJECT_ROOT)
    env = cm.load_env()
    settings = cm.load_settings()

    if not env["api_key"]:
        print("✗ 未配置 API Key，请在 .env 中设置 DASHSCOPE_API_KEY")
        return

    chat = OmniChatService(
        api_key=env["api_key"],
        model=settings["models"]["non_realtime"],
        base_url=cm.get_base_url(),
    )

    system_prompt = cm.build_system_prompt()
    chat.set_system_prompt(system_prompt)
    voice = cm.get_voice()

    output_audio = False  # 默认关闭音频（命令行没法播）
    print(f"\n模型: {settings['models']['non_realtime']}")
    print(f"角色: {cm.load_active_persona().get('name', 'N/A')}")
    enable_search = settings.get("non_realtime", {}).get("enable_search", False)
    print(f"音色: {voice}")
    print(f"音频输出: {'开' if output_audio else '关'}")
    print(f"联网搜索: {'开' if enable_search else '关'}")
    print("\n命令: /img, /audio on|off, /search on|off, /clear, /history, /quit")
    print("-" * 50)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break

        if not user_input:
            continue

        # 命令处理
        if user_input == "/quit":
            print("退出")
            break
        elif user_input == "/clear":
            chat.clear_history()
            chat.set_system_prompt(system_prompt)
            print("✓ 对话历史已清空")
            continue
        elif user_input == "/history":
            history = chat.get_history()
            print(f"\n--- 对话历史 ({len(history)} 条) ---")
            for msg in history:
                role = msg["role"]
                content = msg["content"]
                if isinstance(content, list):
                    text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    has_image = any(c.get("type") == "image_url" for c in content)
                    display = " ".join(text_parts)
                    if has_image:
                        display += " [附图]"
                else:
                    display = content
                print(f"  [{role}] {display[:80]}")
            continue
        elif user_input.startswith("/audio"):
            arg = user_input.replace("/audio", "").strip()
            if arg == "on":
                output_audio = True
                print("✓ 音频输出已开启")
            else:
                output_audio = False
                print("✓ 音频输出已关闭")
            continue
        elif user_input.startswith("/search"):
            arg = user_input.replace("/search", "").strip()
            if arg == "on":
                settings.setdefault("non_realtime", {})["enable_search"] = True
                print("✓ 联网搜索已开启")
            else:
                settings.setdefault("non_realtime", {})["enable_search"] = False
                print("✓ 联网搜索已关闭")
            continue
        elif user_input.startswith("/img"):
            # 发送文本+图片
            print("请输入要附带的文字（直接回车则用默认）:")
            text = input("  文字: ").strip() or "请描述这张图片"
            print("请输入图片文件的绝对路径:")
            img_path = input("  路径: ").strip()

            if not os.path.isabs(img_path):
                print("✗ 请输入绝对路径")
                continue
            if not os.path.exists(img_path):
                print(f"✗ 文件不存在: {img_path}")
                continue

            # 读取图片转 base64
            with open(img_path, "rb") as f:
                img_data = f.read()
            img_b64 = base64.b64encode(img_data).decode()

            # 判断格式
            ext = Path(img_path).suffix.lower()
            mime_map = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".gif": "gif", ".webp": "webp"}
            mime = mime_map.get(ext, "jpeg")

            # 构造多模态 content
            content = [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{mime};base64,{img_b64}"}
                },
            ]
            print(f"  发送: 文字=\"{text}\" + 图片({len(img_data)}字节)")
        else:
            # 纯文本
            content = user_input

        # 发送并流式接收回复
        modalities = ["text", "audio"] if output_audio else ["text"]
        print("\n助手: ", end="", flush=True)

        audio_chunks = []
        async for chunk in chat.send_message(
            content=content,
            modalities=modalities,
            voice=voice,
            enable_search=settings.get("non_realtime", {}).get("enable_search", False),
        ):
            if chunk["type"] == "text":
                print(chunk["data"], end="", flush=True)
            elif chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "error":
                print(f"\n✗ 错误: {chunk['data']}")
            elif chunk["type"] == "done":
                done_data = chunk.get("data", {})
                break

        print()  # 换行

        # 显示 usage 和联网搜索信息
        if done_data and isinstance(done_data, dict):
            usage = done_data.get("usage")
            if usage:
                print(f"  [tokens: {usage.get('total_tokens', '?')}]", end="")
            if settings.get("non_realtime", {}).get("enable_search", False):
                search_used = done_data.get("search_used", False)
                if search_used:
                    print(f"  [联网搜索: ✓ 已调用]", end="")
                else:
                    # SDK 可能无法检测 plugins，只显示已开启
                    print(f"  [联网搜索: 已开启]", end="")
            print()

        # 播放音频
        if audio_chunks:
            audio_b64 = "".join(audio_chunks)
            audio_bytes = base64.b64decode(audio_b64)
            if HAS_PYAUDIO:
                print("  [播放音频...]")
                pa = pyaudio.PyAudio()
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=24000,
                    output=True,
                )
                stream.write(audio_bytes)
                stream.stop_stream()
                stream.close()
                pa.terminate()
                print("  [播放完成]")
            else:
                print(f"  [收到音频 {len(audio_bytes)} 字节，安装 pyaudio 可播放: pip install pyaudio]")


if __name__ == "__main__":
    asyncio.run(main())
