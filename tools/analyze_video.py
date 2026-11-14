"""'Xem' video cho agent: thông số, điểm cắt cảnh, bảng khung hình có mốc thời gian, khoảng lặng, lời thoại.

Dùng:
  python tools/analyze_video.py <file hoặc thư mục> --out <thư mục analysis> [--lang vi] [--model small]
        [--no-transcribe] [--interval 2.0]
  python tools/analyze_video.py <file> --out <dir> --dense 3.0 6.5 --fps 6
        -> dải khung hình dày đặc của đoạn 3.0s-6.5s để soi chuyển động / hiệu ứng chữ / chuyển cảnh

Kết quả cho mỗi video <tên>:
  <out>/<tên>.json            thông số, shots, speech, transcript (theo câu và theo từ)
  <out>/<tên>.sheet-NN.jpg    bảng khung hình (đọc bằng Read để nhìn nội dung)
  <out>/INDEX.md              tóm tắt toàn bộ video
"""
import argparse
import json
import re
import shutil
import statistics
import tempfile
from pathlib import Path

from common import FFMPEG, FFPROBE, VIDEO_EXT, read_json, run, write_json


def probe(path):
    _, out, _ = run([FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    d = json.loads(out)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    if not v:
        raise RuntimeError("Không có luồng video")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) in (90, 270):
        w, h = h, w
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = round(float(num) / float(den), 3) if float(den) else 0
    dur = float(d["format"].get("duration") or v.get("duration") or 0)
    ratio = w / h
    orient = "ngang" if ratio > 1.2 else "dọc" if ratio < 0.85 else "vuông"
    return {
        "duration": round(dur, 3), "width": w, "height": h, "fps": fps,
        "orientation": orient, "has_audio": bool(a), "codec": v.get("codec_name"),
        "bytes": int(d["format"].get("size") or 0),
    }


def detect_cuts(path, threshold):
    _, _, err = run(
        [FFMPEG, "-hide_banner", "-i", str(path), "-an", "-vf",
         f"scale=320:-2,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
        check=False,
    )
    return [round(float(t), 3) for t in re.findall(r"pts_time:([\d.]+)", err)]


def detect_speech(path, duration):
    """Trả về các đoạn có tiếng (ngược của silencedetect) và âm lượng trung bình."""
    _, _, err = run(
        [FFMPEG, "-hide_banner", "-i", str(path), "-vn", "-af",
         "silencedetect=noise=-34dB:d=0.45,volumedetect", "-f", "null", "-"],
        check=False,
    )
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    mean = re.search(r"mean_volume: ([-\d.]+) dB", err)
    sound, cur = [], 0.0
    for i, s in enumerate(starts):
        if s - cur > 0.2:
            sound.append([round(cur, 2), round(s, 2)])
        cur = ends[i] if i < len(ends) else duration
    if duration - cur > 0.2:
        sound.append([round(cur, 2), round(duration, 2)])
    return sound, (float(mean.group(1)) if mean else None)


def label_font(size):
    from PIL import ImageFont

    for name in ("arialbd.ttf", "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def build_sheets(path, out_prefix, times, info, cuts=()):
    """Trích khung hình tại các mốc `times`, ghép thành bảng có nhãn thời gian."""
    from PIL import Image, ImageDraw

    portrait = info["height"] > info["width"]
    cols = 6 if portrait else 4
    tile_w = 300 if portrait else 448
    tile_h = int(tile_w * info["height"] / info["width"])
    per_sheet = cols * (3 if portrait else 4)
    font = label_font(20)
    tmp = Path(tempfile.mkdtemp(prefix="kuto_frames_"))
    sheets = []
    try:
        frames = []
        for i, t in enumerate(times):
            fp = tmp / f"f{i:05d}.jpg"
            run([FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(path),
                 "-frames:v", "1", "-vf", f"scale={tile_w}:{tile_h}", "-q:v", "4", "-y", str(fp)], check=False)
            if fp.exists():
                frames.append((t, fp))
        for si in range(0, len(frames), per_sheet):
            chunk = frames[si:si + per_sheet]
            rows = -(-len(chunk) // cols)
            sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (18, 18, 22))
            draw = ImageDraw.Draw(sheet)
            for k, (t, fp) in enumerate(chunk):
                x, y = (k % cols) * tile_w, (k // cols) * tile_h
                sheet.paste(Image.open(fp), (x, y))
                is_cut = any(abs(t - c) < 0.02 for c in cuts)
                tag = f"{t:.2f}s" + (" CUT" if is_cut else "")
                tw = draw.textlength(tag, font=font)
                draw.rectangle([x, y, x + tw + 12, y + 28], fill=(230, 40, 110) if is_cut else (0, 0, 0))
                draw.text((x + 6, y + 3), tag, fill=(255, 255, 255), font=font)
            name = f"{out_prefix}-{len(sheets) + 1:02d}.jpg"
            sheet.save(name, quality=82)
            sheets.append(Path(name).name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return sheets


_model = None


def transcribe(path, lang, model_name):
    global _model
    import subprocess

    import numpy as np
    from faster_whisper import WhisperModel

    # Tự giải mã âm thanh bằng FFmpeg (16 kHz mono) thay vì PyAV
    raw = subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
         "-f", "f32le", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    if audio.size < 1600:
        return {"language": lang, "sentences": [], "words": []}

    if _model is None:
        try:
            _model = WhisperModel(model_name, device="cuda", compute_type="float16")
            list(_model.transcribe(audio[:16000 * 5], language=lang)[0])  # thử thật: thiếu DLL CUDA sẽ lỗi ở đây
        except Exception:
            _model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, meta = _model.transcribe(audio, language=lang, vad_filter=True, word_timestamps=True)
    sentences, words = [], []
    for s in segs:
        text = s.text.strip()
        if not text:
            continue
        sentences.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": text})
        for w in s.words or []:
            words.append({"text": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)})
    return {"language": meta.language, "sentences": sentences, "words": words}


def analyze(path, out, args):
    info = probe(path)
    stem = re.sub(r"[^\w.-]+", "_", path.stem)
    cuts = [c for c in detect_cuts(path, args.scene) if 0.15 < c < info["duration"] - 0.15]
    bounds = [0.0] + cuts + [info["duration"]]
    shots = [{"i": i + 1, "start": bounds[i], "end": bounds[i + 1], "len": round(bounds[i + 1] - bounds[i], 2)}
             for i in range(len(bounds) - 1)]
    lens = [s["len"] for s in shots]
    rhythm = {
        "shots": len(shots),
        "avg_shot": round(statistics.mean(lens), 2),
        "median_shot": round(statistics.median(lens), 2),
        "min_shot": min(lens), "max_shot": max(lens),
        "cuts_per_min": round(len(cuts) / max(info["duration"], 0.1) * 60, 1),
    }

    interval = args.interval or min(10.0, max(0.5, info["duration"] / 32))
    times = [round(i * interval, 2) for i in range(int(info["duration"] / interval) + 1)]
    times = sorted(set(times + [round(c + 0.05, 2) for c in cuts]))
    times = [t for t in times if t < info["duration"] - 0.05] or [0.0]
    sheets = build_sheets(path, str(out / f"{stem}.sheet"), times, info, cuts=[round(c + 0.05, 2) for c in cuts])

    data = {"file": str(path), "name": path.name, **info, "rhythm": rhythm, "shots": shots, "sheets": sheets}
    if info["has_audio"]:
        data["sound_segments"], data["mean_volume_db"] = detect_speech(path, info["duration"])
        if not args.no_transcribe:
            try:
                data["transcript"] = transcribe(path, args.lang, args.model)
            except Exception as e:  # noqa: BLE001
                data["transcript_error"] = str(e)[:300]
    write_json(out / f"{stem}.json", data)
    return stem, data


def write_index(out):
    lines = ["# Tóm tắt phân tích video", ""]
    for jf in sorted(out.glob("*.json")):
        d = read_json(jf)
        if not d or "rhythm" not in d:
            continue
        said = " ".join(s["text"] for s in d.get("transcript", {}).get("sentences", []))
        lines += [
            f"## {d['name']}",
            f"- {d['duration']}s · {d['width']}x{d['height']} ({d['orientation']}) · {d['fps']}fps · "
            f"{'có tiếng' if d['has_audio'] else 'không tiếng'}",
            f"- Nhịp: {d['rhythm']['shots']} cảnh, TB {d['rhythm']['avg_shot']}s/cảnh, {d['rhythm']['cuts_per_min']} cắt/phút",
            f"- Lời thoại: {said[:400] if said else '(không có lời / chưa phiên âm)'}",
            f"- Bảng khung hình: {', '.join(d['sheets'])}",
            f"- Chi tiết: {jf.name}",
            "",
        ]
    (out / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="vi")
    ap.add_argument("--model", default="small")
    ap.add_argument("--no-transcribe", action="store_true")
    ap.add_argument("--interval", type=float, default=0, help="giây giữa 2 khung hình; 0 = tự chọn")
    ap.add_argument("--scene", type=float, default=0.32, help="ngưỡng phát hiện cắt cảnh")
    ap.add_argument("--dense", nargs=2, type=float, metavar=("START", "END"))
    ap.add_argument("--fps", type=float, default=6)
    a = ap.parse_args()

    src, out = Path(a.input), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    if a.dense:
        info = probe(src)
        s, e = a.dense
        n = max(1, int((e - s) * a.fps))
        times = [round(s + i / a.fps, 3) for i in range(n + 1)]
        stem = re.sub(r"[^\w.-]+", "_", src.stem)
        sheets = build_sheets(src, str(out / f"{stem}.dense-{s:.1f}-{e:.1f}"), times, info)
        print("Dải khung hình:", ", ".join(str(out / x) for x in sheets))
        return

    files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.suffix.lower() in VIDEO_EXT)
    if not files:
        print("Không tìm thấy video nào.")
        raise SystemExit(2)
    for f in files:
        try:
            stem, d = analyze(f, out, a)
            print(f"OK {f.name}: {d['duration']}s {d['width']}x{d['height']} {d['rhythm']['shots']} cảnh -> {stem}.json")
        except Exception as e:  # noqa: BLE001
            print(f"LỖI {f.name}: {e}")
    write_index(out)
    print(f"Tóm tắt: {out / 'INDEX.md'}")


if __name__ == "__main__":
    main()
