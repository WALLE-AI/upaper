# -*- coding: utf-8 -*-
"""
Academic Markdown chunker (modified):
- Split by Markdown headings (#..######) to get sections.
- If a section body > max_chars, split by sentences (Chinese/English punctuation).
- For REFERENCES section: DO NOT try to group by items; simply split by newline.
  Each non-empty line becomes a citation chunk, keeping URLs inside `text`.
- Output fields: chunk_id (UUID), section_id (like "4.5" if present), section_title, text.

Usage:
    from pathlib import Path
    md_text = Path("/mnt/data/2510.18866.md").read_text(encoding="utf-8", errors="ignore")
    chunks = chunk_md_academic_refs_by_newline(md_text, max_chars=1024)
"""

import re
import uuid
from typing import List, Dict, Tuple


# ---------- Regex patterns ----------
_HEADING_RE = re.compile(
    r'^\s*(?P<level>#{1,6})\s*(?P<num>\d+(?:\.\d+)*)?\s*(?P<title>.+?)\s*$'
)
_REF_TITLE_RE = re.compile(r'^(references|reference|参考文献)\b', re.IGNORECASE)

# Sentence split for long bodies (Chinese + English punctuation)
_SENT_SPLIT_RE = re.compile(r'(?<=[。！？!?；;。\.])\s+')


# ---------- Helpers ----------
def _emit_chunk(section_id: str, section_title: str, text: str) -> Dict:
    return {
        "chunk_id": str(uuid.uuid4()),
        "section_id": (section_id or "").strip(),
        "section_title": (section_title or "").strip(),
        "text": (text or "").strip(),
    }


def _greedy_sentence_pack(sentences: List[str], max_chars: int) -> List[str]:
    """Greedy pack sentences into pieces no longer than max_chars."""
    chunks, buf = [], []
    cur_len = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # If a single sentence is longer than the limit, hard-split to avoid infinite loop
        if len(s) > max_chars:
            if buf:
                chunks.append(' '.join(buf).strip())
                buf, cur_len = [], 0
            for i in range(0, len(s), max_chars):
                chunks.append(s[i:i + max_chars])
            continue
        if cur_len + len(s) + (1 if buf else 0) <= max_chars:
            buf.append(s)
            cur_len += len(s) + (1 if buf else 0)
        else:
            chunks.append(' '.join(buf).strip())
            buf, cur_len = [s], len(s)
    if buf:
        chunks.append(' '.join(buf).strip())
    return chunks


# ---------- Main chunker ----------
def chunk_md_academic_refs_by_newline(md_text: str, max_chars: int = 1024) -> List[Dict]:
    """
    Chunk an academic Markdown:
      1) Split by headings.
      2) If a normal section body > max_chars, sentence-pack into sub-chunks.
      3) For REFERENCES/参考文献 section: split by newline; emit one chunk per non-empty line.

    Args:
        md_text: Markdown content.
        max_chars: max characters per chunk for non-reference sections.

    Returns:
        List of chunk dicts with (chunk_id, section_id, section_title, text).
    """
    lines = md_text.splitlines()
    sections: List[Tuple[str, str, List[str], int]] = []  # (section_id, title, body_lines, level)
    cur_sid, cur_title, cur_lines, cur_level = "", "", [], 0

    def push_section():
        # push only if title exists or body has any non-empty line
        if cur_title or any(l.strip() for l in cur_lines):
            sections.append((cur_sid, cur_title, cur_lines[:], cur_level))

    # Pass 1: scan headings to form sections
    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            push_section()
            cur_sid = (m.group('num') or "").strip()
            cur_title = (m.group('title') or "").strip()
            cur_lines = []
            cur_level = len(m.group('level'))
        else:
            cur_lines.append(line)
    push_section()

    # Pass 2: emit chunks
    chunks: List[Dict] = []
    for sid, title, body_lines, _lvl in sections:
        if _REF_TITLE_RE.match(title.lower()):
            # REFERENCES: split by newline; each non-empty line -> one chunk
            for ln in body_lines:
                t = ln.strip()
                if t:
                    chunks.append(_emit_chunk(sid, title, t))
            continue

        # Normal sections
        text = "\n".join(body_lines).strip()
        if not text:
            continue

        if len(text) <= max_chars:
            chunks.append(_emit_chunk(sid, title, text))
        else:
            # Merge hard newlines to not break sentences; then sentence-pack
            normalized = re.sub(r'\s*\n\s*', ' ', text)
            sentences = _SENT_SPLIT_RE.split(normalized)
            for piece in _greedy_sentence_pack(sentences, max_chars):
                if piece.strip():
                    chunks.append(_emit_chunk(sid, title, piece))
    return chunks


# ---------- Optional: CLI demo ----------
if __name__ == "__main__":
    import json
    from pathlib import Path

    # Example run (adjust path as needed)
    src = Path("hf_papers/2510.23564/2510.23564.md")
    if src.exists():
        md_text = src.read_text(encoding="utf-8", errors="ignore")
        out = chunk_md_academic_refs_by_newline(md_text, max_chars=1024)
        Path("chunks_by_newline.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"Done. {len(out)} chunks written to chunks_by_newline.json")
    else:
        print("Source Markdown not found; please update the path.")
