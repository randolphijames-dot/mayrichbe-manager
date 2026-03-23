"""
账号养号任务：模拟真实用户行为，提升账号权重，降低封号风险。
支持指纹浏览器模式和 instagrapi(无浏览器) 模式。
"""
import asyncio
import random
import time
import logging

logger = logging.getLogger(__name__)


def _write_warmup_log(account_id: int, success: bool, message: str, detail: str = None):
    """写养号日志到 publish_logs 表"""
    from app.db.session import SessionLocal
    from app.models.log import PublishLog, LogLevel
    from app.models.account import Account

    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        owner_id = getattr(account, 'owner_id', 1) if account else 1
        log = PublishLog(
            owner_id=owner_id,
            account_id=account_id,
            task_id=None,
            level=LogLevel.SUCCESS if success else LogLevel.ERROR,
            event="warmup_success" if success else "warmup_error",
            message=message,
            detail=detail,
        )
        db.add(log)
        db.commit()
    except Exception:
        pass  # 写日志失败不影响主流程
    finally:
        db.close()


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

        _write_warmup_log(account_id, success=True, message=f"养号完成: {account.username}")

    except Exception as e:
        logger.error(f"养号失败（{account_id}）: {e}")
        _account_name = account.username if 'account' in locals() and account else str(account_id)
        _write_warmup_log(account_id, success=False, message=f"养号失败: {_account_name}", detail=str(e))
    finally:
        db.close()


