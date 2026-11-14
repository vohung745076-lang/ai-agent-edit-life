"""Tải video từ link Google Drive (thư mục hoặc file) về projects/<id>/raw.

Dùng:  python tools/drive_fetch.py "<link drive>" "projects/<id>"

Link phải ở chế độ "Bất kỳ ai có đường liên kết đều xem được".
Thoát mã 2 kèm hướng dẫn nếu link riêng tư / không tải được.
"""
import re
import sys
from pathlib import Path

from common import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT, write_json


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    link, project = sys.argv[1], Path(sys.argv[2])
    raw = project / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    import gdown

    try:
        if "/folders/" in link:
            # remaining_ok chỉ có ở gdown < 5; bản mới đã bỏ tham số này.
            try:
                files = gdown.download_folder(url=link, output=str(raw), quiet=False, remaining_ok=True)
            except TypeError:
                files = gdown.download_folder(url=link, output=str(raw), quiet=False)
            if not files:
                raise RuntimeError("Thư mục trống hoặc không có quyền xem.")
        else:
            m = re.search(r"/d/([\w-]+)|[?&]id=([\w-]+)", link)
            if not m:
                raise RuntimeError("Không nhận ra ID file trong link.")
            fid = m.group(1) or m.group(2)
            out = gdown.download(id=fid, output=str(raw) + "/", quiet=False)
            if not out:
                raise RuntimeError("Không tải được file.")
    except Exception as e:  # noqa: BLE001
        print(f"\nLỖI TẢI DRIVE: {e}")
        print(
            "Cách xử lý: (1) mở quyền 'Bất kỳ ai có đường liên kết' cho thư mục; "
            "(2) thư mục >50 file thì chia nhỏ; "
            "(3) hoặc chép video thẳng vào thư mục raw của dự án rồi chạy lại bước phân tích."
        )
        sys.exit(2)

    items = []
    for p in sorted(raw.rglob("*")):
        if p.is_file():
            ext = p.suffix.lower()
            kind = "video" if ext in VIDEO_EXT else "image" if ext in IMAGE_EXT else "audio" if ext in AUDIO_EXT else "other"
            items.append({"file": p.relative_to(project).as_posix(), "kind": kind, "bytes": p.stat().st_size})
    write_json(project / "raw_manifest.json", {"source": link, "items": items})
    n = sum(1 for i in items if i["kind"] == "video")
    print(f"\nĐã tải {len(items)} file ({n} video) vào {raw}")


if __name__ == "__main__":
    main()
