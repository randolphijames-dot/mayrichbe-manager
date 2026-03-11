"""
账号养号任务：模拟真实用户行为，提升账号权重，降低封号风险。
支持指纹浏览器模式和 instagrapi(无浏览器) 模式。
"""
import asyncio
import random
import time
import logging

logger = logging.getLogger(__name__)


def warmup_account(account_id: int):
    """对单个账号执行养号操作"""
    from app.db.session import SessionLocal
    from app.models.account import Account, Platform, BrowserType

    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account or account.platform != Platform.INSTAGRAM:
            return

        browser_type = account.browser_type or "adspower"

        if browser_type == "none":
            # instagrapi 模式养号
            _warmup_instagrapi(account)
        else:
            # 指纹浏览器模式养号
            _warmup_browser(account, browser_type)

    except Exception as e:
        logger.error(f"养号失败（{account_id}）: {e}")
    finally:
        db.close()


def _warmup_instagrapi(account):
    """使用 instagrapi 模拟手机刷 Feed 和随机点赞"""
    from app.services.instagrapi_publisher import _get_client
    from app.core.encryption import safe_decrypt

    password = safe_decrypt(account.ins_password_encrypted)
    totp = safe_decrypt(account.ins_totp_secret_encrypted) if account.ins_totp_secret_encrypted else None
    
    if not password:
        logger.warning(f"账号 {account.username} 未保存密码，无法执行 instagrapi 养号")
        return

    logger.info(f"开始养号 (instagrapi): {account.username}")
    cl = _get_client(account.id, account.username, password, account.proxy, totp)

    try:
        # 1. 刷主页 Feed 流
        logger.info(f"[{account.username}] 正在刷主页 Feed...")
        feed_items = cl.timeline_feed()
        time.sleep(random.uniform(3, 8))

        # 随机给 1-2 个 Feed 帖子点赞
        if feed_items:
            like_count = random.randint(1, 2)
            for item in random.sample(feed_items, min(like_count, len(feed_items))):
                if not item.has_liked:
                    cl.media_like(item.id)
                    logger.info(f"[{account.username}] 点赞了帖子 {item.code}")
                    time.sleep(random.uniform(5, 15))

        # 2. 刷 Explore (发现页)
        logger.info(f"[{account.username}] 正在刷 Explore 页...")
        explore_items = cl.explore()
        time.sleep(random.uniform(5, 10))

        # 3. 随机看一个用户的 Story
        if feed_items:
            # 找一个发了帖子的用户，看看他有没有 story
            target_user = random.choice(feed_items).user
            user_stories = cl.user_stories(target_user.pk)
            if user_stories:
                logger.info(f"[{account.username}] 观看了 {target_user.username} 的 Story")
                # 模拟观看时长
                time.sleep(random.uniform(3, 8) * len(user_stories[:3]))

        logger.info(f"养号完成 (instagrapi): {account.username}")

    except Exception as e:
        logger.error(f"[{account.username}] instagrapi 养号异常: {e}")


def _warmup_browser(account, browser_type):
    """使用指纹浏览器执行养号"""
    from app.services.adspower import adspower_client
    from app.services.bitbrowser import bitbrowser_client
    from app.models.account import BrowserType

    profile_id = account.browser_profile_id or account.adspower_profile_id
    if not profile_id:
        logger.warning(f"账号 {account.username} 无指纹浏览器 Profile，跳过养号")
        return

    browser_client = bitbrowser_client if browser_type == BrowserType.BITBROWSER else adspower_client
    browser_info = browser_client.open_browser(profile_id)

    async def _run():
        from playwright.async_api import async_playwright
        from app.services.human_behavior import human_delay, human_scroll, random_page_interaction

        async with async_playwright() as p:
            ws_url = browser_info["ws"]["puppeteer"]
            browser = await p.chromium.connect_over_cdp(ws_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()

            try:
                logger.info(f"开始养号 (Browser): {account.username}")

                # 1. 访问主页，随机浏览
                await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
                await human_delay(3000, 6000)
                await random_page_interaction(page)

                # 2. 随机点赞 Feed 流里的一个帖子
                like_buttons = await page.locator('svg[aria-label="Like"], svg[aria-label="赞"]').all()
                if like_buttons:
                    # 避开已经点过赞的（通常 aria-label 会变成 Unlike/取消赞）
                    btn = random.choice(like_buttons[:5])
                    try:
                        await btn.click()
                        logger.info(f"[{account.username}] 在主页点了一个赞")
                        await human_delay(2000, 5000)
                    except:
                        pass

                # 3. 随机查看 Reels（停留 5-15 秒）
                await page.goto("https://www.instagram.com/reels/", wait_until="domcontentloaded")
                await human_delay(2000, 4000)
                for _ in range(random.randint(2, 5)):
                    await human_scroll(page, "down", random.randint(300, 600))
                    await human_delay(5000, 15000)  # 模拟认真看视频

                logger.info(f"养号完成 (Browser): {account.username}")

            finally:
                await browser.close()

    try:
        asyncio.run(_run())
    finally:
        try:
            browser_client.close_browser(profile_id)
        except Exception:
            pass


def batch_warmup(account_ids: list = None):
    """批量养号调度（由 APScheduler 调用）"""
    from app.db.session import SessionLocal
    from app.models.account import Account, Platform
    import threading

    db = SessionLocal()
    try:
        query = db.query(Account).filter(
            Account.platform == Platform.INSTAGRAM,
            Account.is_active == True,
        )
        if account_ids:
            query = query.filter(Account.id.in_(account_ids))

        accounts = query.all()
        logger.info(f"批量养号：准备执行 {len(accounts)} 个账号")

        def _run_delayed(acc_id, delay_sec):
            time.sleep(delay_sec)
            warmup_account(acc_id)

        for i, account in enumerate(accounts):
            # 每个账号间隔 2-5 分钟，避免同时操作
            delay = i * random.randint(120, 300)
            threading.Thread(target=_run_delayed, args=(account.id, delay), daemon=True).start()

    finally:
        db.close()
