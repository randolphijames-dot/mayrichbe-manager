"""Instagram 登录服务：处理首次登录、二步验证、登录状态维持"""
import asyncio
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page
else:
    Page = Any

from app.services.human_behavior import human_type, human_delay, random_page_interaction


class InstagramLoginStatus:
    LOGGED_IN = "logged_in"
    NEEDS_LOGIN = "needs_login"
    NEEDS_2FA = "needs_2fa"
    CHECKPOINT = "checkpoint"
    CAPTCHA = "captcha"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class InstagramLoginService:
    """
    Instagram 登录管理。

    关键规则：
    1. 每个账号用独立 AdsPower Profile（独立指纹 + 独立代理）
    2. 首次登录后 Cookie 存储在 Profile 中，不需要每次重登
    3. 每次打开浏览器先检查是否已登录，如已登录直接用
    4. 登录失败分类处理（2FA / checkpoint / CAPTCHA）
    """

    INS_HOME = "https://www.instagram.com/"
    INS_LOGIN = "https://www.instagram.com/accounts/login/"

    def __init__(self, profile_id: str):
        self.profile_id = profile_id
        self._browser_info: Optional[dict] = None

    async def check_login_status(self, page: Page) -> str:
        """检测当前页面的登录状态"""
        try:
            await page.goto(self.INS_HOME, wait_until="domcontentloaded", timeout=30000)
            await human_delay(1500, 3000)

            url = page.url

            if "challenge" in url and "action=deactivated" in url:
                return InstagramLoginStatus.SUSPENDED

            if "login" not in url and "challenge" not in url:
                nav_exists = await page.locator('[role="navigation"]').count() > 0
                if nav_exists:
                    return InstagramLoginStatus.LOGGED_IN

            if "checkpoint" in url:
                return InstagramLoginStatus.CHECKPOINT

            if "two_factor" in url or "two-factor" in url:
                return InstagramLoginStatus.NEEDS_2FA

            captcha = await page.locator('[id*="captcha"], [class*="captcha"]').count()
            if captcha > 0:
                return InstagramLoginStatus.CAPTCHA

            return InstagramLoginStatus.NEEDS_LOGIN

        except Exception:
            return InstagramLoginStatus.UNKNOWN

    async def login(
        self,
        page: Page,
        username: str,
        password: str,
        totp_secret: Optional[str] = None,
    ) -> str:
        """执行登录流程。"""
        await page.goto(self.INS_LOGIN, wait_until="domcontentloaded", timeout=60000)
        await human_delay(2000, 4000)
        await random_page_interaction(page)

        username_sel = 'input[name="username"]'
        await page.wait_for_selector(username_sel, timeout=10000)
        await human_type(page, username_sel, username)
        await human_delay(500, 1500)

        password_sel = 'input[name="password"]'
        await human_type(page, password_sel, password)
        await human_delay(800, 2000)

        login_btn = page.locator('button[type="submit"]').first
        await login_btn.click()

        await asyncio.sleep(3)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception:
            pass
        await human_delay(2000, 4000)

        url = page.url
        if "two_factor" in url or "two-factor" in url:
            if totp_secret:
                return await self._handle_2fa_totp(page, totp_secret)
            return InstagramLoginStatus.NEEDS_2FA

        if "checkpoint" in url:
            return InstagramLoginStatus.CHECKPOINT

        captcha = await page.locator('[id*="captcha"]').count()
        if captcha > 0:
            return InstagramLoginStatus.CAPTCHA

        if "action=deactivated" in url:
            return InstagramLoginStatus.SUSPENDED

        error = await page.locator('[role="alert"], #slfErrorAlert').count()
        if error > 0:
            error_text = await page.locator('[role="alert"]').first.text_content()
            raise ValueError(f"登录失败: {error_text}")

        save_login = page.locator(
            'button:has-text("Not now"), button:has-text("今はしない"), button:has-text("以后再说")'
        )
        if await save_login.count() > 0:
            await human_delay(1000, 2000)
            await save_login.first.click()

        await asyncio.sleep(2)
        notif_btn = page.locator('button:has-text("Not Now"), button:has-text("今はしない")')
        if await notif_btn.count() > 0:
            await human_delay(500, 1500)
            await notif_btn.first.click()

        return InstagramLoginStatus.LOGGED_IN

    async def _handle_2fa_totp(self, page: Page, totp_secret: str) -> str:
        """处理 TOTP 二步验证（Google Authenticator 类型）"""
        try:
            import pyotp
            totp = pyotp.TOTP(totp_secret)
            code = totp.now()

            code_input = page.locator('input[name="verificationCode"], input[aria-label*="code"]').first
            await code_input.wait_for(timeout=10000)
            await human_type(page, 'input[name="verificationCode"]', code)
            await human_delay(500, 1500)

            confirm_btn = page.locator(
                'button[type="button"]:has-text("Confirm"), button:has-text("確認")'
            ).first
            await confirm_btn.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            return InstagramLoginStatus.LOGGED_IN

        except ImportError:
            return InstagramLoginStatus.NEEDS_2FA
        except Exception as e:
            raise RuntimeError(f"2FA 处理失败: {e}")

    async def ensure_logged_in(
        self,
        page: Page,
        username: str,
        password: Optional[str] = None,
        totp_secret: Optional[str] = None,
    ) -> bool:
        """确保账号已登录。"""
        status = await self.check_login_status(page)
        current_url = page.url or ""
        if "instagram.com" in current_url and "/accounts/login" not in current_url:
            return True

        if status == InstagramLoginStatus.LOGGED_IN:
            return True

        if status == InstagramLoginStatus.SUSPENDED:
            raise RuntimeError(f"账号 {username} 已被封禁")

        if status in (InstagramLoginStatus.CAPTCHA, InstagramLoginStatus.CHECKPOINT):
            raise RuntimeError(f"账号 {username} 需要人工验证（{status}），请在比特浏览器中手动处理后重试")

        if not password:
            raise RuntimeError(f"账号 {username} 未登录，且未配置密码。请在比特浏览器中手动登录，或在系统中配置密码")

        if status == InstagramLoginStatus.NEEDS_LOGIN:
            result = await self.login(page, username, password, totp_secret)
            if result == InstagramLoginStatus.LOGGED_IN:
                return True
            raise RuntimeError(f"登录失败，状态: {result}，请人工处理")

        return False
