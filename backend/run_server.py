"""PyInstaller 打包入口 — 启动 uvicorn 服务"""
import os
import sys
import uvicorn


def get_base_path():
    """获取基础路径（兼容 PyInstaller 打包后的路径）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


if __name__ == "__main__":
    base = get_base_path()
    os.chdir(base)

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )
