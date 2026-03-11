"""YouTube 发布服务（通过 Google Data API v3）"""
import os
import json
import time
from typing import Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.models.material import Material


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

# YouTube 视频分类 ID（日本版）
CATEGORY_IDS = {
    "新闻": "25",
    "教育": "27",
    "娱乐": "24",
    "科技": "28",
    "财经": "25",  # News & Politics
    "生活": "22",  # People & Blogs
}


class YouTubePublisher:
    """YouTube 视频上传服务"""

    def __init__(self, oauth_token_json: str):
        """
        :param oauth_token_json: 存储在数据库的 OAuth Token JSON 字符串
        """
        self._token_json = oauth_token_json
        self._credentials: Optional[Credentials] = None
        self._service = None

    def _build_credentials(self) -> Credentials:
        """从存储的 Token JSON 构建 Credentials 并自动刷新"""
        token_data = json.loads(self._token_json)
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.YT_CLIENT_ID,
            client_secret=settings.YT_CLIENT_SECRET,
            scopes=SCOPES,
        )
        # 自动刷新过期 Token
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds

    def _get_service(self):
        """获取 YouTube API 服务对象（懒加载）"""
        if self._service is None:
            self._credentials = self._build_credentials()
            self._service = build("youtube", "v3", credentials=self._credentials)
        return self._service

    def get_updated_token_json(self) -> str:
        """返回刷新后的 Token JSON（用于更新数据库存储）"""
        if self._credentials:
            return json.dumps({
                "token": self._credentials.token,
                "refresh_token": self._credentials.refresh_token,
                "expiry": self._credentials.expiry.isoformat() if self._credentials.expiry else None,
            })
        return self._token_json

    def upload_video(self, material: Material) -> Dict[str, Any]:
        """上传视频到 YouTube，返回视频 ID 和 URL"""
        if not material.file_path or not os.path.exists(material.file_path):
            raise FileNotFoundError(f"视频文件不存在: {material.file_path}")

        service = self._get_service()

        # 构建视频元数据
        tags = []
        if material.yt_tags:
            try:
                tags = json.loads(material.yt_tags)
            except json.JSONDecodeError:
                tags = [t.strip() for t in material.yt_tags.split(",") if t.strip()]

        body = {
            "snippet": {
                "title": material.yt_title or material.title or "Untitled",
                "description": material.caption or "",
                "tags": tags,
                "categoryId": material.yt_category_id or "25",
            },
            "status": {
                "privacyStatus": material.yt_privacy or "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        # 分片上传（支持大文件）
        media = MediaFileUpload(
            material.file_path,
            mimetype=material.mime_type or "video/mp4",
            resumable=True,
            chunksize=8 * 1024 * 1024,  # 8MB 分片
        )

        insert_request = service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        video_id = self._resumable_upload(insert_request)
        return {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }

    def _resumable_upload(self, request) -> str:
        """断点续传上传，返回 video_id"""
        response = None
        error = None
        retry = 0
        max_retries = 10

        while response is None:
            try:
                status, response = request.next_chunk()
                if response is not None:
                    if "id" in response:
                        return response["id"]
                    else:
                        raise RuntimeError(f"上传完成但响应异常: {response}")
            except HttpError as e:
                if e.resp.status in (500, 502, 503, 504):
                    # 服务器错误，指数退避重试
                    if retry >= max_retries:
                        raise RuntimeError(f"上传失败（重试 {max_retries} 次后放弃）: {e}")
                    sleep_seconds = min(2 ** retry, 64)
                    time.sleep(sleep_seconds)
                    retry += 1
                else:
                    raise RuntimeError(f"YouTube API 错误: {e}")

        raise RuntimeError("上传循环异常退出")

    def get_channel_info(self) -> Dict[str, Any]:
        """获取频道基本信息"""
        service = self._get_service()
        resp = service.channels().list(part="snippet,statistics", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            raise RuntimeError("未找到 YouTube 频道，请确认 OAuth 账号正确")
        return items[0]


def build_oauth_flow():
    """构建 OAuth 授权 Flow（用于首次授权绑定账号）"""
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.YT_CLIENT_ID,
                "client_secret": settings.YT_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.YT_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.YT_REDIRECT_URI,
    )
    return flow
