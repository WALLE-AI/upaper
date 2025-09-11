import os
from typing import List

from anyio import Path
from backend.utils.parse_mineru import parse_pdf
from smolagents import tool 
import os
import re
from typing import Optional
from playwright.sync_api import sync_playwright, Error as PlaywrightError
# import packages that are used in our tools
import requests
from bs4 import BeautifulSoup
import json

from huggingface_hub import HfApi

import arxiv

from smolagents.gradio_ui import GradioUI

from dotenv import load_dotenv
load_dotenv()

# pdf_file_root = "D:/LLM/project/smolagents/pdf"
##参考：https://www.datacamp.com/tutorial/smolagents
pdf_file_root = os.getenv("PDF_FILE_ROOT", "./papers")

# @tool
# def download_paper_by_id(paper_id: str) -> None:
#     """
#     This tool gets the id of a paper and downloads it from arxiv. It saves the paper locally 
#     in the current directory as "paper.pdf".

#     Args:
#         paper_id: The id of the paper to download.
#     """
#     paper = next(arxiv.Client().results(arxiv.Search(id_list=paper_id)))
#     # for paper in arxiv.Client().results(arxiv.Search(id_list=paper_id)):
#     # pdf_file_name = paper.title+".pdf"
#     # print("download pdf:",pdf_file_name) 
#     # save_pdf_path = os.path.join(pdf_file_root,pdf_file_name.replace(": ",""))
#     ##Todo:这个地方应该加入browser use 来进行下载
#     paper.download_pdf(filename=paper_id+".pdf", dirpath=pdf_file_root)
#     return None
def save_markdown_to_file(markdown_content: str, filename: str):
    """将生成的 markdown 内容保存到本地文件。

    Args:
        markdown_content (str): 需要保存的 markdown 内容。
        filename (str): 保存文件的路径和名称（如 'report.md'）。
    """
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(markdown_content)
        print(f"Markdown report has been saved as {filename}")
    except Exception as e:
        print(f"Error saving markdown file: {str(e)}")    


@tool
def download_paper_by_id(paper_id: str) -> None:
    """
    使用浏览器(Playwright)下载 arXiv 论文 PDF 到 pdf_file_root 目录。
    Args:
        paper_id: 论文 ID（支持带版本号，如 '2401.12345' 或 '2401.12345v2'）
    """
    os.makedirs(pdf_file_root, exist_ok=True)

    # 构造 URL（arXiv 的直链形如 /pdf/{id}.pdf）
    # 若传入包含空格或非法字符，这里做个简单清洗
    pid = re.sub(r"[^0-9A-Za-z.\-v]", "", paper_id)
    pdf_url = f"https://arxiv.org/pdf/{pid}.pdf"
    save_path = os.path.join(pdf_file_root, f"{pid}.pdf")

    try:
        with sync_playwright() as p:
            # 启动无头浏览器，设置常见 UA，规避部分站点的简单拦截
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            # 方式1：用浏览器上下文的 request 客户端直接 GET（依旧走浏览器栈，稳定省心）
            resp = context.request.get(pdf_url, timeout=60_000)
            if resp.ok:
                with open(save_path, "wb") as f:
                    f.write(resp.body())
            else:
                # 方式2（回退）：进入摘要页点击“PDF”按钮并捕获下载事件
                # 有些站点会对直链做限制时可触发下载事件保存
                page = context.new_page()
                page.goto(f"https://arxiv.org/abs/{pid}", wait_until="domcontentloaded")
                with page.expect_download() as dl_info:
                    # “Download PDF” 链接文字通常包含 "PDF"
                    # 也可以更精确地选择  a[href*="/pdf/"]
                    page.locator('a[href*="/pdf/"]').first.click()
                download = dl_info.value
                # 将下载保存到目标路径
                download.save_as(save_path)

            context.close()
            browser.close()

        # 你之前函数返回 None，这里也保持一致；如需返回路径，可改为 return save_path
        return save_path

    except PlaywrightError as e:
        # 让上层知道失败原因
        raise RuntimeError(f"Playwright 下载失败: {e}") from e

