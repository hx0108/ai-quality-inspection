"""
Prompt 模板管理器
支持版本化、热加载、在线编辑
从数据库读取最新版本，DB无记录时使用代码中的默认值
"""
import json
from datetime import datetime
from typing import Optional, Dict, List
from database import SessionLocal
from core.logger import get_logger

logger = get_logger("prompt_manager")


class PromptManager:
    """Prompt模板管理器 — 支持版本化和热加载"""

    def __init__(self):
        self._cache: Dict[str, dict] = {}  # prompt_key → {template, version, updated_at}
        self._cache_loaded = False

    def _ensure_cache(self):
        """懒加载缓存"""
        if self._cache_loaded:
            return
        self.reload_cache()

    def reload_cache(self):
        """从数据库重新加载所有活跃Prompt到缓存"""
        try:
            from models.models import PromptTemplate
            db = SessionLocal()
            try:
                templates = db.query(PromptTemplate).filter(
                    PromptTemplate.is_active == True
                ).all()
                self._cache = {}
                for t in templates:
                    self._cache[t.prompt_key] = {
                        "template": t.template,
                        "version": t.version,
                        "description": t.description or "",
                        "updated_at": t.updated_at.isoformat() if t.updated_at else "",
                    }
                self._cache_loaded = True
                logger.info(f"Prompt缓存已加载: {len(self._cache)} 个模板")
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"Prompt缓存加载失败（可能表尚未创建）: {e}")
            self._cache_loaded = True  # 避免反复尝试

    def get_prompt(self, key: str, default: str = "") -> str:
        """
        获取最新版本的Prompt
        优先从DB缓存读取，未命中时使用default

        Args:
            key: Prompt键名（如 'scoring_module', 'report_generate'）
            default: 默认Prompt文本（代码中的硬编码值）

        Returns:
            Prompt模板字符串
        """
        self._ensure_cache()
        if key in self._cache:
            return self._cache[key]["template"]
        return default

    def update_prompt(self, key: str, template: str, description: str = "",
                      updated_by: int = None) -> dict:
        """
        更新Prompt（创建新版本）

        Args:
            key: Prompt键名
            template: 新的Prompt文本
            description: 变更说明
            updated_by: 操作人ID

        Returns:
            更新结果
        """
        from models.models import PromptTemplate
        db = SessionLocal()
        try:
            existing = db.query(PromptTemplate).filter(
                PromptTemplate.prompt_key == key
            ).first()

            if existing:
                existing.version += 1
                existing.template = template
                existing.description = description or existing.description
                existing.updated_by = updated_by
                existing.updated_at = datetime.utcnow()
                db.commit()
                # 更新缓存
                self._cache[key] = {
                    "template": template,
                    "version": existing.version,
                    "description": description or existing.description or "",
                    "updated_at": existing.updated_at.isoformat(),
                }
                return {"key": key, "version": existing.version, "status": "updated"}
            else:
                new_t = PromptTemplate(
                    prompt_key=key,
                    version=1,
                    template=template,
                    description=description,
                    is_active=True,
                    updated_by=updated_by,
                )
                db.add(new_t)
                db.commit()
                self._cache[key] = {
                    "template": template,
                    "version": 1,
                    "description": description or "",
                    "updated_at": datetime.utcnow().isoformat(),
                }
                return {"key": key, "version": 1, "status": "created"}
        finally:
            db.close()

    def list_prompts(self) -> List[dict]:
        """列出所有Prompt及其版本信息"""
        self._ensure_cache()
        results = []
        for key, info in self._cache.items():
            results.append({
                "prompt_key": key,
                "version": info["version"],
                "description": info["description"],
                "updated_at": info["updated_at"],
                "template_preview": info["template"][:200] + "..." if len(info["template"]) > 200 else info["template"],
            })
        return results

    def get_prompt_detail(self, key: str) -> Optional[dict]:
        """获取Prompt完整详情"""
        self._ensure_cache()
        if key in self._cache:
            return {
                "prompt_key": key,
                **self._cache[key],
            }
        return None

    def deactivate_prompt(self, key: str) -> bool:
        """停用Prompt（回退到代码默认值）"""
        from models.models import PromptTemplate
        db = SessionLocal()
        try:
            t = db.query(PromptTemplate).filter(
                PromptTemplate.prompt_key == key
            ).first()
            if t:
                t.is_active = False
                db.commit()
                self._cache.pop(key, None)
                return True
            return False
        finally:
            db.close()


# 全局单例
prompt_manager = PromptManager()
