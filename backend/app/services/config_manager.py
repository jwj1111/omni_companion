"""
配置管理服务
负责加载和保存各层配置文件
"""
import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv, set_key


class ConfigManager:
    """统一配置管理器"""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            # 默认：backend/ 的上级目录即项目根目录
            project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.project_root = project_root
        self.env_path = project_root / ".env"
        self.settings_path = project_root / "config" / "settings.yaml"
        self.personas_dir = project_root / "config" / "personas"
        self.prompts_dir = project_root / "prompts"

        # 运行期微调只保存在内存中；前端刷新会主动重置，文件中的默认值保持权威
        self._env_override: dict = {}
        self._settings_override: dict = {}
        self._persona_overrides: dict[str, dict] = {}
        self._interaction_rules_override: Optional[str] = None

        # 加载 .env
        load_dotenv(self.env_path)

    # ==================== 加载 ====================

    def load_env(self) -> dict:
        """加载 .env 和运行期环境变量覆盖。"""
        api_key = os.getenv("DASHSCOPE_API_KEY", "")
        api_key_realtime = os.getenv("DASHSCOPE_API_KEY_REALTIME", "")
        env = {
            "api_key": api_key,
            "api_key_realtime": api_key_realtime or api_key,  # 默认共用同一个 key
            "region": os.getenv("API_REGION", "beijing"),
        }
        return self._deep_merge(env, self._env_override)

    def load_settings(self) -> dict:
        """加载默认 settings，并叠加本次运行期微调。"""
        defaults = self._default_settings()
        if self.settings_path.exists():
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            defaults = self._deep_merge(defaults, data)
        return self._deep_merge(defaults, self._settings_override)

    def load_persona(self, persona_id: str) -> dict:
        """加载指定角色的 persona 配置，并叠加本次运行期微调。"""
        persona_path = self.personas_dir / f"{persona_id}.yaml"
        if not persona_path.exists():
            raise FileNotFoundError(f"角色配置不存在: {persona_id}")
        with open(persona_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        override = self._persona_overrides.get(persona_id, {})
        return self._deep_merge(data, override)

    def load_active_persona(self) -> dict:
        """加载当前激活角色"""
        settings = self.load_settings()
        persona_id = settings.get("active_persona", "a001")
        return self.load_persona(persona_id)

    def load_interaction_rules(self) -> str:
        """加载通用行为规范，并叠加本次运行期微调。"""
        if self._interaction_rules_override is not None:
            return self._interaction_rules_override
        rules_path = self.prompts_dir / "interaction_rules.txt"
        if not rules_path.exists():
            return ""
        with open(rules_path, "r", encoding="utf-8") as f:
            return f.read()


    def build_system_prompt(self, persona_id: Optional[str] = None) -> str:
        """
        组装完整的 system prompt
        结构：角色人设 + 行为规范
        """
        if persona_id is None:
            settings = self.load_settings()
            persona_id = settings.get("active_persona", "a001")

        persona = self.load_persona(persona_id)
        rules = self.load_interaction_rules()

        # 拼装人设部分（Markdown 格式）
        sections = []
        name = persona.get("name", "")
        if name:
            sections.append(f"# 角色：{name}")

        field_map = {
            "personality": "## 性格",
            "background": "## 背景身份",
            "speaking_style": "## 说话风格",
            "relationship": "## 与用户的关系",
            "quirks": "## 口癖",
        }

        for field, heading in field_map.items():
            value = persona.get(field, "").strip()
            if value:
                sections.append(f"{heading}\n\n{value}")

        persona_text = "\n\n".join(sections)

        # 拼装最终 prompt
        system_prompt = persona_text
        if rules.strip():
            system_prompt += "\n\n---\n\n" + rules.strip()

        return system_prompt

    def get_voice(self, persona_id: Optional[str] = None) -> str:
        """获取音色（persona 优先，否则用 settings 默认值）"""
        settings = self.load_settings()
        if persona_id is None:
            persona_id = settings.get("active_persona", "a001")

        try:
            persona = self.load_persona(persona_id)
            voice = persona.get("voice", "")
            if voice:
                return voice
        except FileNotFoundError:
            pass

        return settings.get("voice", "Tina")

    def get_base_url(self) -> str:
        """根据区域获取 base_url"""
        env = self.load_env()
        region = env.get("region", "beijing")
        if region == "singapore":
            return "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def get_realtime_url(self) -> str:
        """获取 Realtime WebSocket URL"""
        env = self.load_env()
        region = env.get("region", "beijing")
        if region == "singapore":
            return "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime"
        return "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"

    # ==================== 保存 ====================

    def save_settings(self, data: dict):
        """应用 settings 运行期微调，不写回默认配置文件。"""
        self._settings_override = self._deep_merge(self._settings_override, data)

    def save_persona(self, persona_id: str, data: dict):
        """应用角色运行期微调，不写回默认角色文件。"""
        current = self._persona_overrides.get(persona_id, {})
        self._persona_overrides[persona_id] = self._deep_merge(current, data)

    def save_env_key(self, key: str, value: str):
        """更新环境变量；API Key 持久化，区域只作为本次运行期微调。"""
        if key == "API_REGION":
            self._env_override["region"] = value
            return

        if not self.env_path.exists():
            self.env_path.touch()
        set_key(str(self.env_path), key, value)
        # 重新加载
        load_dotenv(self.env_path, override=True)

    def save_interaction_rules(self, content: str):
        """应用行为规范运行期微调，不写回默认 prompt 文件。"""
        self._interaction_rules_override = content

    def reset_runtime_overrides(self):
        """清除所有运行期微调，恢复文件中的默认配置。"""
        self._env_override.clear()
        self._settings_override.clear()
        self._persona_overrides.clear()
        self._interaction_rules_override = None


    # ==================== 查询 ====================

    def list_personas(self) -> list:
        """列出所有可用角色"""
        if not self.personas_dir.exists():
            return []
        personas = []
        for f in self.personas_dir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                personas.append({
                    "id": f.stem,
                    "role_id": data.get("role_id", f.stem),
                    "name": data.get("name", f.stem),
                    "voice": data.get("voice", ""),
                })
            except Exception:
                continue
        return personas

    # ==================== 内部工具 ====================

    @staticmethod
    def _default_settings() -> dict:
        return {
            "active_persona": "a001",
            "models": {
                "non_realtime": "qwen3.5-omni-plus",
                "realtime": "qwen3.5-omni-plus-realtime",
            },
            "voice": "Tina",
            "output": {
                "modalities": ["text", "audio"],
            },
            "realtime": {
                "vad_type": "semantic_vad",
                "vad_threshold": 0.5,
                "silence_duration_ms": 800,
                "enable_search": False,
                "input_audio_transcription": True,
                "transcription_model": "qwen3-asr-flash-realtime",
            },
            "non_realtime": {
                "enable_search": False,
            },
            "screen_capture": {
                "enabled": True,
                "interval_ms": 1000,
                "max_resolution": "720p",
                "format": "jpeg",
                "max_size_kb": 190,
            },
        }

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """深度合并字典，override 覆盖 base"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
