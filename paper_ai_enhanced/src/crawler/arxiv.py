"""
Arxiv 论文爬取模块
"""
from datetime import datetime
from typing import Dict, List

import arxiv

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ArxivCrawler:
    """Arxiv 爬虫类"""

    def __init__(self, config: Dict):
        """
        初始化爬虫
        :param config: 配置字典
        """
        self.config = config
        self.arxiv_config = config.get('arxiv', {})
        self.crawler_config = config.get('crawler', {})

    def fetch_papers(
        self,
        start_date: datetime,
        end_date: datetime,
        categories: List[str] = None,
        max_results: int = None,
    ) -> List[Dict]:
        """
        从 arxiv 获取指定时间段的论文
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param categories: arxiv 分类列表，如 ['cs.AI', 'cs.LG']
        :param max_results: 最大结果数，如果为 None 则使用配置中的值
        :return: 论文列表
        """
        if categories is None:
            categories = self.arxiv_config.get('categories', [])
        if max_results is None:
            max_results = self.arxiv_config.get('max_results', 1000)

        date_format = "%Y%m%d%H%M%S"
        start_str = start_date.strftime(date_format)
        end_str = end_date.strftime(date_format)

        query = f"submittedDate:[{start_str} TO {end_str}]"

        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query = f"({query}) AND ({cat_query})"

        logger.info(f"查询语句: {query}")
        logger.info("正在获取论文...")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        try:
            for result in search.results():
                paper = {
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "summary": result.summary.replace('\n', ' ').strip(),
                    "published": result.published.strftime("%Y-%m-%d %H:%M:%S"),
                    "categories": result.categories,
                    "primary_category": result.primary_category,
                    "pdf_url": result.pdf_url,
                    "entry_id": result.entry_id,
                    "doi": result.doi if result.doi else None,
                }
                papers.append(paper)
                logger.info(f"已获取: {paper['title'][:50]}...")

        except Exception as e:
            logger.error(f"获取论文时出错: {e}")

        return papers


def fetch_papers(
    start_date: datetime,
    end_date: datetime,
    categories: List[str] = None,
    max_results: int = 1000,
) -> List[Dict]:
    """
    便捷函数：从 arxiv 获取指定时间段的论文
    """
    # 为了向后兼容，创建一个临时配置
    config = {
        'arxiv': {'categories': categories or [], 'max_results': max_results},
        'crawler': {},
    }
    crawler = ArxivCrawler(config)
    return crawler.fetch_papers(start_date, end_date, categories, max_results)
