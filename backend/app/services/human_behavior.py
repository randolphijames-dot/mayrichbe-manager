"""人类行为模拟模块：让自动化操作更像真人，减少被检测风险"""
import asyncio
import random
import math
from typing import Optional
from playwright.async_api import Page


# ──────────────────────────────────────────────
# 延迟工具
# ──────────────────────────────────────────────

async def human_delay(min_ms: int = 500, max_ms: int = 2000):
    """随机延迟，模拟人类思考时间（正态分布，更真实）"""
    mean = (min_ms + max_ms) / 2
    std = (max_ms - min_ms) / 6
    delay_ms = max(min_ms, min(max_ms, random.gauss(mean, std)))
    await asyncio.sleep(delay_ms / 1000)


async def typing_delay():
    """按键间隔延迟（50-200ms，模拟真人打字速度）"""
    await asyncio.sleep(random.uniform(0.05, 0.2))


# ──────────────────────────────────────────────
# 鼠标行为模拟
# ──────────────────────────────────────────────

async def human_move_and_click(page: Page, selector: str, timeout: int = 10000):
    """人类鼠标轨迹：先移动到元素附近，再精确点击"""
    element = page.locator(selector).first
    await element.wait_for(timeout=timeout)
    box = await element.bounding_box()
    if not box:
        await element.click()
        return

    # 计算点击位置（在元素内随机偏移，非正中心）
    target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
    target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

    # 贝塞尔曲线鼠标移动（模拟真实轨迹）
    await _bezier_mouse_move(page, target_x, target_y)
    await human_delay(50, 200)
    await page.mouse.click(target_x, target_y)


async def _bezier_mouse_move(page: Page, end_x: float, end_y: float, steps: int = 20):
    """贝塞尔曲线鼠标移动，模拟真实手部抖动"""
    # 获取当前鼠标位置（估算起点）
    start_x = end_x + random.uniform(-200, 200)
    start_y = end_y + random.uniform(-100, 100)

    # 随机控制点（让曲线有自然弯曲）
    ctrl_x = (start_x + end_x) / 2 + random.uniform(-50, 50)
    ctrl_y = (start_y + end_y) / 2 + random.uniform(-50, 50)

    for i in range(steps + 1):
        t = i / steps
        # 二次贝塞尔曲线公式
        x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * end_x
        y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * end_y
        # 加入微小抖动
        x += random.uniform(-1, 1)
        y += random.uniform(-1, 1)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.005, 0.02))


# ──────────────────────────────────────────────
# 打字行为模拟
# ──────────────────────────────────────────────

async def human_type(page: Page, selector: str, text: str, clear_first: bool = True):
    """模拟人类打字：逐字输入，随机速度，偶尔"出错再纠正"""
    element = page.locator(selector).first

    if clear_first:
        await element.click()
        await asyncio.sleep(0.3)
        # 用快捷键全选删除（更真实）
        await page.keyboard.press("Meta+a" if "mac" in (await page.evaluate("navigator.platform")).lower() else "Control+a")
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.2)

    for char in text:
        # 偶尔（3% 概率）输入错误字符再删除
        if random.random() < 0.03 and char.isalpha():
            wrong = random.choice("qwertyuiopasdfghjklzxcvbnm")
            await element.type(wrong)
            await asyncio.sleep(random.uniform(0.1, 0.4))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.1, 0.3))

        await element.type(char)
        await typing_delay()

    await human_delay(200, 500)


# ──────────────────────────────────────────────
# 滚动行为模拟
# ──────────────────────────────────────────────

async def human_scroll(page: Page, direction: str = "down", distance: int = None):
    """模拟人类滚动页面（分段、变速）"""
    if distance is None:
        distance = random.randint(200, 600)

    segments = random.randint(3, 8)
    per_segment = distance // segments

    for _ in range(segments):
        delta = per_segment + random.randint(-20, 20)
        await page.mouse.wheel(0, delta if direction == "down" else -delta)
        await asyncio.sleep(random.uniform(0.05, 0.3))


async def random_page_interaction(page: Page):
    """发布前随机浏览，模拟真实用户行为"""
    actions = [
        lambda: human_scroll(page, "down", random.randint(100, 400)),
        lambda: human_scroll(page, "up", random.randint(50, 200)),
        lambda: asyncio.sleep(random.uniform(1, 3)),
    ]
    # 随机执行 2-4 个动作
    for _ in range(random.randint(2, 4)):
        await random.choice(actions)()
        await human_delay(300, 1000)


# ──────────────────────────────────────────────
# 账号冷却期管理
# ──────────────────────────────────────────────

class AccountCooldownManager:
    """管理账号操作频率，防止触发限流"""

    # 每个账号每日发布上限
    DAILY_POST_LIMIT = {
        "instagram": 3,   # INS 建议每日不超过 3 帖
        "youtube": 2,     # YT 每日不超过 2 视频
    }

    # 连续发布最小间隔（秒）
    MIN_INTERVAL_BETWEEN_POSTS = {
        "instagram": 3600,    # INS：每帖最少间隔 1 小时
        "youtube": 1800,      # YT：每帖最少间隔 30 分钟
    }

    # 新账号养号期（7 天内每日只发 1 帖）
    NEW_ACCOUNT_DAYS = 7
    NEW_ACCOUNT_DAILY_LIMIT = 1

    def _get_history(self, account_id: int) -> list:
        """从数据库读取该账号最近 24 小时的发布记录"""
        from datetime import datetime, timezone, timedelta
        from app.db.session import SessionLocal
        from app.models.task import PublishTask, TaskStatus
        
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            yesterday = now - timedelta(hours=24)
            
            # 查找过去 24 小时内执行成功的任务
            tasks = db.query(PublishTask).filter(
                PublishTask.account_id == account_id,
                PublishTask.status == TaskStatus.SUCCESS,
                PublishTask.actual_executed_at >= yesterday
            ).order_by(PublishTask.actual_executed_at.asc()).all()
            
            # 返回带时区的 UTC 时间列表
            return [t.actual_executed_at.replace(tzinfo=timezone.utc) if t.actual_executed_at.tzinfo is None else t.actual_executed_at for t in tasks]
        finally:
            db.close()

    def can_post(self, account_id: int, platform: str, account_age_days: int = 30) -> tuple[bool, str]:
        """
        检查账号是否可以发布
        返回 (可发布, 原因说明)
        """
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        history = self._get_history(account_id)

        # 新账号限制
        daily_limit = self.DAILY_POST_LIMIT.get(platform, 2)
        if account_age_days < self.NEW_ACCOUNT_DAYS:
            daily_limit = self.NEW_ACCOUNT_DAILY_LIMIT

        # 检查每日上限
        if len(history) >= daily_limit:
            next_available = history[0] + timedelta(hours=24)
            return False, f"今日已发 {len(history)} 帖，明天 {next_available.strftime('%H:%M')} 后可发"

        # 检查最小间隔
        min_interval = self.MIN_INTERVAL_BETWEEN_POSTS.get(platform, 3600)
        if history:
            last_post = history[-1]
            elapsed = (now - last_post).total_seconds()
            if elapsed < min_interval:
                wait_secs = min_interval - elapsed
                return False, f"距上次发布才 {int(elapsed)//60} 分钟，需再等 {int(wait_secs)//60} 分钟"

        return True, "ok"

    def record_post(self, account_id: int):
        """记录一次发布（现在由数据库任务状态自动记录，此方法保留为空实现兼容）"""
        pass


# 全局单例
cooldown_manager = AccountCooldownManager()
