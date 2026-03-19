"""Windows 运行时兼容辅助。"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import AsyncPlaywright


VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"


def _humanize_playwright_import_error(exc: Exception) -> RuntimeError:
    msg = str(exc)
    if "greenlet" in msg.lower() or "DLL load failed" in msg:
        return RuntimeError(
            "Windows 缺少 Playwright 运行时依赖，通常是未安装 Visual C++ Redistributable (x64)。"
            f" 请先安装：{VC_REDIST_URL}，安装完成后重新启动程序。"
        )
    return RuntimeError(f"Playwright 运行时初始化失败：{msg}")


def load_async_playwright():
    """按需导入 Playwright，避免模块加载时直接炸 greenlet。"""
    try:
        from playwright.async_api import async_playwright
        return async_playwright
    except Exception as exc:  # pragma: no cover - 依赖运行环境
        raise _humanize_playwright_import_error(exc) from exc
