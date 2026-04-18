"""
统一日志配置模块
所有模块使用: from core.logger import logger; logger.info("message")
"""
import logging
import sys

def setup_logging():
    """配置全局日志格式和级别"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

# 初始化时调用一次
setup_logging()

def get_logger(name: str) -> logging.Logger:
    """获取指定名称的logger"""
    return logging.getLogger(name)
