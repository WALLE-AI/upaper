import os
from pathlib import Path
import re
from typing import Optional

from .deep_paper_report import IMAGE_RE, PaperImage
from .deep_paper_report import deep_analysis_run, deep_analysis_strem_run
from loguru import logger
from playwright.sync_api import sync_playwright, Error as PlaywrightError

from .hf_papers_download_or_parser_to_oss import PaperFileDownloadAndParser

from .md_bilingual import translate_markdown_file
from ..db.ext_storage import storage
import alibabacloud_oss_v2 as oss


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
# # 设置使用CNAME
# cfg.use_cname = True

# 使用配置好的信息创建OSS客户端
client = oss.Client(cfg)

def download_paper_by_id(paper_id: str, pdf_file_root) -> None:
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
    # object storage key for saving the PDF via Storage
    storage_key = f"papers/{paper_id}/{pid}.pdf"
    
    if os.path.exists(save_path):
        # 文件已存在则跳过下载
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
                pdf_bytes = resp.body()
                with open(save_path, "wb") as f:
                    f.write(pdf_bytes)
                # Save to OSS (or configured storage) as well
                try:
                    # avoid duplicate uploads if already exists
                    if not storage.exists(storage_key):
                        storage.save(storage_key, pdf_bytes)
                except Exception as _e:
                    # best-effort upload; do not fail download
                    print(f"storage save failed for {storage_key}: {_e}")
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
                # Read file bytes and save to storage
                try:
                    with open(save_path, "rb") as f:
                        file_bytes = f.read()
                    if not storage.exists(storage_key):
                        storage.save(storage_key, file_bytes)
                except Exception as _e:
                    print(f"storage save failed for {storage_key}: {_e}")

            context.close()
            browser.close()

        # 你之前函数返回 None，这里也保持一致；如需返回路径，可改为 return save_path
        return save_path,pid_dir
    except PlaywrightError as e:
        # 让上层知道失败原因
        raise RuntimeError(f"Playwright 下载失败: {e}") from e


