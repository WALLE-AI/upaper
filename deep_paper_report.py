# -*- coding: utf-8 -*-
"""
paper_deep_reader.py

功能：
1) 解析 Markdown 学术论文（含图片链接），抽取题目、作者、摘要、章节大纲与图片清单
2) **自适应 Prompt**：根据论文研究属性（综述/方法/系统/理论/数据集/效率/消融/领域）动态生成深度解读 Prompt
3) 可选：接入大模型（GPT-5/OpenAI、Gemini、豆包）与 WebSearch，直接生成**中文图文深度报告**
4) 严格复用源 MD 的图片 URL，在“方法/实验”小节就地内联；若模型未插图则自动补图
"""

import os, re, json, argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple
from datetime import datetime

try:
    import requests
except Exception:
    requests = None

HEADING_RE = re.compile(r'^(#{1,6})\s*(.+?)\s*$', re.MULTILINE)
IMAGE_RE   = re.compile(r'!\[(.*?)\]\((.*?)\)')

@dataclass
class PaperImage:
    alt: str
    url: str
    context_heading: Optional[str] = None

@dataclass
class PaperSection:
    level: int
    title: str
    start: int
    end: int
    text: str
    images: List[PaperImage] = field(default_factory=list)

@dataclass
class ParsedPaper:
    title: str
    authors: List[str]
    abstract: str
    sections: List[PaperSection]
    images: List[PaperImage]
    raw_text: str

def _extract_title(md: str) -> str:
    m = re.search(r'^\#\s+(.+)$', md, re.MULTILINE)
    if m: return m.group(1).strip()
    for line in md.splitlines():
        if line.strip(): return line.strip()
    return "未命名论文"

def _extract_authors(md: str) -> List[str]:
    lines = md.splitlines()
    authors = []
    title_idx = None
    for i, line in enumerate(lines[:50]):
        if line.startswith("# "):
            title_idx = i; break
    if title_idx is None: title_idx = 0
    window = lines[title_idx+1:min(title_idx+8, len(lines))]
    for w in window:
        lw = w.strip()
        if not lw: continue
        if any(k in lw.lower() for k in ["university", "google", "meta", "deepmind", "lab", "department", "@"]):
            parts = re.split(r',|;|\band\b|\&', lw)
            for p in parts:
                p = p.strip().strip("*")
                if p and len(p.split()) <= 8 and not p.lower().startswith(("abstract", "figure", "table")):
                    authors.append(p)
    authors_clean = []
    for a in authors:
        a = re.sub(r'\s+', ' ', a)
        if a not in authors_clean:
            authors_clean.append(a)
    return authors_clean[:12]

def _extract_abstract(md: str) -> str:
    abs_pat = re.compile(r'^\s*#*\s*(Abstract|摘要)\s*\n+(.+?)(?:\n\s*#{1,6}\s|\Z)', re.IGNORECASE|re.DOTALL|re.MULTILINE)
    m = abs_pat.search(md)
    if m: return m.group(2).strip()
    txt = md.strip()
    first_para = re.split(r'\n\s*\n', txt, maxsplit=1)[0]
    return first_para.strip()

def _slice_sections(md: str) -> List[PaperSection]:
    sections: List[PaperSection] = []
    headings = [(m.start(), m.end(), len(m.group(1)), m.group(2).strip()) for m in HEADING_RE.finditer(md)]
    if not headings:
        imgs = [PaperImage(alt=a, url=u, context_heading=None) for a,u in IMAGE_RE.findall(md)]
        return [PaperSection(level=1, title="全文", start=0, end=len(md), text=md, images=imgs)]
    for i, (s, e, lvl, title) in enumerate(headings):
        start = e
        end = headings[i+1][0] if i+1 < len(headings) else len(md)
        block = md[start:end]
        imgs = []
        for a,u in IMAGE_RE.findall(block):
            imgs.append(PaperImage(alt=a, url=u, context_heading=title))
        sections.append(PaperSection(level=lvl, title=title, start=start, end=end, text=block.strip(), images=imgs))
    return sections

def parse_markdown(md_text: str) -> ParsedPaper:
    title = _extract_title(md_text)
    authors = _extract_authors(md_text)
    abstract = _extract_abstract(md_text)
    sections = _slice_sections(md_text)
    images = []
    for s in sections: images.extend(s.images)
    return ParsedPaper(title=title, authors=authors, abstract=abstract, sections=sections, images=images, raw_text=md_text)

