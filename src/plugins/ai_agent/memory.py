from typing import List, Dict, Optional, Deque
from collections import deque
import time

from .config import plugin_config


class ConversationMemory:
    """管理每个会话的对话记忆"""

    def __init__(self, max_length: Optional[int] = None):
        self.max_length = max_length or plugin_config.max_context_length
        self._messages: Dict[str, Deque[Dict[str, any]]] = {}  # 会话ID -> 消息队列
        self._personalities: Dict[str, str] = {}  # 会话ID -> 自定义人格

    def _get_session_queue(self, session_id: str) -> Deque[Dict[str, any]]:
        """获取会话的消息队列，如果不存在则创建"""
        if session_id not in self._messages:
            self._messages[session_id] = deque(
                maxlen=self.max_length * 2
            )  # 每条消息包含用户和AI，所以乘2
        return self._messages[session_id]

    def add_user_message(self, session_id: str, content: str) -> None:
        """添加用户消息"""
        queue = self._get_session_queue(session_id)
        queue.append({"role": "user", "content": content, "timestamp": time.time()})

    def add_assistant_message(self, session_id: str, content: str) -> None:
        """添加助手消息"""
        queue = self._get_session_queue(session_id)
        queue.append(
            {"role": "assistant", "content": content, "timestamp": time.time()}
        )

    def get_recent_messages(
        self, session_id: str, include_system: bool = True
    ) -> List[Dict[str, str]]:
        """获取最近的对话消息，用于API请求"""
        queue = self._get_session_queue(session_id)
        messages = list(queue)
        if include_system:
            system_prompt = self.get_personality(session_id)
            if system_prompt:
                return [{"role": "system", "content": system_prompt}] + messages
        return messages

    def set_personality(self, session_id: str, personality: str) -> None:
        """设置会话的自定义人格"""
        self._personalities[session_id] = personality

    def get_personality(self, session_id: str) -> str:
        """获取会话的人格（如果没有自定义则返回默认人格）"""
        return self._personalities.get(session_id, plugin_config.default_personality)

    def clear(self, session_id: str) -> None:
        """清除指定会话的记忆和人格设置"""
        self._messages.pop(session_id, None)
        self._personalities.pop(session_id, None)

    def get_session_count(self) -> int:
        """获取当前活跃会话数量"""
        return len(self._messages)

    def cleanup_old_sessions(self, max_age: float = 3600) -> int:
        """清理超过指定时间的旧会话（默认1小时）"""
        current_time = time.time()
        removed_count = 0
        for session_id, queue in list(self._messages.items()):
            if queue and (current_time - queue[-1]["timestamp"]) > max_age:
                self.clear(session_id)
                removed_count += 1
        return removed_count


# 全局记忆实例
memory = ConversationMemory()
