"""VIDEO ANALYSIS: đo ngữ pháp dựng của một video theo các nhóm dữ liệu cụ thể.

Dùng:
  python tools/analyze_style.py <video> --out <thư mục analysis> [--max-seconds 600]

Đo được bằng máy (ghi trong style_metrics.json, mục nào cũng có nhãn "đo được" hay "ước lượng"):
  pacing        số cảnh, độ dài cảnh, phân bố, mật độ cắt theo từng phần video
  transition    phân loại từng điểm cắt: cắt thẳng / dissolve / fade qua đen / flash trắng / whip pan / zoom
  camera        chuyển động máy từng cảnh (tĩnh, pan, tilt, zoom, cầm tay) + cỡ cảnh ước lượng theo khuôn mặt
  color         bảng màu chủ đạo, độ sáng, tương phản, bão hoà, độ ấm/lạnh
  sound         BPM, lưới beat, tỉ lệ cắt đúng beat, điểm nhấn âm thanh, đường cong âm lượng, độ phủ lời thoại
  composition   vị trí khuôn mặt/chủ thể theo lưới 1/3, khổ hình
  energy        đường cong năng lượng theo thời gian (để người phân tích gắn hook / cao trào / CTA)
KHÔNG đo được bằng máy, người phân tích phải nhìn bảng khung hình + ảnh tĩnh để điền:
  typography (font, vị trí chữ, animation), storytelling (hook, nội dung chính, cao trào, CTA), góc máy cao/thấp.

Kết quả:
  <out>/style_metrics.json     toàn bộ số liệu
  <out>/STYLE_METRICS.md       bản tóm tắt dễ đọc
  <out>/stills/shot-NN.jpg     ảnh tĩnh độ phân giải cao của các cảnh (để soi chữ, bố cục)
"""
import argparse
import re
import statistics
import subprocess
from pathlib import Path

import cv2
import numpy as np

import analyze_video as av
from common import FFMPEG, ROOT, read_json, write_json

AW = 192  # bề ngang khung phân tích
TARGET_FPS = 12


