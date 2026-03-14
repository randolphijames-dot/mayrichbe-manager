"""Instagram 发布服务（BitBrowser + Playwright，含防封号行为模拟）"""
import asyncio
import os
from typing import Optional
from playwright.async_api import async_playwright, Page

from app.services.adspower import adspower_client
from app.services.bitbrowser import bitbrowser_client
from app.services.instagram_login import InstagramLoginService, InstagramLoginStatus
from app.models.account import BrowserType
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

    def __init__(
        self,
        profile_id: str,
        username: str,
        password: Optional[str] = None,
        totp_secret: Optional[str] = None,
        browser_type: Optional[str] = None,
    ):
        """初始化 Instagram 发布器。

        browser_type: "adspower" 或 "bitbrowser"，用于选择正确的浏览器 API。
        """
        self.profile_id = profile_id
        self.username = username
        self.password = password  # 可选：如果浏览器已登录，可以不填
        self.totp_secret = totp_secret
        # 统一成字符串，便于和 Enum / 配置对接
        self.browser_type = (getattr(browser_type, "value", browser_type) or "bitbrowser").lower()
        self._browser_info: Optional[dict] = None
        self._login_service = InstagramLoginService(profile_id)

    async def __aenter__(self):
        loop = asyncio.get_event_loop()
        # 根据 browser_type 选择正确的浏览器客户端
        browser_client = (
            bitbrowser_client
            if self.browser_type == "bitbrowser"
            else adspower_client
        )
        self._browser_info = await loop.run_in_executor(
            None, lambda: browser_client.open_browser(self.profile_id)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 发布完成后停留 1 秒再关闭（优化速度）
        await human_delay(1000, 1000)
        loop = asyncio.get_event_loop()
        # 根据 browser_type 选择正确的浏览器客户端
        browser_client = (
            bitbrowser_client
            if self.browser_type == "bitbrowser"
            else adspower_client
        )
        await loop.run_in_executor(
            None, lambda: browser_client.close_browser(self.profile_id)
        )

    async def _connect_page(self, playwright) -> tuple:
        """通过 CDP 连接 BitBrowser 指纹浏览器"""
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
        import logging
        logger = logging.getLogger(__name__)
        await _click_share(page)

        # 检测并等待 "Sharing" 上传对话框消失
        logger.info("检查是否有 Sharing 上传对话框...")
        try:
            # 等待 "Sharing" 对话框出现
            sharing_dialog = page.locator('text="Sharing"').first
            if await sharing_dialog.is_visible(timeout=3000):
                logger.info("✅ 检测到 Sharing 对话框，Instagram 正在上传...")
                # 等待对话框消失（上传完成）
                await sharing_dialog.wait_for(state="hidden", timeout=60000)  # 最多等 60 秒
                logger.info("✅ Sharing 对话框消失，上传完成！")
            else:
                logger.info("未检测到 Sharing 对话框，可能已经完成")
        except Exception as e:
            logger.info(f"等待 Sharing 完成时出现异常: {e}")

        # 再等待 2 秒确保处理完成
        await human_delay(2000, 2000)

        return await _get_post_url(page, self.username)

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

        # 检测并等待 "Sharing" 上传对话框消失
        import logging
        logger = logging.getLogger(__name__)
        logger.info("检查是否有 Sharing 上传对话框...")
        try:
            sharing_dialog = page.locator('text="Sharing"').first
            if await sharing_dialog.is_visible(timeout=3000):
                logger.info("✅ 检测到 Sharing 对话框，正在上传...")
                await sharing_dialog.wait_for(state="hidden", timeout=30000)
                logger.info("✅ 上传完成！")
        except Exception as e:
            logger.info(f"等待上传完成: {e}")

        await human_delay(2000, 2000)

        return await _get_post_url(page, self.username)


# ──────────────────────────────────────────────
# 内部辅助函数
# ──────────────────────────────────────────────

async def _warmup_browse(page: Page):
    """发布前浏览几秒，让账号行为更自然（优化速度版）"""
    import random
    await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    await human_delay(1000, 2000)  # 缩短等待

    # 只滚动 1 次（加快速度）
    await human_scroll(page, "down", random.randint(200, 400))
    await human_delay(500, 1000)  # 缩短等待


async def _post_publish_browse(page: Page):
    """发布后停留浏览，不立即关闭（优化速度版）"""
    # 只简单等待 1 秒（大幅加快速度）
    await human_delay(1000, 1000)


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
    """直接点击 Share 按钮 - 最简单直接的方式"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("🎯 直接点击 Share 按钮！")
    logger.info("=" * 50)

    # 使用 Playwright 的真实点击，不用 JavaScript
    try:
        # 查找包含 "Share" 文本的按钮
        share_button = page.get_by_role("button", name="Share").first

        logger.info("等待 Share 按钮可见...")
        await share_button.wait_for(state="visible", timeout=10000)

        logger.info("Share 按钮已找到，准备点击...")

        # 强制点击，忽略任何遮挡
        await share_button.click(force=True, timeout=5000)

        logger.info("✅ 已点击 Share 按钮！")

    except Exception as e:
        logger.error(f"❌ 点击 Share 按钮失败: {e}")
        await page.screenshot(path="/tmp/ig_share_error.png", full_page=True)
        raise RuntimeError(f"无法点击 Share 按钮: {e}")

    # 只等待 2 秒（加快速度）
    logger.info("等待 2 秒...")
    await human_delay(2000, 2000)

    logger.info("=" * 50)


async def _check_publish_errors(page: Page):
    """检查发布过程中是否有错误提示"""
    import logging
    logger = logging.getLogger(__name__)

    # 检查常见的错误提示
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
            screenshot_path = f"/tmp/ig_publish_error_{int(asyncio.get_event_loop().time())}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            raise RuntimeError(f"Instagram 发布失败: {error_text}。截图已保存至: {screenshot_path}")


async def _get_post_url(page: Page, username: str) -> str:
    """尝试获取发布成功后的帖子 URL。如果找不到，说明发布失败。"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # 检查是否弹出了"分享到其他平台"对话框（发布成功的标志）
        logger.info("检查是否有分享对话框...")
        share_dialog_visible = False
        try:
            share_dialog = page.locator('div[role="dialog"]').filter(has_text="Share").first
            share_dialog_visible = await share_dialog.is_visible(timeout=8000)
            if not share_dialog_visible:
                # 尝试其他检测方式
                share_text = await page.locator('text="Share"').first.is_visible(timeout=3000)
                if share_text:
                    share_dialog_visible = True
        except Exception as e:
            logger.info(f"检查分享对话框异常: {e}")

        if share_dialog_visible:
            logger.info("✅ 检测到「Share」对话框，发布成功！正在关闭对话框...")

            # 保存对话框截图
            await page.screenshot(path="/tmp/ig_share_dialog.png", full_page=True)

            # 方案1：按 ESC 键关闭
            await page.keyboard.press("Escape")
            await human_delay(2000, 3000)

            # 检查是否关闭成功
            try:
                still_visible = await share_dialog.is_visible(timeout=1000)
                if still_visible:
                    logger.info("ESC 未关闭，尝试点击 X 按钮...")
                    # 方案2：查找并点击 X 关闭按钮
                    close_clicked = await page.evaluate(
                        """() => {
                            const dialog = document.querySelector('div[role="dialog"]');
                            if (!dialog) return false;

                            // 查找 X 按钮（通常在右上角）
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

        # 等待"查看帖子"链接出现（发布成功的标志）
        view_link = page.locator(
            'a:has-text("投稿を見る"), a:has-text("View Post"), a:has-text("View Reel"), '
            'a:has-text("View post"), a:has-text("View reel"), a:has-text("View your Reel")'
        ).first

        logger.info("等待「查看帖子」链接出现...")
        if await view_link.is_visible(timeout=15000):  # 增加到 15 秒
            href = await view_link.get_attribute("href")
            if href:
                logger.info(f"发布成功，帖子 URL: {href}")
                return f"https://www.instagram.com{href}"

        # 如果没有找到"查看帖子"链接，尝试从当前 URL 获取
        # 发布成功后，URL 可能会变成帖子页面
        current_url = page.url
        if "/reel/" in current_url or "/p/" in current_url:
            logger.info(f"从 URL 获取帖子链接: {current_url}")
            return current_url

        # 如果之前检测到了 Share 对话框，说明发布成功了
        # 即使找不到具体的帖子链接，也认为成功
        if share_dialog_visible:
            logger.info("虽然未找到帖子链接，但 Share 对话框出现说明发布成功")
            # 返回用户主页，用户可以手动查看最新帖子
            return f"https://www.instagram.com/{username}/"

        # 没有找到链接，也没有检测到 Share 对话框，可能发布失败
        logger.error("未找到「查看帖子」链接，且未检测到 Share 对话框")
        screenshot_path = f"/tmp/ig_publish_failed_{int(asyncio.get_event_loop().time())}.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        logger.error(f"已保存截图: {screenshot_path}")
        raise RuntimeError(f"发布后未找到「查看帖子」链接，可能发布失败。页面截图已保存至: {screenshot_path}")

    except Exception as e:
        if "未找到" in str(e) or "可能发布失败" in str(e):
            raise  # 重新抛出我们的自定义异常
        logger.error(f"获取帖子 URL 时出错: {e}")
        raise RuntimeError(f"发布验证失败: {e}")
