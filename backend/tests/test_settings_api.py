"""
测试设置管理 API
运行: cd backend && python tests/test_settings_api.py
"""
import asyncio
import json

import httpx

BASE_URL = "http://localhost:8000"


async def test_get_all_settings():
    """测试获取所有配置"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/settings/all")
        assert resp.status_code == 200
        data = resp.json()
        assert "env" in data
        assert "settings" in data
        assert "persona" in data
        assert "interaction_rules" in data
        print(f"✓ API Key 已配置: {data['env']['api_key_set']}")
        print(f"✓ 区域: {data['env']['region']}")
        print(f"✓ 激活角色: {data['settings']['active_persona']}")
        print(f"✓ 角色名: {data['persona'].get('name', 'N/A')}")


async def test_list_personas():
    """测试列出所有角色"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/settings/personas")
        assert resp.status_code == 200
        data = resp.json()
        assert "personas" in data
        print(f"✓ 角色数量: {len(data['personas'])}")
        for p in data["personas"]:
            print(f"  - {p['id']}: {p['name']} (voice={p['voice']})")


async def test_get_persona():
    """测试获取指定角色"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/settings/persona/a001")
        assert resp.status_code == 200
        data = resp.json()
        assert "persona" in data
        print(f"✓ 角色: {data['persona'].get('name', 'N/A')}")


async def test_get_voices():
    """测试获取音色列表"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/settings/voices")
        assert resp.status_code == 200
        data = resp.json()
        assert "voices" in data
        assert len(data["voices"]) > 0
        print(f"✓ 可用音色数: {len(data['voices'])}")
        for v in data["voices"][:5]:
            print(f"  - {v['id']}: {v['name']} - {v['desc']}")
        if len(data["voices"]) > 5:
            print(f"  ... 还有 {len(data['voices']) - 5} 个")


async def test_get_nonexistent_persona():
    """测试获取不存在的角色（应返回404）"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/settings/persona/nonexistent")
        assert resp.status_code == 404
        print("✓ 不存在的角色正确返回 404")


async def main():
    print("=" * 50)
    print("设置管理 API 测试")
    print(f"目标: {BASE_URL}")
    print("=" * 50)
    print("\n⚠ 请确保后端已启动: python run.py\n")

    tests = [
        test_get_all_settings,
        test_list_personas,
        test_get_persona,
        test_get_voices,
        test_get_nonexistent_persona,
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
