"""
SSE (Server-Sent Events) 端点
实时推送评分进度、报告生成进度、分析进度到前端

用法:
  前端: const es = new EventSource('/api/v1/events/stream?task_id=xxx');
        es.onmessage = (e) => console.log(JSON.parse(e.data));
"""
import asyncio
import json
from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import StreamingResponse
from api.deps import get_current_user
from core.event_bus import event_bus
from core.logger import get_logger

logger = get_logger("sse_events")

router = APIRouter()


@router.get("/stream")
async def sse_stream(
    request: Request,
    task_id: str = Query(None, description="订阅特定任务事件"),
    channel: str = Query(None, description="自定义频道名"),
    current_user=Depends(get_current_user)
):
    """
    SSE 推送端点
    - task_id: 订阅特定任务的进度事件
    - channel: 订阅自定义频道
    - 无参数: 订阅全局事件
    """
    # 确定订阅频道
    if task_id:
        sub_channel = f"task:{task_id}"
    elif channel:
        sub_channel = channel
    else:
        sub_channel = "global"

    queue = await event_bus.subscribe(sub_channel)
    username = current_user.username

    async def event_generator():
        try:
            logger.info(f"SSE 连接建立: user={username}, channel={sub_channel}")
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # 心跳保活
                    yield f": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await event_bus.unsubscribe(sub_channel, queue)
            logger.info(f"SSE 连接关闭: user={username}, channel={sub_channel}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 禁用缓冲
        }
    )


@router.get("/stats")
async def sse_stats(current_user=Depends(get_current_user)):
    """SSE 事件总线统计"""
    return event_bus.get_stats()
