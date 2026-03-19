"""比特浏览器（BitBrowser）API 封装
官方文档：https://doc.bitbrowser.cn/
本地 API 端口：54345
"""
import requests
import time
from typing import Optional, Dict, Any

from app.core.config import settings


class BitBrowserClient:
    """比特浏览器本地 API 客户端"""

    def __init__(self):
        self.base_url = settings.BITBROWSER_API_URL.rstrip("/")

    def _post(self, path: str, data: dict = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.post(url, json=data or {}, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if result.get("success") is False:
                raise RuntimeError(f"比特浏览器错误: {result.get('msg', '未知')}")
            return result
        except requests.RequestException as e:
            raise RuntimeError(f"比特浏览器连接失败（确认软件已启动）: {e}")

    def open_browser(self, profile_id: str) -> Dict[str, Any]:
        """
        启动浏览器窗口。
        返回 {"http": "http://127.0.0.1:PORT", "driver": "...", "ws": "..."} 统一给上层使用。
        """
        result = self._post("/browser/open", {"id": profile_id})
        data = result.get("data", {})
        # BitBrowser 返回字段为 ws / http / driver
        ws_url = data.get("ws") or data.get("webSocketDebuggerUrl", "")
        return {
            "ws": {"puppeteer": ws_url},
            "webdriver": data.get("driver", ""),
            "http": data.get("http", ""),
        }

    def close_browser(self, profile_id: str) -> None:
        """关闭浏览器窗口"""
        try:
            self._post("/browser/close", {"id": profile_id})
        except Exception:
            pass

    def create_profile(
        self,
        name: str,
        proxy: Optional[str] = None,
        group_id: str = "0",
    ) -> str:
        """
        创建新 Profile，返回 Profile ID。
        
        代理格式：http://user:pass@ip:port 或 socks5://user:pass@ip:port
        """
        payload = {
            "name": name,
            "groupId": group_id,
            "browserFingerPrint": {
                "coreVersion": "124",           # Chrome 内核版本
                "ostype": "MacIntel",
                "os": "Mac OS X",
                "userAgent": "",                # 空=自动生成
                "webrtcType": "disabled",       # 禁用 WebRTC
                "canvas": "1",                  # 随机 Canvas 指纹
                "webgl": "1",
                "timezone": "Asia/Tokyo",
                "language": "ja-JP",
            },
        }

        if proxy:
            proxy_config = _parse_proxy_for_bitbrowser(proxy)
            if proxy_config:
                payload["proxyConfig"] = proxy_config

        result = self._post("/browser/create", payload)
        return result["data"]["id"]

    def get_profile_status(self, profile_id: str) -> str:
        """检查 Profile 是否在运行"""
        try:
            result = self._post("/browser/isactive", {"id": profile_id})
            return "Active" if result.get("data", {}).get("isActive") else "Inactive"
        except Exception:
            return "Unknown"

    def list_profiles(self, page: int = 1, page_size: int = 100) -> list:
        """列出 Profile"""
        result = self._post("/browser/list", {"page": page, "pageSize": page_size})
        return result.get("data", {}).get("list", [])

    def delete_profile(self, profile_ids: list) -> None:
        """删除 Profile（物理删除）"""
        self._post("/browser/delete", {"ids": profile_ids})


def _parse_proxy_for_bitbrowser(proxy_str: str) -> Optional[dict]:
    """解析代理字符串为比特浏览器所需格式"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(proxy_str)
        proxy_type = parsed.scheme or "http"
        # 比特浏览器支持: http/https/socks5
        config = {
            "proxyType": proxy_type if proxy_type in ("http", "https", "socks5") else "http",
            "proxyHost": parsed.hostname,
            "proxyPort": str(parsed.port),
        }
        if parsed.username:
            config["proxyUserName"] = parsed.username
        if parsed.password:
            config["proxyPassword"] = parsed.password
        return config
    except Exception:
        return None


# 全局单例
bitbrowser_client = BitBrowserClient()
