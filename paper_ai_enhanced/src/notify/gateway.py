"""
网关推送模块
将论文数据推送到指定网关
"""
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from ..config.paths import get_push_all_dir, get_push_failed_dir
from ..config.settings import load_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def convert_paper_json_to_payload(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将论文JSON数据转换为推送格式

    Args:
        paper_data: 论文JSON数据，包含title, authors, summary等字段

    Returns:
        转换后的推送数据格式：
        {
            "title": "论文标题",
            "author": "作者",
            "content": "正文",
            "en_content": "content",
            "digest": "摘要",
            "time": "2025-01-01 00:00:00",
            "url": "论文链接"
        }
    """
    # 提取标题
    title = paper_data.get("title", "")

    # 提取作者（将列表转换为字符串）
    authors = paper_data.get("authors", [])
    if isinstance(authors, list):
        author = ", ".join(authors[:5])  # 最多取前5个作者
        if len(authors) > 5:
            author += f" et al. (total {len(authors)} authors)"
    else:
        author = str(authors) if authors else ""

    # 提取正文（优先使用content，其次使用llm_summary，最后使用summary）
    content = (
        paper_data.get("content", "")
        or paper_data.get("llm_summary", "")
        or paper_data.get("refined_summary", "")
        or paper_data.get("translated_summary", "")
        or paper_data.get("summary", "")
    )

    # 提取摘要（优先使用refined_summary，其次使用translated_summary，最后使用summary）
    digest = (
        paper_data.get("refined_summary", "")
        or paper_data.get("translated_summary", "")
        or paper_data.get("summary", "")
    )

    # 提取时间（格式化published字段）
    published = paper_data.get("published", "")
    if published:
        # 如果已经是格式化的时间字符串，直接使用；否则尝试转换
        time_str = published
    else:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 提取URL（优先使用pdf_url，其次使用entry_id）
    url =  paper_data.get("aipaper_url", "") or paper_data.get("pdf_url", "") or paper_data.get("entry_id", "")

    return {
        "title": title,
        "author": author,
        "content": content,
        "en_content": content,
        "digest": digest,
        "time": time_str,
        "url": url,
    }


def build_push_payload(payload_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    构建完整的推送报文

    Args:
        payload_data: 转换后的论文数据

    Returns:
        完整的推送报文格式：
        {
            "source_system": "external",
            "control": {
                "event_type": "news",
                "recommend_inner": true
            },
            "payload": {
                "title": "...",
                "author": "...",
                ...
            }
        }
    """
    return {
        "source_system": "external",
        "control": {
            "event_type": "news",
            "recommend_inner": True,
        },
        "payload": payload_data,
    }


def push_paper_to_gateway(
    config: Dict[str, Any], paper_data: Dict[str, Any], timestamp: Optional[str] = None
) -> bool:
    """
    推送单篇论文到网关

    Args:
        config: 配置字典
        paper_data: 论文JSON数据
        timestamp: 可选的时间戳，用于目录命名。如果为None，则使用当前时间生成

    Returns:
        是否推送成功
    """
    gateway_cfg = config.get("gateway", {})
    if not gateway_cfg.get("enabled", False):
        logger.info("网关推送未启用（gateway.enabled=false），跳过推送")
        return False

    gateway_url = gateway_cfg.get("url", "")
    if not gateway_url:
        logger.warning("网关推送未执行：网关地址未配置")
        return False

    # 转换数据格式
    try:
        payload_data = convert_paper_json_to_payload(paper_data)
        push_data = build_push_payload(payload_data)
    except Exception as e:
        logger.error(f"数据格式转换失败: {e}")
        return False

    # 获取时间戳用于目录命名
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d")
    title_safe = "".join(c for c in payload_data.get("title", "unknown")[:50] if c.isalnum() or c in (" ", "-", "_")).strip()
    if not title_safe:
        title_safe = "unknown"

    # 获取保存目录
    push_all_dir = get_push_all_dir(config)
    push_failed_dir = get_push_failed_dir(config)

    # 创建时间戳目录
    timestamp_dir_all = os.path.join(push_all_dir, timestamp)
    timestamp_dir_failed = os.path.join(push_failed_dir, timestamp)
    os.makedirs(timestamp_dir_all, exist_ok=True)
    os.makedirs(timestamp_dir_failed, exist_ok=True)

    # 保存推送数据到all目录
    filename = f"{title_safe}.json"
    filepath_all = os.path.join(timestamp_dir_all, filename)
    try:
        with open(filepath_all, "w", encoding="utf-8") as f:
            json.dump(push_data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存推送数据到: {filepath_all}")
    except Exception as e:
        logger.error(f"保存推送数据失败: {e}")

    # 执行推送
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            gateway_url, json=push_data, headers=headers, timeout=30
        )

        if response.status_code == 200 or response.status_code == 202:
            logger.info(f"论文推送成功: {payload_data.get('title', 'Unknown')}")
            return True
        else:
            logger.error(
                f"论文推送失败，状态码: {response.status_code}, "
                f"响应: {response.text[:200]}"
            )
            # 保存失败数据
            filepath_failed = os.path.join(timestamp_dir_failed, filename)
            try:
                with open(filepath_failed, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "push_data": push_data,
                            "error": {
                                "status_code": response.status_code,
                                "response": response.text[:500],
                            },
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
                logger.info(f"已保存失败数据到: {filepath_failed}")
            except Exception as e:
                logger.error(f"保存失败数据失败: {e}")
            return False

    except Exception as e:
        logger.error(f"论文推送异常: {e}")
        # 保存失败数据
        filepath_failed = os.path.join(timestamp_dir_failed, filename)
        try:
            with open(filepath_failed, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "push_data": push_data,
                        "error": {"exception": str(e)},
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            logger.info(f"已保存失败数据到: {filepath_failed}")
        except Exception as save_error:
            logger.error(f"保存失败数据失败: {save_error}")
        return False


def push_papers_via_gateway(
    config: Dict[str, Any], papers: list[Dict[str, Any]]
) -> None:
    """
    批量推送论文列表到网关

    Args:
        config: 配置字典
        papers: 论文列表
    """
    gateway_cfg = config.get("gateway", {})
    if not gateway_cfg.get("enabled", False):
        logger.info("网关推送未启用（gateway.enabled=false），跳过推送")
        return

    if not papers:
        logger.info("没有论文需要推送")
        return

    logger.info(f"开始通过网关推送论文，共 {len(papers)} 篇...")

    # 批量推送使用统一的时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    success_count = 0
    failed_count = 0

    for idx, paper in enumerate(papers, 1):
        logger.info(f"正在推送第 {idx}/{len(papers)} 篇论文...")
        if push_paper_to_gateway(config, paper, timestamp):
            success_count += 1
        else:
            failed_count += 1

    logger.info(
        f"网关推送完成，成功 {success_count} / {len(papers)} 篇，"
        f"失败 {failed_count} 篇"
    )


def push_paper_from_json_file(
    config: Dict[str, Any], json_file_path: str
) -> bool:
    """
    从JSON文件读取论文数据并推送到网关

    Args:
        config: 配置字典
        json_file_path: JSON文件路径

    Returns:
        是否推送成功
    """
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            paper_data = json.load(f)
        logger.info(f"已读取JSON文件: {json_file_path}")
        return push_paper_to_gateway(config, paper_data)
    except Exception as e:
        logger.error(f"读取JSON文件失败: {e}")
        return False


def main():
    """
    主函数：支持从命令行参数读取JSON文件路径并重复推送
    用法: python -m src.notify.gateway <json_file_path> [--config <config_path>]
    """
    parser = argparse.ArgumentParser(
        description="推送历史论文JSON文件到网关",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m src.notify.gateway data/2025-01-15/json/paper_title.json
  python -m src.notify.gateway data/push/failed/20250115/paper_title.json --config config.yaml
        """,
    )
    parser.add_argument(
        "json_file",
        type=str,
        help="要推送的论文JSON文件路径",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="配置文件路径（默认: config.yaml）",
    )

    args = parser.parse_args()

    # 检查文件是否存在
    json_file_path = args.json_file
    if not os.path.exists(json_file_path):
        logger.error(f"文件不存在: {json_file_path}")
        sys.exit(1)

    if not os.path.isfile(json_file_path):
        logger.error(f"路径不是文件: {json_file_path}")
        sys.exit(1)

    # 加载配置
    try:
        config = load_config(args.config)
        logger.info(f"已加载配置文件: {args.config}")
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        sys.exit(1)

    # 检查网关配置
    gateway_cfg = config.get("gateway", {})
    if not gateway_cfg.get("enabled", False):
        logger.warning("网关推送未启用（gateway.enabled=false）")
        response = input("是否继续推送? (y/n): ")
        if response.lower() != "y":
            logger.info("用户取消推送")
            sys.exit(0)

    # 执行推送
    logger.info(f"开始推送论文JSON文件: {json_file_path}")
    success = push_paper_from_json_file(config, json_file_path)

    if success:
        logger.info("推送成功！")
        sys.exit(0)
    else:
        logger.error("推送失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
