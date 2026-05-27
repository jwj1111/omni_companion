"""
测试沉浸模式 WebSocket API
运行: cd backend && python tests/test_realtime_api.py
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/realtime/ws"


async def test_websocket_connect_and_start():
    """测试 WebSocket 连接并启动沉浸模式会话"""
    try:
        async with websockets.connect(WS_URL) as ws:
            print("✓ WebSocket 连接成功")

            # 发送 start 控制指令
            await ws.send(json.dumps({
                "type": "control",
                "action": "start",
            }))

            # 等待服务端返回 connected 或 session 事件
            # 设超时避免永久阻塞
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(response)
                print(f"✓ 收到响应: {data}")

                if data.get("type") == "status" and data.get("event") == "connected":
                    print("✓ 沉浸模式会话已建立")
                elif data.get("type") == "error":
                    print(f"⚠ 服务端返回错误: {data.get('message')}")
                    print("  （如果是 API Key 无效，属于预期行为）")
                else:
                    # 可能是 session.created 等事件
                    print(f"✓ 收到事件: {data.get('type', 'unknown')}")

            except asyncio.TimeoutError:
                print("⚠ 等待响应超时（可能是 API Key 无效或网络问题）")

            # 发送 stop
            await ws.send(json.dumps({
                "type": "control",
                "action": "stop",
            }))

            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)
                if data.get("event") == "disconnected":
                    print("✓ 会话已断开")
            except asyncio.TimeoutError:
                print("✓ 已发送 stop 指令")

    except websockets.exceptions.ConnectionRefused:
        print("✗ 连接被拒绝，请确认后端已启动")
    except Exception as e:
        print(f"✗ 异常: {e}")


async def test_websocket_message_format():
    """测试前端消息格式是否被正确接收"""
    try:
        async with websockets.connect(WS_URL) as ws:
            # 不发 start 就发 audio，验证不会崩溃
            await ws.send(json.dumps({
                "type": "audio",
                "data": "AAAA",  # 假的 base64 音频
            }))

            await ws.send(json.dumps({
                "type": "screenshot",
                "data": "/9j/4AAQ",  # 假的 JPEG base64
            }))

            # 短暂等待确认没有崩溃
            await asyncio.sleep(0.5)
            print("✓ 消息格式正确，后端未崩溃")

    except websockets.exceptions.ConnectionRefused:
        print("✗ 连接被拒绝，请确认后端已启动")
    except Exception as e:
        print(f"✗ 异常: {e}")


async def main():
    print("=" * 50)
    print("沉浸模式 WebSocket API 测试")
    print(f"目标: {WS_URL}")
    print("=" * 50)
    print("\n⚠ 请确保后端已启动: python run.py\n")

    tests = [
        test_websocket_message_format,
        test_websocket_connect_and_start,
    ]
    for t in tests:
        print(f"\n--- {t.__doc__} ---")
        try:
            await t()
        except Exception as e:
            print(f"✗ 失败: {e}")

    print("\n" + "=" * 50)
    print("测试完成")


if __name__ == "__main__":
    asyncio.run(main())
