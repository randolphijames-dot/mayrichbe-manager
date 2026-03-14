"""数据库初始化：建表 + 安全迁移新列"""
from app.db.base import Base
from app.db.session import engine

# 导入所有 model 确保 Base 能发现它们
from app.models.account import Account  # noqa
from app.models.material import Material, material_account_association  # noqa
from app.models.task import PublishTask  # noqa
from app.models.log import PublishLog  # noqa
from app.models.oauth_state import OAuthState  # noqa
from app.models.post_metric import PostMetricSnapshot  # noqa


def init_db() -> None:
    """
    创建所有表（全新数据库）。
    如果表已存在，执行安全迁移（只增列，不删列）。
    """
    Base.metadata.create_all(bind=engine)
    _safe_migrate()


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
        ("materials", "folder_tag", "VARCHAR(50)"),
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