# -------- 自适应属性检测 --------
def detect_attrs(md: str) -> Dict[str, bool]:
    low = md.lower()
    flags = {
        "is_survey": any(k in low for k in ["survey", "综述", "review of", "a review"]),
        "is_dataset": any(k in low for k in ["dataset", "数据集", "benchmark", "基准", "leaderboard"]),
        "is_system": any(k in low for k in ["system", "framework", "pipeline", "platform", "engine"]),
        "is_method": any(k in low for k in ["we propose", "we present", "提出一种", "提出了", "方法", "approach"]),
        "is_theory": any(k in low for k in ["theorem", "lemma", "proof", "证明", "bound", "上界", "下界"]),
        "has_code": any(k in low for k in ["code", "github.com", "implementation", "开源代码"]),
        "has_math": bool(re.search(r'(\$[^$]+\$|\$\$[\s\S]+?\$\$|\\begin\{equation\})', md)),
        "has_algo": any(k in low for k in ["algorithm", "伪代码", "pseudo-code", "pseudocode"]),
        "has_ablation": ("ablation" in low) or ("消融" in low),
        "has_user_study": ("user study" in low) or ("用户研究" in low),
        "is_multimodal": any(k in low for k in ["multimodal", "multi-modal", "vision-language", "ocr", "speech", "audio", "image", "图文", "语音", "视觉"]),
        "has_safety": any(k in low for k in ["safety", "bias", "安全", "偏见", "ethic", "伦理"]),
        "has_eval": any(k in low for k in ["evaluation", "experiment", "results", "实验", "评测"]),
        "has_efficiency": any(k in low for k in ["latency", "throughput", "efficien", "效率", "显存", "memory", "复杂度", "complexity", "o("]),
        "has_data_recipe": any(k in low for k in ["data collection", "数据收集", "curation", "标注", "annotation"]),
        "domain_bridge": any(k in low for k in ["bridge", "桥梁", "结构健康监测", "structural health"]),
    }
    # counts
    flags["fig_count"] = len(re.findall(r'!\[[^\]]*\]\([^)]+\)', md))
    flags["tbl_count"] = len(re.findall(r'^\s*\|', md, flags=re.MULTILINE))
    return flags

# -------- Prompt 生成（自适应） --------
def extract_outline(sections: List[PaperSection], max_items=18) -> str:
    rows = []
    for s in sections:
        rows.append(f"- [{'#'*s.level} {s.title} {s.text}]")
    return "\n".join(rows) if rows else "（未检测到章节标题）"

def build_image_inventory(images: List[PaperImage], max_items:int=30) -> str:
    rows = []
    for i, im in enumerate(images[:max_items], 1):
        rows.append(f"{i}. ({im.context_heading or '全文'}) {im.alt or 'figure'} → {im.url}")
    return "\n".join(rows) if rows else "（源文未检测到图片链接）"

