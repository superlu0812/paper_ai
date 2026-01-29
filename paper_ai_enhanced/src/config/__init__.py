"""
配置管理模块
"""
from .settings import load_config, get_config
from .paths import get_data_root, get_log_dir

__all__ = ['load_config', 'get_config', 'get_data_root', 'get_log_dir']
