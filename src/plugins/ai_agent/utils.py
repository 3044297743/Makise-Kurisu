from openai import AsyncOpenAI
from typing import List, Dict, Optional
from nonebot import logger
import asyncio

from .config import plugin_config


async def call_ai_api(
    messages: List[Dict[str, str]], retries: int = 3
) -> Optional[str]:
    """调用外部AI API（使用OpenAI库，适配阿里云百炼），带重试机制"""
    if not plugin_config.api_key:
        logger.error("API key 未配置")
        return None

    for attempt in range(retries):
        try:
            client = AsyncOpenAI(
                api_key=plugin_config.api_key,
                base_url=plugin_config.api_base,
            )
            completion = await client.chat.completions.create(
                model=plugin_config.model,
                messages=messages,  # 直接传入历史消息（包含system, user, assistant）
                max_tokens=plugin_config.max_tokens,
                temperature=plugin_config.temperature,
            )
            # 提取回复内容
            content = completion.choices[0].message.content
            if content:
                return content.strip()
            else:
                logger.warning(f"AI API 返回空内容，重试 {attempt + 1}/{retries}")
        except Exception as e:
            logger.error(f"调用AI API失败 (尝试 {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(1 * (attempt + 1))  # 指数退避
            continue

    logger.error("AI API 调用失败，已达到最大重试次数")
    return None
