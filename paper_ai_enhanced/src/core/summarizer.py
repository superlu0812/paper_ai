"""
论文总结模块
使用大模型对论文进行总结，输出Markdown格式
"""
import os
from typing import Dict, Optional

import PyPDF2
from urllib.request import urlretrieve

from ..api.llm import LLMClient
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PaperSummarizer:
    """论文总结器"""

    def __init__(self, config: Dict, data_root: str):
        """
        初始化论文总结器
        :param config: 配置字典
        :param data_root: 数据根目录（所有PDF/Markdown等都保存在该目录下）
        """
        self.llm_config = config.get('llm', {})
        self.enabled = self.llm_config.get('enabled', False)
        self.prompt_template = self.llm_config.get('prompt_template', '')
        self.data_root = data_root

        # 初始化 LLM 客户端
        if self.enabled:
            self.llm_client = LLMClient(
                api_url=self.llm_config.get('api_url', ''),
                api_key=self.llm_config.get('api_key', 'none'),
                model=self.llm_config.get('model', 'gpt-3.5-turbo'),
                timeout=self.llm_config.get('timeout', 300),
                max_retries=self.llm_config.get('max_retries', 3),
                retry_delay=self.llm_config.get('retry_delay', 5),
            )
        else:
            self.llm_client = None

    def _download_pdf(self, pdf_url: str, save_path: str) -> bool:
        """下载PDF文件"""
        try:
            logger.info(f"正在下载PDF: {pdf_url}")
            urlretrieve(pdf_url, save_path)
            logger.info(f"PDF下载成功: {save_path}")
            return True
        except Exception as e:
            logger.error(f"PDF下载失败: {e}")
            return False

    def _extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """从PDF文件中提取文字并保存到content目录"""
        try:
            logger.info(f"正在从PDF提取文字: {pdf_path}")
            text_content = []

            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)

                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text:
                        text_content.append(text)

                full_text = '\n\n'.join(text_content)
                logger.info(f"PDF文字提取成功，共 {total_pages} 页")

                # 将提取的文字保存在与pdf目录同级的content目录下
                try:
                    pdf_dir = os.path.dirname(pdf_path)
                    date_dir = os.path.dirname(pdf_dir)  # pdf目录的上一级目录
                    content_dir = os.path.join(date_dir, 'content')
                    os.makedirs(content_dir, exist_ok=True)

                    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                    content_path = os.path.join(content_dir, f"{base_name}.txt")

                    with open(content_path, 'w', encoding='utf-8') as content_file:
                        content_file.write(full_text)

                    logger.info(f"PDF文字内容已保存到: {content_path}")
                except Exception as save_err:
                    # 保存文本失败不影响后续流程，只记录日志
                    logger.error(f"保存PDF文字内容到content目录失败: {save_err}")

                return full_text
        except Exception as e:
            logger.error(f"PDF文字提取失败: {e}")
            return None

    def _get_pdf_text(self, paper: Dict) -> Optional[str]:
        """获取论文PDF的文字内容（下载并提取）"""
        pdf_url = paper.get('pdf_url', '')
        if not pdf_url:
            logger.warning("论文没有PDF链接")
            return None

        published = paper.get('published', '')
        if published:
            date_str = published.split(' ')[0]
        else:
            date_str = 'unknown'

        date_dir = os.path.join(self.data_root, date_str)
        pdf_dir = os.path.join(date_dir, 'pdf')
        os.makedirs(pdf_dir, exist_ok=True)

        title = paper.get('title', 'untitled')
        safe_title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        safe_title = safe_title[:100]
        pdf_filename = f"{safe_title}.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        if os.path.exists(pdf_path):
            logger.info(f"PDF文件已存在: {pdf_path}")
            return self._extract_text_from_pdf(pdf_path)

        if not self._download_pdf(pdf_url, pdf_path):
            return None

        return self._extract_text_from_pdf(pdf_path)

    def _generate_prompt(self, paper: Dict, pdf_text: Optional[str] = None) -> str:
        """生成论文总结的提示词"""
        title = paper.get('title', '')
        authors = paper.get('authors', [])
        summary = paper.get('summary', '')

        authors_str = ', '.join(authors) if authors else 'Unknown'

        content_text = pdf_text if pdf_text else summary

        if pdf_text and len(pdf_text) > 100000:
            logger.info(f"PDF文字过长（{len(pdf_text)}字符），截取前100000字符")
            content_text = pdf_text[:100000] + "\n\n[内容已截断...]"

        if '{pdf_text}' in self.prompt_template:
            prompt = self.prompt_template.format(
                title=title,
                authors=authors_str,
                summary=summary,
                pdf_text=content_text
            )
        else:
            prompt = self.prompt_template.format(
                title=title,
                authors=authors_str,
                summary=content_text
            )

        return prompt

    def summarize_paper(self, paper: Dict) -> Dict[str, Optional[str]]:
        """对论文进行总结，并返回总结结果与PDF文字内容"""
        result: Dict[str, Optional[str]] = {
            "summary_markdown": None,
            "pdf_text": None,
        }

        if not self.enabled or not self.llm_client:
            logger.info("大模型总结功能未启用")
            return result

        logger.info(f"开始总结论文: {paper.get('title', 'Unknown')[:50]}...")

        pdf_text = self._get_pdf_text(paper)
        result["pdf_text"] = pdf_text

        if pdf_text:
            logger.info(f"已获取PDF文字内容（{len(pdf_text)}字符）")
        else:
            logger.info("无法获取PDF文字，将使用摘要进行总结")

        prompt = self._generate_prompt(paper, pdf_text)
        summary_markdown = self.llm_client.chat(prompt)
        result["summary_markdown"] = summary_markdown

        if summary_markdown:
            logger.info("论文总结完成")
        else:
            logger.error("论文总结失败")

        return result

    def save_summary(self, paper: Dict, summary_markdown: str) -> str:
        """保存论文总结到markdown文件"""
        title = paper.get('title', 'untitled')
        safe_title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        safe_title = safe_title[:100]

        published = paper.get('published', '')
        if published:
            date_str = published.split(' ')[0]
        else:
            date_str = 'unknown'

        date_dir = os.path.join(self.data_root, date_str)
        markdown_subdir = os.path.join(date_dir, 'markdown')
        os.makedirs(markdown_subdir, exist_ok=True)

        filename = f"{safe_title}.md"
        filepath = os.path.join(markdown_subdir, filename)

        full_markdown = self._build_full_markdown(paper, summary_markdown)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_markdown)
            logger.info(f"论文总结已保存到: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"保存markdown文件失败: {e}")
            return ""

    def _build_full_markdown(self, paper: Dict, summary_markdown: str) -> str:
        """构建完整的markdown内容"""
        title = paper.get('title', 'Unknown Title')
        authors = paper.get('authors', [])
        categories = paper.get('categories', [])
        published = paper.get('published', 'Unknown')
        pdf_url = paper.get('pdf_url', '')
        entry_id = paper.get('entry_id', '')
        summary = paper.get('summary', '')

        authors_str = ', '.join(authors) if authors else 'Unknown'
        categories_str = ', '.join(categories) if categories else 'Unknown'

        markdown = f"""# {title}

## 论文信息

- **作者**: {authors_str}
- **分类**: {categories_str}
- **发布时间**: {published}
- **PDF链接**: [{pdf_url}]({pdf_url})
- **Arxiv链接**: [{entry_id}]({entry_id})

## 摘要

{summary}

## 详细总结

{summary_markdown}

---

*本总结由AI生成，仅供参考。*
"""
        return markdown

    def process_paper(self, paper: Dict) -> Dict:
        """处理单篇论文：总结并保存"""
        result = {
            'success': False,
            'markdown_path': '',
            'summary': '',
            'pdf_text': None,
        }

        if not self.enabled:
            return result

        summary_result = self.summarize_paper(paper)
        summary_markdown = summary_result.get("summary_markdown")
        pdf_text = summary_result.get("pdf_text")

        if summary_markdown:
            markdown_path = self.save_summary(paper, summary_markdown)
            if markdown_path:
                result['success'] = True
                result['markdown_path'] = markdown_path
                result['summary'] = summary_markdown

        if pdf_text:
            result['pdf_text'] = pdf_text

        return result
