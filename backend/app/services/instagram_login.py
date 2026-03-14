"""Instagram 登录服务：处理首次登录、二步验证、登录状态维持"""
import asyncio
import random
import os
from typing import Optional
from playwright.async_api import Page, async_playwright

from app.services.adspower import adspower_client
from app.services.human_behavior import human_type, human_delay, human_move_and_click, random_page_interaction


class InstagramLoginStatus:
    LOGGED_IN = "logged_in"
    NEEDS_LOGIN = "needs_login"
    NEEDS_2FA = "needs_2fa"
    CHECKPOINT = "checkpoint"       # 需要邮件/手机验证
    CAPTCHA = "captcha"             # 出现 CAPTCHA
    SUSPENDED = "suspended"         # 账号被封
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
            title = await page.title()

            # 被封禁
            if "challenge" in url and "action=deactivated" in url:
                return InstagramLoginStatus.SUSPENDED

            # 登录成功标志：URL 不跳转到 login，且有导航栏
            if "login" not in url and "challenge" not in url:
                # 检查是否有用户头像/导航（登录后才有）
                nav_exists = await page.locator('[role="navigation"]').count() > 0
                if nav_exists:
                    return InstagramLoginStatus.LOGGED_IN

            # checkpoint 验证
            if "checkpoint" in url:
                return InstagramLoginStatus.CHECKPOINT

            # 二步验证
            if "two_factor" in url or "two-factor" in url:
                return InstagramLoginStatus.NEEDS_2FA

            # CAPTCHA
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
        """
        执行登录流程。
        
        返回值：InstagramLoginStatus 枚举值
        
        登录成功后 Cookie 自动保存到浏览器 Profile，
        下次打开同一 Profile 时无需重新登录。
        """
        # 有些网络环境下 IG 长时间保持长连接，networkidle 很难达成，这里放宽为 domcontentloaded 并拉长超时时间
        await page.goto(self.INS_LOGIN, wait_until="domcontentloaded", timeout=60000)
        await human_delay(2000, 4000)

        # 随机浏览一会儿（模拟真人进入）
        await random_page_interaction(page)

        # 输入用户名
        username_sel = 'input[name="username"]'
        await page.wait_for_selector(username_sel, timeout=10000)
        await human_type(page, username_sel, username)
        await human_delay(500, 1500)

        # 输入密码
        password_sel = 'input[name="password"]'
        await human_type(page, password_sel, password)
        await human_delay(800, 2000)

        # 点击登录按钮
        login_btn = page.locator('button[type="submit"]').first
        await login_btn.click()

        # 等待页面变化：先简单等待 + domcontentloaded，避免因长期长连接导致 networkidle 超时
        await asyncio.sleep(3)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception:
            # 即便未达到 domcontentloaded，也继续后续检查，由后续逻辑判断是否登录成功
            pass
        await human_delay(2000, 4000)

        # 检测登录结果
        url = page.url

        # 二步验证
        if "two_factor" in url or "two-factor" in url:
            if totp_secret:
                return await self._handle_2fa_totp(page, totp_secret)
            return InstagramLoginStatus.NEEDS_2FA

        # checkpoint（需要手机/邮件验证码）
        if "checkpoint" in url:
            return InstagramLoginStatus.CHECKPOINT

        # CAPTCHA
        captcha = await page.locator('[id*="captcha"]').count()
        if captcha > 0:
            return InstagramLoginStatus.CAPTCHA

        # 账号被封
        if "action=deactivated" in url:
            return InstagramLoginStatus.SUSPENDED

        # 错误提示（密码错误等）
        error = await page.locator('[role="alert"], #slfErrorAlert').count()
        if error > 0:
            error_text = await page.locator('[role="alert"]').first.text_content()
            raise ValueError(f"登录失败: {error_text}")

        # 处理「保存登录信息」弹窗
        save_login = page.locator('button:has-text("Not now"), button:has-text("今はしない"), button:has-text("以后再说")')
        if await save_login.count() > 0:
            await human_delay(1000, 2000)
            await save_login.first.click()

        # 处理通知权限弹窗
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

            # 等待验证码输入框
            code_input = page.locator('input[name="verificationCode"], input[aria-label*="code"]').first
            await code_input.wait_for(timeout=10000)
            await human_type(page, 'input[name="verificationCode"]', code)
            await human_delay(500, 1500)

            confirm_btn = page.locator('button[type="button"]:has-text("Confirm"), button:has-text("確認")').first
            await confirm_btn.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            return InstagramLoginStatus.LOGGED_IN

        except ImportError:
            # pyotp 未安装，返回需要人工处理
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
        """
        确保账号已登录（先检查，未登录则执行登录）。
        返回 True 表示已登录可操作。
        
        如果浏览器已登录，password 可以为 None。
        如果未登录且没有 password，会抛出错误提示手动登录。
        """
        status = await self.check_login_status(page)

        # 如果当前已经在 instagram.com 主页（例如用户手动登录后停留在首页），
        # 即便 check_login_status 返回的是 UNKNOWN，也直接视为已登录。
        current_url = page.url or ""
        if "instagram.com" in current_url and "/accounts/login" not in current_url:
            return True

        if status == InstagramLoginStatus.LOGGED_IN:
            return True

        if status == InstagramLoginStatus.SUSPENDED:
            raise RuntimeError(f"账号 {username} 已被封禁")

        if status in (InstagramLoginStatus.CAPTCHA, InstagramLoginStatus.CHECKPOINT):
            raise RuntimeError(f"账号 {username} 需要人工验证（{status}），请在比特浏览器中手动处理后重试")

        # 未登录但没有密码
        if not password:
            raise RuntimeError(f"账号 {username} 未登录，且未配置密码。请在比特浏览器中手动登录，或在系统中配置密码")

        if status == InstagramLoginStatus.NEEDS_LOGIN:
            result = await self.login(page, username, password, totp_secret)
            if result == InstagramLoginStatus.LOGGED_IN:
                return True
            raise RuntimeError(f"登录失败，状态: {result}，请人工处理")

        return False
