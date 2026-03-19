"""Windows Playwright/greenlet runtime checks."""
from __future__ import annotations

import platform

VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"


def format_playwright_runtime_error(exc: BaseException) -> str | None:
    """Convert Windows greenlet DLL failures into readable messages."""
    text = f"{exc.__class__.__name__}: {exc}".lower()
    if platform.system() != "Windows":
        return None

    if "dll load failed" in text and "greenlet" in text:
        return (
            "Windows is missing the Microsoft Visual C++ runtime, so Playwright "
            "cannot load greenlet. Install Visual C++ Redistributable (x64): "
            f"{VC_REDIST_URL} . Then restart the app and retry Instagram browser publishing."
        )

    if "_greenlet" in text or "greenlet" in text:
        return (
            "Playwright could not load greenlet on Windows. "
            "This is usually caused by a missing Microsoft Visual C++ runtime. Install: "
            f"{VC_REDIST_URL}"
        )

    return None


def ensure_playwright_available():
    """Import Playwright lazily so module import does not crash immediately."""
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - 取决于目标系统环境
        friendly = format_playwright_runtime_error(exc)
        if friendly:
            raise RuntimeError(friendly) from exc
        raise
    return async_playwright


def check_playwright_runtime() -> tuple[bool, str]:
    """Quick check for startup and diagnostics scripts."""
    try:
        ensure_playwright_available()
        import greenlet  # noqa: F401
        return True, "Playwright and greenlet imported successfully."
    except Exception as exc:  # pragma: no cover - 取决于目标系统环境
        return False, format_playwright_runtime_error(exc) or str(exc)