def generate_adaptive_prompt(parsed: ParsedPaper) -> str:
    attrs = detect_attrs(parsed.raw_text)
    outline = extract_outline(parsed.sections)
    images  = build_image_inventory(parsed.images)

    sections = ["1. 论文速览（1 句问题定义 + 3 句贡献）"]
    if attrs["is_survey"]:
        sections += [
            "2. 综述脉络与分类标准（时间线/任务线/方法线）",
            "3. 代表性方法纵览（按分类，每类 3–5 篇，对比优缺点与适用场景）",
            "4. 评测与结论一致性复核（不同实验设置的稳定性/争议点/复现记录）"
        ]
    else:
        sections += [
            "2. 背景与相关工作定位（对比 3–5 篇最相关研究）",
            "3. 方法总览（系统图/数据流/符号表；内联源图链接）",
        ]
        if attrs["is_theory"] or attrs["has_math"]:
            sections.append("4. 关键理论与推导（定理/假设/证明直觉；复杂度或收敛性）")
        else:
            sections.append("4. 关键技术细节（模块/损失/复杂度/训练细节/消融假设）")

    if attrs["has_eval"]:
        sections.append("5. 实验与结果复核（数据集/指标/SOTA/统计显著性；结论与边界）")
    if attrs["has_ablation"]:
        sections.append("6. 消融与误差分析（失败类型与成因；可改进方向）")
    else:
        sections.append("6. 误差分析与失败案例（为何失败、失败分布、可视化）")

    if attrs["is_dataset"] or attrs["has_data_recipe"]:
        sections.append("7. 数据/基准构建与清洗（采集→标注→质控→隐私合规；分层划分与泄漏排查）")
    else:
        sections.append("7. 可复现清单（环境/数据/脚本/关键超参/评测命令）")

    if attrs["has_efficiency"] or attrs["is_system"]:
        sections.append("8. 工程效率与资源占用（延迟/吞吐/显存；推理加速与代价）")
    else:
        sections.append("8. 局限与风险（学术/伦理/合规/部署）")

    if attrs["domain_bridge"]:
        sections.append("9. 产业与应用建议（桥梁/结构健康监测落地清单：数据采集→上线监控→回滚策略）")
    else:
        sections.append("9. 产业与应用建议（可落地场景、投入产出、监控与回滚策略）")

    sections += [
        "10. 术语对照表（EN→ZH 简释）",
        "11. 值得继续追问的 10 个高质量问题"
    ]

    layout = ["- 公式：Markdown+KaTeX；复杂推导给直觉解释"]
    if attrs["fig_count"] >= 3:
        layout.append("- 图片：仅使用源 URL，在“方法/实验”小节就地内联，图题含关键信息点")
    if attrs["tbl_count"] >= 1:
        layout.append("- 表格：SOTA/消融用 Markdown 表格；统一指标与小数位数")
    if attrs["has_algo"]:
        layout.append("- 若原文有伪代码：转写为更清晰的伪代码块并配注释")

    prompt = f"""你是一名资深学术研究员与技术评审专家。请对下面论文做“深度解读”，输出**中文图文报告**（严格复用源 MD 的图片链接）。

【标题】{parsed.title}
【作者】{"；".join(parsed.authors) if parsed.authors else "（未解析到作者）"}
【摘要】{parsed.abstract}

【原文结构（截断展示）】
{outline}

【图片清单（来自源 MD）】
{images}

【必须包含的章节】
""" + "\n".join(sections) + """

【图文排版】
""" + "\n".join(layout) + """

【自适应策略】
- 若检测到“理论/证明/复杂度”信号，优先给出定理与证明直觉，再回到工程可复现要点。
- 若检测到“数据集/基准”，补充数据治理、泄漏风险、评测稳健性与复现实证。
- 若检测到“系统/效率”，量化延迟/吞吐/显存曲线，并给出可复用的优化配方（如张量并行/显存优化/裁剪蒸馏）。
- 若为“综述”，产出分类法、代表性工作对照矩阵与研究空白图谱。
- 若与“桥梁/结构健康监测”等垂域相关，将方法映射到该域的业务指标与监管要求。
"""
    return prompt

# ------- WebSearch -------
def websearch(query: str, provider: str = "bing", topk: int = 5) -> List[Tuple[str,str,str]]:
    out: List[Tuple[str,str,str]] = []
    try:
        if provider == "bing":
            key = os.environ.get("BING_SEARCH_KEY")
            if not key or not requests: return []
            endpoint = "https://api.bing.microsoft.com/v7.0/search"
            r = requests.get(endpoint, params={"q": query, "count": topk, "mkt":"en-US"}, headers={"Ocp-Apim-Subscription-Key": key}, timeout=20)
            r.raise_for_status()
            j = r.json()
            for it in j.get("webPages", {}).get("value", []):
                out.append((it.get("name",""), it.get("url",""), it.get("snippet","")))
        elif provider == "serpapi":
            key = os.environ.get("SERPAPI_KEY")
            if not key or not requests: return []
            r = requests.get("https://serpapi.com/search.json", params={"engine":"google","q":query,"api_key":key}, timeout=20)
            r.raise_for_status()
            j = r.json()
            for it in j.get("organic_results", [])[:topk]:
                out.append((it.get("title",""), it.get("link",""), it.get("snippet","")))
    except Exception:
        return []
    return out[:topk]

def weave_web_results_to_prompt(prompt: str, topics: List[str], provider: str) -> str:
    lines = []
    for q in topics:
        items = websearch(q, provider=provider, topk=5)
        if not items: 
            continue
        lines.append(f"- 主题：{q}")
        for (t,u,s) in items:
            lines.append(f"  - [{t}]({u}) — {s}")
    if not lines:
        return prompt
    return prompt + "\n\n【WebSearch 增强材料】\n" + "\n".join(lines)

# ------- LLM -------
class LLMAdapter:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

class OpenAIAdapter(LLMAdapter):
    def __init__(self, model: str = "gpt-5.0-instruct", base_url: Optional[str]=None):
        self.model = "Qwen3-30B-A3B-Instruct-2507"
        self.base_url = base_url or os.environ.get("LOCAL_QWEN3_INSTRUCT_BASE", "https://api.openai.com/v1")
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def generate(self, prompt: str) -> str:
        if not requests:
            return "【占位】requests 未安装，无法直接联网调用。请复制 prompt 到你的模型中运行。"
        if not self.api_key:
            return "【占位】未提供 OPENAI_API_KEY。请复制 prompt 到你的模型中运行。"
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type":"application/json"}
            data = {
                "model": self.model,
                "messages": [
                    {"role":"system","content":"You are a meticulous Chinese academic reviewer who writes structured Markdown and keeps image links intact."},
                    {"role":"user","content": prompt}
                ],
                "temperature": 0.3
            }
            resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data, timeout=120)
            resp.raise_for_status()
            j = resp.json()
            return j["choices"][0]["message"]["content"]
        except Exception as e:
            return f"【占位】OpenAI 调用失败：{e}\n请复制 prompt 手动到模型中生成。"

