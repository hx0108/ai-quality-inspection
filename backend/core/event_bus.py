"""
进程内事件总线
asyncio.Queue fan-out 模式，支持 SSE 推送

用法:
  # 发布事件（在 Agent nodes 中）
  await event_bus.publish(f"task:{task_id}", {"type": "scoring_progress", "progress": 30})

  # 订阅事件（在 SSE 端点中）
  queue = event_bus.subscribe(f"task:{task_id}")
  data = await queue.get()
"""
import asyncio
import time
from typing import Dict, Set, Any, Optional
from core.logger import get_logger

logger = get_logger("event_bus")


class EventBus:
    """进程内事件总线 — asyncio.Queue fan-out"""

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._event_count = 0

    async def subscribe(self, channel: str) -> asyncio.Queue:
        """
        订阅频道，返回一个 Queue
        调用方从 queue.get() 读取事件
        """
        queue = asyncio.Queue(maxsize=50)
        async with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = set()
            self._subscribers[channel].add(queue)
        logger.debug(f"SSE 订阅: {channel} (当前订阅者: {len(self._subscribers.get(channel, set()))})")
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue):
        """取消订阅"""
        async with self._lock:
            if channel in self._subscribers:
                self._subscribers[channel].discard(queue)
                if not self._subscribers[channel]:
                    del self._subscribers[channel]
        logger.debug(f"SSE 取消订阅: {channel}")

    async def publish(self, channel: str, data: Dict[str, Any]):
        """
        发布事件到频道的所有订阅者
        """
        self._event_count += 1
        subscribers = self._subscribers.get(channel, set())
        if not subscribers:
            return

        message = {
            **data,
            "_timestamp": time.time(),
            "_seq": self._event_count,
        }

        dead_queues = []
        for q in list(subscribers):  # 复制一份避免遍历中修改
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                # 队列满，丢弃最旧消息后重试
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    q.put_nowait(message)
                except asyncio.QueueFull:
                    dead_queues.append(q)

        # 清理死掉的队列
        if dead_queues:
            async with self._lock:
                for q in dead_queues:
                    if channel in self._subscribers:
                        self._subscribers[channel].discard(q)

    def publish_sync(self, channel: str, data: Dict[str, Any]):
        """
        同步发布（从非 async 上下文调用）
        用于在 threading.Thread 中发布事件
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.publish(channel, data))
            else:
                loop.run_until_complete(self.publish(channel, data))
        except RuntimeError:
            # 没有 event loop，创建一个新的
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.publish(channel, data))
                loop.close()
            except Exception as e:
                logger.debug(f"事件发布失败(无event loop): {e}")

    def get_stats(self) -> Dict:
        """获取事件总线统计"""
        return {
            "channels": len(self._subscribers),
            "total_subscribers": sum(len(s) for s in self._subscribers.values()),
            "total_events_published": self._event_count,
            "channels_detail": {
                ch: len(subs) for ch, subs in self._subscribers.items()
            }
        }


# 全局单例
event_bus = EventBus()