@tool
def get_paper_id_by_title(title: str) -> str:
    """
    This is a tool that returns the arxiv paper id by its title.
    It returns the title of the paper

    Args:
        title: The paper title for which to get the id.
    """
    # api = HfApi()
    # paper_id_list = []
    # for _title in title:
    #     papers = api.list_papers(query=_title)
    #     if papers:
    #         paper = next(iter(papers))
    #         paper_id_list.append(paper.id)
    # print("paper id list:",paper_id_list)
    # return paper_id_list
    api = HfApi()
    papers = api.list_papers(query=title)
    if papers:
        paper = next(iter(papers))
        return paper.id
    else:
        return None
    
    
# mineru2_0="http://36.103.251.31:9005/mineru/file_parse"
  
    
from pypdf import PdfReader

@tool
def read_pdf_file(file_path: str) -> str:
    """
    This function reads the first three pages of a PDF file and returns its content as a string.
    Args:
        file_path: The path to the PDF file.
    Returns:
        A string containing the content of the PDF file.
    """
    # content = ""
    # reader = PdfReader(file_path)
    # print(len(reader.pages))
    # ##前三页解读，这个部分也采用mineru或者其他智能文本解析工具实现
    # # pages = reader.pages[:3]
    # for page in reader.pages:
    #     content += page.extract_text()
    # return content
    file_path = Path(file_path)
    file_name = file_path.name
    return parse_pdf(file_path,file_name)




@tool
def get_hugging_face_top_daily_paper() -> List:
    """
    This is a tool that returns the most upvoted paper on Hugging Face daily papers.
    It returns the title of the paper
    """
    try:
      url = "https://huggingface.co/papers"
      response = requests.get(url)
      response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
      soup = BeautifulSoup(response.content, "html.parser")

      # Extract the title element from the JSON-like data in the "data-props" attribute
      containers = soup.find_all('div', class_='SVELTE_HYDRATER contents')
      top_paper_list = []
      top_paper = ""

      for container in containers:
          data_props = container.get('data-props', '')
          if data_props:
              try:
                  # Parse the JSON-like string
                  json_data = json.loads(data_props.replace('&quot;', '"'))
                  if 'dailyPapers' in json_data:
                    #   top_paper = json_data['dailyPapers'][0]['title']
                      for top_paper in json_data['dailyPapers']:
                          top_paper_list.append(top_paper['paper']['id'])
              except json.JSONDecodeError:
                  continue
      print("top paper list:",top_paper_list)
    #   with open("top_daily_paper_list.jsonl", "w", encoding="utf-8") as f:
    #         f.write(json.dumps(top_paper_list,ensure_ascii=False,indent=4))
      return top_paper_list
    except requests.exceptions.RequestException as e:
      print(f"Error occurred while fetching the HTML: {e}")
      return None
  
  
from smolagents import CodeAgent, OpenAIServerModel

# model_id = "Qwen/Qwen2.5-Coder-32B-Instruct"
arxiv_paper_summary_prompts = '''
请帮我分析 Hugging Face 平台今日关注的最新论文。以下是分析报告结构，重点突出创新性、技术亮点与实际应用价值：

一. 基础信息

论文标题（中英文）

作者与机构

发表时间与相关会议/期刊（如有）

代码库地址（如有）

二. 核心内容

研究背景与动机：简要概述研究背景及其动机。

解决的核心问题：明确指出论文要解决的关键问题。

技术创新点：列出 3-5 个创新技术，简明扼要地阐述其意义。

实现方法：简述论文的核心方法与技术，必要时举例说明。

与现有方法的对比优势：突出创新与优势。

三. 实验评估

实验设置与数据集：概述实验设计与使用的数据集。

关键性能指标：列出评估的主要指标（如准确率等）。

对比基准方法的结果：总结与现有方法的对比结果。

消融实验的发现：描述消融实验的关键发现及其意义。

四. 应用价值

潜在商业应用场景：分析技术的实际应用场景。

技术改进空间：探讨现有技术的不足与改进空间。

研究局限性：简述研究的局限性与未来的改进方向。

未来研究方向：提出潜在的后续研究方向。

五. 个人见解

创新性评价：简要评价论文的创新性。

实用性分析：分析其实际应用的可行性。

对领域的潜在影响：评估该论文对相关领域的推动作用。

附加要求：

简洁易懂：用通俗易懂的语言进行总结。

突出创新与实用性：强调技术创新及其实际应用价值。

图表解读：若有图表，简要描述其意义与实验作用。

输出格式： Markdown 格式的中文解读报告

'''


