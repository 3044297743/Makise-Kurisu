from nonebot import get_plugin_config, get_bot, on_message, get_driver
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    Message,
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot_plugin_apscheduler import scheduler
from pixivpy3 import AppPixivAPI
import random
import asyncio
import re
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
import requests
from dotenv import load_dotenv
import os

from .config import Config, load_config

# 加载环境变量
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env.prod")

__plugin_meta__ = PluginMetadata(
    name="picture_send",
    description="定时发送Pixiv高收藏图片，支持手动发送",
    usage="自动定时发送指定tag的高收藏Pixiv图片，或在私聊中使用/色图，群聊中@机器人/使用昵称后发送/色图手动获取",
    config=Config,
)

# 使用独立的配置加载函数
config = load_config()

# 配置代理
proxies = None
if config.proxy_host and config.proxy_port > 0:
    proxy_url = f"http://{config.proxy_host}:{config.proxy_port}"
    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }

api = AppPixivAPI()

# 设置代理（如果已配置）
if proxies:
    # 设置requests会话的代理
    api.requests.proxies.update(proxies)

# 初始化Pixiv API
auth_success = False
if config.pixiv_refresh_token:
    try:
        api.auth(refresh_token=config.pixiv_refresh_token)
        auth_success = True
        print("Pixiv认证成功")
    except Exception as e:
        print(f"Pixiv认证失败: {e}")
        auth_success = False


async def download_image_to_temp(image_url: str) -> str:
    """下载图片到临时文件并返回文件路径"""
    try:
        # 设置代理（如果配置了）
        proxies = None
        if config.proxy_host and config.proxy_port > 0:
            proxy_url = f"http://{config.proxy_host}:{config.proxy_port}"
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }

        # 下载图片
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.pixiv.net/",
        }

        response = requests.get(image_url, headers=headers, proxies=proxies, timeout=30)
        response.raise_for_status()

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(response.content)
            return temp_file.name

    except Exception as e:
        print(f"下载图片失败 {image_url}: {e}")
        raise


def _extract_next_search_params(next_url: str | None) -> dict[str, str]:
    if not next_url:
        return {}

    query_params = parse_qs(urlparse(next_url).query)
    return {key: values[0] for key, values in query_params.items() if values}


def _is_r18_illust(illust: dict) -> bool:
    tags = illust.get("tags", [])
    for tag in tags:
        tag_name = tag.get("name", "") if isinstance(tag, dict) else str(tag)
        if tag_name.startswith("R-18"):
            return True
    return False


async def get_random_high_bookmark_illust(
    keyword: str,
    min_bookmarks: int = 1000,
    max_pages: int = 5,
    allow_r18: bool = False,
    excluded_illust_ids: set[int] | None = None,
) -> tuple[dict | None, str | None]:
    # 每次调用前检查认证状态
    global auth_success
    if not auth_success and config.pixiv_refresh_token:
        try:
            api.auth(refresh_token=config.pixiv_refresh_token)
            auth_success = True
            print("Pixiv认证成功")
        except Exception as e:
            print(f"Pixiv认证失败: {e}")
            auth_success = False

    if not auth_success:
        raise Exception("Pixiv API需要认证，请检查refresh_token配置是否正确")

    matched_illusts = []
    high_bookmarks = []
    excluded_ids = excluded_illust_ids or set()

    if keyword:  # 如果关键词不为空，使用搜索
        # 使用输入关键词搜索作品标签，并在前几页中继续查找高收藏结果
        search_params = {
            "word": keyword,
            "search_target": "partial_match_for_tags",
            "sort": "date_desc",
        }
        for _ in range(max_pages):
            json_result = await asyncio.to_thread(api.search_illust, **search_params)
            current_illusts = json_result.get("illusts", [])
            if not current_illusts:
                break

            matched_illusts.extend(current_illusts)
            high_bookmarks.extend(
                illust
                for illust in current_illusts
                if illust.get("total_bookmarks", 0) >= min_bookmarks
                and (allow_r18 or not _is_r18_illust(illust))
                and illust.get("id") not in excluded_ids
            )

            next_params = _extract_next_search_params(json_result.get("next_url"))
            if not next_params:
                break
            search_params = next_params
    else:  # 如果tag为空，使用推荐图片
        json_result = await asyncio.to_thread(api.illust_recommended)

        if "illusts" not in json_result:
            return None, "no_results"

        matched_illusts = json_result["illusts"]
        high_bookmarks = [
            illust
            for illust in matched_illusts
            if illust.get("total_bookmarks", 0) >= min_bookmarks
            and (allow_r18 or not _is_r18_illust(illust))
            and illust.get("id") not in excluded_ids
        ]

    if not matched_illusts:
        return None, "no_results"

    if not high_bookmarks:
        return None, "bookmark_filtered"

    # 随机选择
    illust = random.choice(high_bookmarks)
    return illust, None


