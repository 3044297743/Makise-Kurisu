from pathlib import Path
import asyncio
from time import monotonic

import httpx
from nonebot import get_driver, on_message
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    MessageSegment,
    Bot,
    Event,
)
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="netease_music",
    description="网易云音乐点歌插件",
    usage="私聊中使用 /点歌、/选择；群聊中需先@机器人或使用昵称，再发送 /点歌、/选择 命令",
)

config = Config()  # 使用默认配置
CACHE_TTL_SECONDS = 120

# 选择缓存：key 为 group_id/user_id，用于存储点歌结果供 /选择 调用
selection_cache: dict[str, tuple[list[dict], float]] = {}

# 导入 pyncm（需要在 requirements.txt 中）
try:
    from pyncm import apis
except ImportError:
    apis = None


async def search_music_official(keyword: str) -> list[dict]:
    """官方API搜索，返回前100首歌曲"""
    if not apis:
        return []
    try:
        result = apis.cloudsearch.GetSearchResult(
            keyword=keyword, stype=apis.cloudsearch.SONG, limit=100
        )
        songs = result.get("result", {}).get("songs", [])
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "artist": " / ".join(ar["name"] for ar in s.get("ar", [])),
                "pop": s.get("pop", 0),
            }
            for s in songs[:100]
        ]
    except Exception:
        return []


async def search_music_autumnfish(keyword: str) -> list[dict]:
    """autumnfish API搜索，返回前100首歌曲"""
    url = f"https://autumnfish.cn/search?keywords={keyword}&limit=100"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            data = resp.json()
            songs = data.get("result", {}).get("songs", [])
            return [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "artist": " / ".join(ar["name"] for ar in s.get("ar", [])),
                    "pop": s.get("pop", 0),
                }
                for s in songs[:100]
            ]
        except Exception:
            return []


async def search_music_imjad(keyword: str) -> list[dict]:
    """imjad API搜索，返回前100首歌曲"""
    url = f"https://api.imjad.cn/cloudmusic/?type=search&search_type=1&s={keyword}&limit=100"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            data = resp.json()
            songs = data.get("result", {}).get("songs", [])
            return [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "artist": " / ".join(ar["name"] for ar in s.get("ar", [])),
                    "pop": s.get("pop", 0),
                }
                for s in songs[:100]
            ]
        except Exception:
            return []


async def get_consensus_songs(keyword: str, sources: list[str]) -> list[dict]:
    """获取共识的歌曲列表，搜索100首，按热度排序，取前10首"""
    tasks = []
    if "official" in sources:
        tasks.append(search_music_official(keyword))
    if "autumnfish" in sources:
        tasks.append(search_music_autumnfish(keyword))
    if "imjad" in sources:
        tasks.append(search_music_imjad(keyword))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_songs = []
    for r in results:
        if isinstance(r, list):
            all_songs.extend(r)

    # 去重并按热度排序，取前10首
    unique_songs = list({s["id"]: s for s in all_songs}.values())
    unique_songs.sort(key=lambda x: x.get("pop", 0), reverse=True)
    return unique_songs[:10]


def _strip_nickname_prefix(message_text: str) -> str:
    nicknames = get_driver().config.nickname or []
    for nick in nicknames:
        if message_text.startswith(nick):
            return message_text[len(nick) :].lstrip(" ，,：:").strip()
    return message_text


def _extract_music_command(bot: Bot, event: Event) -> str:
    message_text = event.get_message().extract_plain_text().strip()
    if not message_text:
        return ""

    if not hasattr(event, "group_id") or not event.group_id:
        return message_text if message_text.startswith("/") else ""

    if event.is_tome():
        return message_text if message_text.startswith("/") else ""

    stripped_text = _strip_nickname_prefix(message_text)
    return stripped_text if stripped_text.startswith("/") else ""


def _music_command_rule(*commands: str):
    def _rule(bot: Bot, event: Event) -> bool:
        command_text = _extract_music_command(bot, event)
        return any(command_text.startswith(command) for command in commands)

    return _rule


def _selection_key(event: MessageEvent) -> str:
    return f"{event.group_id or 'private'}:{event.user_id}"


