"""
论文过滤模块
支持两种过滤方式：
1. 关键词过滤：基于预定义的关键词列表进行匹配
2. 语义理解过滤：使用小模型通过标题、摘要等信息进行语义判定
"""
import time
from typing import Dict, List, Optional

import requests

from ..utils.logging import get_logger

logger = get_logger(__name__)


class PaperFilter:
    """论文过滤器"""

    def __init__(self, config: Dict):
        """
        初始化论文过滤器
        :param config: 配置字典
        """
        self.filter_config = config.get('filter', {})
        self.enabled = self.filter_config.get('enabled', False)
        self.mode = self.filter_config.get('mode', 'both')  # keyword, semantic, both

        # 关键词过滤配置
        self.keyword_config = self.filter_config.get('keyword', {})
        self.keyword_enabled = self.keyword_config.get('enabled', False)
        self.keywords = self.keyword_config.get('keywords', [])
        self.keyword_match_mode = self.keyword_config.get('match_mode', 'any')
        self.keyword_case_sensitive = self.keyword_config.get('case_sensitive', False)

        # 语义理解过滤配置
        self.semantic_config = self.filter_config.get('semantic', {})
        self.semantic_enabled = self.semantic_config.get('enabled', False)
        self.semantic_api_url = self.semantic_config.get('api_url', '')
        self.semantic_api_key = self.semantic_config.get('api_key', 'none')
        self.semantic_model = self.semantic_config.get('model', 'gpt-3.5-turbo')
        self.semantic_timeout = self.semantic_config.get('timeout', 30)
        self.semantic_max_retries = self.semantic_config.get('max_retries', 3)
        self.semantic_retry_delay = self.semantic_config.get('retry_delay', 2)
        self.semantic_prompt_template = self.semantic_config.get('prompt_template', '')

    def _keyword_filter(self, paper: Dict) -> bool:
        """关键词过滤"""
        if not self.keyword_enabled or not self.keywords:
            return True

        title = paper.get('title', '')
        summary = paper.get('summary', '')
        text = f"{title} {summary}"

        if not self.keyword_case_sensitive:
            text = text.lower()
            keywords = [kw.lower() for kw in self.keywords]
        else:
            keywords = self.keywords

        if self.keyword_match_mode == 'all':
            return all(kw in text for kw in keywords)
        else:
            return any(kw in text for kw in keywords)

    def _call_semantic_filter_api(self, prompt: str) -> Optional[bool]:
        """调用小模型API进行语义过滤"""
        if not self.semantic_api_url:
            logger.error("错误: 未配置语义过滤API地址")
            return None

        headers = {"Content-Type": "application/json"}

        if self.semantic_api_key and self.semantic_api_key != 'none':
            headers["Authorization"] = f"Bearer {self.semantic_api_key}"

        payload = {
            "model": self.semantic_model,
            "messages": [{"role": "user", "content": prompt}],
            "thinking": {"type": "disabled"},
            "temperature": 0.3,
            "max_tokens": 100,
        }

        for attempt in range(self.semantic_max_retries):
            try:
                response = requests.post(
                    self.semantic_api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.semantic_timeout,
                )

                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        message = result['choices'][0]['message']
                        content = message.get('content', '').strip()
                        if not content and 'reasoning_content' in message:
                            content = message.get('reasoning_content', '').strip()

                        if content:
                            content_lower = content.lower()
                            logger.info(content_lower)
                            if '是' in content or 'yes' in content_lower or 'true' in content_lower or '相关' in content:
                                return True
                            elif '否' in content or 'no' in content_lower or 'false' in content_lower or '不相关' in content:
                                return False
                            else:
                                logger.warning(f"警告: 语义过滤API返回了意外的结果: {content}")
                                return None
                        else:
                            logger.warning("警告: 语义过滤API返回的内容为空")
                            return None
                    else:
                        logger.error(f"错误: API响应格式异常 - {result}")
                        return None
                else:
                    logger.error(f"语义过滤API调用失败，状态码: {response.status_code}, 响应: {response.text}")

            except requests.exceptions.Timeout:
                logger.warning(f"语义过滤请求超时（尝试 {attempt + 1}/{self.semantic_max_retries}）")
            except Exception as e:
                logger.error(f"语义过滤API调用异常（尝试 {attempt + 1}/{self.semantic_max_retries}）: {e}")

            if attempt < self.semantic_max_retries - 1:
                time.sleep(self.semantic_retry_delay)

        logger.error("语义过滤API调用失败，已达最大重试次数")
        return None

    def _semantic_filter(self, paper: Dict) -> Optional[bool]:
        """语义理解过滤"""
        if not self.semantic_enabled:
            return True

        title = paper.get('title', '')
        summary = paper.get('summary', '')

        prompt = self.semantic_prompt_template.format(title=title, summary=summary)

        return self._call_semantic_filter_api(prompt)

    def filter_paper(self, paper: Dict) -> Dict:
        """过滤单篇论文"""
        result = {
            'passed': True,
            'method': 'none',
            'keyword_result': None,
            'semantic_result': None,
        }

        if not self.enabled:
            result['method'] = 'disabled'
            return result

        if self.mode == 'keyword':
            keyword_result = self._keyword_filter(paper)
            result['keyword_result'] = keyword_result
            result['method'] = 'keyword'
            result['passed'] = keyword_result

        elif self.mode == 'semantic':
            semantic_result = self._semantic_filter(paper)
            result['semantic_result'] = semantic_result
            result['method'] = 'semantic'
            result['passed'] = semantic_result if semantic_result is not None else True

        elif self.mode == 'both':
            keyword_result = self._keyword_filter(paper)
            result['keyword_result'] = keyword_result

            if keyword_result:
                result['method'] = 'keyword'
                result['passed'] = True
            else:
                semantic_result = self._semantic_filter(paper)
                result['semantic_result'] = semantic_result
                result['method'] = 'semantic'
                result['passed'] = semantic_result if semantic_result is not None else False
        else:
            result['method'] = 'unknown'
            result['passed'] = True

        return result

    def filter_papers(self, papers: List[Dict]) -> tuple:
        """批量过滤论文"""
        if not self.enabled:
            return papers, []

        filtered_papers = []
        removed_papers = []

        logger.info(f"开始过滤论文（模式: {self.mode}）...")

        for idx, paper in enumerate(papers, 1):
            title = paper.get('title', 'Unknown')[:50]
            logger.info(f"过滤论文 {idx}/{len(papers)}: {title}...")

            filter_result = self.filter_paper(paper)

            if filter_result['passed']:
                paper['filter_info'] = filter_result
                filtered_papers.append(paper)
                logger.info(f"  通过过滤（方法: {filter_result['method']}）")
            else:
                removed_papers.append(paper)
                logger.info(f"  未通过过滤（方法: {filter_result['method']}）")

        logger.info(f"过滤完成: 通过 {len(filtered_papers)} 篇，过滤掉 {len(removed_papers)} 篇")

        return filtered_papers, removed_papers
