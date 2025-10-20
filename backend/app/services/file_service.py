import codecs
import datetime
import hashlib
import os
from pathlib import Path
import time
import uuid
from collections.abc import Generator
from typing import Dict, Iterable, Optional, Union

from ..file.file_download import FileDonwloader

from ..file.file_to_mardown import FileToMarkdown
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import NotFound

# from core.file.upload_file_parser import UploadFileParser
# from core.rag.extractor.extract_processor import ExtractProcessor
# from extensions.ext_database import db
from ..db.ext_storage import storage
# from models.account import Account
# from models.model import EndUser, UploadFile
from ..file.errors.file import FileTooLargeError, UnsupportedFileTypeError

IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "gif", "svg"]
IMAGE_EXTENSIONS.extend([ext.upper() for ext in IMAGE_EXTENSIONS])

ALLOWED_EXTENSIONS = ["txt", "markdown", "md", "pdf", "html", "htm", "xlsx", "xls", "docx", "csv"]
UNSTRUCTURED_ALLOWED_EXTENSIONS = [
    "txt",
    "markdown",
    "md",
    "pdf",
    "html",
    "htm",
    "xlsx",
    "xls",
    "docx",
    "csv",
    "eml",
    "msg",
    "pptx",
    "ppt",
    "xml",
    "epub",
]

PREVIEW_WORDS_LIMIT = 3000

class FileService:
    
    @staticmethod
    def download_file(paper_id: str) -> str:
        file_downloader = FileDonwloader()
        path = file_downloader.download(paper_id)
        return path
        
    @staticmethod
    def parser_file(file_path: str,file_name_dir:str,parser_type="mineru") -> str:
        file_to_md = FileToMarkdown()
        md_content = file_to_md.convert(file_path,file_name_dir,parser_type)
        return md_content
    
    @staticmethod
    def upload_file(file: FileStorage, only_image: bool = False):
        filename = file.filename
        extension = file.filename.split(".")[-1]
        if len(filename) > 200:
            filename = filename.split(".")[0][:200] + "." + extension
        etl_type = ""
        allowed_extensions = (
            UNSTRUCTURED_ALLOWED_EXTENSIONS + IMAGE_EXTENSIONS
            if etl_type == "Unstructured"
            else ALLOWED_EXTENSIONS + IMAGE_EXTENSIONS
        )
        if extension.lower() not in allowed_extensions:
            raise UnsupportedFileTypeError()
        elif only_image and extension.lower() not in IMAGE_EXTENSIONS:
            raise UnsupportedFileTypeError()

        # read file content
        file_content = file.read()

        # get file size
        file_size = len(file_content)

        if extension.lower() in IMAGE_EXTENSIONS:
            file_size_limit = os.getenv("UPLOAD_IMAGE_FILE_SIZE_LIMIT") * 1024 * 1024
        else:
            file_size_limit = os.getenv("UPLOAD_FILE_SIZE_LIMIT") * 1024 * 1024

        if file_size > file_size_limit:
            message = f"File size exceeded. {file_size} > {file_size_limit}"
            raise FileTooLargeError(message)

        # user uuid as file name
        file_uuid = str(uuid.uuid4())

        file_key = "upload_files/" + "/" + file_uuid + "." + extension

        # save file to storage
        storage.save(file_key, file_content)

    @staticmethod  
    def _iter_mock_translation(paper: Dict, target_lang: str, delay_s: float = 0.02) -> Iterable[str]:
        ##"""按词流式输出 mock 翻译，内容与前端 fallback 文案保持一致。"""
        title = paper.get("title") or ""
        abstract = paper.get("abstract") or ""
        mock_title = f"**标题 ({target_lang}):** {title} (模拟翻译)"
        mock_abs = (
            f"**摘要 ({target_lang}):**\n"
            f"{abstract} (这是一个模拟的 {target_lang} 翻译，用于在无法连接到后端服务时进行演示。)"
        )
        full_text = f"{mock_title}\n\n{mock_abs}"
        for word in full_text.split(" "):
            yield word + " "
            # 小睡以演示“流式效果”；生产可去掉或减小
            time.sleep(delay_s)
    @staticmethod
    def _iter_stream_markdown(md_source: Union[str, Path], chunk_bytes: int = 8192) -> Generator[str, None, None]:
        """
        兼容两种输入：
        - 本地文件路径（.md）
        - 直接的 Markdown 字符串内容
        以 UTF-8 增量解码方式，按字节块流式输出，避免拆断多字节字符。
        """
        # 情况 A：是一个存在的本地路径文件
        try:
            p = Path(str(md_source))
            is_path_like = p.exists() and p.is_file()
        except Exception:
            is_path_like = False

        if is_path_like:
            decoder = codecs.getincrementaldecoder("utf-8")()
            with open(p, "rb") as f:
                while True:
                    buf = f.read(chunk_bytes)
                    if not buf:
                        rem = decoder.decode(b"", final=True)
                        if rem:
                            yield rem
                        break
                    out = decoder.decode(buf)
                    if out:
                        yield out
            return

        # 情况 B：把它当作 Markdown 字符串内容处理
        # 为了不拆多字节字符：先转成 bytes，再用同样的增量解码切块
        if not isinstance(md_source, str):
            md_source = str(md_source)
        data = md_source.encode("utf-8")
        decoder = codecs.getincrementaldecoder("utf-8")()
        offset = 0
        n = len(data)
        while offset < n:
            chunk = data[offset: offset + chunk_bytes]
            offset += len(chunk)
            out = decoder.decode(chunk)
            if out:
                yield out
        rem = decoder.decode(b"", final=True)
        if rem:
            yield rem
        
    @staticmethod
    def _iter_real_translation(paper: Dict, target_lang: str, chunk_bytes: int = 4096) -> Iterable[str]:
        """
        读取本地已翻译好的 xx.md 文件，并流式输出给前端。
        - 默认从 ./data/translations/ 查找（可通过 current_app.config['TRANSLATIONS_DIR'] 改）
        - 支持 paper['translated_path'] 指定文件（路径会进行安全校验）
        - 逐块 bytes -> 增量 UTF-8 解码，避免多字节字符被截断
        """
        # 统一叫 md_source：可能是“路径”，也可能是“Markdown 字符串”
        md_source = FileDonwloader.donwload_translate_md_to_local(paper_id=paper["id"])

        if not md_source:
            # 未拿到任何内容 → 退回 mock
            yield from FileService._iter_mock_translation(paper, target_lang)
            return

        # 直接用统一的流式输出
        yield from FileService._iter_stream_markdown(md_source, chunk_bytes=chunk_bytes)
    @staticmethod
    def _as_plain_text_stream(gen: Iterable[str], heartbeat_interval_s: Optional[float] = None) -> Iterable[bytes]:
        """
        将 str 生成器封装为 bytes，并可选地周期性发出心跳，避免中间件/代理回收空闲连接。
        """
        last_flush = time.time()
        for chunk in gen:
            data = chunk if isinstance(chunk, str) else str(chunk)
            yield data.encode("utf-8")
            last_flush = time.time()

            # 如需强制“更细粒度”分块，可考虑在此处切分 \n 或句号。
            # 生产环境大多交给上游流来决定 chunk 大小。

            if heartbeat_interval_s:
                now = time.time()
                if now - last_flush >= heartbeat_interval_s:
                    # 发送极小心跳（不可影响前端显示，选用零宽空格或空字符串+flush）
                    yield b"\xee\x80\x80"  # ZERO-WIDTH-NON-BREAKING-SPACE (U+FEFF)
                    last_flush = now
