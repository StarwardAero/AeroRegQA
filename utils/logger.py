import sys
from pathlib import Path
from loguru import logger
from config.settings import settings

# 移除默认的 handler
logger.remove()

# 控制台输出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    enqueue=True
)

# 文件输出
log_file = settings.LOGS_DIR / "app.log"
logger.add(
    str(log_file),
    rotation="10 MB",
    retention="10 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    enqueue=True,
    encoding="utf-8"
)

def get_logger(module_name: str):
    """获取带模块名前缀的 logger"""
    return logger.bind(module=module_name)
