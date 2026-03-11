"""AdsPower API 封装：管理指纹浏览器 Profile"""
import requests
import time
from typing import Optional, Dict, Any

from app.core.config import settings


class AdsPowerClient:
    """AdsPower 本地 API 客户端（本地 HTTP 接口）"""

    def __init__(self):
        self.base_url = settings.ADSPOWER_API_URL.rstrip("/")
        self.api_key = settings.ADSPOWER_API_KEY

    def _get(self, path: str, params: dict = None) -> Dict[str, Any]:
        """发送 GET 请求到 AdsPower 本地 API"""
        url = f"{self.base_url}{path}"
        if self.api_key:
            params = params or {}
            params["serial_number"] = self.api_key
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"AdsPower 错误: {data.get('msg', '未知错误')}")
            return data
        except requests.RequestException as e:
            raise RuntimeError(f"AdsPower 连接失败: {e}")

    def _post(self, path: str, json: dict = None) -> Dict[str, Any]:
        """发送 POST 请求到 AdsPower 本地 API"""
        url = f"{self.base_url}{path}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = requests.post(url, json=json or {}, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"AdsPower 错误: {data.get('msg', '未知错误')}")
            return data
        except requests.RequestException as e:
            raise RuntimeError(f"AdsPower 连接失败: {e}")

    def create_profile(
        self,
        name: str,
        proxy: Optional[str] = None,
        group_id: str = "0",
    ) -> str:
        """创建新指纹浏览器 Profile，返回 Profile ID"""
        payload = {
            "name": name,
            "group_id": group_id,
            "browser_fingerprint": {
                "automatic_timezone": "1",
                "language": ["ja-JP", "ja", "en-US", "en"],
                "flash": "block",
                "webrtc": "disabled",  # 禁用 WebRTC 防 IP 泄露
            },
        }
        # 解析代理格式: http://user:pass@ip:port
        if proxy:
            proxy_config = _parse_proxy(proxy)
            if proxy_config:
                payload["user_proxy_config"] = proxy_config

        data = self._post("/api/v1/user/create", payload)
        return data["data"]["id"]

    def open_browser(self, profile_id: str) -> Dict[str, Any]:
        """启动指定 Profile 的浏览器，返回 WebSocket debugger URL 和 webdriver 端口"""
        data = self._get("/api/v1/browser/start", params={"user_id": profile_id})
        return data["data"]  # {"ws": {"puppeteer": "..."}, "webdriver": "..."}

    def close_browser(self, profile_id: str) -> None:
        """关闭指定 Profile 的浏览器"""
        try:
            self._get("/api/v1/browser/stop", params={"user_id": profile_id})
        except Exception:
            pass  # 关闭失败不抛出异常

    def get_profile_status(self, profile_id: str) -> str:
        """获取 Profile 状态: Active / Inactive"""
        try:
            data = self._get("/api/v1/browser/active", params={"user_id": profile_id})
            return data["data"].get("status", "Inactive")
        except Exception:
            return "Unknown"

    def delete_profile(self, profile_ids: list) -> None:
        """删除 Profile"""
        self._post("/api/v1/user/delete", {"user_ids": profile_ids})

    def list_profiles(self, group_id: str = None, page: int = 1, page_size: int = 100) -> list:
        """列出 Profile"""
        params = {"page": page, "page_size": page_size}
        if group_id:
            params["group_id"] = group_id
        data = self._get("/api/v1/user/list", params=params)
        return data["data"].get("list", [])


def _parse_proxy(proxy_str: str) -> Optional[dict]:
    """解析代理字符串为 AdsPower 所需格式
    支持格式: http://user:pass@ip:port 或 http://ip:port
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(proxy_str)
        config = {
            "proxy_soft": "other",
            "proxy_type": parsed.scheme or "http",
            "proxy_host": parsed.hostname,
            "proxy_port": str(parsed.port),
        }
        if parsed.username:
            config["proxy_user"] = parsed.username
        if parsed.password:
            config["proxy_password"] = parsed.password
        return config
    except Exception:
        return None


# 全局单例
adspower_client = AdsPowerClient()
