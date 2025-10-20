import os
import base64
from pathlib import Path
import re
from typing import Dict, Any, Optional
from ..db.repositories.paper_repo_supabase import PaperRepositorySupabase
from loguru import logger
import requests
from playwright.sync_api import sync_playwright, Error as PlaywrightError
import alibabacloud_oss_v2 as oss

from .md_bilingual import translate_markdown_file
from dotenv import load_dotenv

load_dotenv()
    
required_envs = {
    "ALIYUN_OSS_ENDPOINT": os.getenv("ALIYUN_OSS_ENDPOINT"),
    "ALIYUN_OSS_BUCKET_NAME": os.getenv("ALIYUN_OSS_BUCKET_NAME"),
    "ALIYUN_OSS_REGION": os.getenv("ALIYUN_OSS_REGION"),
}
missing = [name for name, value in required_envs.items() if not value]
if missing:
    logger.warning(f"Aliyun OSS 未配置，缺少环境变量: {', '.join(missing)}，跳过上传。")
credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()
# 加载SDK的默认配置，并设置凭证提供者
cfg = oss.config.load_default()
cfg.credentials_provider = credentials_provider
# 设置配置中的区域信息
cfg.region = required_envs.get("ALIYUN_OSS_REGION")
cfg.endpoint = required_envs.get("ALIYUN_OSS_ENDPOINT")

# 使用配置好的信息创建OSS客户端
client = oss.Client(cfg)


def download_paper_by_id(paper_id: str,pdf_file_root) -> None:
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
    ##创建一个以paper_id命名的文件夹
    pid_dir = os.path.join(pdf_file_root, paper_id)
    if not os.path.exists(pid_dir):
        os.makedirs(pid_dir)
    save_path = os.path.join(pid_dir, f"{pid}.pdf")
    
    if os.path.exists(save_path):
        # 文件已存在则跳过下载
        print(f'文件 {save_path} 已存在，跳过下载。')
        return save_path,pid_dir
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
        return save_path,pid_dir
    except PlaywrightError as e:
        # 让上层知道失败原因
        raise RuntimeError(f"Playwright 下载失败: {e}") from e
    

PARSE_TIMEOUT = 1800    # nginx配置30分钟超时
MINERU_CFG = {
    # 'output_dir': './outputs',
    # 'lang_list': 'ch',    # [ch|ch_server|ch_lite|en|korean|japan|chinese_cht|ta|te|ka|th|el|latin|arabic|east_slavic|cyrillic|devanagari]，文档语言类型，可提升 OCR 准确率，仅用于 pipeline 后端
    # 'backend': 'vlm-sglang-engine', # [pipeline|vlm-transformers|vlm-sglang-engine|vlm-sglang-client] 解析后端（默认为 pipeline）
    # 'parse_method': 'auto', # [auto|txt|ocr] 解析方法
    # 'formula_enable': 'true', # 是否解析公式，默认开启
    # 'table_enable': 'true', # 是否解析表格，默认开启
    # 'server_url': '', 服务器url,使用client模式时的服务器参数
    # 'return_md': 'true', 是否返回markdown格式文档，默认开启
    'return_middle_json': 'true',   # 返回中间结果，默认关闭
    # 'return_model_output': 'true',    # 返回模型输出，仅用于 pipeline 后端，默认关闭
    # 'return_content_list': 'true',    # 返回简要结果（没有坐标框等详细信息），默认关闭
    'return_images': 'true',  # 是否以base64形式返回模型图片，默认关闭
    # 'start_page_id': 0,   # 起始页，默认0
    # 'end_page_id': 99999, # 结束页，默认99999
    'extract_catalog': 'false' # 是否解析目录，默认开启
}

