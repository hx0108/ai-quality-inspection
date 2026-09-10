"""
配置管理模块
从 .env 文件读取配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "物业品质检查系统"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'data' / 'inspection.db'}"
    )

    # JWT 配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # CORS 配置（支持多域名，用逗号分隔）
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

    # LLM API 配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # LLM 降级模型（主模型熔断时自动切换，留空则不降级）
    QWEN_FALLBACK_MODEL: str = os.getenv("QWEN_FALLBACK_MODEL", "qwen-turbo")
    DEEPSEEK_FALLBACK_MODEL: str = os.getenv("DEEPSEEK_FALLBACK_MODEL", "deepseek-chat")

    # Human-in-the-Loop 审核门控（默认关闭，开启后低置信度评分需人工审核才继续生成报告）
    ENABLE_HUMAN_REVIEW_GATE: bool = os.getenv("ENABLE_HUMAN_REVIEW_GATE", "false").lower() == "true"
    HUMAN_REVIEW_CONFIDENCE_THRESHOLD: float = float(os.getenv("HUMAN_REVIEW_CONFIDENCE_THRESHOLD", "0.8"))

    # 文件上传安全配置
    MAX_PHOTO_SIZE: int = int(os.getenv("MAX_PHOTO_SIZE", str(10 * 1024 * 1024)))  # 默认10MB

    # 文件存储路径
    DATA_DIR: Path = BASE_DIR / "data"
    PHOTOS_DIR: Path = DATA_DIR / "photos"
    REPORTS_DIR: Path = DATA_DIR / "reports"
    TEMPLATES_DIR: Path = DATA_DIR / "templates"
    ANALYSIS_DIR: Path = DATA_DIR / "analysis"
    MODULE_WEIGHTS: dict = {
        "客户服务": 0.15,
        "安全管理": 0.15,
        "EHS及风险管理": 0.10,
        "环境管理": 0.15,
        "机电运维": 0.15,
        "设施维护": 0.15,
        "综合管理": 0.10,
        "财务管理": 0.05,
    }

    # ==================== 多标准注册表 ====================
    # 按检查标准(standard_type)组织模块清单与计分模型。
    # - weighted_5pt: 0-5分 × 权重 → 百分制加权平均 = 100（蝶城/非蝶城）
    # - point_cap:    各项按自身分值打分，计分模块封顶 max_score，扣分模块只减分（砺质）
    # MODULE_WEIGHTS 保留为蝶城默认权重的向后兼容别名。
    STANDARDS: dict = {
        "diecheng": {
            "label": "蝶城版",
            "scoring_model": "weighted_5pt",
            "modules": {
                "客户服务": {"weight": 0.15},
                "安全管理": {"weight": 0.15},
                "EHS及风险管理": {"weight": 0.10},
                "环境管理": {"weight": 0.15},
                "机电运维": {"weight": 0.15},
                "设施维护": {"weight": 0.15},
                "综合管理": {"weight": 0.10},
                "财务管理": {"weight": 0.05},
            },
        },
        "feidiecheng": {
            "label": "非蝶城版",
            "scoring_model": "weighted_5pt",
            "modules": {
                "客户服务": {"weight": 0.15},
                "安全管理": {"weight": 0.15},
                "EHS及风险管理": {"weight": 0.10},
                "环境管理": {"weight": 0.15},
                "机电运维": {"weight": 0.15},
                "设施维护": {"weight": 0.15},
                "综合管理": {"weight": 0.10},
                "财务管理": {"weight": 0.05},
            },
        },
        "lizhi": {
            "label": "砺质版",
            "scoring_model": "point_cap",
            "modules": {
                "管家礼韵塑新颜": {"max_score": 25, "role": "score"},
                "安防礼韵塑新颜": {"max_score": 25, "role": "score"},
                "环境礼韵塑新颜": {"max_score": 25, "role": "score"},
                "技术礼韵塑新颜": {"max_score": 25, "role": "score"},
                "其他场所5S": {"max_score": 0, "role": "deduction"},
            },
        },
    }

    def __init__(self):
        # 确保目录存在
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()
