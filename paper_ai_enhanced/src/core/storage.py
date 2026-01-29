"""
论文数据存储模块
"""
import json
import os
import re
from typing import Dict, List, Optional
from urllib.parse import quote

from ..utils.logging import get_logger

logger = get_logger(__name__)


def _build_paper_json_path(paper: Dict, data_root: str) -> str:
    """
    根据论文信息构造 JSON 文件路径，位于 data_root 下的 日期/json 目录中
    """
    published = paper.get('published', '')
    if published:
        date_str = published.split(' ')[0]
    else:
        date_str = 'unknown'

    date_dir = os.path.join(data_root, date_str)
    json_dir = os.path.join(date_dir, 'json')

    title = paper.get('title', 'untitled')
    safe_title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
    safe_title = safe_title[:100]

    filename = f"{safe_title}.json"
    return os.path.join(json_dir, filename)


def _get_paper_id(paper: Dict) -> str:
    """
    生成论文ID，与前端逻辑保持一致
    前端逻辑：
    function getPaperId(paper) {
      const dateStr = paper.published ? paper.published.split(' ')[0] : 'unknown'
      const title = paper.title || 'untitled'
      const safeTitle = title.replace(/[^a-zA-Z0-9\s\-_]/g, '_').substring(0, 100)
      return `${dateStr}_${safeTitle}`
    }
    
    :param paper: 论文信息字典
    :return: 论文ID字符串
    """
    # 获取日期字符串
    published = paper.get('published', '')
    if published:
        date_str = published.split(' ')[0]
    else:
        date_str = 'unknown'
    
    # 获取标题并处理
    title = paper.get('title', 'untitled')
    # 替换非字母数字、空格、连字符、下划线之外的字符为下划线
    safe_title = re.sub(r'[^a-zA-Z0-9\s\-_]', '_', title)
    # 限制长度为100
    safe_title = safe_title[:100]
    
    return f"{date_str}_{safe_title}"


def generate_aipaper_url(paper: Dict, config: Dict) -> Optional[str]:
    """
    生成 AI Paper URL
    
    :param paper: 论文信息字典
    :param config: 配置字典
    :return: AI Paper URL，如果未启用则返回 None
    """
    aipaper_config = config.get('aipaper_url', {})
    
    # 检查是否启用
    if not aipaper_config.get('enabled', False):
        return None
    
    # 获取基础URL
    base_url = aipaper_config.get('base_url', '').rstrip('/')
    if not base_url:
        return None
    
    # 生成 paperId
    paper_id = _get_paper_id(paper)
    
    # URL编码 paperId（处理空格等特殊字符）
    encoded_paper_id = quote(paper_id, safe='')
    
    # 构建完整URL
    return f"{base_url}/{encoded_paper_id}"


class PaperStorage:
    """论文存储管理类"""

    def __init__(self, data_root: str, config: Optional[Dict] = None):
        """
        初始化存储管理器
        :param data_root: 数据根目录
        :param config: 配置字典（可选，用于生成 aipaper_url）
        """
        self.data_root = data_root
        self.config = config

    def is_paper_saved(self, paper: Dict) -> bool:
        """
        判断论文是否已经保存
        :param paper: 论文信息字典
        :return: True表示已存在对应JSON文件
        """
        filepath = _build_paper_json_path(paper, self.data_root)
        return os.path.exists(filepath)

    def save_papers(self, papers: List[Dict]) -> int:
        """
        保存论文列表到JSON文件
        :param papers: 论文列表
        :return: 保存的论文数量
        """
        saved_count = 0
        for paper in papers:
            filepath = _build_paper_json_path(paper, self.data_root)
            json_dir = os.path.dirname(filepath)
            os.makedirs(json_dir, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper, f, ensure_ascii=False, indent=2)

            saved_count += 1
            logger.info(f"已保存论文JSON到: {filepath}")

        logger.info(f"已保存 {saved_count} 篇论文的JSON文件")
        return saved_count

    def update_paper_summary(self, paper: Dict, llm_summary: str) -> bool:
        """
        更新论文JSON文件，添加llm_summary字段
        :param paper: 论文信息字典
        :param llm_summary: LLM生成的总结内容
        :return: 是否更新成功
        """
        try:
            filepath = _build_paper_json_path(paper, self.data_root)

            if not os.path.exists(filepath):
                logger.warning(f"JSON文件不存在，无法更新: {filepath}")
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                paper_data = json.load(f)

            paper_data['llm_summary'] = llm_summary

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper_data, f, ensure_ascii=False, indent=2)

            logger.info(f"已更新论文JSON，添加llm_summary字段: {filepath}")
            return True
        except Exception as e:
            logger.error(f"更新JSON文件失败: {e}")
            return False

    def update_paper_content(self, paper: Dict, content: str) -> bool:
        """
        更新论文JSON文件，添加或更新content字段（PDF提取的文字内容）
        :param paper: 论文信息字典
        :param content: PDF提取的完整文字内容
        :return: 是否更新成功
        """
        try:
            filepath = _build_paper_json_path(paper, self.data_root)

            if not os.path.exists(filepath):
                logger.warning(f"JSON文件不存在，无法更新content字段: {filepath}")
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                paper_data = json.load(f)

            paper_data['content'] = content

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper_data, f, ensure_ascii=False, indent=2)

            logger.info(f"已更新论文JSON，添加/更新content字段: {filepath}")
            return True
        except Exception as e:
            logger.error(f"更新JSON文件content字段失败: {e}")
            return False

    def update_paper_translated_summary(self, paper: Dict, translated_summary: str) -> bool:
        """
        更新论文JSON文件，添加或更新translated_summary字段（翻译后的摘要）
        :param paper: 论文信息字典
        :param translated_summary: 翻译后的摘要内容
        :return: 是否更新成功
        """
        try:
            filepath = _build_paper_json_path(paper, self.data_root)

            if not os.path.exists(filepath):
                logger.warning(f"JSON文件不存在，无法更新translated_summary字段: {filepath}")
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                paper_data = json.load(f)

            paper_data['translated_summary'] = translated_summary

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper_data, f, ensure_ascii=False, indent=2)

            logger.info(f"已更新论文JSON，添加/更新translated_summary字段: {filepath}")
            return True
        except Exception as e:
            logger.error(f"更新JSON文件translated_summary字段失败: {e}")
            return False

    def update_paper_refined_summary(self, paper: Dict, refined_summary: str) -> bool:
        """
        更新论文JSON文件，添加或更新refined_summary字段（精炼后的AI总结）
        :param paper: 论文信息字典
        :param refined_summary: 精炼后的AI总结内容
        :return: 是否更新成功
        """
        try:
            filepath = _build_paper_json_path(paper, self.data_root)

            if not os.path.exists(filepath):
                logger.warning(f"JSON文件不存在，无法更新refined_summary字段: {filepath}")
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                paper_data = json.load(f)

            paper_data['refined_summary'] = refined_summary

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper_data, f, ensure_ascii=False, indent=2)

            logger.info(f"已更新论文JSON，添加/更新refined_summary字段: {filepath}")
            return True
        except Exception as e:
            logger.error(f"更新JSON文件refined_summary字段失败: {e}")
            return False


# 便捷函数（向后兼容）
def is_paper_already_saved(paper: Dict, data_root: str) -> bool:
    """判断论文是否已经保存（便捷函数）"""
    storage = PaperStorage(data_root)
    return storage.is_paper_saved(paper)
