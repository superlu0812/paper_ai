"""
路径管理
"""
import os
from typing import Dict


def get_data_root(config: Dict) -> str:
    """
    从配置中获取数据根目录（所有 JSON/PDF/Markdown 等数据文件都保存在该目录下）。
    配置项：paths.data_root，默认 ./data
    """
    paths_cfg = config.get("paths", {})
    data_root = paths_cfg.get("data_root", "./data")
    data_root = os.path.abspath(data_root)
    os.makedirs(data_root, exist_ok=True)
    return data_root


def get_log_dir(config: Dict, data_root: str) -> str:
    """
    获取日志目录，默认在 data_root/logs 下
    可以通过 paths.log_dir 单独配置
    """
    paths_cfg = config.get("paths", {})
    log_dir = paths_cfg.get("log_dir")
    if not log_dir:
        log_dir = os.path.join(data_root, "logs")
    log_dir = os.path.abspath(log_dir)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def get_push_all_dir(config: Dict) -> str:
    """
    获取推送数据保存目录（所有推送数据），默认在 data_root/push/all 下
    可以通过 paths.push_all_dir 单独配置
    """
    paths_cfg = config.get("paths", {})
    push_all_dir = paths_cfg.get("push_all_dir")
    if not push_all_dir:
        data_root = get_data_root(config)
        push_all_dir = os.path.join(data_root, "push", "all")
    push_all_dir = os.path.abspath(push_all_dir)
    os.makedirs(push_all_dir, exist_ok=True)
    return push_all_dir


def get_push_failed_dir(config: Dict) -> str:
    """
    获取推送失败数据保存目录，默认在 data_root/push/failed 下
    可以通过 paths.push_failed_dir 单独配置
    """
    paths_cfg = config.get("paths", {})
    push_failed_dir = paths_cfg.get("push_failed_dir")
    if not push_failed_dir:
        data_root = get_data_root(config)
        push_failed_dir = os.path.join(data_root, "push", "failed")
    push_failed_dir = os.path.abspath(push_failed_dir)
    os.makedirs(push_failed_dir, exist_ok=True)
    return push_failed_dir
