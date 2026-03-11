"""Instagram 发布服务（AdsPower + Playwright，含防封号行为模拟）"""
import asyncio
import os
from typing import Optional
from playwright.async_api import async_playwright, Page

from app.services.adspower import adspower_client
from app.services.instagram_login import InstagramLoginService, InstagramLoginStatus
from app.services.human_behavior import (
    human_delay, human_type, random_page_interaction, human_scroll
)
from app.models.material import Material, MaterialType


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

    def __init__(self, profile_id: str, username: str, password: str, totp_secret: Optional[str] = None):
        self.profile_id = profile_id
        self.username = username
        self.password = password
        self.totp_secret = totp_secret
        self._browser_info: Optional[dict] = None
        self._login_service = InstagramLoginService(profile_id)

    async def __aenter__(self):
        loop = asyncio.get_event_loop()
        self._browser_info = await loop.run_in_executor(
            None, lambda: adspower_client.open_browser(self.profile_id)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 发布完成后随机停留 3-10 秒再关闭（模拟真人使用后离开）
        await human_delay(3000, 10000)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: adspower_client.close_browser(self.profile_id)
        )

    async def _connect_page(self, playwright) -> tuple:
        """通过 CDP 连接 AdsPower 浏览器"""
        ws_url = self._browser_info["ws"]["puppeteer"]
        browser = await playwright.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        pages = context.pages
        page = pages[0] if pages else await context.new_page()
        return browser, page

    async def publish(self, material: Material) -> str:
        """
        发布内容到 Instagram。
        自动判断视频/图片类型。
        返回帖子 URL。
        """
        async with async_playwright() as p:
            browser, page = await self._connect_page(p)
            try:
                # Step 1: 确保已登录
                logged_in = await self._login_service.ensure_logged_in(
                    page, self.username, self.password, self.totp_secret
                )
                if not logged_in:
                    raise RuntimeError("登录失败")

                # Step 2: 发布前预热（随机浏览主页）
                await _warmup_browse(page)

                # Step 3: 根据类型发布
                if material.material_type == MaterialType.VIDEO:
                    url = await self._publish_video(page, material)
                else:
                    url = await self._publish_image(page, material)

                # Step 4: 发布后随机浏览（不立即关闭）
                await _post_publish_browse(page)

                return url

            finally:
                await browser.close()

    async def _publish_video(self, page: Page, material: Material) -> str:
        """发布视频 Reels"""
        if not material.file_path or not os.path.exists(material.file_path):
            raise FileNotFoundError(f"视频文件不存在: {material.file_path}")

        # 点击创建按钮
        await _click_create_button(page)
        await human_delay(1000, 2000)

        # 选择 Reels
        reels_btn = page.locator('[role="menu"] >> text=/Reel/i, [role="menuitem"] >> text=/Reel/i').first
        if await reels_btn.count() == 0:
            # 尝试另一种选择方式
            reels_btn = page.get_by_text("Reel").first
        if await reels_btn.is_visible(timeout=5000):
            await human_delay(300, 800)
            await reels_btn.click()

        await human_delay(1000, 2000)

        # 上传文件
        await _upload_file(page, material.file_path)
        await human_delay(5000, 10000)  # 等待视频处理

        # 跳过裁切/效果页面（点 Next）
        await _click_next(page)
        await human_delay(1000, 2000)
        await _click_next(page)  # 可能有第二个 Next
        await human_delay(1000, 2000)

        # 输入文案
        if material.caption:
            await _fill_caption(page, material.caption)

        # 发布
        await _click_share(page)
        await human_delay(8000, 15000)  # 等待发布完成

        return await _get_post_url(page)

    async def _publish_image(self, page: Page, material: Material) -> str:
        """发布图片帖子"""
        if not material.file_path or not os.path.exists(material.file_path):
            raise FileNotFoundError(f"图片文件不存在: {material.file_path}")

        await _click_create_button(page)
        await human_delay(1000, 2000)

        # 选择 Post（图片）
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
        await human_delay(6000, 12000)

        return await _get_post_url(page)


# ──────────────────────────────────────────────
# 内部辅助函数
# ──────────────────────────────────────────────

async def _warmup_browse(page: Page):
    """发布前浏览几秒，让账号行为更自然"""
    import random
    await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    await human_delay(2000, 5000)

    # 随机滚动 1-3 次
    for _ in range(random.randint(1, 3)):
        await human_scroll(page, "down", random.randint(200, 500))
        await human_delay(1000, 3000)


async def _post_publish_browse(page: Page):
    """发布后停留浏览，不立即关闭"""
    import random
    await human_delay(2000, 5000)
    # 随机浏览一些内容
    for _ in range(random.randint(1, 2)):
        await human_scroll(page, "down", random.randint(100, 300))
        await human_delay(1500, 4000)


async def _click_create_button(page: Page):
    """点击「创建」按钮（适配中英日文界面）"""
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
    # fallback：找包含 "+" 的导航按钮
    await page.locator('a[href="/create/style/"]').first.click()


async def _upload_file(page: Page, file_path: str):
    """上传文件到文件输入框"""
    # 等待文件上传对话框或直接输入框
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
        await human_type(page, caption_area, caption[:2200])  # INS 文案上限 2200 字符


async def _click_share(page: Page):
    """点击分享/发布按钮"""
    share_btn = page.locator(
        'button:has-text("シェア"), button:has-text("Share"), '
        'button:has-text("投稿する"), div[role="button"]:has-text("Share")'
    ).first
    await human_delay(500, 1500)
    await share_btn.click()


async def _get_post_url(page: Page) -> str:
    """尝试获取发布成功后的帖子 URL"""
    try:
        view_link = page.locator(
            'a:has-text("投稿を見る"), a:has-text("View Post"), a:has-text("View Reel")'
        ).first
        if await view_link.is_visible(timeout=8000):
            href = await view_link.get_attribute("href")
            if href:
                return f"https://www.instagram.com{href}"
    except Exception:
        pass
    return "https://www.instagram.com/"
