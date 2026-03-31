
# Makise-Kurisu

一个基于 NoneBot2 的多功能 QQ 机器人，支持 AI 聊天、网易云点歌、Pixiv 色图推送等功能。

## 功能插件

### 1. ai_agent 聊天插件
- **功能**：接入外部 AI API，支持上下文记忆和自定义人格。
- **命令**：
	- `@机器人 <消息>` 或使用唤醒词（如“小爱”、“助手”等）直接对话
	- `/清除记忆`（仅超级用户）：清除当前会话记忆
	- `/setpersonality <内容>` 或 `/设置人格 <内容>`：设置当前会话人格

### 2. netease_music 网易云点歌插件
- **功能**：支持网易云多源点歌、歌曲选择。
- **命令**：
	- `@机器人 /点歌 <歌名> [歌手]`：点歌
	- `/选择 <数字>`：选择点歌结果

### 3. picture_send Pixiv色图插件
- **功能**：定时或手动发送Pixiv高收藏图片，支持关键词、数量、r18参数。
- **命令**：
	- `@机器人 /色图 <关键词> [数量] [r18]`：获取Pixiv高收藏图片

### 4. help 帮助插件
- **功能**：发送“@机器人 /help”时，回复所有命令及用法（激活后不激活其他插件）
- **命令**：
	- `@机器人 /help`：查看所有命令及用法

---

## 安装与启动
1. 克隆本项目并进入目录
2. 创建虚拟环境并安装依赖：
	 ```bash
	 python -m venv .venv
	 .venv\Scripts\activate  # Windows
	 pip install -r requirements.txt
	 ```
3. 配置 `.env.prod`、`pyproject.toml` 及各插件配置文件
4. 启动机器人：
	 ```bash
	 nb run
	 ```

## .env.prod 配置教学（完整）

本项目通过根目录下的 `.env.prod` 进行运行配置。建议先复制模板，再按你的环境逐项修改。

### 1. 可直接使用的模板

```env
# ========== NoneBot / OneBot 基础配置 ==========
DRIVER=~fastapi+~httpx+~websockets
ONEBOT_ACCESS_TOKEN=请替换为你的OneBot access token
HOST=0.0.0.0
PORT=8080
SUPERUSERS=["123456789"]
NICKNAME=["克里斯蒂娜","助手","克里斯","Cristina"]

# ========== ai_agent 插件 ==========
AI_TIMEOUT=30

# 当前项目里常用键（建议保留）
API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY="请替换为你的AI密钥"
MODEL="qwen-plus"

# ai_agent config.py 实际读取键（建议与上方保持一致）
API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY="请替换为你的AI密钥"
MODEL="qwen-plus"

MAX_TOKENS=1000
TEMPERATURE=0.7
MAX_CONTEXT_LENGTH=10
REQUIRE_AT=false
WAKE_WORDS=小爱,助手,克里斯蒂娜,克里斯,Cristina
DEFAULT_PERSONALITY="你是一个乐于助人的AI助手。"

# ========== picture_send 插件 ==========
PICTURE_SEND_PIXIV_REFRESH_TOKEN=请替换为你的pixiv refresh token
PICTURE_SEND_PIXIV_TAG=original
PICTURE_SEND_PIXIV_MIN_BOOKMARKS=500
PICTURE_SEND_PIXIV_MAX_SEARCH_PAGES=20
PICTURE_SEND_ALLOW_R18=false

# 代理可选（不需要代理可留空/设为0）
PICTURE_SEND_PROXY_HOST=127.0.0.1
PICTURE_SEND_PROXY_PORT=8099

# 定时推送目标：群聊用 group_群号，私聊用 QQ号字符串
PICTURE_SEND_SEND_TARGETS=["group_123456789","123456789"]

# 二选一：推荐设置固定时间；若为空则走间隔模式
PICTURE_SEND_SEND_TIME=08:00
PICTURE_SEND_SEND_INTERVAL=24:00:00
PICTURE_SEND_SEND_COUNT=1
```

### 2. 字段说明（按现有插件）

- `DRIVER`：NoneBot 驱动组合，默认即可。
- `ONEBOT_ACCESS_TOKEN`：与 OneBot 实现端保持一致。
- `HOST` / `PORT`：机器人监听地址与端口。
- `SUPERUSERS`：超级用户列表（JSON 数组字符串），用于高权限命令与功能。
- `NICKNAME`：机器人昵称列表，群聊昵称唤醒会用到。

- `AI_TIMEOUT`：AI 请求超时秒数。
- `API_BASE` / `API_KEY` / `MODEL`：AI 服务基础配置（建议与 `AI_BASE_URL` / `AI_API_KEY` / `AI_MODEL` 同步）。
- `MAX_TOKENS` / `TEMPERATURE`：模型生成参数。
- `MAX_CONTEXT_LENGTH`：会话上下文保留长度。
- `REQUIRE_AT`：群聊是否必须 @ 机器人才触发 AI。
- `WAKE_WORDS`：昵称唤醒词，逗号分隔。
- `DEFAULT_PERSONALITY`：默认人格提示词。

- `PICTURE_SEND_PIXIV_REFRESH_TOKEN`：Pixiv 刷新令牌。
- `PICTURE_SEND_PIXIV_TAG`：手动/定时搜图关键词。
- `PICTURE_SEND_PIXIV_MIN_BOOKMARKS`：最低收藏数过滤。
- `PICTURE_SEND_PIXIV_MAX_SEARCH_PAGES`：最大搜索页数。
- `PICTURE_SEND_ALLOW_R18`：全局是否允许 r18（当前代码中，手动 r18 参数仅超级用户可用）。
- `PICTURE_SEND_PROXY_HOST` / `PICTURE_SEND_PROXY_PORT`：网络代理。
- `PICTURE_SEND_SEND_TARGETS`：定时推送目标列表。
- `PICTURE_SEND_SEND_TIME`：每日固定发送时间（`HH:MM`）。
- `PICTURE_SEND_SEND_INTERVAL`：间隔发送（`HH:MM:SS`），当未设置固定时间时生效。
- `PICTURE_SEND_SEND_COUNT`：每次发送数量。

### 3. 常见坑位

- `SUPERUSERS`、`NICKNAME`、`PICTURE_SEND_SEND_TARGETS` 必须使用 JSON 风格字符串。
- 不要在 `.env.prod` 里使用 Python 语法（例如 `SUPERUSERS = {3044297743}` 这种写法无效）。
- 含空格或特殊字符的值建议加引号。
- 修改 `.env.prod` 后建议重启机器人。

## 插件开发
所有插件位于 `src/plugins/` 目录下，参考已有插件结构进行开发。

## 相关链接
- [NoneBot2 官方文档](https://nonebot.dev/)

---
如需详细配置与高级用法，请参考各插件 README 或源码注释。
