"""共享依赖：用户身份 + 数据所有权验证（Phase 2 数据隔离）"""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session


def get_current_user(request: Request) -> dict:
    """从 request.state.user 获取当前用户信息（中间件已解析 JWT）。

    返回 dict: {"user_id": int, "username": str, "is_admin": bool}
    """
    user = getattr(request.state, "user", None)
    if not user or not user.get("user_id"):
        raise HTTPException(status_code=401, detail="未登录")
    return user


def apply_owner_filter(query, model, user: dict):
    """根据用户角色过滤查询：

    - admin  → 不加过滤（看全部数据）
    - 普通用户 → 只看 owner_id == user_id
    """
    if user.get("is_admin"):
        return query
    return query.filter(model.owner_id == user["user_id"])


def verify_ownership(db: Session, model, obj_id: int, user: dict):
    """查询单个对象并验证所有权。

    - admin 可以访问任何对象
    - 普通用户只能访问 owner_id == user_id 的对象
    返回对象实例，不通过则抛 404 或 403。
    """
    obj = db.query(model).filter(model.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="资源不存在")
    if not user.get("is_admin") and getattr(obj, "owner_id", None) != user["user_id"]:
        raise HTTPException(status_code=403, detail="无权访问此资源")
    return obj


def verify_batch_ownership(db: Session, model, obj_ids: list, user: dict) -> list:
    """查询多个对象并验证所有权。

    - admin 可以访问所有对象
    - 普通用户：任何一个对象不属于自己就抛 403
    返回对象列表。
    """
    if not obj_ids:
        return []
    objs = db.query(model).filter(model.id.in_(obj_ids)).all()
    if len(objs) != len(obj_ids):
        found_ids = {o.id for o in objs}
        missing = [i for i in obj_ids if i not in found_ids]
        raise HTTPException(status_code=404, detail=f"以下 ID 不存在: {missing}")
    if not user.get("is_admin"):
        forbidden = [o.id for o in objs if getattr(o, "owner_id", None) != user["user_id"]]
        if forbidden:
            raise HTTPException(status_code=403, detail=f"无权访问以下资源: {forbidden}")
    return objs
