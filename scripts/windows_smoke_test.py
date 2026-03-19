#!/usr/bin/env python3
"""Windows/Web 打包前的关键烟雾测试。

目标：
1. 验证视频上传在 application/octet-stream 场景下仍能按后缀识别 MIME。
2. 验证视频缩略图能生成（包括无系统 ffmpeg 时的 fallback）。
3. 验证“立即发布”会推进任务状态，并写入日志，而不是前端看起来像没反应。
"""

from __future__ import annotations

import importlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _set_env(tmp_dir: Path) -> None:
    db_path = tmp_dir / "social_manager.db"
    upload_dir = tmp_dir / "uploads"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.resolve().as_posix()}"
    os.environ["UPLOAD_DIR"] = str(upload_dir)
    os.environ["SECRET_KEY"] = "windows-smoke-secret"
    os.environ["ACCESS_PASSWORD"] = ""


def _create_sample_video(tmp_dir: Path) -> Path:
    video_path = tmp_dir / "smoke-video.mp4"
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg_bin = get_ffmpeg_exe()

    subprocess.run(
        [
            ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=#0ea5e9:s=320x240:d=1",
            "-pix_fmt",
            "yuv420p",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return video_path


def main() -> int:
    tmp_dir = Path(tempfile.mkdtemp(prefix="social-manager-smoke-"))
    _set_env(tmp_dir)

    app_main = importlib.import_module("app.main")
    from fastapi.testclient import TestClient

    with TestClient(app_main.app) as client:
        account_res = client.post(
            "/api/v1/accounts/",
            json={
                "name": "Smoke Insta",
                "username": "smoke_insta",
                "platform": "instagram",
                "group_name": "smoke",
                "browser_type": "none",
            },
        )
        assert account_res.status_code == 201, account_res.text
        account_id = account_res.json()["id"]

        image_res = client.post(
            "/api/v1/materials/upload",
            files={"file": ("smoke.png", io.BytesIO(PNG_BYTES), "image/png")},
            data={"material_type": "image", "title": "smoke-image", "target_account_ids": str(account_id)},
        )
        assert image_res.status_code == 201, image_res.text
        assert image_res.json()["thumbnail_url"], image_res.text

        video_path = _create_sample_video(tmp_dir)
        with video_path.open("rb") as fh:
            video_res = client.post(
                "/api/v1/materials/upload",
                files={"file": ("smoke-video.mp4", fh, "application/octet-stream")},
                data={"material_type": "video", "title": "smoke-video", "target_account_ids": str(account_id)},
            )
        assert video_res.status_code == 201, video_res.text
        video_data = video_res.json()
        assert video_data["mime_type"] == "video/mp4", video_data
        assert video_data["thumbnail_url"], video_data

        thumb_name = Path(video_data["thumbnail_path"]).name
        thumb_path = tmp_dir / "uploads" / thumb_name
        assert thumb_path.exists(), f"缩略图文件不存在: {thumb_path}"

        task_res = client.post(
            "/api/v1/tasks/batch",
            json={
                "material_id": video_data["id"],
                "account_ids": [account_id],
                "instant": True,
                "random_offset_minutes": 0,
            },
        )
        assert task_res.status_code == 201, task_res.text
        task_id = task_res.json()[0]["id"]

        deadline = time.time() + 8
        task_data = None
        while time.time() < deadline:
            current = client.get(f"/api/v1/tasks/{task_id}")
            assert current.status_code == 200, current.text
            task_data = current.json()
            if task_data["status"] == "failed":
                break
            time.sleep(0.25)

        assert task_data is not None
        assert task_data["status"] == "failed", task_data
        assert "未存储密码" in (task_data["error_message"] or ""), task_data

        logs = client.get("/api/v1/logs/").json()
        events = {item["event"] for item in logs}
        assert "publish_start" in events, logs
        assert "publish_failed" in events, logs

    print("Windows smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
