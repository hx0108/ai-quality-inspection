"""
系统设置模型
运行时可编辑的配置项（API KEY 等）
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