# ───────────────────────── khung hình ─────────────────────────
def scan_frames(path, max_seconds):
    """Đọc tuần tự, lấy mẫu ~12 khung/giây: độ sáng, sai khác, luồng quang học (dx, dy, zoom, độ lớn)."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(1, round(fps / TARGET_FPS))
    sfps = fps / step
    rows, prev, i = [], None, 0
    grid = None
    while True:
        ok = cap.grab()
        if not ok:
            break
        t = i / fps
        if t > max_seconds:
            break
        if i % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            h, w = frame.shape[:2]
            small = cv2.resize(frame, (AW, max(8, int(AW * h / w))), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            row = {"t": round(t, 3), "luma": float(gray.mean()), "diff": 0.0, "dx": 0.0, "dy": 0.0, "zoom": 0.0, "mag": 0.0,
                   "blocks": 0, "local": 0.0}
            if prev is not None:
                ad = cv2.absdiff(gray, prev)
                row["diff"] = float(ad.mean())
                # sai khác theo lưới 6x6 ô: bắt được điểm cắt nằm trong khung nhỏ (khung-trong-khung)
                bd = cv2.resize(ad, (6, 6), interpolation=cv2.INTER_AREA).ravel()
                hot = bd[bd > 34]
                row["blocks"] = int(hot.size)
                row["local"] = float(hot.mean()) if hot.size else 0.0
                flow = cv2.calcOpticalFlowFarneback(prev, gray, None, 0.5, 2, 15, 2, 5, 1.1, 0)
                if grid is None:
                    gh, gw = gray.shape
                    ys, xs = np.mgrid[0:gh, 0:gw].astype(np.float32)
                    xs, ys = xs - gw / 2, ys - gh / 2
                    norm = np.sqrt(xs ** 2 + ys ** 2) + 1e-3
                    grid = (xs / norm, ys / norm, norm / norm.max())
                fx, fy = flow[..., 0], flow[..., 1]
                # quy đổi sang % bề ngang mỗi giây để không phụ thuộc độ phân giải
                k = sfps / AW * 100
                row["dx"] = float(np.median(fx)) * k
                row["dy"] = float(np.median(fy)) * k
                row["mag"] = float(np.sqrt(fx ** 2 + fy ** 2).mean()) * k
                # thành phần hướng tâm: dương = hình nở ra = máy đẩy vào (zoom in)
                row["zoom"] = float(((fx - np.median(fx)) * grid[0] + (fy - np.median(fy)) * grid[1]).mean()) * k
            rows.append(row)
            prev = gray
        i += 1
    cap.release()
    return rows, sfps


def between(rows, a, b):
    return [r for r in rows if a <= r["t"] < b]


def refine_cuts(rows, cuts, sfps, duration):
    """Gộp điểm cắt của FFmpeg với các 'gai' sai khác cục bộ (một mẫu đột biến, hai bên yên)."""
    found = list(cuts)
    for i in range(1, len(rows) - 1):
        r, a, b = rows[i], rows[i - 1], rows[i + 1]
        if r["blocks"] < 4:
            continue
        score = r["blocks"] * r["local"]
        side = max(a["blocks"] * a["local"], b["blocks"] * b["local"])
        if score > 2.5 * side + 1:
            found.append(round(r["t"] - 0.5 / sfps, 3))
    out = []
    for c in sorted(found):
        if 0.15 < c < duration - 0.15 and (not out or c - out[-1] > 0.25):
            out.append(c)
    return out


# ───────────────────────── pacing ─────────────────────────
def pacing(shots, duration):
    lens = [s["len"] for s in shots]
    cuts = [s["start"] for s in shots[1:]]
    third = duration / 3
    parts = []
    for i, name in enumerate(["đầu", "giữa", "cuối"]):
        n = sum(1 for c in cuts if i * third <= c < (i + 1) * third)
        parts.append({"part": name, "cuts": n, "cuts_per_min": round(n / max(third, 0.1) * 60, 1)})
    buckets = {"<1s": 0, "1-2s": 0, "2-4s": 0, ">4s": 0}
    for x in lens:
        buckets["<1s" if x < 1 else "1-2s" if x < 2 else "2-4s" if x < 4 else ">4s"] += 1
    cpm = len(cuts) / max(duration, 0.1) * 60
    label = "rất nhanh" if cpm >= 45 else "nhanh" if cpm >= 25 else "vừa" if cpm >= 12 else "chậm"
    trend = "tăng tốc dần" if parts[2]["cuts_per_min"] > parts[0]["cuts_per_min"] * 1.3 else \
        "chậm dần" if parts[2]["cuts_per_min"] < parts[0]["cuts_per_min"] * 0.7 else "đều"
    return {
        "nguon": "đo được",
        "shots": len(shots), "duration": round(duration, 2),
        "avg_shot": round(statistics.mean(lens), 2), "median_shot": round(statistics.median(lens), 2),
        "min_shot": round(min(lens), 2), "max_shot": round(max(lens), 2),
        "cuts_per_min": round(cpm, 1), "tempo_label": label, "trend": trend,
        "first_shot": round(lens[0], 2), "distribution": buckets, "by_part": parts,
    }


# ───────────────────────── transition ─────────────────────────
def classify_cut(rows, c, sfps):
    win = between(rows, c - 0.6, c + 0.6)
    pre = between(rows, c - 0.4, c - 0.04)
    around = between(rows, c - 1.5, c + 1.5)
    if not win or not around:
        return "cắt thẳng"
    base_luma = statistics.median(r["luma"] for r in around)
    lo, hi = min(r["luma"] for r in win), max(r["luma"] for r in win)
    if lo < 22 and lo < base_luma * 0.45:
        return "fade qua đen"
    if hi > 225 and hi > base_luma * 1.6:
        return "flash trắng"
    if pre:
        mag = statistics.mean(r["mag"] for r in pre)
        dxs = [r["dx"] for r in pre]
        zm = statistics.mean(r["zoom"] for r in pre)
        same_dir = abs(sum(np.sign(dxs))) >= len(dxs) * 0.7
        if mag > 45 and abs(statistics.mean(dxs)) > 30 and same_dir:
            return "whip pan"
        if abs(zm) > 9:
            return "zoom vào điểm cắt" if zm > 0 else "zoom lùi vào điểm cắt"
    peak = max(r["diff"] for r in win)
    if peak > 0:
        wide = sum(1 for r in win if r["diff"] > peak * 0.4)
        if wide >= max(3, round(sfps * 0.25)) and peak < 40:
            return "dissolve"
    return "cắt thẳng"


def transitions(rows, shots, sfps):
    items, counts = [], {}
    for s in shots[1:]:
        kind = classify_cut(rows, s["start"], sfps)
        items.append({"t": s["start"], "type": kind})
        counts[kind] = counts.get(kind, 0) + 1
    total = max(1, len(items))
    return {
        "nguon": "ước lượng (phân loại tự động từ độ sáng và luồng chuyển động, cần đối chiếu bằng mắt)",
        "counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
        "share": {k: round(v / total, 2) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])},
        "items": items,
    }


# ───────────────────────── camera ─────────────────────────
def classify_motion(rs):
    if len(rs) < 3:
        return "quá ngắn", 0.0
    dx = statistics.mean(r["dx"] for r in rs)
    dy = statistics.mean(r["dy"] for r in rs)
    zm = statistics.mean(r["zoom"] for r in rs)
    mag = statistics.mean(r["mag"] for r in rs)
    jitter = statistics.pstdev([r["dx"] for r in rs]) + statistics.pstdev([r["dy"] for r in rs])
    if abs(zm) > 2.2 and abs(zm) > abs(dx) * 0.5:
        return ("zoom in / đẩy máy vào" if zm > 0 else "zoom out / kéo máy ra"), mag
    if abs(dx) > 4 and abs(dx) >= abs(dy):
        return ("pan phải" if dx < 0 else "pan trái"), mag  # hình trôi trái = máy lia phải
    if abs(dy) > 4:
        return ("tilt xuống" if dy < 0 else "tilt lên"), mag
    if jitter > 9 and mag > 6:
        return "cầm tay / rung", mag
    if mag > 8:
        return "máy tĩnh, chủ thể chuyển động nhiều", mag
    return "máy tĩnh", mag


def camera(rows, shots):
    per, counts = [], {}
    for s in shots:
        kind, mag = classify_motion(between(rows, s["start"] + 0.15, s["end"] - 0.15))
        per.append({"shot": s["i"], "motion": kind, "energy": round(mag, 1)})
        if kind != "quá ngắn":
            counts[kind] = counts.get(kind, 0) + s["len"]
    total = sum(counts.values()) or 1
    return {
        "nguon": "ước lượng (luồng quang học; góc máy cao/thấp phải nhìn bằng mắt)",
        "motion_share_by_time": {k: round(v / total, 2) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])},
        "per_shot": per,
    }


# ───────────────────────── color ─────────────────────────
def color(path, duration, n=36):
    cap = cv2.VideoCapture(str(path))
    pix = []
    for k in range(n):
        cap.set(cv2.CAP_PROP_POS_MSEC, (k + 0.5) / n * duration * 1000)
        ok, f = cap.read()
        if ok:
            pix.append(cv2.resize(f, (64, 64), interpolation=cv2.INTER_AREA).reshape(-1, 3))
    cap.release()
    if not pix:
        return {"nguon": "không đọc được khung hình"}
    px = np.vstack(pix).astype(np.float32)
    hsv = cv2.cvtColor(px.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2HSV).reshape(-1, 3)
    luma = 0.114 * px[:, 0] + 0.587 * px[:, 1] + 0.299 * px[:, 2]
    _, labels, centers = cv2.kmeans(px, 6, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(labels.ravel(), minlength=6) / len(labels)
    palette = [{"hex": "#%02x%02x%02x" % (int(c[2]), int(c[1]), int(c[0])), "share": round(float(s), 2)}
               for c, s in sorted(zip(centers, share), key=lambda cs: -cs[1])]
    warmth = float(px[:, 2].mean() - px[:, 0].mean())
    sat, contrast, bright = float(hsv[:, 1].mean()) / 255, float(luma.std()) / 255, float(luma.mean()) / 255
    return {
        "nguon": "đo được",
        "palette": palette,
        "brightness": round(bright, 2), "contrast": round(contrast, 2), "saturation": round(sat, 2),
        "black_point": int(np.percentile(luma, 1)), "white_point": int(np.percentile(luma, 99)),
        "warmth": round(warmth, 1),
        "labels": {
            "tone": "ấm" if warmth > 12 else "lạnh" if warmth < -12 else "trung tính",
            "contrast": "cao" if contrast > 0.27 else "thấp, phẳng" if contrast < 0.17 else "vừa",
            "saturation": "rực" if sat > 0.45 else "nhạt, trầm" if sat < 0.22 else "vừa",
            "brightness": "sáng" if bright > 0.58 else "tối" if bright < 0.35 else "trung bình",
            "blacks": "đen được nâng (kiểu phim, mờ)" if np.percentile(luma, 1) > 18 else "đen sâu",
        },
    }


# ───────────────────────── sound ─────────────────────────
def load_audio(path, sr=22050):
    raw = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1",
                          "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32), sr


def sound(path, cuts, duration, transcript):
    y, sr = load_audio(path)
    if y.size < sr:
        return {"nguon": "video không có âm thanh"}
    n_fft, hop = 1024, 512
    frames = 1 + (len(y) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(frames)[:, None]
    spec = np.abs(np.fft.rfft(y[idx] * np.hanning(n_fft), axis=1))
    flux = np.maximum(0, np.diff(np.log1p(spec), axis=0)).sum(axis=1)
    flux = flux - np.convolve(flux, np.ones(43) / 43, mode="same")  # bỏ nền chậm
    flux = np.maximum(0, flux)
    fps = sr / hop

    # BPM: tự tương quan của đường bao onset trong khoảng 60–180 BPM
    bpm, conf, beats = None, 0.0, []
    if flux.std() > 1e-6:
        f = flux - flux.mean()
        ac = np.correlate(f, f, mode="full")[len(f) - 1:]
        lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)
        if hi < len(ac):
            lag = lo + int(np.argmax(ac[lo:hi]))
            conf = float(ac[lag] / (ac[0] + 1e-9))
            bpm = round(60 * fps / lag, 1)
            phase = max(range(lag), key=lambda p: flux[p::lag].sum())
            beats = [round((phase + k * lag) / fps, 3) for k in range(int((len(flux) - phase) / lag) + 1)]

    # điểm nhấn mạnh (ứng viên SFX / hit)
    thr = flux.mean() + 2.8 * flux.std()
    accents, last = [], -1.0
    for i in np.where(flux > thr)[0]:
        t = i / fps
        if t - last > 0.25:
            accents.append(round(t, 2))
            last = t

    def near(ts, grid, tol):
        g = np.array(grid) if len(grid) else np.array([1e9])
        return sum(1 for t in ts if np.min(np.abs(g - t)) <= tol)

    on_beat = near(cuts, beats, 0.09) / len(cuts) if cuts and beats else None
    chance = min(1.0, 2 * 0.09 / (60 / bpm)) if bpm else None
    on_accent = near(cuts, accents, 0.12) / len(cuts) if cuts and accents else None

    # đường cong âm lượng theo 0,5 giây
    win = sr // 2
    rms = [float(np.sqrt(np.mean(y[i:i + win] ** 2) + 1e-12)) for i in range(0, len(y) - win + 1, win)]
    db = [round(20 * np.log10(r + 1e-9), 1) for r in rms]
    active = sum(1 for d in db if d > -45) / max(1, len(db))
    speech = sum(s["end"] - s["start"] for s in (transcript or {}).get("sentences", [])) / max(duration, 0.1)
    reliable = bool(bpm and conf > 0.12)
    return {
        "nguon": "đo được (BPM và lưới beat là ước lượng; tin cậy khi beat_confidence > 0.12)",
        "bpm": bpm, "beat_confidence": round(conf, 2), "bpm_reliable": reliable,
        "beats": beats[:400],
        "cuts_on_beat": round(on_beat, 2) if on_beat is not None else None,
        "cuts_on_beat_by_chance": round(chance, 2) if chance else None,
        "cuts_follow_beat": bool(reliable and on_beat is not None and chance and on_beat > max(0.5, chance * 1.6)),
        "accents": accents[:200], "accents_per_min": round(len(accents) / max(duration, 0.1) * 60, 1),
        "cuts_on_accent": round(on_accent, 2) if on_accent is not None else None,
        "loudness_db_per_half_second": db,
        "loudness_mean_db": round(float(np.mean(db)), 1), "loudness_range_db": round(float(max(db) - min(db)), 1),
        "sound_coverage": round(active, 2),
        "speech_coverage": round(min(1.0, speech), 2),
        "labels": {
            "voice": "lời thoại/giọng đọc xuyên suốt" if speech > 0.6 else "có lời từng đoạn" if speech > 0.15 else "gần như không lời",
            "bed": "âm thanh nền liên tục (nhiều khả năng có nhạc)" if active > 0.9 else "có khoảng lặng rõ",
        },
    }


# ───────────────────────── composition ─────────────────────────
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"


def face_detector():
    """Bộ nhận diện mặt YuNet (OpenCV). Tự tải mô hình ~230 KB lần đầu; không tải được thì bỏ qua phần mặt."""
    model = ROOT / ".runtime" / "models" / "yunet.onnx"
    try:
        if not model.exists():
            import urllib.request

            model.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(YUNET_URL, model)
        return cv2.FaceDetectorYN.create(str(model), "", (320, 320), 0.7, 0.3, 50)
    except Exception:  # noqa: BLE001
        return None


def composition(path, shots, info, stills_dir, max_stills=24):
    stills_dir.mkdir(parents=True, exist_ok=True)
    detector = face_detector()
    cap = cv2.VideoCapture(str(path))
    keep = set(np.linspace(0, len(shots) - 1, min(max_stills, len(shots))).round().astype(int).tolist())
    per, scales, cells, saved = [], {}, {}, []
    for k, s in enumerate(shots):
        cap.set(cv2.CAP_PROP_POS_MSEC, (s["start"] + s["len"] / 2) * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        h, w = f.shape[:2]
        if k in keep:
            sc = 1280 / max(h, w)
            out = cv2.resize(f, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA) if sc < 1 else f
            name = f"shot-{s['i']:03d}.jpg"
            cv2.imwrite(str(stills_dir / name), out, [cv2.IMWRITE_JPEG_QUALITY, 88])
            saved.append({"shot": s["i"], "t": round(s["start"] + s["len"] / 2, 2), "file": f"stills/{name}"})
        g = cv2.resize(f, (480, int(480 * h / w)))
        faces = []
        if detector is not None:
            detector.setInputSize((g.shape[1], g.shape[0]))
            found = detector.detect(g)[1]
            faces = [] if found is None else [row[:4] for row in found]
        entry = {"shot": s["i"], "faces": int(len(faces))}
        if len(faces):
            x, y, fw, fh = max(faces, key=lambda b: b[2] * b[3])
            ratio = fh / g.shape[0]
            scale = "cận" if ratio > 0.33 else "trung" if ratio > 0.14 else "toàn"
            cx, cy = (x + fw / 2) / g.shape[1], (y + fh / 2) / g.shape[0]
            col = "trái" if cx < 0.38 else "phải" if cx > 0.62 else "giữa"
            row = "trên" if cy < 0.38 else "dưới" if cy > 0.62 else "giữa"
            entry.update({"scale": scale, "face_height": round(float(ratio), 2), "position": f"{row}-{col}"})
            scales[scale] = scales.get(scale, 0) + 1
            cells[f"{row}-{col}"] = cells.get(f"{row}-{col}", 0) + 1
        per.append(entry)
    cap.release()
    with_face = sum(1 for p in per if p["faces"])
    return {
        "nguon": "ước lượng (dựa trên nhận diện khuôn mặt; bố cục chi tiết phải nhìn ảnh tĩnh)",
        "aspect": f"{info['width']}x{info['height']} ({info['orientation']})",
        "shots_with_face": round(with_face / max(1, len(per)), 2),
        "shot_scale_counts": scales, "subject_position_counts": cells,
        "per_shot": per, "stills": saved,
    }


# ───────────────────────── energy / cấu trúc ─────────────────────────
def energy_curve(rows, shots, snd, duration, n=10):
    seg = duration / n
    cuts = [s["start"] for s in shots[1:]]
    db = snd.get("loudness_db_per_half_second") or []
    out = []
    for i in range(n):
        a, b = i * seg, (i + 1) * seg
        rs = between(rows, a, b)
        loud = [d for k, d in enumerate(db) if a <= k * 0.5 < b]
        out.append({
            "from": round(a, 1), "to": round(b, 1),
            "cuts": sum(1 for c in cuts if a <= c < b),
            "motion": round(statistics.mean(r["mag"] for r in rs), 1) if rs else 0,
            "loudness_db": round(statistics.mean(loud), 1) if loud else None,
        })

    def norm(vals):
        vals = [v if v is not None else min(x for x in vals if x is not None) for v in vals] if any(v is not None for v in vals) else [0] * len(vals)
        lo, hi = min(vals), max(vals)
        return [(v - lo) / (hi - lo) if hi > lo else 0.5 for v in vals]

    c, m, l = norm([o["cuts"] for o in out]), norm([o["motion"] for o in out]), norm([o["loudness_db"] for o in out])
    for o, x, y_, z in zip(out, c, m, l):
        o["energy"] = round((x + y_ + z) / 3, 2)
    peak = max(out, key=lambda o: o["energy"])
    return {"nguon": "đo được (gợi ý: đoạn năng lượng cao nhất thường là cao trào)", "tenths": out,
            "peak": {"from": peak["from"], "to": peak["to"]}}


# ───────────────────────── báo cáo ─────────────────────────
def write_md(out, m):
    p, tr, cam, col, snd, comp = m["pacing"], m["transition"], m["camera"], m["color"], m["sound"], m["composition"]
    L = [f"# Số liệu ngữ pháp dựng — {m['name']}", "",
         f"{m['duration']}s · {m['width']}x{m['height']} ({m['orientation']}) · {m['fps']}fps", "",
         "## 1. Pacing (đo được)",
         f"- {p['shots']} cảnh · trung bình {p['avg_shot']}s · trung vị {p['median_shot']}s · ngắn nhất {p['min_shot']}s · dài nhất {p['max_shot']}s",
         f"- {p['cuts_per_min']} lần cắt/phút → nhịp **{p['tempo_label']}**, xu hướng **{p['trend']}**; cảnh mở đầu dài {p['first_shot']}s",
         f"- Phân bố độ dài cảnh: {p['distribution']}",
         "- Theo phần: " + " · ".join(f"{x['part']} {x['cuts_per_min']}/phút" for x in p["by_part"]), "",
         "## 2. Transition (ước lượng — đối chiếu bằng mắt)",
         "- " + (" · ".join(f"{k}: {v} ({int(tr['share'][k] * 100)}%)" for k, v in tr["counts"].items()) or "không có điểm cắt"),
         "- Điểm cắt không phải cắt thẳng: " + (", ".join(f"{i['t']}s {i['type']}" for i in tr["items"] if i["type"] != "cắt thẳng")[:600] or "không"), "",
         "## 3. Camera (ước lượng)",
         "- Theo thời lượng: " + " · ".join(f"{k} {int(v * 100)}%" for k, v in cam["motion_share_by_time"].items()),
         "- Góc máy cao/thấp/ngang mắt: phải nhìn ảnh tĩnh", "",
         "## 4. Typography", "- Không đo bằng máy. Nhìn `stills/` và dải khung hình dày (`analyze_video.py --dense`).", ""]
    if "palette" in col:
        lb = col["labels"]
        L += ["## 5. Color grading (đo được)",
              "- Bảng màu: " + " ".join(f"{c['hex']} ({int(c['share'] * 100)}%)" for c in col["palette"]),
              f"- Tông {lb['tone']} · tương phản {lb['contrast']} ({col['contrast']}) · bão hoà {lb['saturation']} ({col['saturation']}) · {lb['brightness']} ({col['brightness']}) · {lb['blacks']}", ""]
    L += ["## 6. Sound design"]
    if "bpm" in snd:
        L += [f"- BPM ≈ {snd['bpm']} (độ tin cậy {snd['beat_confidence']}, {'tin được' if snd['bpm_reliable'] else 'KHÔNG chắc'})",
              f"- Cắt đúng beat: {snd['cuts_on_beat']} (ngẫu nhiên sẽ là {snd['cuts_on_beat_by_chance']}) → {'CÓ cắt theo nhạc' if snd['cuts_follow_beat'] else 'không thấy cắt theo beat rõ ràng'}",
              f"- Điểm nhấn âm thanh: {snd['accents_per_min']}/phút; cắt trùng điểm nhấn: {snd['cuts_on_accent']}",
              f"- Âm lượng trung bình {snd['loudness_mean_db']} dB, dao động {snd['loudness_range_db']} dB · {snd['labels']['voice']} · {snd['labels']['bed']}"]
    else:
        L += [f"- {snd['nguon']}"]
    L += ["", "## 7. Storytelling", "- Không đo bằng máy. Dùng phụ đề/lời thoại + đường cong năng lượng dưới đây để gắn hook, nội dung chính, cao trào, CTA.",
          "- Năng lượng theo 1/10 video: " + " ".join(f"[{o['from']}s {o['energy']}]" for o in m["energy"]["tenths"]),
          f"- Đỉnh năng lượng: {m['energy']['peak']['from']}–{m['energy']['peak']['to']}s", "",
          "## 8. Composition (ước lượng)",
          f"- Khổ hình {comp['aspect']} · {int(comp['shots_with_face'] * 100)}% cảnh có mặt người",
          f"- Cỡ cảnh: {comp['shot_scale_counts'] or 'không nhận diện được'} · Vị trí chủ thể: {comp['subject_position_counts'] or 'không nhận diện được'}",
          f"- Ảnh tĩnh để soi: {len(comp['stills'])} file trong `stills/`", ""]
    (out / "STYLE_METRICS.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-seconds", type=float, default=600)
    ap.add_argument("--scene", type=float, default=0.32)
    a = ap.parse_args()
    path, out = Path(a.video), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    info = av.probe(path)
    duration = min(info["duration"], a.max_seconds)
    stem = re.sub(r"[^\w.-]+", "_", path.stem)
    prior = read_json(out / f"{stem}.json") or {}  # kết quả analyze_video.py nếu đã chạy
    base_cuts = [s["start"] for s in prior["shots"][1:]] if prior.get("shots") else av.detect_cuts(path, a.scene)

    rows, sfps = scan_frames(path, duration)
    cuts = refine_cuts(rows, base_cuts, sfps, duration)
    b = [0.0] + cuts + [duration]
    shots = [{"i": i + 1, "start": b[i], "end": b[i + 1], "len": round(b[i + 1] - b[i], 2)} for i in range(len(b) - 1)]
    snd = sound(path, [s["start"] for s in shots[1:]], duration, prior.get("transcript"))
    metrics = {
        "name": path.name, **{k: info[k] for k in ("width", "height", "fps", "orientation")}, "duration": round(duration, 2),
        "pacing": pacing(shots, duration),
        "transition": transitions(rows, shots, sfps),
        "camera": camera(rows, shots),
        "typography": {"nguon": "không đo bằng máy: người phân tích điền sau khi nhìn stills và dải khung hình dày"},
        "color": color(path, duration),
        "sound": snd,
        "storytelling": {"nguon": "không đo bằng máy: gắn nhãn dựa trên phụ đề/lời thoại và energy"},
        "composition": composition(path, shots, info, out / "stills"),
        "energy": energy_curve(rows, shots, snd, duration),
        "shots": shots,
    }
    write_json(out / "style_metrics.json", metrics)
    write_md(out, metrics)
    print((out / "STYLE_METRICS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
