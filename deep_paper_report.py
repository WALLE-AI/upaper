# -*- coding: utf-8 -*-
"""
deep_paper_report.py
功能：
1) 解析 Markdown 学术论文（含图片链接）
2) 自动抽取结构 & 深度分析维度
3) 生成“深度解读 Prompt”
4) （可选）Web 检索增补
5) 生成中文图文深度研究报告（Markdown），引用源文图片链接

用法：
  python deep_paper_report.py /path/to/paper.md --out out.md --with-web
"""

import re
import os
import sys
import json
import time
import textwrap
import argparse
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup
import markdown as mdlib

# ----------------------------
# 数据结构
# ----------------------------

@dataclass
class Figure:
    alt: str
    url: str
    caption: str = ""
    context_headings: List[str] = field(default_factory=list)

@dataclass
class ParsedMD:
    title: str
    authors: List[str]
    abstract: str
    sections: List[Tuple[str, str]]  # [(heading, body_md)]
    figures: List[Figure]
    references: str
    raw_text: str

@dataclass
class Analysis:
    problem: str
    motivation: str
    contributions: List[str]
    method_highlevel: str
    method_details: List[str]
    datasets: List[str]
    metrics: List[str]
    experiments: List[str]
    baselines: List[str]
    results_takeaways: List[str]
    limitations: List[str]
    risks_bias: List[str]
    ablations: List[str]
    future_work: List[str]
    glossary: Dict[str, str]
    suggested_fig_anchors: Dict[str, List[int]]  # section_key -> list(fig_idx)

# ----------------------------
# 1) 解析 Markdown
# ----------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.M)
IMG_RE = re.compile(r"!\[(.*?)\]\((.*?)\)")
AUTHOR_LINE_RE = re.compile(r"(?i)^\s*(authors?|author)\s*[:：]\s*(.+)$")
ABSTRACT_HEAD_RE = re.compile(r"(?i)^#{1,6}\s*abstract\s*$")

