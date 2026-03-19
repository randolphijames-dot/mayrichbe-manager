"""自动截流 API"""
import threading
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.account import Account

router = APIRouter(prefix="/traffic", tags=["自动截流"])

# 任务运行状态（内存，轻量跟踪）
_running_tasks: dict = {}   # task_key -> {"status": "running"/"done"/"failed", "result": ...}


class TrafficTask(BaseModel):
    account_ids: List[int]             # 用哪些账号去截流
    mode: str                          # "hashtag" 或 "competitor"
    target: str                        # hashtag 名 或 竞品账号名
    action: str = "like"               # "like" 或 "comment"
    comment_text: Optional[str] = None # 评论话术，| 分隔多条
    limit_per_account: int = 5         # 每个账号最多互动几条（≤10）


@router.post("/run")
def run_traffic_task(req: TrafficTask, db: Session = Depends(get_db)):
    """
    启动截流任务（后台异步执行）
    mode="hashtag": 从话题标签下的帖子截流
    mode="competitor": 从对标账号的粉丝截流
    """
    if req.action == "comment" and not req.comment_text:
        raise HTTPException(status_code=400, detail="选择「评论」动作时必须填写评论话术")

    accounts = db.query(Account).filter(
        Account.id.in_(req.account_ids),
        Account.platform == "instagram",
    ).all()

    if not accounts:
        raise HTTPException(status_code=400, detail="未找到有效的 Instagram 账号")

    missing_pw = [a.username for a in accounts if not a.ins_password_encrypted]
    if missing_pw:
        raise HTTPException(status_code=400, detail=f"以下账号缺少密码：{', '.join(missing_pw)}")

    # 生成唯一任务 key
    import time
    task_key = f"traffic_{int(time.time())}"
    _running_tasks[task_key] = {"status": "running", "results": [], "done": 0, "total": len(accounts)}

    def _run():
        all_results = []
        for i, acc in enumerate(accounts):
            try:
                if req.mode == "hashtag":
                    from app.services.traffic_service import traffic_by_hashtag
                    result = traffic_by_hashtag(acc, req.target, req.action, req.comment_text, req.limit_per_account)
                else:
                    from app.services.traffic_service import traffic_by_competitor
                    result = traffic_by_competitor(acc, req.target, req.action, req.comment_text, req.limit_per_account)

                all_results.append(result)
                _running_tasks[task_key]["done"] = i + 1
                _running_tasks[task_key]["results"] = all_results

                # 账号之间随机等待 2-5 分钟
                import random
                if i < len(accounts) - 1:
                    wait = random.randint(120, 300)
                    import time as _t
                    _t.sleep(wait)

            except Exception as e:
                all_results.append({"account": acc.username, "error": str(e)})

        _running_tasks[task_key]["status"] = "done"
        _running_tasks[task_key]["results"] = all_results

    threading.Thread(target=_run, daemon=True).start()

    return {
        "task_key": task_key,
        "status": "started",
        "total_accounts": len(accounts),
        "message": f"截流任务已启动，共 {len(accounts)} 个账号，每个账号最多 {req.limit_per_account} 个互动",
    }


@router.get("/status/{task_key}")
def get_task_status(task_key: str):
    """查询截流任务进度"""
    task = _running_tasks.get(task_key)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return task


@router.get("/status")
def list_recent_tasks():
    """列出最近的截流任务"""
    return list(_running_tasks.items())[-10:]
