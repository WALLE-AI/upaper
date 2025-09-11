import re
from urllib.parse import urljoin

from markdownify import markdownify as md
from readabilipy import simple_json_from_html_string

import logging
import os

import requests

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()


class Article:
    url: str

    def __init__(self, title: str, html_content: str):
        self.title = title
        self.html_content = html_content

    def to_markdown(self, including_title: bool = True) -> str:
        markdown = ""
        if including_title:
            markdown += f"# {self.title}\n\n"
        markdown += md(self.html_content)
        return markdown

    def to_message(self) -> list[dict]:
        image_pattern = r"!\[.*?\]\((.*?)\)"

        content: list[dict[str, str]] = []
        parts = re.split(image_pattern, self.to_markdown())

        for i, part in enumerate(parts):
            if i % 2 == 1:
                image_url = urljoin(self.url, part.strip())
                content.append({"type": "image_url", "image_url": {"url": image_url}})
            else:
                content.append({"type": "text", "text": part.strip()})

        return content
    

class JinaClient:
    def crawl(self, url: str, return_format: str = "html") -> str:
        headers = {
            "Content-Type": "application/json",
            "X-Return-Format": return_format,
        }
        if os.getenv("JINA_API_KEY"):
            headers["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
        else:
            logger.warning(
                "Jina API key is not set. Provide your own key to access a higher rate limit. See https://jina.ai/reader for more information."
            )
        data = {"url": url}
        response = requests.post("https://r.jina.ai/", headers=headers, json=data)
        return response.text

class ReadabilityExtractor:
    def extract_article(self, html: str) -> Article:
        article = simple_json_from_html_string(html, use_readability=True)
        return Article(
            title=article.get("title"),
            html_content=article.get("content"),
        )


class Crawler:
    def crawl(self, url: str) -> Article:
        # To help LLMs better understand content, we extract clean
        # articles from HTML, convert them to markdown, and split
        # them into text and image blocks for one single and unified
        # LLM message.
        #
        # Jina is not the best crawler on readability, however it's
        # much easier and free to use.
        #
        # Instead of using Jina's own markdown converter, we'll use
        # our own solution to get better readability results.
        jina_client = JinaClient()
        html = jina_client.crawl(url, return_format="html")
        extractor = ReadabilityExtractor()
        article = extractor.extract_article(html)
        article.url = url
        return article
    
    
crawler = Crawler()
    
    
def visit_webpage(url: str) -> str:
    """Visits a webpage at the given URL and returns its content as a markdown string.

    Args:
        url: The URL of the webpage to visit.

    Returns:
        The content of the webpage converted to Markdown, or an error message if the request fails.
    """
    try:
        # Send a GET request to the URL
        # response = requests.get(url)
        # response.raise_for_status()  # Raise an exception for bad status codes

        # # Convert the HTML content to Markdown  是否可以采用jina来完成
        # markdown_content = markdownify(response.text).strip()
        result = crawler.crawl(url)
        markdown_content = result.to_markdown()

        # Remove multiple line breaks
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        return markdown_content

    except requests.RequestException as e:
        return f"Error fetching the webpage: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"
    
    

def test_crawler_markdown_output():
    """Test that crawler output can be converted to markdown."""
    crawler = Crawler()
    test_url = "https://finance.sina.com.cn/stock/relnews/us/2024-08-15/doc-incitsya6536375.shtml"
    # test_weixinarticl = "https://pypi.org/project/readability/"
    result = crawler.crawl(test_url)
    markdown = result.to_markdown()
    print("markdown:", markdown)
    
    
    
    
    
if __name__ == "__main__":
    test_crawler_markdown_output()