class GeminiAdapter(LLMAdapter):
    def __init__(self, model: str = "gemini-2.0-pro"):
        self.model = model
        self.api_key = os.environ.get("GEMINI_API_KEY")

    def generate(self, prompt: str) -> str:
        if not requests:
            return "【占位】requests 未安装，无法直接联网调用。"
        if not self.api_key:
            return "【占位】未提供 GEMINI_API_KEY。"
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            data = {"contents":[{"parts":[{"text": prompt}]}]}
            resp = requests.post(url, json=data, timeout=120)
            resp.raise_for_status()
            j = resp.json()
            return j["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return f"【占位】Gemini 调用失败：{e}"

class DoubaoAdapter(LLMAdapter):
    def __init__(self, model: str = "ep-20240601-doubao-pro"):
        self.model = model
        self.api_key = os.environ.get("DOUBAO_API_KEY")
        self.base_url = os.environ.get("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

    def generate(self, prompt: str) -> str:
        if not requests:
            return "【占位】requests 未安装，无法直接联网调用。"
        if not self.api_key:
            return "【占位】未提供 DOUBAO_API_KEY。"
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type":"application/json"}
            data = {"model": self.model, "messages": [{"role":"user","content":prompt}], "temperature":0.3}
            resp = requests.post(url, json=data, headers=headers, timeout=120)
            resp.raise_for_status()
            j = resp.json()
            if "choices" in j and j["choices"]:
                msg = j["choices"][0].get("message", {}).get("content") or j["choices"][0].get("text","")
                return msg or "（空响应）"
            return json.dumps(j, ensure_ascii=False)
        except Exception as e:
            return f"【占位】豆包调用失败：{e}"

def pick_adapter(model_name: str) -> Optional[LLMAdapter]:
    m = (model_name or "none").lower()
    if m.startswith("gpt"): return OpenAIAdapter()
    if "gemini" in m: return GeminiAdapter()
    if "doubao" in m or "byte" in m: return DoubaoAdapter()
    return None

# ------- 图片注入 -------
def choose_images_by_keyword(images: List[PaperImage], keywords: List[str], max_count:int=4) -> List[str]:
    picked = []
    for kw in keywords:
        for im in images:
            ctx = (im.context_heading or "").lower() + " " + (im.alt or "").lower()
            if kw in ctx and im.url not in picked:
                picked.append(im.url)
                if len(picked) >= max_count: return picked
    if not picked:
        for im in images[:max_count]: picked.append(im.url)
    return picked

def render_img_md(urls: List[str]) -> str:
    if not urls: return "（无）"
    return "\n".join([f"![]({u})" for u in urls])

REPORT_SKELETON_TMPL = """# {title} — 深度解读

> 生成时间：{ts}

## 1. 论文速览
（占位）一句话问题定义；三句话贡献。

## 2. 背景与相关工作定位
（占位）对比近 3 年 3–5 篇相关研究。

## 3. 方法总览
（占位）系统图/数据流/符号表。若原文有图，内联如下：
{method_imgs}

## 4. 关键技术细节
（占位）核心模块、损失、复杂度、训练细节、消融假设。

## 5. 实验与结果复核
（占位）数据集、指标、SOTA 对比、统计显著性；结论与边界。
{exp_imgs}

## 6. 误差分析与失败案例
（占位）失败类型与可能原因。

## 7. 可复现清单
（占位）环境/数据/脚本/关键超参/评测指令。

## 8. 局限性与潜在风险
（占位）学术/伦理/合规/部署。

## 9. 产业与应用建议
（占位）可落地场景、投入产出、监控与回滚策略。

## 10. 关键术语对照表
| 英文 | 中文 | 说明 |
|---|---|---|
|  |  |  |

## 11. 值得继续追问的 10 个高质量问题
1. （占位）
2. …

---

### 附：原文图片参考（自动收集）
{all_imgs}
"""

def build_report_skeleton(parsed: ParsedPaper) -> str:
    method_imgs = render_img_md(choose_images_by_keyword(parsed.images, ["overview","method","architecture","framework","模型","方法"]))
    exp_imgs    = render_img_md(choose_images_by_keyword(parsed.images, ["experiment","results","ablation","消融","性能","实验"]))
    all_imgs    = render_img_md([im.url for im in parsed.images[:20]])
    return REPORT_SKELETON_TMPL.format(
        title=parsed.title,
        ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
        method_imgs=method_imgs,
        exp_imgs=exp_imgs,
        all_imgs=all_imgs
    )

def inject_images_into_sections(markdown_text: str, parsed: ParsedPaper) -> str:
    needles = {
        "方法": choose_images_by_keyword(parsed.images, ["overview","method","architecture","framework","模型","方法"], 3),
        "实验": choose_images_by_keyword(parsed.images, ["experiment","results","ablation","消融","性能","实验"], 3),
    }
    out = markdown_text
    for key, urls in needles.items():
        if not urls: continue
        pat = re.compile(rf'(^##\s*[^\n]*{key}[^\n]*\n)', re.MULTILINE)
        if not pat.search(out):
            out = f"{render_img_md(urls)}\n\n" + out
        else:
            out = pat.sub(lambda m: m.group(1) + render_img_md(urls) + "\n\n", out, count=1)
    return out

# ------- 主流程 -------
def run(md_path: str, out_dir: str, model: str="none", use_websearch: bool=False, search_provider: str="bing", adaptive: bool=True) -> Dict[str,str]:
    os.makedirs(out_dir, exist_ok=True)
    with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
        md = f.read()

    parsed = parse_markdown(md)
    if adaptive:
        prompt = generate_adaptive_prompt(parsed)
        prompt_name = "prompt_adaptive_zh.txt"
    else:
        # 简化版固定 Prompt（少用）
        outline = "\n".join([f"- [{'#'*s.level} {s.title}]" for s in parsed.sections]) or "（未检测到章节标题）"
        images  = build_image_inventory(parsed.images)
        prompt = f"""你是一名资深学术研究员与技术评审专家。请对下面论文做“深度解读”，输出**中文图文报告**（严格复用源 MD 的图片链接）。

【标题】{parsed.title}
【作者】{"；".join(parsed.authors) if parsed.authors else "（未解析到作者）"}
【摘要】{parsed.abstract}

【原文结构（截断展示）】
{outline}

【图片清单（来自源 MD）】
{images}
"""
        prompt_name = "prompt_zh.txt"

    # WebSearch 增强（可选）
    if use_websearch:
        topics = [
            f"{parsed.title} 复现",
            "related work 2023..2025",
            "ablation study methodology for this topic"
        ]
        prompt = weave_web_results_to_prompt(prompt, topics, provider=search_provider)

    # 保存 prompt
    prompt_path = os.path.join(out_dir, prompt_name)
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    # 调用模型或输出骨架
    report_path = os.path.join(out_dir, "report_zh.md")
    adapter = pick_adapter(model)
    if adapter is None:
        content = build_report_skeleton(parsed)
    else:
        llm_md = adapter.generate(prompt)
        content = llm_md if llm_md and llm_md.strip() else build_report_skeleton(parsed)
        content = inject_images_into_sections(content, parsed)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 另存解析结构
    meta_path = os.path.join(out_dir, "parsed_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "title": parsed.title,
            "authors": parsed.authors,
            "abstract": parsed.abstract[:1000],
            "sections": [{"level": s.level, "title": s.title, "len": len(s.text), "images": [im.url for im in s.images]} for s in parsed.sections],
            "images": [{"alt": im.alt, "url": im.url, "ctx": im.context_heading} for im in parsed.images]
        }, f, ensure_ascii=False, indent=2)

    return {"prompt_path": prompt_path, "report_path": report_path, "meta_path": meta_path}

if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--md", required=True, help="论文 MD 路径")
    # parser.add_argument("--out_dir", required=True, help="输出目录")
    # parser.add_argument("--model", default="none", help="gpt5 / gemini / doubao / none")
    # parser.add_argument("--use_websearch", default="false", choices=["true","false"])
    # parser.add_argument("--search_provider", default="bing", choices=["bing","serpapi"])
    # parser.add_argument("--adaptive", default="true", choices=["true","false"], help="是否使用自适应 Prompt")
    # args = parser.parse_args()
    md_path = "hf_papers/2305.03043/2305.03043.md"
    with_web = False
    md_out = "hf_papers/2305.03043/2305.03043_report.md"
    res = run(md_path, md_out, "gpt", False, "sdsds",True)
    # res = run(args.md, args.out_dir, args.model, args.use_websearch.lower()=="true", args.search_provider, args.adaptive.lower()=="true")
    print(json.dumps(res, ensure_ascii=False, indent=2))
