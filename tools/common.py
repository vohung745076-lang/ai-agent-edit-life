"""Tiện ích dùng chung cho các công cụ của agent."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FF_BIN = ROOT / ".runtime" / "ffmpeg" / "bin"
FFMPEG = str(FF_BIN / "ffmpeg.exe") if (FF_BIN / "ffmpeg.exe").exists() else "ffmpeg"
FFPROBE = str(FF_BIN / "ffprobe.exe") if (FF_BIN / "ffprobe.exe").exists() else "ffprobe"

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mts", ".3gp"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run(cmd, check=True):
    """Chạy lệnh, trả về (returncode, stdout, stderr) dạng text."""
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"Lệnh lỗi ({p.returncode}): {' '.join(map(str, cmd))}\n{p.stderr[-2000:]}")
    return p.returncode, p.stdout, p.stderr


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def ffmpeg_env():
    env = dict(os.environ)
    env["PATH"] = f"{FF_BIN}{os.pathsep}{env.get('PATH', '')}"
    return env
