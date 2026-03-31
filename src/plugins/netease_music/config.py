from typing import List

from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""

    # 是否在群聊中需要@机器人（如果为False，则支持昵称唤醒）
    require_at: bool = False

    # 唤醒词列表（仅在 require_at=False 时生效）
    wake_words: List[str] = ["点歌"]

    # 网易云音乐API来源列表
    api_sources: List[str] = [
        "official",  # pyncm官方API
        "autumnfish",  # https://autumnfish.cn/
        "imjad",  # https://api.imjad.cn/
    ]
