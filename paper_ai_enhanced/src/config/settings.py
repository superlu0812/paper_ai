"""
配置加载和管理
"""
import sys
from typing import Dict, Optional

import yaml


_config: Optional[Dict] = None


def load_config(config_path: str = "config.yaml") -> Dict:
    """
    加载配置文件
    :param config_path: 配置文件路径
    :return: 配置字典
    """
    global _config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            _config = yaml.safe_load(f)
        return _config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        sys.exit(1)


def get_config() -> Dict:
    """
    获取已加载的配置（需要先调用 load_config）
    :return: 配置字典
    """
    if _config is None:
        raise RuntimeError("配置未加载，请先调用 load_config()")
    return _config
