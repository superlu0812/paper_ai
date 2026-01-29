"""
日志工具
"""
import logging
import os
from typing import Optional

_LOGGING_CONFIGURED = False


def setup_logging(data_root: str, filename: str = "app.log", level: int = logging.INFO) -> None:
    """
    初始化日志系统，将日志写入 data_root/logs 下的文件。
    只应在程序启动时调用一次。
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    log_dir = os.path.join(data_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, filename)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )

    _LOGGING_CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取一个 logger 实例。
    在调用前需要通过 setup_logging 配置好全局日志。
    """
    return logging.getLogger(name)
