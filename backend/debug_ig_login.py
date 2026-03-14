import asyncio
from pathlib import Path

from app.db.session import SessionLocal
from app.models.account import Account, Platform, BrowserType
# 导入相关模型以完成 SQLAlchemy 关系配置
from app.models import task as _task_models  # noqa: F401
from app.models import log as _log_models  # noqa: F401
from app.models import material as _material_models  # noqa: F401
from app.services.bitbrowser import bitbrowser_client
from app.services.instagram_login import InstagramLoginService
from playwright.async_api import async_playwright


BASE_DIR = Path(__file__).resolve().parent
SCREEN_DIR = BASE_DIR / "debug_screens"
SCREEN_DIR.mkdir(exist_ok=True)


def _get_first_instagram_account() -> Account:
    """获取第一个 Instagram 账号，用于调试登录。"""
    session = SessionLocal()
    try:
        acc = (
            session.query(Account)
            .filter(Account.platform == Platform.INSTAGRAM)
            .order_by(Account.id.asc())
            .first()
        )
        if not acc:
            raise SystemExit("数据库中没有 Instagram 账号可用于调试。")
        return acc
    finally:
        session.close()


async def main() -> None:
    acc = _get_first_instagram_account()
    print(f"[INFO] 使用账号: id={acc.id}, username={acc.username}")

    profile_id = acc.browser_profile_id
    if not profile_id:
        raise SystemExit("[ERROR] 该账号未配置 BitBrowser Profile ID。")

    # 打开 BitBrowser 窗口
    print(f"[STEP] 打开 BitBrowser Profile: {profile_id}")
    browser_info = bitbrowser_client.open_browser(profile_id)
    ws_url = browser_info["ws"]["puppeteer"]
    print(f"[INFO] WebSocket URL: {ws_url}")

    # 通过 Playwright 连接
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

        # 使用数据库中的加密密码（如果存在）
        from app.core.encryption import safe_decrypt
        password = safe_decrypt(acc.ins_password_encrypted) if acc.ins_password_encrypted else ""

        # 调试登录流程
        login_service = InstagramLoginService(profile_id)
        print("[STEP] 开始执行 ensure_logged_in 流程...")
        status = await login_service.ensure_logged_in(
            page,
            username=acc.username,
            password=password,
            totp_secret=None,
        )
        print(f"[RESULT] ensure_logged_in 返回状态: {status}")

        # 截一张当前页面截图
        screenshot_path = SCREEN_DIR / f"ig_login_debug_{acc.id}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"[INFO] 已保存截图: {screenshot_path}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

