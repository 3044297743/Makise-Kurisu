from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="Awesome Chat",
    description="接入外部AI API的聊天插件，支持上下文记忆和自定义人格",
    usage="@机器人 发送消息即可对话，或使用小爱、助手等唤醒词",
    type="application",
    homepage="https://github.com/your/repo",
    supported_adapters=None,
)

# 导入处理器模块以注册 matcher。
from . import chat as chat