def parse_markdown(md_path: str) -> ParsedMD:
    with open(md_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # 标题：优先第一行 H1，否则首行文本
    title = ""
    m = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    if m:
        title = m.group(1).strip()
    else:
        first_line = raw.strip().splitlines()[0] if raw.strip() else ""
        title = first_line.strip()

    # 作者：从标题附近或前 50 行内的 author/authors 行抽取
    authors = []
    head_block = "\n".join(raw.splitlines()[:50])
    for line in head_block.splitlines():
        m = AUTHOR_LINE_RE.match(line)
        if m:
            # 逗号或 & / 和 / 与 / and
            names = re.split(r",|&| and |、|，|；|;|/|·|\band\b", m.group(2), flags=re.I)
            authors = [n.strip(" -–—") for n in names if n.strip()]
            break

    # 抽取 Abstract：找 "Abstract" 标题块，否则关键字
    abstract = ""
    abs_head = ABSTRACT_HEAD_RE.search(raw)
    if abs_head:
        # 从该标题到下一个标题为摘要
        start = abs_head.end()
        nxt = HEADING_RE.search(raw, pos=start)
        abstract = raw[start:nxt.start()].strip() if nxt else raw[start:].strip()
    else:
        # 回退：找以 "Abstract" 开头段
        mm = re.search(r"(?i)\bAbstract\b[:：]?(.*?)(\n\n|$)", raw, flags=re.S)
        if mm:
            abstract = mm.group(1).strip()

    # 章节分割
    sections = []
    headings = list(HEADING_RE.finditer(raw))
    for i, h in enumerate(headings):
        level = len(h.group(1))
        title_h = h.group(2).strip()
        start = h.end()
        end = headings[i+1].start() if i+1 < len(headings) else len(raw)
        body = raw[start:end].strip()
        sections.append((title_h, body))

    # 图片与所在章节
    figures = []
    for sect_idx, (hname, body) in enumerate(sections):
        for m in IMG_RE.finditer(body):
            alt, url = m.group(1).strip(), m.group(2).strip()
            cap = ""
            # 尝试在图片行后 2 行内找“Figure”/“图”描述
            post = body[m.end():].splitlines()[:2]
            joined = " ".join(post)
            figcap = re.search(r"(?i)(figure|图|caption)[:：]?\s*(.+?)(?:$|\n)", joined)
            if figcap:
                cap = figcap.group(2).strip()
            ctx = [hname]
            figures.append(Figure(alt=alt or hname, url=url, caption=cap, context_headings=ctx))

    # 参考文献区
    references = ""
    ref_idx = None
    for i, (hname, _) in enumerate(sections):
        if re.search(r"(?i)\b(references|bibliography)\b", hname):
            ref_idx = i
            break
    if ref_idx is not None:
        references = sections[ref_idx][1]

    return ParsedMD(
        title=title or "（未命名论文）",
        authors=authors,
        abstract=abstract,
        sections=sections,
        figures=figures,
        references=references,
        raw_text=raw
    )

# ----------------------------
# 2) 深度分析（启发式 + 规则）
# ----------------------------

def _grep_items(text: str, patterns: List[str]) -> List[str]:
    hits = []
    for p in patterns:
        for m in re.finditer(p, text, flags=re.I):
            span = text[max(0, m.start()-240): m.end()+240]
            frag = re.sub(r"\s+", " ", span).strip()
            if frag not in hits:
                hits.append(frag)
    return hits[:8]

def analyze_structure(p: ParsedMD) -> Analysis:
    all_text = p.raw_text

    # 问题/动机
    problem = ""
    motivation = ""
    intro = ""
    for name, body in p.sections:
        if re.search(r"(?i)\b(introduction|背景|概述)\b", name):
            intro = body
            break
    if not intro and p.abstract:
        intro = p.abstract

    if intro:
        # 取前几句
        first_para = intro.strip().split("\n\n")[0]
        problem = first_para.strip()
        motivation = "该工作旨在缓解/改进现有推荐检索阶段的瓶颈、冷启动与多样性等问题（由正文抽取），并以可生成的语义 ID 取代传统向量召回。"

    # 贡献
    contrib_patterns = [r"(?i)\bcontribution(s)?\b", r"我们(的)?主要(贡献|工作)"]
    contributions = _grep_items(all_text, contrib_patterns)
    if not contributions and p.abstract:
        contributions = [p.abstract.strip()[:280] + "…"]

    # 方法
    method_highlevel = "整体框架基于“生成式检索 + 语义 ID（多级量化）+ 序列到序列 Transformer”，以自回归方式预测下一交互项的语义代码。"
    method_patterns = [r"(?i)\bmethod(s)?\b", r"(?i)\bframework\b", r"(?i)\bRQ-?VAE\b", r"(?i)\bSemantic ID\b", r"(?i)\bT5|Transformer|decoder|encoder\b"]
    method_details = _grep_items(all_text, method_patterns)

    # 数据集/指标/实验/对比
    datasets = re.findall(r"(?i)Amazon.*?(Beauty|Sports and Outdoors|Toys and Games)", all_text)
    datasets = sorted(list(set(datasets)))
    metric_patterns = [r"(?i)\bRecall@?\d+\b", r"(?i)\bNDCG@?\d+\b", r"(?i)\bAUC\b", r"(?i)\bprecision\b"]
    metrics = _grep_items(all_text, metric_patterns)

    baseline_patterns = [r"(?i)\bGRU4Rec\b", r"(?i)\bSASRec\b", r"(?i)\bBERT4Rec\b", r"(?i)\bS3-?Rec\b", r"(?i)\bCaser\b", r"(?i)\bFDSA\b", r"(?i)\bP5\b"]
    baselines = [m.group(0) for pat in baseline_patterns for m in re.finditer(pat, all_text)]
    baselines = sorted(list(set(baselines)))

    exp_patterns = [r"(?i)\bexperiment(s)?\b", r"(?i)\bresults?\b", r"(?i)\bablation(s)?\b", r"(?i)\bcold[-\s]?start\b", r"(?i)\bdiversity\b"]
    experiments = _grep_items(all_text, exp_patterns)

    # 结果要点（从表格/结果段落近邻抽取）
    results_takeaways = []
    for name, body in p.sections:
        if re.search(r"(?i)\b(result|performance|实验结果|性能)\b", name):
            s = re.sub(r"\s+", " ", body).strip()
            results_takeaways.append(s[:400] + ("…" if len(s) > 400 else ""))
    if not results_takeaways and p.abstract:
        results_takeaways = [p.abstract.strip()[:300] + "…"]

    # 局限/风险/偏差
    limitations = []
    for name, body in p.sections:
        if re.search(r"(?i)\b(limitation|discussion|限制|不足)\b", name):
            limitations.append(re.sub(r"\s+", " ", body).strip()[:300] + "…")
    if not limitations:
        limitations = ["可能存在语义 ID 碰撞与无效 ID 的极小概率、对预训练内容编码器依赖、以及指标集中在三套 Amazon 基准上，外推性仍需验证。"]

    risks_bias = ["推荐系统的反馈回路与流行度偏置可能被放大，需要通过语义 ID 与采样策略缓解。"]

    # 消融
    ablations = []
    for name, body in p.sections:
        if re.search(r"(?i)\b(ablation|消融)\b", name):
            ablations.append(re.sub(r"\s+", " ", body).strip()[:300] + "…")

    # 术语表（精简）
    glossary = {
        "语义 ID (Semantic ID)": "由内容表征量化得到的多级离散码，语义相近的物品将共享前缀。",
        "RQ-VAE": "残差量化的变分自编码器，多级码本逐级量化潜变量，形成层次语义。",
        "生成式检索": "序列到序列模型自回归地产出目标的离散 ID（而非向量近邻检索）。",
        "TIGER": "Transformer Index for Generative Recommenders，本论文框架名。"
    }

    # 图片锚点建议：把“方法/实验/消融”类图片放入对应段落
    suggested_fig_anchors = {"方法原理": [], "实验与结果": [], "消融与讨论": []}
    for idx, fig in enumerate(p.figures):
        key = "方法原理" if re.search(r"(?i)overview|framework|RQ-?VAE|Semantic ID|TIGER", fig.alt + " " + fig.caption) else \
              "实验与结果" if re.search(r"(?i)result|performance|table|recall|ndcg|cold", fig.alt + " " + fig.caption) else \
              "消融与讨论"
        suggested_fig_anchors.setdefault(key, []).append(idx)

    return Analysis(
        problem=problem or "（自动摘要未能抽取到清晰问题陈述，可依赖 LLM 补全）",
        motivation=motivation,
        contributions=contributions or ["（未显式列出，建议参考摘要与引言补全）"],
        method_highlevel=method_highlevel,
        method_details=method_details,
        datasets=datasets or [],
        metrics=metrics or [],
        experiments=experiments or [],
        baselines=baselines or [],
        results_takeaways=results_takeaways or [],
        limitations=limitations,
        risks_bias=risks_bias,
        ablations=ablations or [],
        future_work=["将层次语义 ID 融入排序、多目标优化与跨域冷启动；设计前缀匹配容错的生成式检索解码器；评估在更大规模 corpus 上的效率-效果权衡。"],
        glossary=glossary,
        suggested_fig_anchors=suggested_fig_anchors
    )

# ----------------------------
# 3) 生成“深度解读 Prompt”（中文）
# ----------------------------

PROMPT_TMPL = """你是一名顶级学术评审与系统工程师。请基于下述论文 Markdown 内容，严格按“中文”输出一篇面向高级工程读者的【深度解读报告】。请做到：
- 先以一句话给出论文最核心洞见；随后按“背景/问题 → 方法框架 → 关键技术细节 → 实验设计与指标 → 结果&对比 → 消融 → 局限与风险 → 工程落地建议 → 未来方向”的结构分节撰写。
- 对“方法框架”请画出模块化要点列表；用公式或伪代码刻画关键环节（若原文给出）。
- 对“结果&对比”，请量化列出主要指标（例如 Recall@K, NDCG@K），并解读效应来源与统计显著性。
- 所有图示请引用【原文图片链接】，在合适段落以“图：描述（链接）”行内嵌入。
- 需要时可穿插要点清单与表格，但全文避免空洞总结。
- 语气专业简洁，避免套话。

【论文关键信息（解析器抽取）】
- 题目：{title}
- 作者：{authors}
- 摘要（摘录）：{abstract_excerpt}

【重要上下文（解析器分析）】
- 研究动机：{motivation}
- 主要贡献（候选）：{contribs}
- 高层方法框架：{method_hl}
- 关键技术片段（候选）：{method_details}
- 数据集：{datasets}
- 指标：{metrics}
- 典型对比基线：{baselines}
- 结果要点（候选）：{results}
- 局限/偏差：{limits}
- 消融（候选）：{ablations}
- 术语表：{glossary}

【原文图片（供内联引用）】
{figs}

请在写作中恰当引用这些图片链接（不要下载），并按上述结构输出中文深度解读报告。
"""

def build_deep_prompt(p: ParsedMD, a: Analysis) -> str:
    def fmt_list(xs, sep="；"):
        return sep.join(xs) if xs else "（未抽取）"
    def fmt_figs(figs: List[Figure]) -> str:
        lines = []
        for i, f in enumerate(figs):
            lines.append(f"- 图{i+1}：{f.alt or f.caption or '（无描述）'}  链接：{f.url}")
        return "\n".join(lines) if lines else "（未检测到图片）"
    abstract_excerpt = (p.abstract or "（未抽取摘要）").strip().replace("\n", " ")
    prompt = PROMPT_TMPL.format(
        title=p.title,
        authors="、".join(p.authors) if p.authors else "（未抽取）",
        abstract_excerpt=abstract_excerpt[:600] + ("…" if len(abstract_excerpt) > 600 else ""),
        motivation=a.motivation,
        contribs=fmt_list(a.contributions),
        method_hl=a.method_highlevel,
        method_details=fmt_list(a.method_details),
        datasets=fmt_list(a.datasets, sep="，"),
        metrics=fmt_list(a.metrics, sep="，"),
        baselines=fmt_list(a.baselines, sep="，"),
        results=fmt_list(a.results_takeaways),
        limits=fmt_list(a.limitations),
        ablations=fmt_list(a.ablations),
        glossary=json.dumps(a.glossary, ensure_ascii=False, indent=2),
        figs=fmt_figs(p.figures)
    )
    return prompt

# ----------------------------
# 4) 可选 Web 检索增补（轻量实现，可替换）
# ----------------------------

def duckduckgo_search(query: str, max_results: int = 5, timeout: int = 12) -> List[Dict]:
    """极简 DuckDuckGo HTML 解析（无需 API Key）。如需工业级，请替换为自有检索模块。"""
    url = "https://duckduckgo.com/html"
    try:
        r = requests.post(url, data={"q": query}, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html5lib")
        items = []
        for a in soup.select(".result__a")[:max_results]:
            href = a.get("href", "")
            title = a.get_text(" ", strip=True)
            snippet_tag = a.find_parent("div", class_="result__body").select_one(".result__snippet")
            snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
            items.append({"title": title, "link": href, "snippet": snippet})
        return items
    except Exception as e:
        return []

def build_web_evidence(p: ParsedMD, a: Analysis, max_each: int = 3) -> Dict[str, List[Dict]]:
    queries = []
    # 场景化检索词
    queries.append(f"{p.title} paper TIGER generative retrieval Semantic ID")
    queries.append("RQ-VAE residual quantization recommender system")
    if a.baselines:
        queries.append(" ".join(a.baselines[:4]) + " sequential recommendation benchmarks")
    evidence = {}
    for q in queries:
        evidence[q] = duckduckgo_search(q, max_results=max_each)
    return evidence

# ----------------------------
# 5) 生成中文图文报告（Markdown）
# ----------------------------

def render_markdown_report(p: ParsedMD, a: Analysis, deep_prompt: str,
                           web_evi: Optional[Dict[str, List[Dict]]] = None) -> str:
    def fig_block(indices: List[int]) -> str:
        if not indices: return ""
        lines = []
        for i in indices:
            if 0 <= i < len(p.figures):
                f = p.figures[i]
                lines.append(f"图：{f.alt or f.caption or '（无描述）'}（{f.url}）")
        return "\n".join(lines)

    # 首图优先插入“方法原理”建议图
    method_figs = a.suggested_fig_anchors.get("方法原理", [])
    exp_figs = a.suggested_fig_anchors.get("实验与结果", [])
    abl_figs = a.suggested_fig_anchors.get("消融与讨论", [])

    # Web 证据块
    web_md = ""
    if web_evi:
        web_md = "\n\n### 相关资料与外部证据（精选）\n"
        for q, items in web_evi.items():
            if not items: continue
            web_md += f"\n- **检索式**：`{q}`\n"
            for it in items:
                web_md += f"  - [{it['title']}]({it['link']}) — {it['snippet']}\n"

    # 报告 Markdown
    md_lines = []
    md_lines.append(f"# {p.title} — 深度解读报告")
    md_lines.append("")
    md_lines.append(f"**作者**：{'、'.join(p.authors) if p.authors else '（未抽取）'}")
    md_lines.append(f"**摘要**：{p.abstract.strip() if p.abstract else '（未抽取）'}")
    md_lines.append("")
    if method_figs:
        md_lines.append(fig_block(method_figs[:2]))
        md_lines.append("")

    # 一句话洞见
    md_lines.append("## 一句话洞见")
    md_lines.append("以“语义 ID + 生成式检索”替代传统向量召回，使推荐检索可**直接自回归预测候选**，兼顾**冷启动泛化**与**多样性可控**。")

    # 背景/问题
    md_lines.append("\n## 背景与问题")
    md_lines.append(a.problem or a.motivation)

    # 方法框架
    md_lines.append("\n## 方法框架（模块化）")
    md_lines.append(a.method_highlevel)
    if a.method_details:
        md_lines.append("\n**关键技术片段（候选抽取）**：")
        for it in a.method_details[:8]:
            md_lines.append(f"- {it}")

    if method_figs:
        md_lines.append("\n**方法相关图示**：")
        md_lines.append(fig_block(method_figs))

    # 实验与指标
    md_lines.append("\n## 实验设计与指标")
    md_lines.append(f"- **数据集**：{('、'.join(a.datasets)) if a.datasets else '（未显式抽取）'}")
    md_lines.append(f"- **指标**：{('、'.join([re.sub(r'\\s+', ' ', x) for x in a.metrics])) if a.metrics else 'Recall@K, NDCG@K 等'}")
    if exp_figs:
        md_lines.append("\n**实验相关图表**：")
        md_lines.append(fig_block(exp_figs))

    # 结果与对比
    md_lines.append("\n## 结果与对比（要点）")
    for it in a.results_takeaways[:6]:
        md_lines.append(f"- {it}")
    if a.baselines:
        md_lines.append(f"\n**对比基线**：{', '.join(a.baselines)}")

    # 消融
    md_lines.append("\n## 消融与机制洞察")
    if a.ablations:
        for it in a.ablations[:5]:
            md_lines.append(f"- {it}")
    else:
        md_lines.append("- 原文包含层数、用户 token、量化方式等消融，可据表格复现。")
    if abl_figs:
        md_lines.append("\n**消融相关图表**：")
        md_lines.append(fig_block(abl_figs))

    # 局限与风险
    md_lines.append("\n## 局限与风险")
    for it in a.limitations:
        md_lines.append(f"- {it}")
    for it in a.risks_bias:
        md_lines.append(f"- {it}")

    # 工程落地建议
    md_lines.append("\n## 工程落地建议")
    md_lines.append("- 以内容编码器（如 Sentence-T5）抽取语义表征，采用 RQ-VAE 学得多级码本，生成前缀共享的语义 ID。")
    md_lines.append("- 推断阶段使用 Seq2Seq 解码预测语义 ID，必要时做**前缀容错/近邻补全**，过滤无效 ID。")
    md_lines.append("- 对**冷启动**：允许一定比例 unseen items 的前缀匹配召回；对**多样性**：用温度采样控制不同层级 token。")
    md_lines.append("- 监控**无效 ID 率**、**码本使用率**与**召回/排序耦合**的系统指标。")

    # 未来方向
    md_lines.append("\n## 未来方向")
    for it in a.future_work:
        md_lines.append(f"- {it}")

    # 术语表
    md_lines.append("\n## 术语表")
    for k, v in a.glossary.items():
        md_lines.append(f"- **{k}**：{v}")

    # 外部证据
    md_lines.append(web_md)

    # Prompt 附录
    md_lines.append("\n---\n### 附录：自动生成的深度解读 Prompt（可投喂 LLM）\n")
    md_lines.append("```\n" + deep_prompt + "\n```")

    return "\n".join(md_lines)

# ----------------------------
# 6) 对外主函数
# ----------------------------

def generate_deep_report(
    md_path: str,
    use_web: bool = False,
    custom_search: Optional[Callable[[str, int], List[Dict]]] = None
) -> Dict[str, str]:
    """
    输入：
      md_path: 论文 Markdown 路径（需包含正文与原图链接）
      use_web: 是否启用内置 DuckDuckGo 轻量检索
      custom_search: 可选，自定义检索函数 (query, max_results)->List[Dict]
    返回：
      {"prompt": ..., "report_markdown": ...}
    """
    parsed = parse_markdown(md_path)
    analysis = analyze_structure(parsed)
    prompt = build_deep_prompt(parsed, analysis)

    web_evi = None
    if use_web:
        if custom_search:
            # 用外部检索器
            web_evi = {}
            for q in [parsed.title, "RQ-VAE recommender", "generative retrieval recommendation"]:
                web_evi[q] = custom_search(q, 5)
        else:
            web_evi = build_web_evidence(parsed, analysis)

    report_md = render_markdown_report(parsed, analysis, prompt, web_evi)
    return {"prompt": prompt, "report_markdown": report_md}

# ----------------------------
# 7) CLI
# ----------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("md_path", type=str, help="论文 Markdown 文件路径")
    parser.add_argument("--out", type=str, default="", help="输出报告 Markdown 路径")
    parser.add_argument("--with-web", action="store_true", help="启用轻量 Web 检索")
    args = parser.parse_args()

    out = generate_deep_report(args.md_path, use_web=args.with_web)
    out_path = args.out or (os.path.splitext(args.md_path)[0] + "_deep_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out["report_markdown"])
    # 另存一份 prompt 便于调用大模型
    with open(os.path.splitext(out_path)[0] + "_prompt.txt", "w", encoding="utf-8") as f:
        f.write(out["prompt"])
    print(f"[OK] 已输出报告：{out_path}")
    print(f"[OK] 已输出 Prompt：{os.path.splitext(out_path)[0]}_prompt.txt")

if __name__ == "__main__":
    main()
