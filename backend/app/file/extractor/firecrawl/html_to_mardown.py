import logging
import os
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from readabilipy import simple_json_from_html_string
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


class Article:
    def __init__(self, title: str, html_content: str, url: Optional[str] = None):
        self.title = title or ""
        self.html_content = html_content or ""
        self.url = url or ""

    def to_markdown(self, including_title: bool = True) -> str:
        markdown = ""
        if including_title and self.title:
            markdown += f"# {self.title}\n\n"
        markdown += md(self.html_content or "")
        # 清理多余空行
        markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
        return markdown

    def to_message(self) -> List[Dict]:
        """
        将 markdown 切分成文本块和图片块，返回 list[dict]：
        {"type":"text","text": "..."} or {"type":"image_url","image_url":{"url": "..."}}
        """
        image_pattern = r"!\[.*?\]\((.*?)\)"
        content: List[Dict] = []
        markdown = self.to_markdown()
        parts = re.split(image_pattern, markdown)

        for i, part in enumerate(parts):
            if i % 2 == 1:
                # 奇数位是图片 url（正则捕获组）
                image_url = urljoin(self.url, part.strip()) if self.url else part.strip()
                content.append({"type": "image_url", "image_url": {"url": image_url}})
            else:
                text = part.strip()
                if text:
                    content.append({"type": "text", "text": text})
        return content