def _build_illust_caption(illust: dict, index: int) -> str:
    return (
        f"图片 {index}:\n"
        f"Pixiv图片: {illust['title']}\n"
        f"作者: {illust['user']['name']}\n"
        f"收藏数: {illust['total_bookmarks']}\n\n"
    )


def _build_illust_message(
    illust: dict, index: int, temp_file_path: str | None
) -> Message:
    message_segments = [MessageSegment.text(_build_illust_caption(illust, index))]
    if temp_file_path:
        message_segments.append(MessageSegment.image(f"file://{temp_file_path}"))
    else:
        message_segments.append(MessageSegment.text("[图片加载失败]\n"))
    return Message(message_segments)


def _build_illust_fallback_message(
    illust: dict, index: int, error_text: str
) -> Message:
    return Message(
        MessageSegment.text(
            _build_illust_caption(illust, index) + f"[图片发送失败: {error_text}]"
        )
    )


def _with_requester_mention(
    event: GroupMessageEvent | PrivateMessageEvent, message: Message
) -> Message:
    if isinstance(event, GroupMessageEvent):
        return Message(
            [MessageSegment.at(event.user_id), MessageSegment.text("\n"), *message]
        )
    return message


async def _send_with_retry(
    send_func, message: Message, fallback_message: Message
) -> bool:
    for attempt in range(2):
        try:
            await send_func(message)
            return True
        except ActionFailed as e:
            print(f"发送消息失败，第 {attempt + 1} 次尝试: {e}")
            if attempt == 0:
                await asyncio.sleep(1)

    try:
        await send_func(fallback_message)
        return False
    except ActionFailed as e:
        print(f"发送降级消息失败: {e}")
        raise


async def _send_illust_to_event(
    bot: Bot,
    event: GroupMessageEvent | PrivateMessageEvent,
    illust: dict,
    index: int,
    temp_file_path: str | None,
):
    message = _build_illust_message(illust, index, temp_file_path)
    fallback_message = _build_illust_fallback_message(illust, index, "图片发送超时")
    message = _with_requester_mention(event, message)
    fallback_message = _with_requester_mention(event, fallback_message)

    async def _send(message_to_send: Message):
        await bot.send(event=event, message=message_to_send)

    await _send_with_retry(_send, message, fallback_message)


async def _send_illust_to_target(
    bot: Bot,
    target: str,
    illust: dict,
    index: int,
    temp_file_path: str | None,
):
    message = _build_illust_message(illust, index, temp_file_path)
    fallback_message = _build_illust_fallback_message(illust, index, "图片发送超时")

    async def _send(message_to_send: Message):
        if target.startswith("group_"):
            await bot.send_group_msg(group_id=int(target[6:]), message=message_to_send)
        else:
            await bot.send_private_msg(user_id=int(target), message=message_to_send)

    await _send_with_retry(_send, message, fallback_message)


