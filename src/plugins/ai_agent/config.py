from typing import List

from pydantic import BaseModel, Extra, validator
import os
from dotenv import load_dotenv


class Config(BaseModel, extra=Extra.ignore):
    """插件配置项"""

    # 外部AI API配置
    api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key: str = ""
    model: str = "qwen-plus"
    max_tokens: int = 1000
    temperature: float = 0.7

    # 上下文记忆配置
    max_context_length: int = 10  # 保存的最近对话轮数（每轮包含用户和AI的消息）

    # 默认人格设置（系统提示）
    default_personality: str = "你是一个乐于助人的AI助手。"

    # 机器人唤起配置（to_me 已处理 @和私聊，此处留作扩展）
    require_at: bool = True

    # 支持"昵称唤醒"：群聊中消息以某个词开头即可触发（仅在 require_at=False 时生效）
    wake_words: List[str] = ["小爱", "助手"]

    @validator("max_tokens")
    def validate_max_tokens(cls, v):
        if v <= 0:
            raise ValueError("max_tokens 必须大于 0")
        return v

    @validator("temperature")
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError("temperature 必须在 0 到 2 之间")
        return v

    @validator("max_context_length")
    def validate_max_context_length(cls, v):
        if v <= 0:
            raise ValueError("max_context_length 必须大于 0")
        return v

    @validator("api_key")
    def validate_api_key(cls, v):
        if not v:
            raise ValueError("api_key 不能为空")
        return v


# 从环境变量获取插件配置
def load_plugin_config() -> Config:
    """从环境变量加载插件配置"""
    # 加载环境变量
    load_dotenv(".env.prod")

    return Config(
        api_base=os.getenv(
            "AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
        api_key=os.getenv("AI_API_KEY", ""),
        model=os.getenv("AI_MODEL", "qwen-plus"),
        max_tokens=int(os.getenv("MAX_TOKENS", "1000")),
        temperature=float(os.getenv("TEMPERATURE", "0.7")),
        max_context_length=int(os.getenv("MAX_CONTEXT_LENGTH", "10")),
        default_personality=os.getenv(
            "DEFAULT_PERSONALITY", "你是一个乐于助人的AI助手。"
        ),
        require_at=os.getenv("REQUIRE_AT", "true").lower() == "true",
        wake_words=[
            word.strip()
            for word in os.getenv("WAKE_WORDS", "小爱,助手").split(",")
            if word.strip()
        ],
    )


plugin_config = load_plugin_config()
