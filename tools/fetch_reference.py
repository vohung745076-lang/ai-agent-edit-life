"""Tải video mẫu (TikTok / YouTube / Instagram / Facebook / link .mp4...) để học phong cách.

Dùng:  python tools/fetch_reference.py "<link hoặc đường dẫn file>" "styles/<slug>"

Kết quả: styles/<slug>/source/reference.mp4 (tối đa 1080p) + source/info.json
"""
import shutil
import sys
from pathlib import Path

from common import FF_BIN, VIDEO_EXT, write_json


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, style_dir = sys.argv[1], Path(sys.argv[2])
    out_dir = style_dir / "source"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "reference.mp4"

    local = Path(src)
    if local.exists() and local.suffix.lower() in VIDEO_EXT:
        shutil.copy2(local, target)
        write_json(out_dir / "info.json", {"source": str(local), "title": local.stem})
        print(f"Đã chép file mẫu vào {target}")
        return

    import yt_dlp

    opts = {
        "outtmpl": str(out_dir / "reference.%(ext)s"),
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "ffmpeg_location": str(FF_BIN),
        "noplaylist": True,
        "quiet": False,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(src, download=True)
    except Exception as e:  # noqa: BLE001
        print(f"\nLỖI TẢI VIDEO MẪU: {e}")
        print("Cách xử lý: tải video về máy rồi đưa đường dẫn file, hoặc tải lên qua giao diện.")
        sys.exit(2)

    write_json(
        out_dir / "info.json",
        {
            "source": src,
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "width": info.get("width"),
            "height": info.get("height"),
            "description": (info.get("description") or "")[:1500],
        },
    )
    print(f"Đã tải video mẫu vào {target}")


if __name__ == "__main__":
    main()