async def send_picture():
    if not config.send_targets:
        return

    # 获取多张图片（本次任务内去重）
    illusts = []
    selected_illust_ids: set[int] = set()
    max_attempts = max(config.send_count * 3, config.send_count)
    attempts = 0

    while len(illusts) < config.send_count and attempts < max_attempts:
        attempts += 1
        try:
            illust, _ = await get_random_high_bookmark_illust(
                config.pixiv_tag,
                config.pixiv_min_bookmarks,
                config.pixiv_max_search_pages,
                config.allow_r18,
                selected_illust_ids,
            )
            if illust:
                illust_id = illust.get("id")
                if illust_id in selected_illust_ids:
                    print(f"定时发送命中重复图片，跳过: {illust_id}")
                    continue
                if illust_id is not None:
                    selected_illust_ids.add(illust_id)
                illusts.append(illust)
        except Exception as e:
            print(f"定时发送图片失败: {e}")
            return  # 如果认证失败，停止发送

    if not illusts:
        return

    bot = get_bot()
    for i, illust in enumerate(illusts, 1):
        temp_file_path = None
        try:
            image_url = (
                illust["image_urls"]["large"]
                if "large" in illust["image_urls"]
                else illust["image_urls"]["medium"]
            )

            try:
                temp_file_path = await download_image_to_temp(image_url)
                print(f"定时发送图片 {i} 下载成功: {temp_file_path}")
            except Exception as e:
                print(f"定时发送图片 {i} 下载失败: {e}")

            for target in config.send_targets:
                await _send_illust_to_target(bot, target, illust, i, temp_file_path)
        finally:
            if temp_file_path:
                try:
                    Path(temp_file_path).unlink(missing_ok=True)
                    print(f"清理定时发送临时文件: {temp_file_path}")
                except Exception as e:
                    print(f"清理定时发送临时文件失败 {temp_file_path}: {e}")


# 设置定时任务
if config.send_time:
    hour, minute = map(int, config.send_time.split(":"))
    scheduler.add_job(send_picture, "cron", hour=hour, minute=minute)
else:
    # 解析间隔时间 HH:MM:SS
    try:
        h, m, s = map(int, config.send_interval.split(":"))
        interval_seconds = h * 3600 + m * 60 + s
        scheduler.add_job(send_picture, "interval", seconds=interval_seconds)
    except ValueError:
        # 如果解析失败，使用默认24小时
        scheduler.add_job(send_picture, "interval", hours=24)


def _strip_nickname_prefix(message_text: str) -> str:
    nicknames = get_driver().config.nickname or []
    for nick in nicknames:
        if message_text.startswith(nick):
            return message_text[len(nick) :].lstrip(" ，,：:").strip()
    return message_text


def _extract_picture_command(bot: Bot, event: Event) -> str:
    message_text = event.get_message().extract_plain_text().strip()
    if not message_text:
        return ""

    if not hasattr(event, "group_id") or not event.group_id:
        return message_text if message_text.startswith("/色图") else ""

    if event.is_tome():
        return message_text if message_text.startswith("/色图") else ""

    stripped_text = _strip_nickname_prefix(message_text)
    return stripped_text if stripped_text.startswith("/色图") else ""


def _picture_wake_rule(bot: Bot, event: Event) -> bool:
    return bool(_extract_picture_command(bot, event))


def _is_superuser(event: GroupMessageEvent | PrivateMessageEvent) -> bool:
    superusers = get_driver().config.superusers or set()
    return str(event.user_id) in {str(user_id) for user_id in superusers}


def _parse_picture_command(command_text: str) -> tuple[str, int, bool, bool]:
    command_body = command_text[len("/色图") :].strip()
    args = command_body.split()

    allow_r18 = config.allow_r18
    requested_r18 = False
    filtered_args = []
    for arg in args:
        lowered_arg = arg.lower()
        if lowered_arg in {"r18", "-r18", "--r18"}:
            allow_r18 = True
            requested_r18 = True
            continue
        if lowered_arg in {"safe", "-safe", "--safe", "非r18", "全年龄"}:
            allow_r18 = False
            continue
        filtered_args.append(arg)

    keyword = ""
    count = 1

    if len(filtered_args) == 1:
        if filtered_args[0].isdigit():
            count = int(filtered_args[0])
        else:
            keyword = filtered_args[0]
    elif filtered_args:
        if filtered_args[-1].isdigit():
            keyword = " ".join(filtered_args[:-1]).strip()
            count = int(filtered_args[-1])
        else:
            keyword = " ".join(filtered_args).strip()

    return keyword, count, allow_r18, requested_r18


