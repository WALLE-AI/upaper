import re
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


# ---------------------------
# 配置区
# ---------------------------

def resolve_oss_url(image_id: str) -> Optional[str]:
    """
    给定图片ID，向你的 OSS/对象存储服务拿最终可公开的访问形式。

    你需要把这里改成你自己的逻辑：
    - 如果你已经有CDN域名规则，就拼URL返回
    - 如果你有HTTP服务，比如 GET /oss?id=<image_id>，你可以在这儿发请求拿结果
      （如果要requests/httpx，这里可以加；当前示例是离线环境，所以我返回假URL）

    返回值可以是两种:
      1. 直接外链URL字符串 例如 "https://cdn.example.com/abc123.jpg"
      2. HTML片段 例如 '<img src="https://cdn.example.com/abc123.jpg" alt="abc123"/>'
         （会直接内嵌进Markdown）

    如果找不到就返回 None。
    """

    # 示例：假设OSS规则是 https://cdn.example.com/{image_id}.jpg
    # 你可以按需改成 png/webp 或查真实后缀
    public_url = f"https://cdn.example.com/{image_id}.jpg"

    return public_url


# ---------------------------
# 内部工具函数
# ---------------------------

IMG_PATTERN = re.compile(r'!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)')
HTML_IMG_PATTERN = re.compile(r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)


def is_external_or_html(src: str) -> bool:
    """
    True -> 不需要我们映射:
    - http(s):// 开头
    - 直接是 <img ...> 片段
    """
    s = src.strip().lower()
    if s.startswith("http://") or s.startswith("https://"):
        return True
    if s.startswith("<img"):
        return True
    return False


def extract_image_id(src: str) -> str:
    """
    从 Markdown 中的本地路径提取图片ID。
    例: "images/abc123xyz.jpg" -> "abc123xyz"
    """
    filename_full = src.strip().split("/")[-1]
    filename_full = filename_full.split("?")[0].split("#")[0]

    if "." in filename_full:
        image_id = ".".join(filename_full.split(".")[:-1])
    else:
        image_id = filename_full

    return image_id


def replace_md_image_links_auto(md_text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    核心处理函数:
    1. 找出所有 ![](src)
    2. 对本地图片用 image_id -> resolve_oss_url()
    3. 生成替换后的 Markdown
    4. 返回 (新Markdown文本, 替换日志列表)
    """

    replacements: List[Dict[str, Any]] = []
    new_text_parts: List[str] = []

    last_pos = 0

    for match in IMG_PATTERN.finditer(md_text):
        alt = match.group("alt")
        old_src_raw = match.group("src")
        old_src = old_src_raw.strip()
        start_idx, end_idx = match.span()

        # 先拼上前一段原文
        new_text_parts.append(md_text[last_pos:start_idx])

        # 缺省不动
        new_src = old_src
        replaced = False
        skipped_reason = None
        image_id_for_log = None

        if is_external_or_html(old_src):
            # 已经是公网/HTML，直接保留
            skipped_reason = "already_external_or_html"
            new_md_img = f"![{alt}]({new_src})"

        else:
            # 认为是本地路径 -> 提取 image_id
            image_id = extract_image_id(old_src)
            image_id_for_log = image_id

            # 通过OSS拿到最终地址或HTML
            resolved = resolve_oss_url(image_id)

            if resolved is None:
                # OSS没返回，保持原样
                skipped_reason = "oss_lookup_failed"
                new_md_img = f"![{alt}]({new_src})"
            else:
                resolved_strip = resolved.strip()

                if resolved_strip.lower().startswith("<img"):
                    # OSS返回的是完整<img ...>，我们直接塞进去，而不是markdown语法
                    new_md_img = resolved_strip
                else:
                    # OSS返回的是URL，继续沿用Markdown图片语法
                    new_src = resolved_strip
                    new_md_img = f"![{alt}]({new_src})"

                replaced = True
                skipped_reason = None

        new_text_parts.append(new_md_img)

        replacements.append({
            "alt": alt,
            "old_src": old_src,
            "new_src": new_src,
            "start_idx": start_idx,
            "end_idx": end_idx,
            "replaced": replaced,
            "skipped_reason": skipped_reason,
            "image_id": image_id_for_log,
        })

        last_pos = end_idx

    # 拼上剩余尾部
    new_text_parts.append(md_text[last_pos:])
    new_text = "".join(new_text_parts)

    return new_text, replacements


def find_raw_html_imgs(md_text: str) -> List[Dict[str, Any]]:
    """
    可选：抓文中原生 <img ...> 标签的位置，仅用于日志/调试。
    """
    results = []
    for m in HTML_IMG_PATTERN.finditer(md_text):
        start_idx, end_idx = m.span()
        src = m.group(1)
        results.append({
            "tag": m.group(0),
            "src": src,
            "start_idx": start_idx,
            "end_idx": end_idx,
        })
    return results


# ---------------------------
# 文件级接口
# ---------------------------

def process_markdown_file(md_path: str) -> Dict[str, Any]:
    """
    读入本地 md 文件，处理图片链接，写回一个新文件。

    输出:
      {
        "input_path": 原文件路径,
        "output_path": 新文件路径,
        "replacements": 替换日志列表,
        "html_imgs": 文中本来就有的<img>标签信息
      }
    """
    p = Path(md_path)
    if not p.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    original_text = p.read_text(encoding="utf-8")

    new_text, replacements = replace_md_image_links_auto(original_text)
    html_imgs = find_raw_html_imgs(original_text)

    # 结果写到同目录下: xxx.processed.md
    out_path = p.with_name(p.stem + ".processed" + p.suffix)
    out_path.write_text(new_text, encoding="utf-8")

    return {
        "input_path": str(p),
        "output_path": str(out_path),
        "replacements": replacements,
        "html_imgs": html_imgs,
    }


# ---------------------------
# CLI 入口示例
# ---------------------------

if __name__ == "__main__":
    # 把这里改成你的本地md文件路径
    md_path = "hf_papers/2305.03043/2305.03043.md"

    result = process_markdown_file(md_path)

    print("=== 输入文件 ===")
    print(result["input_path"])
    print("=== 输出文件 ===")
    print(result["output_path"])
    print("\n=== 替换日志 ===")
    for r in result["replacements"]:
        print(r)

    print("\n=== 原始HTML <img>（未动） ===")
    for taginfo in result["html_imgs"]:
        print(taginfo)
