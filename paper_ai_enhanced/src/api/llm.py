"""
LLM API 客户端
"""
import time
from typing import Optional

import requests

from ..utils.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    """LLM API 客户端"""

    def __init__(
        self,
        api_url: str,
        api_key: str = "none",
        model: str = "gpt-3.5-turbo",
        timeout: int = 300,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """
        初始化 LLM 客户端
        :param api_url: API 地址
        :param api_key: API 密钥
        :param model: 模型名称
        :param timeout: 超时时间（秒）
        :param max_retries: 最大重试次数
        :param retry_delay: 重试延迟（秒）
        """
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def chat(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        thinking_disabled: bool = True,
    ) -> Optional[str]:
        """
        调用 LLM API 进行对话
        :param prompt: 提示词
        :param temperature: 温度参数
        :param max_tokens: 最大 token 数
        :param thinking_disabled: 是否禁用思考模式
        :return: 模型返回的文本，失败返回 None
        """
        if not self.api_url:
            logger.error("错误: 未配置LLM API地址")
            return None

        headers = {"Content-Type": "application/json"}

        if self.api_key and self.api_key != "none":
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if thinking_disabled:
            payload["thinking"] = {"type": "disabled"}

        for attempt in range(self.max_retries):
            try:
                logger.info(f"正在调用LLM API（尝试 {attempt + 1}/{self.max_retries}）...")
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        logger.info("LLM API调用成功")
                        return content
                    else:
                        logger.error(f"错误: API响应格式异常 - {result}")
                        return None
                else:
                    logger.error(f"API调用失败，状态码: {response.status_code}, 响应: {response.text}")

            except requests.exceptions.Timeout:
                logger.warning(f"请求超时（尝试 {attempt + 1}/{self.max_retries}）")
            except Exception as e:
                logger.error(f"API调用异常（尝试 {attempt + 1}/{self.max_retries}）: {e}")

            if attempt < self.max_retries - 1:
                logger.info(f"等待 {self.retry_delay} 秒后重试...")
                time.sleep(self.retry_delay)

        logger.error("LLM API调用失败，已达最大重试次数")
        return None


def translate_summary_via_llm(config: dict, summary: str) -> Optional[str]:
    """使用LLM将摘要翻译成中文（使用semantic的模型配置）"""
    filter_config = config.get('filter', {})
    semantic_config = filter_config.get('semantic', {})
    if not semantic_config.get('enabled', False):
        return None

    api_url = semantic_config.get('api_url', '')
    api_key = semantic_config.get('api_key', 'none')
    model = semantic_config.get('model', 'glm-4.5-flash')
    timeout = semantic_config.get('timeout', 30)

    if not api_url:
        return None

    prompt = f"""请将以下英文论文摘要翻译成中文，保持专业术语的准确性。

英文摘要：
{summary}

请直接输出中文翻译，不要添加任何前缀或说明。"""

    llm_client = LLMClient(
        api_url=api_url,
        api_key=api_key,
        model=model,
        timeout=timeout,
        max_retries=3,
        retry_delay=2,
    )

    return llm_client.chat(prompt, temperature=0.3, max_tokens=1000)


def refine_summary_via_llm(config: dict, llm_summary: str) -> Optional[str]:
    """使用LLM对总结进行精炼，生成200-300字的简短总结"""
    llm_config = config.get('llm', {})
    if not llm_config.get('enabled', False):
        return None

    api_url = llm_config.get('api_url', '')
    api_key = llm_config.get('api_key', 'none')
    model = llm_config.get('model', 'gpt-3.5-turbo')
    timeout = llm_config.get('timeout', 300)

    if not api_url:
        return None

    prompt = f"""请将以下论文总结精炼为200-300字的中文总结，保留核心研究内容、方法和结论，方便快速判定研究相关性。

原始总结：
{llm_summary}

请直接输出精炼后的总结，不要添加任何前缀或说明。"""

    llm_client = LLMClient(
        api_url=api_url,
        api_key=api_key,
        model=model,
        timeout=timeout,
        max_retries=3,
        retry_delay=2,
    )

    return llm_client.chat(prompt, temperature=0.7, max_tokens=500)