arxiv_paper_summary_prompts_deerflow='''
请帮我分析 Hugging Face 平台今日关注的最新论文,请使用中文进行报告输出

# Role

You should act as an objective and analytical reporter who:
- Presents facts accurately and impartially.
- Organizes information logically.
- Highlights key findings and insights.
- Uses clear and concise language.
- To enrich the report, includes relevant images from the previous steps.
- Relies strictly on provided information.
- Never fabricates or assumes information.
- Clearly distinguishes between facts and analysis

Report_Style

You are a distinguished academic researcher and scholarly writer. 
Your report must embody the highest standards of academic rigor and intellectual discourse. 
Write with the precision of a peer-reviewed journal article, employing sophisticated analytical frameworks, comprehensive literature synthesis, and methodological transparency. 
Your language should be formal, technical, and authoritative, utilizing discipline-specific terminology with exactitude. Structure arguments logically with clear thesis statements, supporting evidence, and nuanced conclusions. Maintain complete objectivity, acknowledge limitations, and present balanced perspectives on controversial topics. The report should demonstrate deep scholarly engagement and contribute meaningfully to academic knowledge.


# Report Structure

Structure your report in the following format:

**Note: All section titles below must be translated according to the locale=chinese.**

1. **Title**
   - Always use the first level heading for the title.
   - A concise title for the report.

2. **Key Points**
   - A bulleted list of the most important findings (4-6 points).
   - Each point should be concise (1-2 sentences).
   - Focus on the most significant and actionable information.

3. **Overview**
   - A brief introduction to the topic (1-2 paragraphs).
   - Provide context and significance.

4. **Detailed Analysis**
   - Organize information into logical sections with clear headings.
   - Include relevant subsections as needed.
   - Present information in a structured, easy-to-follow manner.
   - Highlight unexpected or particularly noteworthy details.
   - **Including images from the previous steps in the report is very helpful.**

5. **Survey Note** (for more comprehensive reports)
   - **Literature Review & Theoretical Framework**: Comprehensive analysis of existing research and theoretical foundations
   - **Methodology & Data Analysis**: Detailed examination of research methods and analytical approaches
   - **Critical Discussion**: In-depth evaluation of findings with consideration of limitations and implications
   - **Future Research Directions**: Identification of gaps and recommendations for further investigation
   
6. **Key Citations**
   - List all references at the end in link reference format.
   - Include an empty line between each citation for better readability.
   - Format: `- [Source Title](URL)`
   
# Writing Guidelines
1. Writing style:
   - Employ sophisticated, formal academic discourse with discipline-specific terminology
   - Construct complex, nuanced arguments with clear thesis statements and logical progression
   - Use third-person perspective and passive voice where appropriate for objectivity
   - Include methodological considerations and acknowledge research limitations
   - Reference theoretical frameworks and cite relevant scholarly work patterns
   - Maintain intellectual rigor with precise, unambiguous language
   - Avoid contractions, colloquialisms, and informal expressions entirely
   - Use hedging language appropriately ("suggests," "indicates," "appears to")

2. Formatting:
   - Use proper markdown syntax.
   - Include headers for sections.
   - Prioritize using Markdown tables for data presentation and comparison.
   - **Including images from the previous steps in the report is very helpful.**
   - Use tables whenever presenting comparative data, statistics, features, or options.
   - Structure tables with clear headers and aligned columns.
   - Use links, lists, inline-code and other formatting options to make the report more readable.
   - Add emphasis for important points.
   - DO NOT include inline citations in the text.
   - Use horizontal rules (---) to separate major sections.
   - Track the sources of information but keep the main text clean and readable.
   
   **Academic Formatting Specifications:**
   - Use formal section headings with clear hierarchical structure (## Introduction, ### Methodology, #### Subsection)
   - Employ numbered lists for methodological steps and logical sequences
   - Use block quotes for important definitions or key theoretical concepts
   - Include detailed tables with comprehensive headers and statistical data
   - Use footnote-style formatting for additional context or clarifications
   - Maintain consistent academic citation patterns throughout
   - Use `code blocks` for technical specifications, formulas, or data samples
   

# Data Integrity

- Only use information explicitly provided in the input.
- State "Information not provided" when data is missing.
- Never create fictional examples or scenarios.
- If data seems incomplete, acknowledge the limitations.
- Do not make assumptions about missing information.

# Table Guidelines

- Use Markdown tables to present comparative data, statistics, features, or options.
- Always include a clear header row with column names.
- Align columns appropriately (left for text, right for numbers).
- Keep tables concise and focused on key information.
- Use proper Markdown table syntax:

```markdown
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |
```

- For feature comparison tables, use this format:

```markdown
| Feature/Option | Description | Pros | Cons |
|----------------|-------------|------|------|
| Feature 1      | Description | Pros | Cons |
| Feature 2      | Description | Pros | Cons |
```

# Notes

- If uncertain about any information, acknowledge the uncertainty.
- Only include verifiable facts from the provided source material.
- Place all citations in the "Key Citations" section at the end, not inline in the text.
- For each citation, use the format: `- [Source Title](URL)`
- Include an empty line between each citation for better readability.
- Include images using `![Image Description](image_url)`. The images should be in the middle of the report, not at the end or separate section.
- The included images should **only** be from the information gathered **from the previous steps**. **Never** include images that are not from the previous steps
- Directly output the Markdown raw content without "```markdown" or "```".
- Always use the language specified by the locale = chinese.

'''

