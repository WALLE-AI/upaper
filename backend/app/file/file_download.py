import os
import re
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from ..db.ext_storage import storage

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
        self.pdf_file_root = os.getenv("STORAGE_LOCAL_PATH",'./save/storage')
    def download(self, paper_id) -> str:
        """Download the file from the given URL to the destination path."""
        print("pdf_file_root:",self.pdf_file_root)
        path = download_paper_by_id(paper_id=paper_id,pdf_file_root=self.pdf_file_root)
        return path