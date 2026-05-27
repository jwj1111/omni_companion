"""
测试配置管理器
运行: cd backend && python -m pytest tests/test_config_manager.py -v
"""
import sys
from pathlib import Path

# 确保可以导入 app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.config_manager import ConfigManager


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_cm():
    return ConfigManager(PROJECT_ROOT)


def test_load_env():
    """测试加载 .env"""
    cm = get_cm()
    env = cm.load_env()
    assert "api_key" in env
    assert "region" in env
    print(f"✓ API Key 已配置: {'是' if env['api_key'] else '否'}")
    print(f"✓ 区域: {env['region']}")


def test_load_settings():
    """测试加载 settings.yaml"""
    cm = get_cm()
    settings = cm.load_settings()
    assert "models" in settings
    assert "realtime" in settings
    assert "non_realtime" in settings
    assert "screen_capture" in settings
    print(f"✓ 非实时模型: {settings['models']['non_realtime']}")
    print(f"✓ 实时模型: {settings['models']['realtime']}")
    print(f"✓ 激活角色: {settings['active_persona']}")


def test_load_persona():
    """测试加载角色配置"""
    cm = get_cm()
    settings = cm.load_settings()
    persona_id = settings.get("active_persona", "a001")
    persona = cm.load_persona(persona_id)
    assert "name" in persona
    assert "personality" in persona
    print(f"✓ 角色名: {persona['name']}")
    print(f"✓ role_id: {persona.get('role_id', 'N/A')}")


def test_load_interaction_rules():
    """测试加载行为规范"""
    cm = get_cm()
    rules = cm.load_interaction_rules()
    assert len(rules) > 0
    assert "行为规范" in rules
    print(f"✓ 行为规范已加载: {len(rules)} 字符")


def test_build_system_prompt():
    """测试组装 system prompt"""
    cm = get_cm()
    prompt = cm.build_system_prompt()
    assert len(prompt) > 0
    # 应包含角色名
    persona = cm.load_active_persona()
    assert persona["name"] in prompt
    # 应包含行为规范
    assert "行为规范" in prompt
    print(f"✓ System prompt 已组装: {len(prompt)} 字符")
    print(f"--- 前200字预览 ---\n{prompt[:200]}...")


def test_get_voice():
    """测试获取音色"""
    cm = get_cm()
    voice = cm.get_voice()
    assert voice != ""
    print(f"✓ 当前音色: {voice}")


def test_get_urls():
    """测试获取 API URL"""
    cm = get_cm()
    base_url = cm.get_base_url()
    realtime_url = cm.get_realtime_url()
    assert "dashscope" in base_url
    assert "wss://" in realtime_url
    print(f"✓ 非实时 URL: {base_url}")
    print(f"✓ 实时 URL: {realtime_url}")


def test_list_personas():
    """测试列出角色"""
    cm = get_cm()
    personas = cm.list_personas()
    assert len(personas) > 0
    print(f"✓ 可用角色数: {len(personas)}")
    for p in personas:
        print(f"  - {p['id']}: {p['name']} (voice={p['voice']})")


if __name__ == "__main__":
    print("=" * 50)
    print("配置管理器测试")
    print("=" * 50)
    tests = [
        test_load_env,
        test_load_settings,
        test_load_persona,
        test_load_interaction_rules,
        test_build_system_prompt,
        test_get_voice,
        test_get_urls,
        test_list_personas,
    ]
    for t in tests:
        print(f"\n--- {t.__doc__} ---")
        try:
            t()
        except Exception as e:
            print(f"✗ 失败: {e}")
    print("\n" + "=" * 50)
    print("测试完成")