# model_name = "accounts/fireworks/models/deepseek-v3p1"
# api_key = "fw_3ZWyqUFYSfmsQyXWADUoS14d"
# api_base = "https://api.fireworks.ai/inference/v1"

def agent_main():
    model_name = "Qwen3-30B-A3B-Thinking-2507"
    # model_name = "Qwen3-30B-A3B-Instruct-2507"
    model_name = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
    # model_name = "Qwen/Qwen3-Coder-480B-A35B-Instruct"
    api_key = os.getenv('API_KEY')
    api_base = os.getenv('API_BASE')
    # model_name = "Qwen3-30B-A3B-Thinking-2507"
    # api_key = os.getenv('API_KEY')
    # api_base = os.getenv('LOCAL_QWEN3_THINKING_BASE')

    model = OpenAIServerModel(model_id=model_name, api_key=api_key, api_base=api_base)
    agent = CodeAgent(tools=[get_hugging_face_top_daily_paper,
                            #  get_paper_id_by_title,
                            download_paper_by_id,
                            read_pdf_file],
                    model=model,
                    add_base_tools=True)
    # return agent

    response = agent.run(
        arxiv_paper_summary_prompts,
    )
    print("Markdown Report:\n", response)
    save_markdown_to_file(response,"test.md")
    
if __name__ == "__main__":
    print("Running smolagents with hf paper example")
    agent_main()
    # GradioUI(agent, file_upload_folder="./data").launch()
    test_paper_title = "'PVPO: Pre-Estimated Value-Based Policy Optimization for Agentic\n  Reasoning'"
    test_paper_list = ['PVPO: Pre-Estimated Value-Based Policy Optimization for Agentic\n  Reasoning', 'No Label Left Behind: A Unified Surface Defect Detection Model for all\n  Supervision Regimes', 'UI-Level Evaluation of ALLaM 34B: Measuring an Arabic-Centric LLM via\n  HUMAIN Chat', 'How Can Input Reformulation Improve Tool Usage Accuracy in a Complex\n  Dynamic Environment? A Study on τ-bench']
    test_paper_id =['2508.21104', '2508.19060']
    # get_hugging_face_top_daily_paper()
    # get_paper_id_by_title(test_paper_list)
    # download_paper_by_id(test_paper_id)