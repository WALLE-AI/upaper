import os
import base64
from typing import Any, Dict, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "REPLACE_ME_WITH_REAL_TOKEN")
GITHUB_OWNER = "WALLE-AI"
GITHUB_REPO = "picx-images-hosting"
TARGET_DIR = "images"
GITHUB_API_BASE = "https://api.github.com"


def _file_to_base64_str(image_path: str) -> str:
    with open(image_path, "rb") as f:
        binary = f.read()
    return base64.b64encode(binary).decode("utf-8")


async def upload_image_to_github(
    filename: str,
    message: str="Upload image github",
    branch: str="master",
    image_path: Optional[str] = None,
    raw_base64_content: Optional[str] = None,
) -> Dict[str, Any]:
    """
    自动处理"新建 or 覆盖同名文件"的情况。

    参数:
        filename: 仓库里的目标文件名，比如 "abc.png"
        message:  commit message
        branch:   分支，比如 "master"
        image_path: 本地图片路径 (二选一)
        raw_base64_content: 直接给纯base64字符串 (二选一)

    返回:
        dict，包含 download_url 等信息
    """

    if GITHUB_TOKEN == "REPLACE_ME_WITH_REAL_TOKEN":
        raise RuntimeError("Server not configured with valid GITHUB_TOKEN")

    # 准备base64
    if raw_base64_content is not None:
        b64_str = raw_base64_content
    elif image_path is not None:
        b64_str = _file_to_base64_str(image_path)
    else:
        raise ValueError("You must provide either image_path or raw_base64_content")

    # 目标路径，比如 images/cat.png
    repo_path = f"{TARGET_DIR}/{filename}"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        # 第一步：尝试获取已有文件信息，拿 sha
        # GET /repos/{owner}/{repo}/contents/{path}?ref={branch}
        get_url = (
            f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{repo_path}"
            f"?ref={branch}"
        )

        existing_sha: Optional[str] = None
        get_resp = await client.get(get_url, headers=headers)

        if get_resp.status_code == 200:
            # 文件已存在，提取 sha
            info = get_resp.json()
            existing_sha = info.get("sha")
        elif get_resp.status_code == 404:
            # 文件不存在 -> 新建
            existing_sha = None
        else:
            # 其他错误，直接报
            raise RuntimeError(
                f"Failed to check existing file (status {get_resp.status_code}): {get_resp.text}"
            )

        # 第二步：PUT 创建或更新
        put_url = (
            f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{repo_path}"
        )

        body = {
            "message": message,
            "branch": branch,
            "content": b64_str,
        }
        # 如果是更新（文件存在），必须带 sha
        if existing_sha:
            body["sha"] = existing_sha

        put_resp = await client.put(put_url, json=body, headers=headers)

        if put_resp.status_code not in (200, 201):
            raise RuntimeError(
                f"GitHub API upload failed ({put_resp.status_code}): {put_resp.text}"
            )

        data = put_resp.json()

    return {
        "status": "ok",
        "filename": filename,
        "branch": branch,
        "github_commit_sha": data.get("commit", {}).get("sha"),
        "download_url": data.get("content", {}).get("download_url"),
        "raw_github_response": data,
    }
