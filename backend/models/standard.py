"""
自定义检查标准模型
由「检查标准导入」功能生成（支持 Word/Excel 上传解析），与内置标准（diecheng/feidiecheng/lizhi）并列使用
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base


class CustomStandard(Base):
    __tablename__ = "custom_standards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    standard_type = Column(String(50), unique=True, nullable=False, index=True)  # custom_<8位hex>
    label = Column(String(100), nullable=False)                                   # 展示名（如「砺质行动检查标准（8月）」）
    scoring_model = Column(String(20), nullable=False, default="point_cap")       # point_cap | weighted_5pt
    modules_json = Column(Text, nullable=False, default="{}")                     # {模块名: {max_score, role} | {weight}}
    module_count = Column(Integer, nullable=False, default=0)
    items_total = Column(Integer, nullable=False, default=0)
    template_file = Column(String(255), nullable=False)                           # data/templates/ 下的规范化模板
    source_filename = Column(String(255), nullable=True)                          # 用户上传的原始文件名
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, nullable=False, default=1)
