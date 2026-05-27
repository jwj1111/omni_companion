"""
测试非沉浸模式聊天 API
运行: cd backend && python -m pytest tests/test_chat_api.py -v
或直接: cd backend && python tests/test_chat_api.py
"""
import asyncio
import sys
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"


async def test_health():
    """测试健康检查"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        print("✓ 健康检查通过")


async def test_send_text_message():
    """测试发送纯文本消息（流式返回）"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/api/chat/send",
            json={
                "content": "你好，你是谁？",
                "output_audio": False,
            },
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200

        # 读取流式返回
        text_parts = []
        for line in resp.text.strip().split("\n"):
            if line:
                import json
                chunk = json.loads(line)
                if chunk["type"] == "text":
                    text_parts.append(chunk["data"])
                elif chunk["type"] == "done":
                    break
                elif chunk["type"] == "error":
                    print(f"✗ 错误: {chunk['data']}")
                    return

        full_text = "".join(text_parts)
        assert len(full_text) > 0
        print(f"✓ 文本回复: {full_text[:100]}...")


async def test_send_text_with_audio():
    """测试发送文本并返回音频"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/api/chat/send",
            json={
                "content": "说一句简短的话",
                "output_audio": True,
            },
        )
        assert resp.status_code == 200

        import json
        has_text = False
        has_audio = False
        for line in resp.text.strip().split("\n"):
            if line:
                chunk = json.loads(line)
                if chunk["type"] == "text":
                    has_text = True
                elif chunk["type"] == "audio":
                    has_audio = True

        print(f"✓ 有文本回复: {has_text}")
        print(f"✓ 有音频回复: {has_audio}")


async def test_get_history():
    """测试获取对话历史"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/chat/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data
        print(f"✓ 对话历史: {len(data['messages'])} 条消息")


async def test_clear_history():
    """测试清空对话历史"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/api/chat/clear")
        assert resp.status_code == 200
        # 验证清空
        resp = await client.get(f"{BASE_URL}/api/chat/history")
        data = resp.json()
        # 应该只剩 system message
        assert len(data["messages"]) <= 1
        print("✓ 对话历史已清空")


async def main():
    print("=" * 50)
    print("非沉浸模式 API 测试")
    print(f"目标: {BASE_URL}")
    print("=" * 50)
    print("\n⚠ 请确保后端已启动: python run.py\n")

    tests = [
        test_health,
        test_send_text_message,
        test_send_text_with_audio,
        test_get_history,
        test_clear_history,
    ]
    for t in tests:
        print(f"\n--- {t.__doc__} ---")
        try:
            await t()
        except httpx.ConnectError:
            print("✗ 连接失败，请确认后端已启动")
            break
        except Exception as e:
            print(f"✗ 失败: {e}")

    print("\n" + "=" * 50)
    print("测试完成")


if __name__ == "__main__":
    asyncio.run(main())
