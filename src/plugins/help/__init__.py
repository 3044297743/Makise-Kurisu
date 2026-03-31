# help 插件入口

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment

from .config import *


HELP_TEXT = """
Makise-Kurisu 机器人命令一览：

【AI 聊天】
    @机器人 <消息> 或 唤醒词：与AI对话
    /清除记忆（仅超级用户）：清除当前会话记忆
    /setpersonality <内容> 或 /设置人格 <内容>：设置当前人格

【网易云点歌】
    @机器人 /点歌 <歌名> [歌手]：点歌
    /选择 <数字>：选择点歌结果

【Pixiv 色图】
    @机器人 /色图 <关键词> [数量] [r18]：获取Pixiv高收藏图片

【帮助】
    @机器人 /help：查看所有命令及用法
"""


def _help_rule(bot: Bot, event: Event) -> bool:
    """仅在 @机器人 /help（私聊可直接 /help）时触发。"""
    message_text = event.get_message().extract_plain_text().strip()
    if not message_text:
        return False

    # 私聊支持直接 /help
    if not hasattr(event, "group_id") or not event.group_id:
        return message_text == "/help"

    # 群聊要求 @机器人 且正文为 /help
    return event.is_tome() and message_text == "/help"


# priority=0 使其高于当前项目内其他插件（1/5/10），block=True 命中后阻断后续插件。
help_matcher = on_message(rule=_help_rule, priority=0, block=True)


@help_matcher.handle()
async def handle_help(bot: Bot, event: Event):
    if hasattr(event, "group_id") and event.group_id:
        await help_matcher.finish(
            Message(
                [
                    MessageSegment.at(event.user_id),
                    MessageSegment.text(f"\n{HELP_TEXT}"),
                ]
            )
        )
        return
    await help_matcher.finish(HELP_TEXT)
