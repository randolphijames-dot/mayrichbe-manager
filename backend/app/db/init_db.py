"""数据库初始化：建表 + 安全迁移新列 + 种子用户"""
from app.db.base import Base
from app.db.session import engine, SessionLocal

# 导入所有 model 确保 Base 能发现它们
from app.models.account import Account  # noqa
from app.models.material import Material, material_account_association  # noqa
from app.models.task import PublishTask  # noqa
from app.models.log import PublishLog  # noqa
from app.models.oauth_state import OAuthState  # noqa
from app.models.post_metric import PostMetricSnapshot  # noqa
from app.models.user import User  # noqa


def init_db() -> None:
    """
    创建所有表（全新数据库）。
    如果表已存在，执行安全迁移（只增列，不删列）。
    最后确保至少有一个 admin 用户（从环境变量种子创建）。
    """
    Base.metadata.create_all(bind=engine)
    _safe_migrate()
    _seed_admin_user()


def _safe_migrate() -> None:
    """
    SQLite 安全迁移：检查并补充新列。
    只添加不存在的列，不删除旧列，保证向后兼容。
    """
    # 新增列列表：(表名, 列名, SQL 类型 + 默认值)
    migrations = [
        ("accounts", "group_name", "VARCHAR(100)"),
        ("accounts", "browser_type", "VARCHAR(20) DEFAULT 'adspower'"),
        ("accounts", "browser_profile_id", "VARCHAR(200)"),
        ("accounts", "ins_password_encrypted", "TEXT"),
        ("accounts", "ins_totp_secret_encrypted", "TEXT"),
        ("accounts", "ins_session_id_encrypted", "TEXT"),
        ("materials", "folder_tag", "VARCHAR(50)"),
        # Phase 2: 数据隔离 — 5 张表加 owner_id（DEFAULT 1 = 归属种子 admin）
        ("accounts", "owner_id", "INTEGER DEFAULT 1"),
        ("materials", "owner_id", "INTEGER DEFAULT 1"),
        ("publish_tasks", "owner_id", "INTEGER DEFAULT 1"),
        ("publish_logs", "owner_id", "INTEGER DEFAULT 1"),
        ("post_metric_snapshots", "owner_id", "INTEGER DEFAULT 1"),
    ]

    with engine.connect() as conn:
        for table, col, col_type in migrations:
            try:
                # 检查列是否已存在
                result = conn.execute(
                    __import__("sqlalchemy").text(f"PRAGMA table_info({table})")
                )
                existing_cols = {row[1] for row in result}
                if col not in existing_cols:
                    conn.execute(
                        __import__("sqlalchemy").text(
                            f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"
                        )
                    )
                    print(f"[Migration] 新增列: {table}.{col}")
            except Exception as e:
                print(f"[Migration] 跳过 {table}.{col}: {e}")


def _seed_admin_user() -> None:
    """
    首次启动：如果 users 表为空，从环境变量 ACCESS_USERNAME / ACCESS_PASSWORD
    创建初始 admin 用户。之后所有用户管理通过数据库和 UI 完成。
    """
    from app.core.config import settings
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count > 0:
            return  # 已有用户，跳过

        username = settings.ACCESS_USERNAME or "admin"
        password = settings.ACCESS_PASSWORD
        if not password:
            print("[Seed] 未设置 ACCESS_PASSWORD，跳过创建种子用户")
            return

        admin = User(
            username=username,
            password_hash=hash_password(password),
            display_name=username,
            is_admin=True,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"[Seed] 已创建管理员用户: {username}")
    except Exception as e:
        db.rollback()
        print(f"[Seed] 创建种子用户失败: {e}")
    finally:
        db.close()
