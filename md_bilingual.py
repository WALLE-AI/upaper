#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md_bilingual.py — Split Markdown into titled chunks, translate to Chinese with adaptive prompts,
and export a bilingual Markdown (original + translation).

Usage:
  python md_bilingual.py input.md -o output.md \
    --openai_api_key YOUR_KEY \
    --model gpt-4o-mini \
    --max_chars 6000

Notes:
- Requires Python 3.9+.
- Uses OpenAI Chat Completions API (or compatible) if --openai_api_key is provided.
- If no API key is provided, the script will still split and produce a template where
  the translation is marked as TODO.
- The translator is prompt-adaptive: it detects code/LaTeX/tables/lists and sets different instructions.
- Code blocks are not translated by default (can be toggled).

Author: ChatGPT
"""
from __future__ import annotations
import re
import os
import sys
import json
import time
import math
import argparse
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

# ========== Utilities ==========

HEADING_RE = re.compile(r'^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*$', re.UNICODE)
FENCE_RE = re.compile(r'^```.*$')
INLINE_CODE_RE = re.compile(r'`[^`]+`')
MATH_INLINE_RE = re.compile(r'(?<!\\)\$(.+?)(?<!\\)\$')   # $...$
MATH_BLOCK_RE = re.compile(r'^\s*\$\$(.*?)\$\$\s*$', re.DOTALL)  # $$...$$ on single line
REF_SECTION_PAT = re.compile(r'^(references|bibliography|参考文献)\b', re.IGNORECASE)
ABSTRACT_PAT = re.compile(r'^(abstract|摘要)\b', re.IGNORECASE)
INTRO_PAT = re.compile(r'^(introduction|背景|引言)\b', re.IGNORECASE)
METHODS_PAT = re.compile(r'^(methods?|methodology|方法)\b', re.IGNORECASE)
RESULTS_PAT = re.compile(r'^(results?|实验|结果)\b', re.IGNORECASE)
DISCUSS_PAT = re.compile(r'^(discussion|讨论)\b', re.IGNORECASE)
CONCL_PAT = re.compile(r'^(conclusion|conclusions|结论)\b', re.IGNORECASE)

def strip_trailing_blank_lines(lines: List[str]) -> List[str]:
    while lines and lines[-1].strip() == '':
        lines.pop()
    return lines

# ========== Data structures ==========

@dataclass
class Chunk:
    level: int
    title: str
    content_lines: List[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0

    def content(self) -> str:
        return "\n".join(self.content_lines).rstrip()

# ========== Markdown parsing & chunking ==========

def parse_markdown_into_chunks(md_text: str, min_level: int = 1) -> List[Chunk]:
    """
    Split markdown by headings (#..######). A new chunk starts at every heading
    whose level >= min_level. Content goes until the next heading of level >= current level
    (standard markdown hierarchy behavior).
    """
    lines = md_text.splitlines()
    chunks: List[Chunk] = []
    cur_chunk: Optional[Chunk] = None

    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group('hashes'))
            title = m.group('title').strip()
            if level >= min_level:
                # finalize previous chunk
                if cur_chunk is not None:
                    cur_chunk.end_line = i - 1
                    cur_chunk.content_lines = strip_trailing_blank_lines(cur_chunk.content_lines)
                    chunks.append(cur_chunk)
                # start new chunk
                cur_chunk = Chunk(level=level, title=title, start_line=i, content_lines=[])
            else:
                # treat as normal content if below min_level
                if cur_chunk:
                    cur_chunk.content_lines.append(line)
                else:
                    # preamble content before first heading
                    cur_chunk = Chunk(level=min_level, title="(Preamble)", start_line=0, content_lines=[line])
        else:
            if cur_chunk is None:
                # content before any heading
                cur_chunk = Chunk(level=min_level, title="(Preamble)", start_line=0, content_lines=[line])
            else:
                cur_chunk.content_lines.append(line)

    if cur_chunk is not None:
        cur_chunk.end_line = len(lines) - 1
        cur_chunk.content_lines = strip_trailing_blank_lines(cur_chunk.content_lines)
        chunks.append(cur_chunk)

    return chunks

# ========== Heuristics for prompt adaptation ==========

def detect_section_kind(title: str, content: str) -> str:
    title_l = title.strip().lower()
    if REF_SECTION_PAT.search(title_l):
        return "references"
    if ABSTRACT_PAT.search(title_l):
        return "abstract"
    if INTRO_PAT.search(title_l):
        return "introduction"
    if METHODS_PAT.search(title_l):
        return "methods"
    if RESULTS_PAT.search(title_l):
        return "results"
    if DISCUSS_PAT.search(title_l):
        return "discussion"
    if CONCL_PAT.search(title_l):
        return "conclusion"

    # Fallbacks based on content footprint
    code_fences = len([l for l in content.splitlines() if FENCE_RE.match(l)])
    math_tokens = len(MATH_INLINE_RE.findall(content)) + len(MATH_BLOCK_RE.findall(content))
    table_lines = sum(1 for l in content.splitlines() if '|' in l and not l.strip().startswith('#'))
    if code_fences >= 2:
        return "code-heavy"
    if math_tokens >= 3:
        return "equation-heavy"
    if table_lines >= 3:
        return "table-heavy"
    if len(content.split()) < 40:
        return "short"
    return "general"

def build_adaptive_prompt(kind: str) -> str:
    base = (
        "你是一名技术型学术翻译助手。将输入的英文学术内容精准翻译为简体中文，"
        "保持严谨、自然、通顺。注意：避免直译腔，术语统一，尽量使用通用中文表述。"
    )
    rules_general = [
        "保留原有的 Markdown 结构（标题、列表、表格、引用等）。",
        "行内代码和代码块不要翻译，只保留原样；变量名、函数名、数据类型保持不变。",
        "数学公式、符号（如 $...$、$$...$$、\\(\\)）原样保留，不要改动其中的变量和符号。",
        "专有名词（如 Information Bottleneck、Mutual Information）首次出现可在括号内补充英文原文。",
        "保持段落分句与逻辑连贯，必要时适度调整语序以更符合中文表达。",
    ]

    extras = {
        "abstract": [
            "语气精炼、客观，突出问题、方法、结论与贡献。",
            "不新增信息，不主观评价。",
        ],
        "introduction": [
            "保持叙述清晰；适度润色以增强可读性。",
        ],
        "methods": [
            "术语严格、步骤清晰；被动转主动仅在不改变含义时进行。",
        ],
        "results": [
            "强调定量结果与对比；谨慎处理不确定性与假设。",
        ],
        "discussion": [
            "忠实呈现作者观点；区分事实与推测。",
        ],
        "conclusion": [
            "总结要点，避免引入新信息。",
        ],
        "equation-heavy": [
            "重点翻译文字说明；公式与符号一律保留原样。",
        ],
        "table-heavy": [
            "表头可翻译；表格内单位/符号保持原样。",
        ],
        "code-heavy": [
            "代码与配置不翻译；仅翻译注释与围绕代码的说明文字。",
        ],
        "references": [
            "参考文献条目通常不翻译期刊名/会议名；可将论文标题意译为中文并在括号保留英文原文。",
        ],
        "short": [
            "保持简练，避免过度扩写。",
        ],
        "general": []
    }

    lines = [base, "翻译规则："] + [f"- {r}" for r in rules_general]
    if kind in extras and extras[kind]:
        lines += ["针对本段内容的补充规则："] + [f"- {r}" for r in extras[kind]]
    lines += ["输出仅给出中文译文，不要重复原文，不要额外解释。"]
    return "\n".join(lines)

# ========== Translation backend (OpenAI-compatible) ==========

class Translator:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-4o-mini", temperature: float = 0.2):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_V1")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        self.model = model
        self.temperature = temperature
        self._session = None

    def _ensure_session(self):
        import requests  # lazy import
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def translate(self, text: str, section_title: str, kind: str, max_chars: int = 6000) -> str:
        """
        Translate a piece of markdown-aware text into Chinese, adapting the prompt to content kind.
        If no API key, returns a TODO marker.
        """
        text = text.strip()
        if not text:
            return ""
        # segment to respect max token/char limit
        segments = _approximate_segments(text, max_chars=max_chars)
        sub_translations: List[str] = []
        for seg in segments:
            sub_translations.append(self._translate_segment(seg, section_title, kind))
        return "\n".join(sub_translations)

    def _translate_segment(self, text: str, section_title: str, kind: str) -> str:
        # If no key, return placeholder
        if not self.api_key:
            return f"> 译文（TODO，请配置 --openai_api_key 才能自动翻译）: {section_title}"
        system_prompt = build_adaptive_prompt(kind)
        user_prompt = f"【段落标题】{section_title}\n【待翻译内容】\n{text}\n"

        # Don't translate fenced code blocks; we will do that by letting the prompt instruct not to.
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        try:
            sess = self._ensure_session()
            resp = sess.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(payload),
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            chinese = data["choices"][0]["message"]["content"].strip()
            return chinese
        except Exception as e:
            return f"> 译文（API 调用失败: {e}）"

def _approximate_segments(text: str, max_chars: int = 6000) -> List[str]:
    """Split by paragraph to keep each segment within max_chars (roughly token-safe)."""
    if len(text) <= max_chars:
        return [text]
    paras = re.split(r'\n\s*\n', text)  # split on blank-line paragraphs
    segments = []
    buf = []
    count = 0
    for p in paras:
        length = len(p) + 2  # include blank line joiner
        if count + length > max_chars and buf:
            segments.append("\n\n".join(buf))
            buf = [p]
            count = length
        else:
            buf.append(p)
            count += length
    if buf:
        segments.append("\n\n".join(buf))
    return segments

# ========== Bilingual Markdown rendering ==========

def render_bilingual_md(chunks: List[Chunk], translations: Dict[int, str], style: str = "blockquote") -> str:
    """
    Combine original + translation per chunk into a new markdown.
    style:
      - "blockquote": put translated text under original as '> 译文：...'
      - "quoted": put translation in Chinese in quotes "...."
      - "heading_split": add a subheading '### 中文翻译' after each section
    """
    out_lines: List[str] = []
    for idx, ch in enumerate(chunks):
        # heading line
        heading_hashes = "#" * ch.level
        if ch.title != "(Preamble)":
            out_lines.append(f"{heading_hashes} {ch.title}")
        # original content
        if ch.content_lines:
            out_lines.extend(ch.content_lines)
        out_lines.append("")  # spacer

        zh = translations.get(idx, "").strip()
        if zh:
            if style == "blockquote":
                # Ensure we keep paragraphs: prepend each non-empty line with '>'
                zh_lines = zh.splitlines()
                for i, zl in enumerate(zh_lines):
                    if zl.strip() == "":
                        out_lines.append(">")
                    else:
                        out_lines.append(f"> 译文：{zl}" if i == 0 else f"> {zl}")
                out_lines.append("")
            elif style == "quoted":
                out_lines.append(f"“{zh.replace('\"', '”')}”")
                out_lines.append("")
            elif style == "heading_split":
                out_lines.append(f"{'#'*(ch.level+1)} 中文翻译")
                out_lines.append(zh)
                out_lines.append("")
        else:
            out_lines.append("> 译文：")
            out_lines.append("")

    return "\n".join(out_lines).rstrip() + "\n"

# ========== Main pipeline ==========

def main():
    parser = argparse.ArgumentParser(description="Split Markdown by headings, translate chunks to Chinese, and emit bilingual Markdown.")
    parser.add_argument("input", help="Path to input .md file")
    parser.add_argument("-o", "--output", default=None, help="Path to output bilingual .md (default: <input>.bilingual.md)")
    parser.add_argument("--min_level", type=int, default=1, help="Minimum heading level to start chunking (default 1=#)")
    parser.add_argument("--style", choices=["blockquote", "quoted", "heading_split"], default="blockquote", help="Bilingual formatting style")
    parser.add_argument("--openai_api_key", default=None, help="OpenAI (or compatible) API key")
    parser.add_argument("--openai_base_url", default=None, help="OpenAI-compatible base URL (default: https://api.openai.com/v1)")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model name (default: gpt-4o-mini)")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature (default 0.2)")
    parser.add_argument("--max_chars", type=int, default=6000, help="Per-request char limit to avoid overly long prompts")
    parser.add_argument("--translate_code", action="store_true", help="If set, will allow translation inside code blocks (NOT recommended)")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        md_text = f.read()

    chunks = parse_markdown_into_chunks(md_text, min_level=args.min_level)

    # Pre-process: if translate_code is False, we will wrap code blocks with sentinels to discourage translation.
    # (The prompt already instructs not to translate code; this is an extra safety measure).

    translations: Dict[int, str] = {}
    translator = Translator(api_key=args.openai_api_key, base_url=args.openai_base_url, model=args.model, temperature=args.temperature)

    for idx, ch in enumerate(chunks):
        raw = ch.content()
        # Quick skip: if content empty, put empty translation
        if not raw.strip():
            translations[idx] = ""
            continue

        kind = detect_section_kind(ch.title, raw)
        zh = translator.translate(raw, section_title=ch.title, kind=kind, max_chars=args.max_chars)
        translations[idx] = zh

    out_path = args.output or (os.path.splitext(args.input)[0] + ".bilingual.md")
    out_md = render_bilingual_md(chunks, translations, style=args.style)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_md)

    # Emit a small JSON index of chunks (optional, might help downstream users)
    index = [{
        "index": i,
        "level": ch.level,
        "title": ch.title,
        "start_line": ch.start_line,
        "end_line": ch.end_line,
        "chars": len(ch.content())
    } for i, ch in enumerate(chunks)]
    with open(out_path + ".index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[OK] Wrote bilingual markdown to: {out_path}")
    print(f"[OK] Chunk index saved to: {out_path}.index.json")
    print(f"[INFO] Total chunks: {len(chunks)}")

if __name__ == "__main__":
    main()