def _warmup_instagrapi(account):
    """使用 instagrapi 模拟手机真实使用行为（约 15-20 分钟）"""
    from app.services.instagrapi_publisher import _get_client
    from app.core.encryption import safe_decrypt

    password = safe_decrypt(account.ins_password_encrypted)
    totp = safe_decrypt(account.ins_totp_secret_encrypted) if account.ins_totp_secret_encrypted else None

    if not password:
        logger.warning(f"账号 {account.username} 未保存密码，无法执行 instagrapi 养号")
        return

    logger.info(f"开始养号 (instagrapi): {account.username}")
    cl = _get_client(account.id, account.username, password, account.proxy, totp)

    # 财经 hashtag 池
    finance_hashtags = [
        "日経平均", "株式投資", "資産形成", "FX投資", "経済ニュース",
        "投資初心者", "NISA", "iDeCo", "お金の勉強", "節約術",
        "インデックス投資", "高配当株", "仮想通貨", "不動産投資", "副業",
    ]
    liked_total = 0  # 全程累计点赞数，控制在 4 个以内

    try:
        # ── 第 1 轮：刷主页 Feed ──────────────────────────
        logger.info(f"[{account.username}] 第1轮：刷主页 Feed...")
        feed_items = cl.timeline_feed()
        # 模拟慢慢向下刷，偶尔停下来"读帖子"
        time.sleep(random.uniform(8, 20))

        if feed_items and liked_total < 4:
            # 随机给 1-2 个帖子点赞，点赞前先"看一会儿"
            for item in random.sample(feed_items, min(2, len(feed_items))):
                if not item.has_liked and liked_total < 4:
                    time.sleep(random.uniform(15, 45))  # 模拟阅读帖子内容
                    cl.media_like(item.id)
                    liked_total += 1
                    logger.info(f"[{account.username}] 点赞帖子 {item.code}（共 {liked_total} 个）")
                    time.sleep(random.uniform(5, 15))

        # 随机看一两条评论（read-only，低风险，模拟看评论区）
        if feed_items:
            pick = random.choice(feed_items[:5])
            try:
                cl.media_comments(pick.id, amount=5)
                logger.info(f"[{account.username}] 看了帖子 {pick.code} 的评论")
                time.sleep(random.uniform(20, 50))  # 模拟读评论
            except Exception:
                pass

        # ── 第 2 轮：浏览财经 Hashtag × 2 个 ───────────────
        selected_tags = random.sample(finance_hashtags, 2)
        for tag in selected_tags:
            logger.info(f"[{account.username}] 浏览财经话题 #{tag}...")
            try:
                tag_medias = cl.hashtag_medias_recent(tag, amount=12)
                time.sleep(random.uniform(10, 25))  # 模拟刚进话题页，扫一眼封面

                if tag_medias:
                    # 随机打开 1 个帖子"看内容"
                    pick = random.choice(tag_medias[:8])
                    try:
                        cl.media_comments(pick.id, amount=5)
                        logger.info(f"[{account.username}] 打开了财经帖子 {pick.code}")
                        time.sleep(random.uniform(25, 60))  # 模拟认真读财经内容
                    except Exception:
                        time.sleep(random.uniform(15, 35))

                    # 概率点赞（50% 概率，上限 4 个）
                    if liked_total < 4 and random.random() < 0.5:
                        for item in random.sample(tag_medias, min(1, len(tag_medias))):
                            if not item.has_liked:
                                cl.media_like(item.id)
                                liked_total += 1
                                logger.info(f"[{account.username}] 点赞财经帖 #{tag}（共 {liked_total} 个）")
                                time.sleep(random.uniform(8, 20))
                                break
            except Exception as e:
                logger.warning(f"[{account.username}] #{tag} 浏览失败（跳过）: {e}")

            # 话题之间模拟"退回去想想，再刷一会儿"
            time.sleep(random.uniform(30, 90))

        # ── 第 3 轮：刷 Explore 发现页 ───────────────────
        logger.info(f"[{account.username}] 第3轮：刷 Explore 发现页...")
        try:
            cl.explore()
            time.sleep(random.uniform(20, 50))
        except Exception:
            pass

        # ── 第 4 轮：看 Story ─────────────────────────────
        if feed_items:
            target_user = random.choice(feed_items[:8]).user
            try:
                user_stories = cl.user_stories(target_user.pk)
                if user_stories:
                    story_watch = random.uniform(4, 10) * len(user_stories[:5])
                    logger.info(f"[{account.username}] 看了 {target_user.username} 的 Story（约 {int(story_watch)}s）")
                    time.sleep(story_watch)
            except Exception:
                pass

        # ── 收尾：模拟放下手机前最后一次刷 Feed ─────────────
        time.sleep(random.uniform(15, 40))
        logger.info(f"养号完成 (instagrapi): {account.username}，共点赞 {liked_total} 个")

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

                # 3. 刷 Reels（5-10 轮，每轮停留更长，模拟认真看视频）
                await page.goto("https://www.instagram.com/reels/", wait_until="domcontentloaded")
                await human_delay(2000, 4000)
                reel_rounds = random.randint(5, 10)
                for i in range(reel_rounds):
                    await human_scroll(page, "down", random.randint(300, 600))
                    watch_time = random.randint(8000, 25000)  # 每个 Reel 看 8-25 秒
                    await human_delay(watch_time, watch_time + 3000)
                    # 30% 概率点赞当前 Reel
                    if random.random() < 0.3:
                        like_btns = await page.locator('svg[aria-label="Like"], svg[aria-label="いいね！"]').all()
                        if like_btns:
                            try:
                                await like_btns[0].click()
                                await human_delay(1000, 3000)
                            except Exception:
                                pass

                # 4. 浏览 2 个财经 hashtag 页面（各停留 1-3 分钟）
                finance_hashtags = [
                    "日経平均", "株式投資", "資産形成", "FX投資", "NISA",
                    "投資初心者", "お金の勉強", "高配当株", "インデックス投資", "副業",
                ]
                for tag in random.sample(finance_hashtags, 2):
                    logger.info(f"[{account.username}] 浏览财经话题页 #{tag}...")
                    await page.goto(f"https://www.instagram.com/explore/tags/{tag}/", wait_until="domcontentloaded")
                    await human_delay(3000, 6000)
                    # 滚动浏览话题下的帖子
                    for _ in range(random.randint(3, 6)):
                        await human_scroll(page, "down", random.randint(200, 400))
                        await human_delay(4000, 12000)  # 模拟看封面图停留

                    # 随机点开一个帖子看详情（停留 20-50 秒）
                    posts = await page.locator("article a").all()
                    if posts:
                        try:
                            await random.choice(posts[:6]).click()
                            await human_delay(20000, 50000)
                            await page.go_back()
                            await human_delay(2000, 4000)
                        except Exception:
                            pass

                    # 话题之间模拟退出、停顿
                    await human_delay(15000, 40000)

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

        # 通知：养号已触发
        try:
            from app.services.notify import _send_all
            count = len(accounts)
            _send_all(f"🏃 批量养号已开始：共 {count} 个账号，每账号间隔 2-5 分钟后台执行")
        except Exception:
            pass

    finally:
        db.close()
