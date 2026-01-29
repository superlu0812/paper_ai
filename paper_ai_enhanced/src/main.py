"""
主程序入口
"""
import argparse
from datetime import datetime, timedelta
from typing import List, Dict

from .config import load_config, get_data_root
from .utils.logging import setup_logging, get_logger
from .crawler import ArxivCrawler
from .core import PaperFilter, PaperStorage, PaperSummarizer, is_paper_already_saved, generate_aipaper_url
from .notify import push_paper_to_gateway
from .api.llm import translate_summary_via_llm, refine_summary_via_llm

logger = get_logger(__name__)


def get_date_range(days_back: int = 1) -> tuple:
    """
    获取日期范围
    :param days_back: 往前推多少天，默认1天（昨天）
    :return: (start_date, end_date)
    """
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days_back)
    return start_date, end_date


def log_paper_info(paper: Dict) -> None:
    """记录论文基本信息到日志"""
    logger.info("=" * 80)
    logger.info(f"标题: {paper.get('title', 'Unknown')}")
    logger.info(f"作者: {', '.join(paper.get('authors', []))}")
    logger.info(f"分类: {', '.join(paper.get('categories', []))}")
    logger.info(f"发布时间: {paper.get('published', 'Unknown')}")
    logger.info(f"摘要: {paper.get('summary', '')[:200]}...")
    logger.info(f"链接: {paper.get('pdf_url', '')}")
    logger.info("=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Arxiv论文爬取和总结工具')
    parser.add_argument('--config', '-c', default='config.yaml',
                        help='配置文件路径（默认: config.yaml）')
    parser.add_argument('--days', '-d', type=int, default=None,
                        help='往前推多少天（默认: 使用配置文件中的值）')
    parser.add_argument('--max-results', '-m', type=int, default=None,
                        help='最大结果数（默认: 使用配置文件中的值）')
    parser.add_argument('--categories', nargs='+', default=None,
                        help='arxiv分类，如: cs.AI cs.LG（默认: 使用配置文件中的值）')
    parser.add_argument('--no-llm', action='store_true',
                        help='禁用大模型总结')
    parser.add_argument('--no-filter', action='store_true',
                        help='禁用论文过滤')
    parser.add_argument('--no-push', action='store_true',
                        help='禁用推送')

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 数据根目录 & 日志
    data_root = get_data_root(config)
    setup_logging(data_root)
    logger.info(f"数据根目录: {data_root}")

    # 获取配置参数
    arxiv_config = config.get('arxiv', {})
    output_config = config.get('output', {})

    # 命令行参数优先级高于配置文件
    days_back = args.days if args.days is not None else arxiv_config.get('days_back', 1)
    max_results = args.max_results if args.max_results is not None else arxiv_config.get('max_results', 50)
    categories = args.categories if args.categories is not None else arxiv_config.get('categories', [])

    # 输出配置
    json_enabled = output_config.get('json_enabled', True)
    console_enabled = output_config.get('console_enabled', True)

    # 初始化论文过滤器
    filter_enabled = not args.no_filter
    if filter_enabled:
        paper_filter = PaperFilter(config)
        filter_enabled = paper_filter.enabled
        if filter_enabled:
            logger.info("论文过滤功能已启用")
        else:
            logger.info("论文过滤功能未启用（配置文件中disabled）")
    else:
        paper_filter = None
        logger.info("论文过滤功能已禁用（命令行参数 --no-filter）")

    # 初始化论文总结器
    llm_enabled = not args.no_llm
    if llm_enabled:
        summarizer = PaperSummarizer(config, data_root=data_root)
        llm_enabled = summarizer.enabled
        if llm_enabled:
            logger.info("大模型总结功能已启用")
        else:
            logger.info("大模型总结功能未启用（配置文件中disabled）")
    else:
        summarizer = None
        logger.info("大模型总结功能已禁用（命令行参数 --no-llm）")

    # 初始化存储管理器
    storage = PaperStorage(data_root, config=config)

    # 初始化爬虫
    crawler = ArxivCrawler(config)

    # 处理日期范围
    start_date, end_date = get_date_range(days_back)

    logger.info("=" * 80)
    logger.info(f"开始执行论文爬取任务: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    logger.info(f"时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    if categories:
        logger.info(f"分类: {', '.join(categories)}")
    logger.info(f"最大结果数: {max_results}")

    # 获取论文
    papers = crawler.fetch_papers(
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        max_results=max_results
    )

    if not papers:
        logger.info("未找到符合条件的论文")
        return

    logger.info(f"共获取 {len(papers)} 篇论文")

    # 去重：过滤掉已经保存过的论文，避免重复处理
    new_papers = []
    existing_papers = []
    for paper in papers:
        if storage.is_paper_saved(paper):
            existing_papers.append(paper)
        else:
            new_papers.append(paper)

    logger.info(f"去重结果: 原始 {len(papers)} 篇，已存在 {len(existing_papers)} 篇，新论文 {len(new_papers)} 篇")

    if not new_papers:
        logger.info("没有新的论文需要处理，程序结束")
        return

    # 论文过滤（仅对新论文进行）
    filtered_papers = new_papers
    removed_papers = []
    if filter_enabled and paper_filter:
        filtered_papers, removed_papers = paper_filter.filter_papers(new_papers)
        logger.info(
            f"过滤结果: 新论文 {len(new_papers)} 篇，通过过滤 {len(filtered_papers)} 篇，"
            f"过滤掉 {len(removed_papers)} 篇 (已存在 {len(existing_papers)} 篇已跳过)"
        )

        if not filtered_papers:
            logger.info("所有新论文都被过滤掉了，程序结束")
            return
    else:
        logger.info("跳过论文过滤步骤")

    # 为过滤后的论文添加 aipaper_url 字段（在保存和推送之前）
    for paper in filtered_papers:
        aipaper_url = generate_aipaper_url(paper, config)
        if aipaper_url:
            paper['aipaper_url'] = aipaper_url

    # 保存JSON数据（只保存过滤后的新论文）
    if json_enabled:
        storage.save_papers(filtered_papers)

    # 使用大模型总结论文（只总结过滤后的论文）
    papers_with_summary = []
    summarized_count = 0

    if llm_enabled and summarizer:
        logger.info("开始使用大模型总结论文...")

        for idx, paper in enumerate(filtered_papers, 1):
            logger.info(f"处理论文 {idx}/{len(filtered_papers)}: {paper['title'][:50]}...")

            result = summarizer.process_paper(paper)

            paper_with_summary = paper.copy()
            if result['success']:
                paper_with_summary['markdown_path'] = result['markdown_path']
                paper_with_summary['summary_markdown'] = result['summary']
                paper_with_summary['llm_summary'] = result['summary']
                # 同步llm_summary到JSON文件
                if json_enabled:
                    storage.update_paper_summary(paper, result['summary'])
                
                # 总结完成后，立即进行翻译和精炼
                llm_summary = result['summary']
                summary = paper.get('summary', '')
                
                # 精炼AI总结
                if llm_summary:
                    logger.info(f"  正在精炼AI总结...")
                    refined_summary = refine_summary_via_llm(config, llm_summary)
                    if refined_summary:
                        paper_with_summary['refined_summary'] = refined_summary
                        if json_enabled:
                            storage.update_paper_refined_summary(paper, refined_summary)
                        logger.info(f"  AI总结精炼完成")
                    else:
                        logger.warning(f"  AI总结精炼失败")
                
                # 翻译摘要
                if summary:
                    logger.info(f"  正在翻译摘要...")
                    translated_summary = translate_summary_via_llm(config, summary)
                    if translated_summary:
                        paper_with_summary['translated_summary'] = translated_summary
                        if json_enabled:
                            storage.update_paper_translated_summary(paper, translated_summary)
                        logger.info(f"  摘要翻译完成")
                    else:
                        logger.warning(f"  摘要翻译失败")
                
                summarized_count += 1
            else:
                logger.error(f"论文总结失败: {paper['title'][:50]}...")
                # 即使总结失败，也尝试翻译摘要
                summary = paper.get('summary', '')
                if summary:
                    logger.info(f"  总结失败，但仍尝试翻译摘要...")
                    translated_summary = translate_summary_via_llm(config, summary)
                    if translated_summary:
                        paper_with_summary['translated_summary'] = translated_summary
                        if json_enabled:
                            storage.update_paper_translated_summary(paper, translated_summary)
                        logger.info(f"  摘要翻译完成")

            # 如果有PDF提取的文字内容，则同步到内存和JSON的content字段
            pdf_text = result.get('pdf_text')
            if pdf_text:
                paper_with_summary['content'] = pdf_text
                if json_enabled:
                    storage.update_paper_content(paper, pdf_text)

            papers_with_summary.append(paper_with_summary)

            # 控制台输出
            if console_enabled:
                log_paper_info(paper_with_summary)
    else:
        papers_with_summary = filtered_papers
        if console_enabled:
            for idx, paper in enumerate(filtered_papers, 1):
                logger.info(f"论文 {idx}/{len(filtered_papers)}")
                log_paper_info(paper)


    # 网关推送
    if not args.no_push:
        gateway_cfg = config.get('gateway', {})
        if gateway_cfg.get('enabled', False):
            logger.info("准备通过网关推送论文...")
            # 使用相同的论文列表进行推送（限制为前10篇）
            gateway_papers_to_push = papers_with_summary
            if len(papers_with_summary) > 10:
                logger.info(f"注意: 网关只推送前10篇论文（共{len(papers_with_summary)}篇）")
            
            for idx, paper in enumerate(gateway_papers_to_push, 1):
                logger.info(f"正在通过网关推送第 {idx}/{len(gateway_papers_to_push)} 篇论文...")
                push_paper_to_gateway(config, paper)
        else:
            logger.info("网关推送未启用（配置文件中disabled）")
    else:
        logger.info("网关推送已禁用（命令行参数 --no-push）")

    logger.info("=" * 80)
    logger.info("任务完成!")
    logger.info(f"原始论文数: {len(papers)}")
    logger.info(f"已存在论文数(跳过处理): {len(existing_papers)}")
    logger.info(f"新论文数: {len(new_papers)}")
    if filter_enabled and paper_filter:
        logger.info(f"过滤后论文数(新论文中): {len(filtered_papers)}")
        logger.info(f"过滤掉论文数(新论文中): {len(removed_papers)}")
    logger.info(f"已总结论文数: {summarized_count}")
    logger.info(f"任务结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
