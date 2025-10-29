import json
import re
from dataclasses import dataclass, asdict
from typing import List, Dict
from pathlib import Path
import html
import textwrap

# 1. 匹配形如 "# 2.2.1 Linear Attention"
SECTION_RE = re.compile(
    r'^\s*#+\s*(?P<num>\d+(?:\.\d+)*)\s+(?P<title>.+?)\s*$'
)

# 2. 简单清洗器：图片占位、表格降维、HTML标签处理
def normalize_block(lines: List[str]) -> str:
    out_lines: List[str] = []
    buffer_table: List[str] = []
    in_table = False

    for line in lines:
        # 去掉多余空格
        raw = line.rstrip()

        # 图片：![](images/xxx.jpg)  Figure ...
        if raw.strip().startswith("![]("):
            # 尝试把下一句描述也放在一起
            out_lines.append("[FIGURE] " + raw)
            continue

        # 表格块：<table> ... </table>
        if "<table" in raw:
            in_table = True
            buffer_table.append(raw)
            continue
        if in_table:
            buffer_table.append(raw)
            if "</table>" in raw:
                # 把整段table转成一行纯文本
                table_txt = " ".join(buffer_table)
                table_txt = re.sub(r"<.*?>", " ", table_txt)  # 去HTML标签
                table_txt = re.sub(r"\s+", " ", table_txt).strip()
                out_lines.append("[TABLE] " + table_txt)
                buffer_table = []
                in_table = False
            continue

        # 数学公式块 $$...$$ 保留
        # （这里不特意改，embedding时原样送进去）

        # HTML转义，例如 &amp; -> &
        clean = html.unescape(raw)

        # <sup>3</sup> 这种小标签，去掉标签只留文本
        clean = re.sub(r"<\/?sup>", "", clean)
        clean = re.sub(r"<\/?sub>", "", clean)
        clean = re.sub(r"<\/?[^>]+>", "", clean)  # 兜底清html标签

        # 多个空格压成一个
        clean = re.sub(r"\s+", " ", clean).strip()

        if clean:
            out_lines.append(clean)

    # 合并
    text = "\n".join(out_lines).strip()

    return text


@dataclass
class DocChunk:
    chunk_id: str
    section_id: str
    section_title: str
    text: str


def split_long_text(text: str, max_len: int = 500) -> List[str]:
    """
    把一个很长的小节正文按句号/换行切成多段，避免>500字的超长chunk。
    简单策略：先按双换行或句号断，再做长度合并。
    """
    # 基于句号/换行粗切
    # 注意英文句号/中文句号/换行都考虑
    raw_units = re.split(r"(?:\n{2,}|。|\.)", text)
    units = [u.strip() for u in raw_units if u.strip()]

    chunks: List[str] = []
    cur = ""
    for u in units:
        # 尝试往当前块里塞
        if len(cur) + len(u) + 1 <= max_len:
            if cur:
                cur += " " + u
            else:
                cur = u
        else:
            if cur:
                chunks.append(cur.strip())
            cur = u
    if cur:
        chunks.append(cur.strip())

    # 如果结果反而太碎，也没关系；embedding检索会处理
    return chunks


def build_chunks_from_md(md_path: str) -> List[DocChunk]:
    """
    读取你这种md格式，输出结构化chunk列表
    """
    text = Path(md_path).read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    sections: List[Dict] = []
    cur_sec = None

    # 遍历整篇文档，把每一个 "# 2.2.1 xxx" 当成新section
    for line in lines:
        m = SECTION_RE.match(line)
        if m:
            # 遇到新小节，先把上一个收掉
            if cur_sec is not None:
                sections.append(cur_sec)

            cur_sec = {
                "section_id": m.group("num").strip(),      # e.g. "2.2.1"
                "section_title": m.group("title").strip(), # e.g. "Linear Attention"
                "body_lines": []
            }
        else:
            # 普通正文行，塞进当前section
            if cur_sec is not None:
                cur_sec["body_lines"].append(line)
            else:
                # 文档开头有时会在第一个小节前有摘要/作者/简介
                # 我们可以把它当成 "0.0 Preface"
                if not sections and (line.strip()):
                    if cur_sec is None:
                        cur_sec = {
                            "section_id": "0.0",
                            "section_title": "Preface",
                            "body_lines": []
                        }
                    cur_sec["body_lines"].append(line)

    # 别忘了把最后一个section也存进去
    if cur_sec is not None:
        sections.append(cur_sec)

    # 现在 sections 是按小节聚合的，还没切片
    doc_chunks: List[DocChunk] = []

    for sec in sections:
        sec_text_clean = normalize_block(sec["body_lines"])
        if not sec_text_clean:
            continue

        parts = split_long_text(sec_text_clean, max_len=5000)

        for idx, part in enumerate(parts, start=1):
            chunk_id = f"{sec['section_id']}__p{idx}"
            ch = DocChunk(
                chunk_id=chunk_id,
                section_id=sec["section_id"],
                section_title=sec["section_title"],
                text=part
            )
            doc_chunks.append(ch.__dict__)

    return doc_chunks


# 使用示例：
if __name__ == "__main__":
    chunks = build_chunks_from_md("hf_papers/2510.21618/2510.21618.md")
    print(f"Total chunks: {len(chunks)}")
    # 看前3个
    for c in chunks[:3]:
        print("----")
    with open("chunk_data.json","w",encoding="utf-8") as file:
        file.write(json.dumps(chunks,ensure_ascii=False,indent=2))
        
    
