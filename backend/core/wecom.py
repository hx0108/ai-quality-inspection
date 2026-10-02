"""
企业微信群机器人推送
通过群机器人 Webhook 将质检摘要推送到企业微信群。
未配置 WECOM_WEBHOOK_URL 时静默跳过；推送失败仅记日志，不影响主流程。
限频：每个机器人 20 条/分钟。
"""
import httpx

from config import settings
from core.logger import get_logger

logger = get_logger("wecom")


def send_wecom_markdown(content: str) -> bool:
    """推送 markdown 消息到企业微信群机器人，成功返回 True"""
    webhook_url = settings.WECOM_WEBHOOK_URL
    if not webhook_url:
        return False
    try:
        resp = httpx.post(
            webhook_url,
            json={"msgtype": "markdown", "markdown": {"content": content}},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode") != 0:
            logger.warning(f"[企业微信] 推送被拒绝: {data}")
            return False
        return True
    except Exception as e:
        logger.warning(f"[企业微信] 推送失败: {e}")
        return False
