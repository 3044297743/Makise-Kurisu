# Picture Send Plugin

这是一个NoneBot2插件，用于定时发送Pixiv上指定tag的高收藏随机图片，或推荐图片。

## 功能

- 从Pixiv搜索指定tag的高收藏图片，或获取推荐图片（当tag为空时）
- 随机选择一张或多张图片发送
- 支持定时发送（每天固定时间或间隔时间）
- 支持发送到群聊或私聊
- 支持手动发送：通过"/色图 <关键词> [数量] [r18]"命令手动获取图片
- 支持代理访问Pixiv API

## 使用方法

### 手动发送图片

在群聊或私聊中发送：
```
/色图 <关键词> [数量] [r18]
```

例如：
- `/色图 original 3` - 发送3张original标签的图片
- `/色图 2` - 发送2张推荐图片（tag为空）
- `/色图 lolicon 1` - 发送1张lolicon标签的图片
- `/色图 初音未来 白丝 2` - 使用完整关键词搜索并发送2张图片
- `/色图 初音未来 白丝` - 使用完整关键词搜索，默认发送1张图片
- `/色图 初音未来 2 r18` - 使用完整关键词搜索，并允许返回R18作品

**注意：**
- 数量限制为1-10张
- 如果只提供数量不提供关键词，则使用推荐图片
- 默认不返回R18作品，可在命令末尾追加 `r18` 开启；追加 `safe` 可强制关闭
- 需要有效的Pixiv refresh_token，否则无法获取图片
- 需要@机器人或使用机器人昵称来唤起

## 配置

在`.env.prod`文件中添加以下配置：

```env
# Pixiv API配置（必需，需要有效的refresh_token）
PICTURE_SEND_PIXIV_REFRESH_TOKEN=your_refresh_token_here
PICTURE_SEND_PIXIV_TAG=  # 搜索的tag，不填写时默认为空，使用推荐图片
PICTURE_SEND_PIXIV_MIN_BOOKMARKS=1000  # 最小收藏数
PICTURE_SEND_PIXIV_MAX_SEARCH_PAGES=5  # 关键词搜索时最多翻页数
PICTURE_SEND_ALLOW_R18=false  # 定时发送默认是否允许R18；手动命令可用 r18/safe 覆盖

# 代理配置（可选，用于访问Pixiv API）
PICTURE_SEND_PROXY_HOST=127.0.0.1  # 代理主机地址
PICTURE_SEND_PROXY_PORT=7890  # 代理端口

# 发送配置
PICTURE_SEND_SEND_TARGETS=["group_123456789", "987654321"]  # 发送目标，group_开头为群聊，否则为用户ID
PICTURE_SEND_SEND_INTERVAL=24:00:00  # 发送间隔，格式HH:MM:SS（如果设置了send_time则忽略）
PICTURE_SEND_SEND_TIME=08:00  # 每天发送时间，格式HH:MM
PICTURE_SEND_SEND_COUNT=1  # 每次发送的图片数量
```

## 故障排除

### API配置错误诊断

如果遇到 `Authentication required` 错误，请按以下步骤排查：

#### 1. 环境变量加载问题
**现象**: 配置正确但仍然提示认证失败
**原因**: NoneBot没有自动加载.env.prod文件
**解决**: 插件已自动加载环境变量，如仍有问题请检查文件路径

#### 2. 网络连接问题
**现象**: 直接连接Pixiv失败，但代理连接成功
**原因**: 网络环境需要代理访问Pixiv
**解决**: 正确配置代理服务器

#### 2. Refresh Token问题
**现象**: 认证失败
**原因**: token过期或无效
**解决**: 重新获取refresh_token

#### 3. API参数问题
**现象**: 认证成功但API调用失败，提示sort参数错误
**原因**: Pixiv API参数格式变更
**解决**: 使用正确的参数格式（如 `sort="date_desc"`）

#### 4. 运行诊断脚本
使用项目根目录下的 `diagnose_pixiv.py` 脚本进行自动诊断：

```bash
# 激活虚拟环境
& .\.venv\Scripts\Activate.ps1

# 运行诊断
python diagnose_pixiv.py
```

#### 常见配置示例
```env
# 代理配置（必需，如果网络需要代理）
PICTURE_SEND_PROXY_HOST=127.0.0.1
PICTURE_SEND_PROXY_PORT=8099

# Token配置（必需）
PICTURE_SEND_PIXIV_REFRESH_TOKEN=your_valid_refresh_token
```

## 安装依赖

项目已添加依赖，运行以下命令安装：

```bash
pip install -e .
```

## 使用

插件会自动启动定时任务，根据配置发送图片。