def parse_pdf(file_path:str,file_name_dir) -> Dict[str, Any]:
    """解析PDF文件"""
    file_name = Path(file_path).name
    ##TODO:采用对象存储的策略
    if not os.path.exists(file_name_dir):
        os.makedirs(file_name_dir)
    md_file_path = os.path.join(file_name_dir, file_name.replace('.pdf','.md'))
    if not os.path.exists(md_file_path):
        logger.info(f'开始解析: {file_name}')
        with open(file_path, 'rb') as f:
            files = {'files': (str(file_name), f, 'application/pdf')}
            data = MINERU_CFG
            response = requests.post(
                os.getenv("PARSE_URL"), 
                files=files, 
                data=data, 
                timeout=PARSE_TIMEOUT
            )
            
        response.raise_for_status()
        res = response.json()
    else:
        logger.info(f'文件已解析，跳过: {file_name}')
        return ""

    for key,value in res['results'].items():  
        md_content = value.get('md_content', '')
        middle_json = value.get('middle_json', '')
        md_content_path = os.path.join(file_name_dir, key+".md")
        with open(md_content_path,"w",encoding="utf-8") as file:
            file.write(md_content)
        middle_json_path = os.path.join(file_name_dir, key+".jsonl")
        with open(middle_json_path,"w",encoding="utf-8") as file:
            file.write(middle_json)
        logger.info(f'Markdown内容已提取, 长度: {len(md_content)} 字符')
        images = value.get('images', {})
        for img_name, img_data in images.items():
            if not os.path.exists(file_name_dir+'/images'):
                os.makedirs(file_name_dir+'/images')
            try:
                m = re.match(r"^data:(image/[\w\+\-\.]+);base64,(.*)$", img_data, flags=re.S | re.I)
                mime = None
                data = img_data
                if m:
                    mime, data = m.group(1).lower(), m.group(2)

                # 2) 清洗+补 padding
                data = re.sub(r"\s+", "", data)
                if (pad := (-len(data)) % 4):
                    data += "=" * pad
                raw = base64.b64decode(data, validate=False)
            except Exception:
            # 兼容 url-safe base64
                raw = base64.urlsafe_b64decode(data)
                
                # 依据 mime 猜扩展名
                ext_map = {
                    "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
                    "image/webp": "webp", "image/gif": "gif", "image/bmp": "bmp",
                    "image/tiff": "tiff", "image/x-icon": "ico", "image/svg+xml": "svg",
                }
                ext = "." + ext_map.get(mime, "bin")
            img_path = os.path.join(file_name_dir+'/images', img_name)
            with open(img_path, 'wb') as img_file:
                img_file.write(raw)
            logger.info(f'图片已保存: {img_path}')
    return md_content

from pathlib import Path
from typing import Dict, List, Iterable, Set

