from nonebot import on_message, on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from .config import plugin_config
from .memory import memory
from .utils import call_ai_api


def _combined_wake_rule(bot: Bot, event: Event) -> bool:
    """同时支持@机器人和唤醒词（私聊始终唤醒）。"""
    # 私聊始终唤醒
    if not hasattr(event, "group_id") or not event.group_id:
        return True

    # 检查是否@机器人
    if event.is_tome():
        return True

    # 检查唤醒词
    raw_msg = event.get_message().extract_plain_text().strip()
    if not raw_msg:
        return False

    for w in plugin_config.wake_words or []:
        if raw_msg.startswith(w):
            return True
    return False


def _generate_session_id(event: Event) -> str:
    """生成会话ID（群聊用 group_群号_QQ号，私聊用 private_QQ号）"""
    if hasattr(event, "group_id") and event.group_id:
        return f"group_{event.group_id}_{event.user_id}"
    else:
        return f"private_{event.user_id}"


def _extract_message_content(event: Event) -> str:
    """提取消息内容，若使用唤醒词则去掉前缀"""
    raw_msg = event.get_message().extract_plain_text().strip()
    if not raw_msg:
        return ""

    # 如果是群聊且使用了唤醒词，去掉前缀
    if hasattr(event, "group_id") and event.group_id:
        for w in plugin_config.wake_words or []:
            if raw_msg.startswith(w):
                return raw_msg[len(w) :].strip()

    return raw_msg


def _build_reply(event: Event, text: str) -> Message:
    if hasattr(event, "group_id") and event.group_id:
        return Message(
            [MessageSegment.at(event.user_id), MessageSegment.text(f" {text}")]
        )
    return Message(text)


# 消息响应器：同时支持@机器人和唤醒词
chat_matcher = on_message(
    rule=_combined_wake_rule,
    priority=10,
)


@chat_matcher.handle()
async def handle_chat(bot: Bot, event: Event):
    # 提取消息内容
    user_message = _extract_message_content(event)
    if not user_message:
        return

    # 生成会话ID
    session_id = _generate_session_id(event)

    # 保存用户消息
    memory.add_user_message(session_id, user_message)

    # 获取带有人格的历史消息
    messages = memory.get_recent_messages(session_id, include_system=True)

    # 调用AI API
    reply = await call_ai_api(messages)

    if reply:
        # 保存AI回复
        memory.add_assistant_message(session_id, reply)
        await chat_matcher.finish(_build_reply(event, reply))
    else:
        await chat_matcher.finish(
            _build_reply(event, "抱歉，AI服务暂时不可用，请稍后再试。")
        )


# 清除当前会话的记忆（仅限超级用户）
clear_cmd = on_command("清除记忆", permission=SUPERUSER, priority=5)


@clear_cmd.handle()
async def handle_clear(bot: Bot, event: Event):
    session_id = _generate_session_id(event)
    memory.clear(session_id)
    await clear_cmd.finish(_build_reply(event, "已清除当前会话的记忆。"))


# 设置当前会话的人格
set_personality_cmd = on_command("setpersonality", aliases={"设置人格"}, priority=5)


@set_personality_cmd.handle()
async def handle_set_personality(bot: Bot, event: Event, args: Message = CommandArg()):
    personality = args.extract_plain_text().strip()
    if not personality:
        await set_personality_cmd.finish(_build_reply(event, "请提供人格设置内容。"))

    session_id = _generate_session_id(event)
    memory.set_personality(session_id, personality)
    await set_personality_cmd.finish(_build_reply(event, "人格设置成功！"))
