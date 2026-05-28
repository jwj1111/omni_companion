"""
设置管理路由
负责配置的读取和更新
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_config_manager, reset_services

router = APIRouter()


# ==================== 请求模型 ====================

class UpdateSettingsRequest(BaseModel):
    """更新设置请求"""
    settings: Optional[dict] = None


class UpdateEnvRequest(BaseModel):
    """更新环境变量请求"""
    key: str
    value: str


class PersonaData(BaseModel):
    """角色数据"""
    role_id: Optional[str] = None
    name: str
    voice: Optional[str] = ""
    personality: Optional[str] = ""
    background: Optional[str] = ""
    speaking_style: Optional[str] = ""
    relationship: Optional[str] = ""
    quirks: Optional[str] = ""


class UpdateRulesRequest(BaseModel):
    """更新行为规范请求"""
    content: str


# ==================== 路由 ====================

@router.get("/all")
async def get_all_settings(cm=Depends(get_config_manager)):
    """获取所有配置"""
    env = cm.load_env()
    settings = cm.load_settings()
    persona = cm.load_active_persona()
    rules = cm.load_interaction_rules()

    return {
        "env": {
            "api_key_set": bool(env["api_key"]),
            "api_key_realtime_set": bool(env["api_key_realtime"]),
            "region": env["region"],
        },
        "settings": settings,
        "persona": persona,
        "interaction_rules": rules,
    }


@router.put("/update")
async def update_settings(req: UpdateSettingsRequest, cm=Depends(get_config_manager)):
    """应用 settings 运行期微调"""
    if req.settings:
        cm.save_settings(req.settings)
        reset_services()
    return {"status": "ok"}


@router.post("/reset-runtime")
async def reset_runtime_settings(cm=Depends(get_config_manager)):
    """清除运行期微调，恢复默认配置"""
    cm.reset_runtime_overrides()
    reset_services()
    return {"status": "ok"}


@router.put("/env")
async def update_env(req: UpdateEnvRequest, cm=Depends(get_config_manager)):
    """更新环境变量；API Key 持久化，区域为运行期微调"""
    allowed_keys = ["DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY_REALTIME", "API_REGION"]
    if req.key not in allowed_keys:
        raise HTTPException(status_code=400, detail=f"不允许修改的 key: {req.key}")
    cm.save_env_key(req.key, req.value)
    reset_services()
    return {"status": "ok"}



@router.get("/personas")
async def list_personas(cm=Depends(get_config_manager)):
    """列出所有可用角色"""
    return {"personas": cm.list_personas()}


@router.get("/persona/{persona_id}")
async def get_persona(persona_id: str, cm=Depends(get_config_manager)):
    """获取指定角色配置"""
    try:
        persona = cm.load_persona(persona_id)
        return {"persona": persona}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"角色不存在: {persona_id}")


@router.put("/persona/{persona_id}")
async def update_persona(persona_id: str, data: PersonaData, cm=Depends(get_config_manager)):
    """应用角色运行期微调"""
    persona_dict = data.model_dump()
    # 确保 role_id 一致
    persona_dict["role_id"] = persona_id
    cm.save_persona(persona_id, persona_dict)
    reset_services()
    return {"status": "ok"}



@router.delete("/persona/{persona_id}")
async def delete_persona(persona_id: str, cm=Depends(get_config_manager)):
    """删除角色"""
    persona_path = cm.personas_dir / f"{persona_id}.yaml"
    if not persona_path.exists():
        raise HTTPException(status_code=404, detail=f"角色不存在: {persona_id}")
    persona_path.unlink()
    return {"status": "ok"}


@router.get("/rules")
async def get_rules(cm=Depends(get_config_manager)):
    """获取行为规范 prompt"""
    return {"content": cm.load_interaction_rules()}


@router.put("/rules")
async def update_rules(req: UpdateRulesRequest, cm=Depends(get_config_manager)):
    """应用行为规范运行期微调"""
    cm.save_interaction_rules(req.content)
    reset_services()
    return {"status": "ok"}



@router.get("/voices")
async def list_voices():
    """返回可用音色列表"""
    # 基于 omni音色列表.md 中的 Qwen3.5-Omni 系列音色
    voices = [
        {"id": "Tina", "name": "甜甜 Tina", "desc": "温热的奶茶，甜甜的、暖暖的"},
        {"id": "Cindy", "name": "林欣宜 Cindy", "desc": "台湾说话嗲嗲的小姐姐"},
        {"id": "Liora Mira", "name": "清欢 Liora Mira", "desc": "用声音织就烟火人间的温柔"},
        {"id": "Sunnybobi", "name": "知芝 Sunnybobi", "desc": "大大咧咧的社恐邻家姑娘"},
        {"id": "Raymond", "name": "林川野 Raymond", "desc": "声音清亮，爱吃外卖的宅男"},
        {"id": "Ethan", "name": "晨煦 Ethan", "desc": "阳光 温暖 活力 朝气"},
        {"id": "Theo Calm", "name": "予安 Theo Calm", "desc": "在静默处传递理解，在言语间疗愈人心"},
        {"id": "Serena", "name": "苏瑶 Serena", "desc": "温柔小姐姐"},
        {"id": "Harvey", "name": "厚 Harvey", "desc": "低沉、温和，带着咖啡与旧书的气息"},
        {"id": "Maia", "name": "四月 Maia", "desc": "知性与温柔的碰撞"},
        {"id": "Evan", "name": "江晨 Evan", "desc": "男大学生，年下奶狗"},
        {"id": "Qiao", "name": "小乔妹 Qiao", "desc": "表面甜妹，个性十足"},
        {"id": "Momo", "name": "茉兔 Momo", "desc": "撒娇搞怪，逗你开心"},
        {"id": "Wil", "name": "伟伦 Wil", "desc": "在深圳长大的港台腔小哥哥"},
        {"id": "Angel", "name": "台普-安琪 Angel", "desc": "略带台式口音，超甜"},
        {"id": "Katerina", "name": "卡捷琳娜 Katerina", "desc": "御姐音色，韵律回味十足"},
        {"id": "Mione", "name": "敏儿 Mione", "desc": "成熟，知性英国邻家妹妹"},
        {"id": "Sunny", "name": "四川-晴儿 Sunny", "desc": "甜到你心里的川妹子"},
        {"id": "Sohee", "name": "素熙 Sohee", "desc": "温柔开朗的韩国欧尼"},
        {"id": "Ono Anna", "name": "小野杏 Ono Anna", "desc": "鬼灵精怪的青梅竹马"},
    ]
    return {"voices": voices}