class FileDonwloader():
    def __init__(self):
        self.pdf_file_root = os.getenv("STORAGE_LOCAL_PATH",'hf_papers')
    def download(self, paper_id) -> str:
        """Download the file from the given URL to the destination path."""
        print("pdf_file_root:",self.pdf_file_root)
        path = download_paper_by_id(paper_id=paper_id,pdf_file_root=self.pdf_file_root)
        return path
    
    def oss_images_url(key:str):
        bucket=required_envs.get("ALIYUN_OSS_BUCKET_NAME")
        if client.is_object_exist(
            bucket=bucket,
            key=key
        ):
            pre_result = client.presign(
                oss.GetObjectRequest(
                    bucket=bucket,  # 指定存储空间名称
                    key=key,        # 指定对象键名
                )
            )
            return pre_result.url
        else:
            logger.exception("{key} is no oss exist")
    
    
    @staticmethod
    def oss_dowload_deep_analysis_file(key:str,folder:str,is_local=False) -> Optional[str]:
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
                    if isinstance(data,bytes):
                        data = bytes(int(b, 2) for b in data.strip().split())
                    data = data.decode('utf-8')
                    # imgs = [PaperImage(alt=a, url=u, context_heading=None) for a,u in IMAGE_RE.findall(data)]
                    # import pdb
                    # pdb.set_trace()
                    # for image in imgs:
                    #     image_key = folder+"/" +image.url
                    #     image_url = FileDonwloader.oss_images_url(image_key)
                    #     print(image_url)
                    return data
        else:
            print(f"{key} is no exist")
            return None
    

    @staticmethod
    def oss_dowload_file(key:str,folder:str,is_local=False) -> Optional[str]:
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
                    # if isinstance(data,bytes):
                    #     data = bytes(int(b, 2) for b in data.strip().split())
                    data = data.decode('utf-8')
                    return data
        else:
            print(f"{key} is no exist")
            return None
    @staticmethod
    def upload_report_to_oss(md_text: str, key: str) -> Optional[str]:
        """Upload the downloaded PDF to Aliyun OSS and return the object key when configured."""
                
        # 用于记录上传进度的字典
        progress_state = {'saved': 0}

        def _progress_fn(n, written, total):
            progress_state['saved'] += n
            rate = int(100 * (float(written) / float(total)))
            print(f'\r上传进度：{rate}% ', end='')
            
        data = " ".join(format(b, "08b") for b in md_text.encode("utf-8"))
        bucket=required_envs.get("ALIYUN_OSS_BUCKET_NAME")
        if client.is_object_exist(
            bucket=bucket,
            key=key
        ):
            print(f'对象 {key} 已存在于存储空间 {required_envs.get("ALIYUN_OSS_BUCKET_NAME")} 中，跳过上传。')
            return "对象已存在，跳过上传。"
        else:
            result = client.put_object(
                oss.PutObjectRequest(
                    bucket=bucket,  # 存储空间名称
                    key=key,
                    body=data,
                    progress_fn=_progress_fn# 对象名称
                )
            )
            print(f"\n上传成功，ETag: {result.etag}"
            f"状态码: {result.status_code}, 请求ID: {result.request_id}"
            )



        
    @staticmethod
    def download_deep_analysis_report_md_content(paper_id: str, is_local: bool = False):
        """
        目标：下载 paper 的 deep analysis report md 内容。
        优先下载 {paper_id}_report.md 文件。
        成功则返回内容（str），否则返回 None
        """
        folder   = f"hf_papers/{paper_id}"
        key_report_md   = f"{folder}/{paper_id}_report.md"
        key_md   = f"{folder}/{paper_id}.md"
        out_bi   = Path(folder) / f"{paper_id}_report.md"  # 本地目标路径
        
        report_md_content = FileDonwloader.oss_dowload_deep_analysis_file(key=key_report_md, folder=folder, is_local=is_local)
        if report_md_content:
            return report_md_content
        # 2) 再试普通 md
        md_path = FileDonwloader.oss_dowload_file(key=key_md, folder=folder, is_local=is_local)
        if md_path:
            # 尝试把 md 解读 report（若失败则退回 md）
            # md_text = None
            # try:
            #     md_text = Path(md_path).read_text(encoding="utf-8")
            # except Exception:
            #     pass
            try:
                report_path_or_content = deep_analysis_run(
                    md_path,
                    folder,
                    "gpt",
                    False,
                    "sdsds",
                    True
                )
                ##save to oss
                FileDonwloader.upload_report_to_oss(md_text=report_path_or_content,key=key_report_md)
                # 若翻译函数直接返回本地路径，优先用之
                if isinstance(report_path_or_content, str) and Path(report_path_or_content).exists():
                    return report_path_or_content
                # 若返回的是内容，则落盘
                if isinstance(report_path_or_content, str) and not Path(report_path_or_content).exists():
                    Path(out_bi).parent.mkdir(parents=True, exist_ok=True)
                    Path(out_bi).write_text(report_path_or_content, encoding="utf-8")
                    return str(out_bi)
            except Exception as e:
                logger.error("download_deep_analysis_report_md_content:{}",e)

            # 翻译失败，至少返回原 md
            return md_path
        
        return None
    
        
    @staticmethod
    def donwload_translate_md_to_local(paper_id: str, is_local: bool = False) -> Optional[str]:
        """
        目标：尽可能返回 paper 的“本地 Markdown 文件路径”（优先 bilingual.md）。
        回退顺序：
        1) 直接下载 {paper_id}.bilingual.md
        2) 直接下载 {paper_id}.md -> 若拿到，则尝试翻译为 bilingual；翻译失败则返回原 md
        3) 下载 {paper_id}.pdf 并解析/翻译生成 bilingual.md
        4) 兜底：直接通过 PaperFileDownloadAndParser.parse() 生成翻译内容并写本地
        成功则返回本地路径（str），否则返回 None
        """
        folder   = f"hf_papers/{paper_id}"
        key_bi   = f"{folder}/{paper_id}.bilingual.md"
        key_md   = f"{folder}/{paper_id}.md"
        key_pdf  = f"{folder}/{paper_id}.pdf"
        out_bi   = Path(folder) / f"{paper_id}.bilingual.md"  # 本地目标路径
        # 1) 先试 bilingual.md
        bi_path = FileDonwloader.oss_dowload_file(key=key_bi, folder=folder, is_local=is_local)
        if bi_path:
            return bi_path

        # 2) 再试普通 md
        md_path = FileDonwloader.oss_dowload_file(key=key_md, folder=folder, is_local=is_local)
        if md_path:
            # 尝试把 md 翻译成 bilingual（若失败则退回 md）
            md_text = None
            try:
                md_text = Path(md_path).read_text(encoding="utf-8")
            except Exception:
                pass

            try:
                trans_path_or_content = translate_markdown_file(
                    paper_id=paper_id,
                    md_text=md_text if md_text is not None else "None",
                    is_local=is_local,
                )
                # 若翻译函数直接返回本地路径，优先用之
                if isinstance(trans_path_or_content, str) and Path(trans_path_or_content).exists():
                    return trans_path_or_content
                # 若返回的是内容，则落盘
                if isinstance(trans_path_or_content, str) and not Path(trans_path_or_content).exists():
                    Path(out_bi).parent.mkdir(parents=True, exist_ok=True)
                    Path(out_bi).write_text(trans_path_or_content, encoding="utf-8")
                    return str(out_bi)
            except Exception:
                pass

            # 翻译失败，至少返回原 md
            return md_path

        # 3) 试 pdf → 解析/翻译
        pdf_path = FileDonwloader.oss_dowload_file(key=key_pdf, folder=folder, is_local=is_local)
        if pdf_path:
            try:
                data = PaperFileDownloadAndParser.parse(paper_id=paper_id)
                # 兼容两种可能的返回字段
                if isinstance(data, dict):
                    if data.get("translated_markdown_path") and Path(data["translated_markdown_path"]).exists():
                        return data["translated_markdown_path"]
                    if data.get("translated_markdown_content"):
                        Path(out_bi).parent.mkdir(parents=True, exist_ok=True)
                        Path(out_bi).write_text(data["translated_markdown_content"], encoding="utf-8")
                        return str(out_bi)
            except Exception:
                pass

        # 4) 兜底：直接解析（即使没有 pdf/md）
        try:
            data = PaperFileDownloadAndParser.parse(paper_id=paper_id)
            if isinstance(data, dict):
                if data.get("translated_markdown_path") and Path(data["translated_markdown_path"]).exists():
                    return data["translated_markdown_path"]
                if data.get("translated_markdown_content"):
                    Path(out_bi).parent.mkdir(parents=True, exist_ok=True)
                    Path(out_bi).write_text(data["translated_markdown_content"], encoding="utf-8")
                    return str(out_bi)
        except Exception:
            pass

        return None
        
        

    