class JinaClient:
    """
    简单封装 Jina r.jina.ai 调用
    """
    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.session = session or requests.Session()
        self.endpoint = "https://r.jina.ai/"

    def crawl(self, url: str, return_format: str = "html") -> str:
        headers = {
            "Content-Type": "application/json",
            "X-Return-Format": return_format,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            logger.warning(
                "Jina API key is not set. Provide your own key to access a higher rate limit. "
                "See https://jina.ai/reader for more information."
            )
        data = {"url": url}
        resp = self.session.post(self.endpoint, json=data, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.text


class ReadabilityExtractor:
    """
    使用 readabilipy 提取正文
    """
    def extract_article(self, html: str) -> Article:
        obj = simple_json_from_html_string(html, use_readability=True)
        title = obj.get("title", "") if isinstance(obj, dict) else ""
        content = obj.get("content", "") if isinstance(obj, dict) else ""
        return Article(title=title, html_content=content)


class WebCrawler:
    """
    对外统一接口：
      - crawl(url) -> Article
      - fetch_markdown(url) -> str
      - fetch_message_blocks(url) -> list[dict]
    可传入自定义 requests.Session、Jina API key、Jina return_format 等。
    """
    def __init__(
        self,
        jina_api_key: Optional[str] = None,
        jina_return_format: str = "html",
        session: Optional[requests.Session] = None,
    ):
        self.session = session or requests.Session()
        self.jina_client = JinaClient(api_key=jina_api_key, session=self.session)
        self.extractor = ReadabilityExtractor()
        self.jina_return_format = jina_return_format

    def crawl(self, url: str) -> Article:
        """抓取并解析为 Article 对象（包含 title, html_content, url）。"""
        html = self.jina_client.crawl(url, return_format=self.jina_return_format)
        article = self.extractor.extract_article(html)
        article.url = url
        return article

    def fetch_markdown(self, url: str, including_title: bool = True) -> str:
        """直接返回页面的 Markdown 字符串（已清理多余空行）。"""
        article = self.crawl(url)
        return article.to_markdown(including_title=including_title)

    def fetch_message_blocks(self, url: str) -> List[Dict]:
        """返回切分好的消息块（文本/图片），方便发送到聊天或其他接口。"""
        article = self.crawl(url)
        return article.to_message()


# ------------------------
# 简单示例
# ------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    crawler = WebCrawler()  # 会自动读取环境变量 JINA_API_KEY（如果有）
    test_url = "https://finance.sina.com.cn/stock/relnews/us/2024-08-15/doc-incitsya6536375.shtml"

    try:
        md_text = crawler.fetch_markdown(test_url)
        print("----- markdown -----")
        print(md_text[:2000])  # 仅打印前 2000 字以示例
        print("----- message blocks -----")
        for block in crawler.fetch_message_blocks(test_url)[:10]:
            print(block)
    except Exception as e:
        logger.exception("抓取失败: %s", e)





























# import logging
# import os
# import re
# from urllib.parse import urljoin

# from readabilipy import simple_json_from_html_string
# import requests
# logger = logging.getLogger(__name__)

# from markdownify import markdownify as md


# '''

# 这里封装一下
# '''

# class Article:
#     url: str

#     def __init__(self, title: str, html_content: str):
#         self.title = title
#         self.html_content = html_content

#     def to_markdown(self, including_title: bool = True) -> str:
#         markdown = ""
#         if including_title:
#             markdown += f"# {self.title}\n\n"
#         markdown += md(self.html_content)
#         return markdown

#     def to_message(self) -> list[dict]:
#         image_pattern = r"!\[.*?\]\((.*?)\)"

#         content: list[dict[str, str]] = []
#         parts = re.split(image_pattern, self.to_markdown())

#         for i, part in enumerate(parts):
#             if i % 2 == 1:
#                 image_url = urljoin(self.url, part.strip())
#                 content.append({"type": "image_url", "image_url": {"url": image_url}})
#             else:
#                 content.append({"type": "text", "text": part.strip()})

#         return content
    

# class JinaClient:
#     def crawl(self, url: str, return_format: str = "html") -> str:
#         headers = {
#             "Content-Type": "application/json",
#             "X-Return-Format": return_format,
#         }
#         if os.getenv("JINA_API_KEY"):
#             headers["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
#         else:
#             logger.warning(
#                 "Jina API key is not set. Provide your own key to access a higher rate limit. See https://jina.ai/reader for more information."
#             )
#         data = {"url": url}
#         response = requests.post("https://r.jina.ai/", headers=headers, json=data)
#         return response.text

# class ReadabilityExtractor:
#     def extract_article(self, html: str) -> Article:
#         article = simple_json_from_html_string(html, use_readability=True)
#         return Article(
#             title=article.get("title"),
#             html_content=article.get("content"),
#         )


# class Crawler:
#     def crawl(self, url: str) -> Article:
#         # To help LLMs better understand content, we extract clean
#         # articles from HTML, convert them to markdown, and split
#         # them into text and image blocks for one single and unified
#         # LLM message.
#         #
#         # Jina is not the best crawler on readability, however it's
#         # much easier and free to use.
#         #
#         # Instead of using Jina's own markdown converter, we'll use
#         # our own solution to get better readability results.
#         jina_client = JinaClient()
#         html = jina_client.crawl(url, return_format="html")
#         extractor = ReadabilityExtractor()
#         article = extractor.extract_article(html)
#         article.url = url
#         return article
    
    

# def test_crawler_markdown_output():
#     """Test that crawler output can be converted to markdown."""
#     crawler = Crawler()
#     test_url = "https://finance.sina.com.cn/stock/relnews/us/2024-08-15/doc-incitsya6536375.shtml"
#     # test_weixinarticl = "https://pypi.org/project/readability/"
#     result = crawler.crawl(test_url)
#     markdown = result.to_markdown()
#     print("markdown:", markdown)
   
# crawler = Crawler() 
    
    
# def visit_webpage(url: str) -> str:
#     """Visits a webpage at the given URL and returns its content as a markdown string.

#     Args:
#         url: The URL of the webpage to visit.

#     Returns:
#         The content of the webpage converted to Markdown, or an error message if the request fails.
#     """
#     try:
#         # Send a GET request to the URL
#         # response = requests.get(url)
#         # response.raise_for_status()  # Raise an exception for bad status codes

#         # # Convert the HTML content to Markdown  是否可以采用jina来完成
#         # markdown_content = markdownify(response.text).strip()
#         result = crawler.crawl(url)
#         markdown_content = result.to_markdown()

#         # Remove multiple line breaks
#         markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

#         return markdown_content

#     except requests.RequestException as e:
#         return f"Error fetching the webpage: {str(e)}"
#     except Exception as e:
#         return f"An unexpected error occurred: {str(e)}"