# 手动发送图片的处理器
picture_handler = on_message(rule=_picture_wake_rule, priority=1, block=True)


@picture_handler.handle()
async def handle_picture_request(
    bot: Bot, event: GroupMessageEvent | PrivateMessageEvent
):
    message_text = _extract_picture_command(bot, event)

    # 解析命令参数：/色图 <关键词> [数量]
    command_body = message_text[len("/色图") :].strip()
    if not command_body:
        await picture_handler.finish(
            "格式错误！请使用：/色图 <关键词> [数量] [r18]\n例如：/色图 original 3 r18"
        )

    keyword, count, allow_r18, requested_r18 = _parse_picture_command(message_text)

    # r18 仅超级用户可用：非超级用户请求 r18 直接判定无效
    if requested_r18 and not _is_superuser(event):
        await picture_handler.finish("你的 r18 请求无效：仅超级用户可使用 r18 参数。")

    # 非超级用户即使全局开启 allow_r18，也强制使用全年龄模式
    if not _is_superuser(event):
        allow_r18 = False

    if count < 1 or count > 10:  # 限制最大数量为10
        await picture_handler.finish("图片数量必须在1-10之间！")

    # 获取指定数量的图片（本次请求内去重）
    illusts = []
    selected_illust_ids: set[int] = set()
    last_failure_reason = None
    max_attempts = max(count * 3, count)
    attempts = 0

    while len(illusts) < count and attempts < max_attempts:
        attempts += 1
        try:
            print(
                f"正在获取图片，keyword: '{keyword}', count: {count}, allow_r18: {allow_r18}, attempt: {attempts}/{max_attempts}"
            )
            illust, failure_reason = await get_random_high_bookmark_illust(
                keyword,
                config.pixiv_min_bookmarks,
                config.pixiv_max_search_pages,
                allow_r18,
                selected_illust_ids,
            )
            if illust:
                illust_id = illust.get("id")
                if illust_id in selected_illust_ids:
                    print(f"手动发送命中重复图片，跳过: {illust_id}")
                    continue
                if illust_id is not None:
                    selected_illust_ids.add(illust_id)
                illusts.append(illust)
                print(f"成功获取图片: {illust['title']}")
            else:
                last_failure_reason = failure_reason
        except Exception as e:
            print(f"获取图片失败: {e}")
            await picture_handler.finish(f"获取图片失败：{str(e)}")

    if not illusts:
        if last_failure_reason == "bookmark_filtered":
            if keyword:
                await picture_handler.finish(
                    f"找到了与“{keyword}”相关的图片，但前 {config.pixiv_max_search_pages} 页结果都未达到最低收藏数 {config.pixiv_min_bookmarks}。"
                )
            await picture_handler.finish(
                f"推荐图片中没有达到最低收藏数 {config.pixiv_min_bookmarks} 的结果，请稍后再试。"
            )

        await picture_handler.finish(
            "没有找到与搜索关键词匹配的图片，请尝试更短或更常见的关键词。"
        )

    for i, illust in enumerate(illusts, 1):
        temp_file_path = None
        try:
            image_url = (
                illust["image_urls"]["large"]
                if "large" in illust["image_urls"]
                else illust["image_urls"]["medium"]
            )

            try:
                temp_file_path = await download_image_to_temp(image_url)
                print(f"图片 {i} 下载成功: {temp_file_path}")
            except Exception as e:
                print(f"图片 {i} 下载失败: {e}")

            await _send_illust_to_event(bot, event, illust, i, temp_file_path)
        finally:
            if temp_file_path:
                try:
                    Path(temp_file_path).unlink(missing_ok=True)
                    print(f"清理临时文件: {temp_file_path}")
                except Exception as e:
                    print(f"清理临时文件失败 {temp_file_path}: {e}")

    await picture_handler.finish()