def find_assets(
    root: Path | str,
    ignore_dirs: Iterable[str] = (".git", ".hg", ".svn", ".DS_Store", "node_modules", "__pycache__"),
    follow_symlinks: bool = False,
) -> Dict[str, List[Path]]:
    """
    递归扫描 root 目录，收集指定类型文件：
      - docs: .md
      - pdfs: .pdf
      - jsons: .json / .jsonl
      - images: 常见图片扩展名（见下）
    返回值为 {category: [Path, ...]} 的字典，路径已去重、按字典序排序。

    参数:
      root: 根目录
      ignore_dirs: 扫描时跳过的目录名（仅匹配最后一级目录名）
      follow_symlinks: 是否跟随符号链接

    用法:
      files = find_assets("/your/project")
      print(files["images"])
    """
    root = Path(root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root path not found: {root}")

    # 统一小写扩展名集合
    doc_exts: Set[str] = {".md"}
    pdf_exts: Set[str] = {".pdf"}
    json_exts: Set[str] = {".json", ".jsonl"}
    image_exts: Set[str] = {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp",
        ".tif", ".tiff", ".webp", ".svg", ".heic", ".heif"
    }

    results = {
        "docs": set(),
        "pdfs": set(),
        "jsons": set(),
        "images": set(),
        "others_matched": set(),  # 保险起见：如果以后扩展匹配逻辑，可放这里
    }

    # 自定义一个目录迭代器，支持忽略目录与软链策略
    def iter_paths(base: Path):
        # 使用 rglob 时不易跳过指定目录，这里手写递归更可控
        for entry in base.iterdir():
            try:
                # 跳过指定目录
                if entry.is_dir():
                    if entry.name in ignore_dirs:
                        continue
                    if entry.is_symlink() and not follow_symlinks:
                        continue
                    yield from iter_paths(entry)
                elif entry.is_file() or (entry.is_symlink() and follow_symlinks):
                    yield entry
            except PermissionError:
                # 跳过无权限路径
                continue

    for p in iter_paths(root):
        ext = p.suffix.lower()
        if ext in doc_exts:
            results["docs"].add(p)
        elif ext in pdf_exts:
            results["pdfs"].add(p)
        elif ext in json_exts:
            results["jsons"].add(p)
        elif ext in image_exts:
            results["images"].add(p)
        else:
            # 可选：把其他类型保留以便后续查看
            pass

    # 转成排序后的列表
    return {k: sorted(v) for k, v in results.items()}


def donwload_md_to_local(paper_id: str,is_local=False) -> Optional[str]:
    folder = "hf_papers/"+paper_id
    key = folder + f"/{paper_id}.md"
    bucket=required_envs.get("ALIYUN_OSS_BUCKET_NAME")

    if client.is_object_exist(
        bucket=bucket,
        key=key
    ):
    # 执行获取对象的请求，指定存储空间名称和对象名称
        result = client.get_object(oss.GetObjectRequest(
            bucket=bucket,  # 指定存储空间名称
            key=key,  # 指定对象键名
        ))
            # 输出获取对象的结果信息，用于检查请求是否成功
        print(f'status code: {result.status_code},'
            f' request id: {result.request_id},')
        # ========== 方式1：完整读取 ==========
        with result.body as body_stream:
            data = body_stream.read()
            print(f"文件读取完成，数据长度：{len(data)} bytes")
            if is_local:
                if not os.path.exists(folder):
                    os.makedirs(folder)
                with open(key, 'wb') as f:
                    f.write(data)
                print(f"文件下载完成，保存至路径：{key}")
                return key
            else:
                ##data 转 str
                data = data.decode('utf-8')
                return data
    else:
        print(f"{key} is no exist")


def upload_pdf_to_oss(file_path: str, paper_id: str) -> Optional[str]:
    """Upload the downloaded PDF to Aliyun OSS and return the object key when configured."""
    
    folder = "hf_papers/"+paper_id
    folder_images = folder + "/images" 
    key = folder + f"/{paper_id}.pdf"
    
    # 用于记录上传进度的字典
    progress_state = {'saved': 0}

    def _progress_fn(n, written, total):
        progress_state['saved'] += n
        rate = int(100 * (float(written) / float(total)))
        print(f'\r上传进度：{rate}% ', end='')

    bucket=required_envs.get("ALIYUN_OSS_BUCKET_NAME")
    if client.is_object_exist(
        bucket=bucket,
        key=key
    ):
        print(f'对象 {key} 已存在于存储空间 {required_envs.get("ALIYUN_OSS_BUCKET_NAME")} 中，跳过上传。')
        return "对象已存在，跳过上传。"
    else:
        all_files = find_assets(folder)
        for pdf_file in all_files['pdfs']:
            key = folder + f"/{pdf_file.name}"
            result = client.put_object_from_file(
                oss.PutObjectRequest(
                    bucket=bucket,  # 存储空间名称
                    key=key,
                    progress_fn=_progress_fn# 对象名称
                ),
                str(pdf_file)          # 本地文件路径
            )
            print(f"\n{pdf_file}上传成功，ETag: {result.etag}"
            f"{pdf_file}状态码: {result.status_code}, 请求ID: {result.request_id}"
        )
        for image_file in all_files['images']:
            key = folder_images + f"/{image_file.name}"
            result = client.put_object_from_file(
                oss.PutObjectRequest(
                    bucket=bucket,  # 存储空间名称
                    key=key,
                    progress_fn=_progress_fn# 对象名称
                ),
                str(image_file)          # 本地文件路径
            )
            print(f"\n{image_file}上传成功，ETag: {result.etag}"
            f"{image_file}状态码: {result.status_code}, 请求ID: {result.request_id}")
        for json_file in all_files['jsons']:
            key = folder + f"/{json_file.name}"
            result = client.put_object_from_file(
                oss.PutObjectRequest(
                    bucket=bucket,  # 存储空间名称
                    key=key,
                    progress_fn=_progress_fn# 对象名称
                ),
                str(json_file)          # 本地文件路径
            )
            print(f"\n{json_file}上传成功，ETag: {result.etag}"
            f"{json_file}状态码: {result.status_code}, 请求ID: {result.request_id}")
        for md_file in all_files['docs']:
            key = folder + f"/{md_file.name}"
            result = client.put_object_from_file(
                oss.PutObjectRequest(
                    bucket=bucket,  # 存储空间名称
                    key=key,
                    progress_fn=_progress_fn# 对象名称
                ),
                str(md_file)          # 本地文件路径
            )
            print(f"\n{md_file}上传成功，ETag: {result.etag}"
            f"{md_file}状态码: {result.status_code}, 请求ID: {result.request_id}") 



def supabase_client():
    from supabase import Client, create_client
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase: Client = create_client(url, key)
    return supabase
paper_db = PaperRepositorySupabase(client=supabase_client())

class PaperFileDownloadAndParser:
    
    @staticmethod
    def get_papers_id_list() -> list:
        ##从supabase获取需要下载的paper_id列表
        paper_id_list = paper_db.get_all_paper_id()
        return paper_id_list
    
    @staticmethod
    def parse(paper_id: str) -> Dict[str, Any]:
        pdf_file_root =os.getenv("STORAGE_LOCAL_PATH",'hf_papers')
        path, pid_dir = download_paper_by_id(paper_id, pdf_file_root)
        md_content = parse_pdf(file_path=path, file_name_dir=pid_dir)
        if md_content:
            trans_md = translate_markdown_file(paper_id=paper_id,md_text=md_content,is_local=True)
        upload_pdf_to_oss(pid_dir, paper_id)
        return {
            "paper_id": paper_id,
            "pdf_path": path,
            "markdown_content": md_content,
            "translated_markdown_content": trans_md
            }
        
        
if __name__ == "__main__":
    paper_id = PaperFileDownloadAndParser.get_papers_id_list()[:20]
    pdf_file_root = "hf_papers"
    for pid in paper_id:
        result = PaperFileDownloadAndParser.parse(pid)
        print(f"解析完成: {result['paper_id']}, PDF路径: {result['pdf_path']}, Markdown内容长度: {len(result['markdown_content'])} 字符")
    # upload_pdf_to_oss("D:/LLM/project/upaper/hf_papers/2304.09355","2304.09355")
