"""Instagram 发布服务（BitBrowser + Playwright，含防封号行为模拟）"""
import asyncio
import os
import tempfile
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page
else:
    Page = Any

from app.core.windows_runtime import ensure_playwright_available
from app.services.adspower import adspower_client
from app.services.bitbrowser import bitbrowser_client
from app.services.instagram_login import InstagramLoginService
from app.services.human_behavior import (
    human_delay, human_type, human_scroll
)
from app.models.material import Material, MaterialType


def _temp_screenshot_path(prefix: str) -> str:
    filename = f"{prefix}_{int(asyncio.get_event_loop().time())}.png"
    return os.path.join(tempfile.gettempdir(), filename)


class InstagramPublisher:
    """
    Instagram 发布器。

    防封号关键设计：
    - 使用 AdsPower 独立指纹 Profile（每账号独立）
    - 每次发布前先随机浏览（预热）
    - 所有操作加入人类延迟
    - 登录状态复用（不重复登录）
    - 发布后随机停留再退出
    """

    def __init__(
        self,
        profile_id: str,
        username: str,
        password: Optional[str] = None,
        totp_secret: Optional[str] = None,
        browser_type: Optional[str] = None,
    ):
        self.profile_id = profile_id
        self.username = username
        self.password = password
        self.totp_secret = totp_secret
        self.browser_type = (getattr(browser_type, "value", browser_type) or "bitbrowser").lower()
        self._browser_info: Optional[dict] = None
        self._login_service = InstagramLoginService(profile_id)

    async def __aenter__(self):
        loop = asyncio.get_event_loop()
        browser_client = bitbrowser_client if self.browser_type == "bitbrowser" else adspower_client
        self._browser_info = await loop.run_in_executor(
            None, lambda: browser_client.open_browser(self.profile_id)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await human_delay(1000, 1000)
        loop = asyncio.get_event_loop()
        browser_client = bitbrowser_client if self.browser_type == "bitbrowser" else adspower_client
        await loop.run_in_executor(None, lambda: browser_client.close_browser(self.profile_id))

    async def _connect_page(self, playwright) -> tuple:
        """通过 CDP 连接指纹浏览器"""
        ws_url = self._browser_info["ws"]["puppeteer"]
        browser = await playwright.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        pages = context.pages
        page = pages[0] if pages else await context.new_page()
        return browser, page

    async def publish(self, material: Material) -> str:
        """发布内容到 Instagram。"""
        async_playwright = ensure_playwright_available()
        async with async_playwright() as p:
            browser, page = await self._connect_page(p)
            try:
                logged_in = await self._login_service.ensure_logged_in(
                    page, self.username, self.password, self.totp_secret
                )
                if not logged_in:
                    raise RuntimeError("登录失败")

                await _warmup_browse(page)

                if material.material_type == MaterialType.VIDEO:
                    url = await self._publish_video(page, material)
                else:
                    url = await self._publish_image(page, material)

                await _post_publish_browse(page)
                return url
            finally:
                await browser.close()

    async def _publish_video(self, page: Page, material: Material) -> str:
        """发布视频 Reels"""
        if not material.file_path or not os.path.exists(material.file_path):
            raise FileNotFoundError(f"视频文件不存在: {material.file_path}")

        await _click_create_button(page)
        await human_delay(1000, 2000)

        reels_btn = page.locator('[role="menu"] >> text=/Reel/i, [role="menuitem"] >> text=/Reel/i').first
        if await reels_btn.count() == 0:
            reels_btn = page.get_by_text("Reel").first
        if await reels_btn.is_visible(timeout=5000):
            await human_delay(300, 800)
            await reels_btn.click()

        await human_delay(1000, 2000)
        await _upload_file(page, material.file_path)
        await human_delay(5000, 10000)

        await _click_next(page)
        await human_delay(1000, 2000)
        await _click_next(page)
        await human_delay(1000, 2000)

        if material.caption:
            await _fill_caption(page, material.caption)

        import logging
        logger = logging.getLogger(__name__)
        await _click_share(page)

        logger.info("检查是否有 Sharing 上传对话框...")
        try:
            sharing_dialog = page.locator('text="Sharing"').first
            if await sharing_dialog.is_visible(timeout=3000):
                logger.info("检测到 Sharing 对话框，Instagram 正在上传...")
                await sharing_dialog.wait_for(state="hidden", timeout=60000)
                logger.info("Sharing 对话框消失，上传完成。")
            else:
                logger.info("未检测到 Sharing 对话框，可能已经完成")
        except Exception as e:
            logger.info(f"等待 Sharing 完成时出现异常: {e}")

        await human_delay(2000, 2000)
        return await _get_post_url(page, self.username)

    async def _publish_image(self, page: Page, material: Material) -> str:
        """发布图片帖子"""
        if not material.file_path or not os.path.exists(material.file_path):
            raise FileNotFoundError(f"图片文件不存在: {material.file_path}")

        await _click_create_button(page)
        await human_delay(1000, 2000)

        post_btn = page.get_by_text("Post").first
        if await post_btn.is_visible(timeout=3000):
            await post_btn.click()
        await human_delay(1000, 2000)

        await _upload_file(page, material.file_path)
        await human_delay(3000, 6000)

        await _click_next(page)
        await human_delay(800, 1500)
        await _click_next(page)
        await human_delay(800, 1500)

        if material.caption:
            await _fill_caption(page, material.caption)

        await _click_share(page)

        import logging
        logger = logging.getLogger(__name__)
        logger.info("检查是否有 Sharing 上传对话框...")
        try:
            sharing_dialog = page.locator('text="Sharing"').first
            if await sharing_dialog.is_visible(timeout=3000):
                logger.info("检测到 Sharing 对话框，正在上传...")
                await sharing_dialog.wait_for(state="hidden", timeout=30000)
                logger.info("上传完成。")
        except Exception as e:
            logger.info(f"等待上传完成: {e}")

        await human_delay(2000, 2000)
        return await _get_post_url(page, self.username)


async def _warmup_browse(page: Page):
    """发布前浏览几秒，让账号行为更自然（优化速度版）"""
    import random
    await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    await human_delay(1000, 2000)
    await human_scroll(page, "down", random.randint(200, 400))
    await human_delay(500, 1000)


async def _post_publish_browse(page: Page):
    """发布后停留浏览，不立即关闭（优化速度版）"""
    await human_delay(1000, 1000)


async def _click_create_button(page: Page):
    """点击创建按钮（适配中英日文界面）"""
    selectors = [
        'svg[aria-label="新規投稿"]',
        'svg[aria-label="New post"]',
        '[aria-label="Create"]',
        '[data-bloks-name="bk.components.Flexbox"] svg',
    ]
    for sel in selectors:
        btn = page.locator(sel).first
        if await btn.is_visible(timeout=3000):
            await btn.click()
            return
    await page.locator('a[href="/create/style/"]').first.click()


async def _upload_file(page: Page, file_path: str):
    """上传文件到文件输入框"""
    file_input = page.locator('input[type="file"]').first
    await file_input.set_input_files(file_path)


async def _click_next(page: Page):
    """点击 Next / 次へ 按钮"""
    next_btn = page.locator(
        'button:has-text("次へ"), button:has-text("Next"), [role="button"]:has-text("Next")'
    ).first
    try:
        if await next_btn.is_visible(timeout=5000):
            await human_delay(300, 800)
            await next_btn.click()
    except Exception:
        pass


async def _fill_caption(page: Page, caption: str):
    """填写发布文案"""
    caption_area = page.locator(
        '[aria-label="キャプションを入力..."], [aria-label="Write a caption..."], '
        '[aria-label="Write a caption"], textarea[placeholder*="caption"]'
    ).first
    if await caption_area.is_visible(timeout=5000):
        await human_type(page, caption_area, caption[:2200])


async def _click_share(page: Page):
    """直接点击 Share 按钮"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("直接点击 Share 按钮")
    logger.info("=" * 50)

    try:
        share_button = page.get_by_role("button", name="Share").first
        logger.info("等待 Share 按钮可见...")
        await share_button.wait_for(state="visible", timeout=10000)
        logger.info("Share 按钮已找到，准备点击...")
        await share_button.click(force=True, timeout=5000)
        logger.info("已点击 Share 按钮。")
    except Exception as e:
        logger.error(f"点击 Share 按钮失败: {e}")
        screenshot_path = _temp_screenshot_path("ig_share_error")
        await page.screenshot(path=screenshot_path, full_page=True)
        raise RuntimeError(f"无法点击 Share 按钮: {e}。截图已保存至: {screenshot_path}")

    logger.info("等待 2 秒...")
    await human_delay(2000, 2000)
    logger.info("=" * 50)


async def _check_publish_errors(page: Page):
    """检查发布过程中是否有错误提示"""
    import logging
    logger = logging.getLogger(__name__)

    error_selectors = [
        '[role="alert"]',
        '[id*="error"]',
        'div:has-text("Try again")',
        'div:has-text("Something went wrong")',
        'div:has-text("エラー")',
        'div:has-text("もう一度")',
    ]

    for selector in error_selectors:
        error_elem = page.locator(selector).first
        if await error_elem.is_visible(timeout=2000):
            error_text = await error_elem.text_content()
            logger.error(f"发布时出现错误提示: {error_text}")
            screenshot_path = _temp_screenshot_path("ig_publish_error")
            await page.screenshot(path=screenshot_path, full_page=True)
            raise RuntimeError(f"Instagram 发布失败: {error_text}。截图已保存至: {screenshot_path}")


async def _get_post_url(page: Page, username: str) -> str:
    """尝试获取发布成功后的帖子 URL。"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info("检查是否有分享对话框...")
        share_dialog_visible = False
        try:
            share_dialog = page.locator('div[role="dialog"]').filter(has_text="Share").first
            share_dialog_visible = await share_dialog.is_visible(timeout=8000)
            if not share_dialog_visible:
                share_text = await page.locator('text="Share"').first.is_visible(timeout=3000)
                if share_text:
                    share_dialog_visible = True
        except Exception as e:
            logger.info(f"检查分享对话框异常: {e}")

        if share_dialog_visible:
            logger.info("检测到 Share 对话框，发布成功，正在关闭对话框...")
            await page.screenshot(path=_temp_screenshot_path("ig_share_dialog"), full_page=True)
            await page.keyboard.press("Escape")
            await human_delay(2000, 3000)

            try:
                still_visible = await share_dialog.is_visible(timeout=1000)
                if still_visible:
                    logger.info("ESC 未关闭，尝试点击 X 按钮...")
                    close_clicked = await page.evaluate(
                        """() => {
                            const dialog = document.querySelector('div[role="dialog"]');
                            if (!dialog) return false;
                            const closeBtn = dialog.querySelector('svg[aria-label*="Close"], svg[aria-label*="close"]');
                            if (closeBtn) {
                                closeBtn.closest('div[role="button"]')?.click();
                                return true;
                            }
                            return false;
                        }"""
                    )
                    if close_clicked:
                        logger.info("已点击 X 按钮")
                    await human_delay(2000, 3000)
            except Exception as e:
                logger.info(f"对话框已关闭: {e}")

        view_link = page.locator(
            'a:has-text("投稿を見る"), a:has-text("View Post"), a:has-text("View Reel"), '
            'a:has-text("View post"), a:has-text("View reel"), a:has-text("View your Reel")'
        ).first

        logger.info("等待查看帖子链接出现...")
        if await view_link.is_visible(timeout=15000):
            href = await view_link.get_attribute("href")
            if href:
                logger.info(f"发布成功，帖子 URL: {href}")
                return f"https://www.instagram.com{href}"

        current_url = page.url
        if "/reel/" in current_url or "/p/" in current_url:
            logger.info(f"从 URL 获取帖子链接: {current_url}")
            return current_url

        if share_dialog_visible:
            logger.info("虽然未找到帖子链接，但 Share 对话框出现说明发布成功")
            return f"https://www.instagram.com/{username}/"

        logger.error("未找到查看帖子链接，且未检测到 Share 对话框")
        screenshot_path = _temp_screenshot_path("ig_publish_failed")
        await page.screenshot(path=screenshot_path, full_page=True)
        logger.error(f"已保存截图: {screenshot_path}")
        raise RuntimeError(f"发布后未找到查看帖子链接，可能发布失败。页面截图已保存至: {screenshot_path}")

    except Exception as e:
        if "未找到" in str(e) or "可能发布失败" in str(e):
            raise
        logger.error(f"获取帖子 URL 时出错: {e}")
        raise RuntimeError(f"发布验证失败: {e}")
