"""MEDIA ACQUISITION (yt-dlp): thu thập video mẫu kèm audio, phụ đề, metadata, ảnh bìa.

Dùng:
  python tools/fetch_reference.py "<link hoặc đường dẫn file>" "styles/<slug>"
        [--max-seconds 300] [--langs vi,en] [--cookies-browser chrome]

Nguồn hợp lệ: YouTube và các trang yt-dlp hỗ trợ (TikTok, Instagram, Facebook...), nguồn được cấp phép,
hoặc file video người dùng cung cấp. Video mẫu chỉ dùng để PHÂN TÍCH cách dựng, không dùng lại nội dung.

Kết quả trong styles/<slug>/source/:
  reference.mp4     video (tối đa 1080p; video dài chỉ lấy --max-seconds giây đầu)
  audio.wav         âm thanh 22.05 kHz mono cho phân tích nhịp/beat
  subtitles.json    phụ đề [{start, end, text}] (nếu nguồn có; ưu tiên phụ đề thật, sau đó phụ đề tự động)
  thumbnail.jpg     ảnh bìa (nếu có)
  info.json         metadata: tiêu đề, kênh, thời lượng, lượt xem/thích, thẻ, mô tả, chương, giấy phép, loại nguồn
Mã thoát 2 = không tải được.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

from common import FF_BIN, FFMPEG, VIDEO_EXT, run, write_json


def parse_vtt(path):
    """Đọc WebVTT/SRT thành [{start, end, text}], bỏ thẻ định dạng và dòng lặp của phụ đề tự động."""
    def sec(t):
        parts = t.replace(",", ".").split(":")
        parts = [0.0] * (3 - len(parts)) + [float(x) for x in parts]
        return round(parts[0] * 3600 + parts[1] * 60 + parts[2], 3)

    cues, last = [], ""
    blocks = re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8", errors="replace"))
    for b in blocks:
        m = re.search(r"((?:\d+:)?\d+:\d+[.,]\d+)\s*-->\s*((?:\d+:)?\d+:\d+[.,]\d+)", b)
        if not m:
            continue
        lines = b[m.end():].split("\n")[1:]
        text = " ".join(re.sub(r"<[^>]+>", "", ln).strip() for ln in lines).strip()
        text = re.sub(r"\s+", " ", text)
        if not text or text == last:
            continue
        if last and text.startswith(last):  # phụ đề tự động cuộn: chỉ giữ phần mới
            text = text[len(last):].strip() or text
        last = " ".join(re.sub(r"<[^>]+>", "", ln).strip() for ln in lines).strip()
        cues.append({"start": sec(m.group(1)), "end": sec(m.group(2)), "text": text})
    return cues


def extract_audio(video, out_dir):
    wav = out_dir / "audio.wav"
    code, _, _ = run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vn",
                      "-ac", "1", "-ar", "22050", str(wav)], check=False)
    if code != 0 or not wav.exists() or wav.stat().st_size < 2000:
        wav.unlink(missing_ok=True)
        return None
    return wav.name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("style_dir")
    ap.add_argument("--max-seconds", type=int, default=300, help="video dài hơn chỉ lấy đoạn đầu")
    ap.add_argument("--langs", default="vi,en", help="ngôn ngữ phụ đề ưu tiên")
    ap.add_argument("--cookies-browser", default="", help="vd. chrome/edge: dùng cookie trình duyệt cho nguồn cần đăng nhập")
    a = ap.parse_args()

    out_dir = Path(a.style_dir) / "source"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "reference.mp4"
    langs = [x.strip() for x in a.langs.split(",") if x.strip()]

    # ── File người dùng cung cấp ──
    local = Path(a.source)
    if local.exists() and local.suffix.lower() in VIDEO_EXT:
        if local.suffix.lower() == ".mp4":
            shutil.copy2(local, target)
        else:
            run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(local), "-c:v", "libx264",
                 "-crf", "18", "-c:a", "aac", str(target)])
        info = {"source": str(local), "source_type": "file người dùng cung cấp", "title": local.stem,
                "audio": extract_audio(target, out_dir), "subtitles": None}
        write_json(out_dir / "info.json", info)
        print(f"Đã nhận file mẫu: {target} (audio: {info['audio'] or 'không có'})")
        return

    # ── Tải bằng yt-dlp ──
    import yt_dlp
    from yt_dlp.utils import download_range_func

    base = {"ffmpeg_location": str(FF_BIN), "noplaylist": True, "quiet": True, "no_warnings": True}
    if a.cookies_browser:
        base["cookiesfrombrowser"] = (a.cookies_browser,)

    try:
        with yt_dlp.YoutubeDL(base) as ydl:
            meta = ydl.extract_info(a.source, download=False)
        opts = {
            **base, "quiet": False,
            "outtmpl": str(out_dir / "reference.%(ext)s"),
            "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
            "merge_output_format": "mp4",
        }
        duration = meta.get("duration") or 0
        clipped = bool(duration and duration > a.max_seconds)
        if clipped:
            opts["download_ranges"] = download_range_func(None, [(0, a.max_seconds)])
            opts["force_keyframes_at_cuts"] = True
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([a.source])
        if not target.exists():
            got = next((p for p in out_dir.glob("reference.*") if p.suffix.lower() in VIDEO_EXT), None)
            if not got:
                raise RuntimeError("yt-dlp không tạo ra file video.")
            run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(got), "-c", "copy", str(target)])
            got.unlink()
    except Exception as e:  # noqa: BLE001
        print(f"\nLỖI TẢI VIDEO MẪU: {e}")
        print("Cách xử lý: tải video về máy rồi tải file lên qua giao diện; "
              "nguồn cần đăng nhập thì thêm --cookies-browser chrome (hoặc edge).")
        sys.exit(2)

    # ── Phụ đề + ảnh bìa (không bắt buộc: lỗi thì bỏ qua) ──
    sub_kind, sub_lang, cues = None, None, []
    manual, auto = meta.get("subtitles") or {}, meta.get("automatic_captions") or {}
    pick = next(((l, "phụ đề thật") for l in langs if l in manual), None) \
        or next(((l, "phụ đề tự động") for l in langs if l in auto), None) \
        or next(((l, "phụ đề thật") for l in manual if not l.startswith("live_chat")), None)
    try:
        sopts = {**base, "skip_download": True, "outtmpl": str(out_dir / "reference.%(ext)s"),
                 "writethumbnail": True}
        if pick:
            sopts.update({"writesubtitles": True, "writeautomaticsub": True, "subtitleslangs": [pick[0]],
                          "subtitlesformat": "vtt/srt/best"})
        with yt_dlp.YoutubeDL(sopts) as ydl:
            ydl.download([a.source])
    except Exception as e:  # noqa: BLE001
        print(f"(Bỏ qua phụ đề/ảnh bìa: {str(e)[:160]})")
    sub_file = next(iter(sorted(out_dir.glob("reference.*.vtt")) + sorted(out_dir.glob("reference.*.srt"))), None)
    if sub_file:
        cues = parse_vtt(sub_file)
        if clipped:
            cues = [c for c in cues if c["start"] < a.max_seconds]
        if cues:
            sub_kind, sub_lang = pick[1], pick[0]
            write_json(out_dir / "subtitles.json", {"lang": sub_lang, "kind": sub_kind, "cues": cues})
    thumb = next((p for p in out_dir.glob("reference.*") if p.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png")), None)
    if thumb:
        run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(thumb), str(out_dir / "thumbnail.jpg")], check=False)
        thumb.unlink(missing_ok=True)

    info = {
        "source": a.source,
        "source_type": f"{meta.get('extractor_key') or 'web'} qua yt-dlp",
        "title": meta.get("title"),
        "uploader": meta.get("uploader") or meta.get("channel"),
        "upload_date": meta.get("upload_date"),
        "duration": duration,
        "analyzed_seconds": a.max_seconds if clipped else duration,
        "width": meta.get("width"), "height": meta.get("height"), "fps": meta.get("fps"),
        "view_count": meta.get("view_count"), "like_count": meta.get("like_count"),
        "comment_count": meta.get("comment_count"),
        "tags": (meta.get("tags") or [])[:25], "categories": meta.get("categories"),
        "license": meta.get("license"),
        "chapters": [{"start": c.get("start_time"), "end": c.get("end_time"), "title": c.get("title")}
                     for c in (meta.get("chapters") or [])],
        "description": (meta.get("description") or "")[:2000],
        "music": {k: meta.get(k) for k in ("track", "artist", "album") if meta.get(k)} or None,
        "audio": extract_audio(target, out_dir),
        "subtitles": {"lang": sub_lang, "kind": sub_kind, "cues": len(cues)} if cues else None,
        "thumbnail": "thumbnail.jpg" if (out_dir / "thumbnail.jpg").exists() else None,
    }
    write_json(out_dir / "info.json", info)
    print(f"\nĐã thu thập: {target}")
    print(f"  Tiêu đề: {info['title']}  ·  Kênh: {info['uploader']}  ·  {duration}s"
          + (f" (chỉ lấy {a.max_seconds}s đầu)" if clipped else ""))
    print(f"  Audio: {info['audio'] or 'không có'}  ·  Phụ đề: "
          + (f"{sub_kind} [{sub_lang}], {len(cues)} câu" if cues else "không có")
          + f"  ·  Ảnh bìa: {'có' if info['thumbnail'] else 'không'}  ·  Giấy phép: {info['license'] or 'không ghi'}")


if __name__ == "__main__":
    main()
