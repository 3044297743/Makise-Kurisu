"""
独立的配置模块，不依赖NoneBot
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field


class Config(BaseModel):
    """Plugin Config Here"""

    model_config = ConfigDict(populate_by_name=True)

    pixiv_refresh_token: str = Field(
        default="", alias="PICTURE_SEND_PIXIV_REFRESH_TOKEN"
    )
    pixiv_tag: str = Field(
        default="", alias="PICTURE_SEND_PIXIV_TAG"
    )  # 搜索的tag，不填写时默认为空
    pixiv_min_bookmarks: int = Field(
        default=1000, alias="PICTURE_SEND_PIXIV_MIN_BOOKMARKS"
    )
    pixiv_max_search_pages: int = Field(
        default=5, alias="PICTURE_SEND_PIXIV_MAX_SEARCH_PAGES"
    )
    allow_r18: bool = Field(default=False, alias="PICTURE_SEND_ALLOW_R18")
    send_targets: list[str] = Field(
        default_factory=list, alias="PICTURE_SEND_SEND_TARGETS"
    )  # 群聊ID或用户ID列表
    send_interval: str = Field(
        default="24:00:00", alias="PICTURE_SEND_SEND_INTERVAL"
    )  # 发送间隔，格式HH:MM:SS
    send_time: str = Field(
        default="08:00", alias="PICTURE_SEND_SEND_TIME"
    )  # 每天发送时间，格式HH:MM，如果设置了interval则忽略
    send_count: int = Field(
        default=1, alias="PICTURE_SEND_SEND_COUNT"
    )  # 每次发送的图片数量
    proxy_host: str = Field(
        default="", alias="PICTURE_SEND_PROXY_HOST"
    )  # 代理主机地址，不填写则不使用代理
    proxy_port: int = Field(
        default=0, alias="PICTURE_SEND_PROXY_PORT"
    )  # 代理端口，不填写则不使用代理


def load_config() -> Config:
    """加载配置"""
    # 加载环境变量
    env_file = Path(__file__).parent.parent.parent.parent / ".env.prod"
    load_dotenv(env_file)

    # 直接从环境变量创建配置对象
    return Config(
        pixiv_refresh_token=os.getenv("PICTURE_SEND_PIXIV_REFRESH_TOKEN", ""),
        pixiv_tag=os.getenv("PICTURE_SEND_PIXIV_TAG", ""),
        pixiv_min_bookmarks=int(os.getenv("PICTURE_SEND_PIXIV_MIN_BOOKMARKS", "1000")),
        pixiv_max_search_pages=int(
            os.getenv("PICTURE_SEND_PIXIV_MAX_SEARCH_PAGES", "5")
        ),
        allow_r18=os.getenv("PICTURE_SEND_ALLOW_R18", "false").lower() == "true",
        send_targets=eval(os.getenv("PICTURE_SEND_SEND_TARGETS", "[]")),
        send_interval=os.getenv("PICTURE_SEND_SEND_INTERVAL", "24:00:00"),
        send_time=os.getenv("PICTURE_SEND_SEND_TIME", "08:00"),
        send_count=int(os.getenv("PICTURE_SEND_SEND_COUNT", "1")),
        proxy_host=os.getenv("PICTURE_SEND_PROXY_HOST", ""),
        proxy_port=int(os.getenv("PICTURE_SEND_PROXY_PORT", "0")),
    )