def _cleanup_expired_selection_cache() -> None:
    now = monotonic()
    expired_keys = [
        key
        for key, (_, cached_at) in selection_cache.items()
        if now - cached_at > CACHE_TTL_SECONDS
    ]
    for key in expired_keys:
        selection_cache.pop(key, None)


def _clear_selection_cache(key: str) -> None:
    selection_cache.pop(key, None)


def _set_selection_cache(key: str, songs: list[dict]) -> None:
    selection_cache[key] = (songs, monotonic())


def _get_selection_cache(key: str) -> list[dict]:
    _cleanup_expired_selection_cache()
    cached = selection_cache.get(key)
    if not cached:
        return []
    songs, _ = cached
    return songs


def _with_mention_reply(event: MessageEvent, content: str | Message) -> Message:
    message = content if isinstance(content, Message) else Message(content)
    if hasattr(event, "group_id") and event.group_id:
        return Message(
            [MessageSegment.at(event.user_id), MessageSegment.text(" "), *message]
        )
    return message


# 命令处理器：点歌
netease_music = on_message(rule=_music_command_rule("/点歌"), priority=5, block=True)


@netease_music.handle()
async def handle_netease_music(bot: Bot, event: MessageEvent):
    _cleanup_expired_selection_cache()
    cache_key = _selection_key(event)
    _clear_selection_cache(cache_key)

    if apis is None:
        await netease_music.finish(
            _with_mention_reply(event, "插件依赖未安装，请安装 pyncm")
        )
        return

    command_text = _extract_music_command(bot, event)
    args = command_text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await netease_music.finish(
            _with_mention_reply(
                event, "请提供歌曲名称，例如：/点歌 夜曲 或 /点歌 夜曲 周杰伦"
            )
        )
        return

    keyword_text = args[1].strip()
    keyword_parts = keyword_text.split()
    song_name = keyword_parts[0]
    artist = " ".join(keyword_parts[1:]) if len(keyword_parts) > 1 else ""

    # 构建搜索关键词
    keyword = song_name if not artist else f"{song_name} {artist}"

    # 多源搜索获取共识歌曲列表
    songs = await get_consensus_songs(keyword, config.api_sources)
    if not songs:
        await netease_music.finish(
            _with_mention_reply(event, "未找到相关歌曲，请检查歌曲名称和歌手。")
        )
        return

    if len(songs) == 1:
        # 只有一首，直接发送
        song_id = songs[0]["id"]
        music_card = f"[CQ:music,type=163,id={song_id}]"
        _clear_selection_cache(cache_key)
        await netease_music.finish(_with_mention_reply(event, Message(music_card)))
    else:
        # 多个结果，让用户选择
        msg = "找到多首歌曲，请使用 /选择 数字 来选择：\n"
        for i, song in enumerate(songs, 1):
            msg += f"{i}. {song['name']} - {song['artist']}\n"
        await netease_music.send(_with_mention_reply(event, msg))

        # 缓存用户选择列表（按群/用户区分）
        _set_selection_cache(cache_key, songs)


# 选择处理器
select_music = on_message(rule=_music_command_rule("/选择"), priority=5, block=True)


@select_music.handle()
async def handle_select_music(bot: Bot, event: MessageEvent):
    _cleanup_expired_selection_cache()
    command_text = _extract_music_command(bot, event)
    args = command_text.split()
    if len(args) < 2:
        await select_music.finish(
            _with_mention_reply(event, "请提供选择数字，例如：/选择 1")
        )
        return

    # 取最后一个数字参数，兼容附带额外空格的情况
    choice_token = args[-1]

    try:
        idx = int(choice_token) - 1
        key = _selection_key(event)
        songs = _get_selection_cache(key)
        if not songs:
            await select_music.finish(
                _with_mention_reply(event, "没有可选择的歌曲，请先点歌")
            )
            return
        if 0 <= idx < len(songs):
            song_id = songs[idx]["id"]
            music_card = f"[CQ:music,type=163,id={song_id}]"
            _clear_selection_cache(key)
            await select_music.finish(_with_mention_reply(event, Message(music_card)))
        else:
            await select_music.finish(
                _with_mention_reply(event, "选择无效，请重新选择")
            )
    except ValueError:
        await select_music.finish(_with_mention_reply(event, "请输入有效的数字"))
