"""Cắt cảnh + tạo nhạc/sfx cho dự án 2026-11-14-141022 (v2: kịch bản tấu hài).
python -I prep.py video audio
"""
import json, shutil, subprocess, sys, wave
from pathlib import Path
import numpy as np

P = Path(r"D:\Ai agent edit video life\projects\2026-11-14-141022")
RAW, A = P / "raw", P / "edit" / "assets"
FF = shutil.which("ffmpeg")
(A / "video").mkdir(parents=True, exist_ok=True)
(A / "audio").mkdir(parents=True, exist_ok=True)

NIGHT = ",eq=brightness=0.05:gamma=1.25:saturation=1.1"
SLOW = {"s01": 0.63, "s06": 0.63, "s07": 0.65, "s12": 0.72, "c3": 0.8}  # quay chậm (tốc độ)
CUTS = [  # out, src, start, dur, extra vf
    ("s01", "IMG_9843.MOV", 0.0, 2.7, ""),
    ("s02", "IMG_9845.MOV", 3.3, 5.93, ""),
    ("s03", "IMG_9863 (1).MOV", 1.5, 2.8, ""),
    ("s04", "IMG_9850 (1).MOV", 2.0, 2.9, ""),
    ("s05", "IMG_9857.MOV", 0.0, 4.7, ""),
    ("s06", "IMG_9861.MOV", 1.2, 2.2, ""),
    ("s07", "IMG_8772.MOV", 0.0, 1.9, ""),
    ("c1", "IMG_8772.MOV", 8.0, 6.9, ""),
    ("c2", "IMG_3995.MOV", 0.0, 9.5, ""),
    ("c3", "IMG_3997.MOV", 0.0, 8.2, ""),
    ("s10a", "IMG_8773.MOV", 9.5, 2.0, NIGHT),
    ("s10c", "IMG_8773.MOV", 3.0, 1.4, NIGHT),
    ("s10b", "IMG_8773.MOV", 13.0, 1.5, NIGHT),
    ("s11", "IMG_3996.MOV", 2.0, 4.6, ""),
    ("s12", "IMG_3996.MOV", 10.3, 4.67, ",eq=gamma=1.15"),
]
VF = "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"

if "video" in sys.argv:
    for out, src, ss, dur, extra in CUTS:
        sp = SLOW.get(out)
        vf = (f"setpts=PTS/{sp}," if sp else "") + VF + extra
        aud = ["-an"] if sp else ["-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]
        subprocess.run([FF, "-y", "-v", "error", "-ss", str(ss), "-t", str(dur), "-i", str(RAW / src), "-vf", vf,
                        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", *aud,
                        str(A / "video" / f"{out}.mp4")], check=True)
        print("cut", out)
    # khung đứng hình cho "À nhầm!"
    subprocess.run([FF, "-y", "-v", "error", "-ss", "2.55", "-i", str(RAW / "IMG_9843.MOV"), "-frames:v", "1",
                    "-vf", VF, "-q:v", "2", str(A / "video" / "s01f.jpg")], check=True)
    print("freeze s01f")

SR = 44100
rng = np.random.default_rng(7)


def save(name, x, peak=0.89):
    x = np.clip(x / (np.max(np.abs(x)) + 1e-9) * peak, -1, 1)
    pcm = (x * 32767).astype(np.int16)
    if pcm.ndim == 1:
        pcm = np.stack([pcm, pcm], 1)
    with wave.open(str(A / "audio" / name), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print("wrote", name, round(len(x) / SR, 2), "s")


def t(d):
    return np.arange(int(d * SR)) / SR


def f(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def tick():
    tt = t(0.035)
    return (np.sin(2 * np.pi * 2400 * tt) * 0.6 + rng.standard_normal(len(tt)) * 0.4) * np.exp(-tt * 160)


if "audio" in sys.argv:
    sys.path.insert(0, str(Path(__file__).parent))
    import build  # dùng chung mốc thời gian

    TOTAL = build.TOTAL
    n = int((TOTAL + 0.5) * SR)

    # ── Nhạc nền hài: marimba nảy + bass "um-pa" + nhạc cụ pizzicato, 128 BPM ──
    mix = np.zeros(n)

    def add(buf, sig, at, gain=1.0):
        i = int(at * SR); j = min(len(buf), i + len(sig))
        if 0 <= i < len(buf): buf[i:j] += sig[: j - i] * gain

    def marimba(freq, d=0.35):
        tt = t(d); return np.exp(-tt * 14) * (np.sin(2*np.pi*freq*tt) + 0.35*np.sin(2*np.pi*4*freq*tt)*np.exp(-tt*40))

    def pizz(freq, d=0.22):
        tt = t(d); return np.exp(-tt * 22) * (np.sin(2*np.pi*freq*tt) + 0.6*np.sin(4*np.pi*freq*tt) + 0.3*np.sin(6*np.pi*freq*tt))

    def tuba(freq, d):
        tt = t(d); env = np.minimum(1, tt * 60) * np.exp(-tt * 5)
        return env * (np.sin(2*np.pi*freq*tt) + 0.5*np.sin(4*np.pi*freq*tt) + 0.2*np.sin(6*np.pi*freq*tt))

    def hat():
        tt = t(0.04); h = np.diff(rng.standard_normal(len(tt)), prepend=0); return h * np.exp(-tt * 90)

    def kick():
        tt = t(0.22); fr = 55 + 80 * np.exp(-tt * 35)
        return np.sin(2*np.pi*np.cumsum(fr)/SR) * np.exp(-tt * 14)

    BPM = 128; beat = 60 / BPM; bar = 4 * beat
    # F - C - Dm - Bb… kiểu nhạc hài sitcom; giai điệu lén lút (sneaky) xen nảy
    prog = [(53, (65, 69, 72)), (48, (64, 67, 72)), (50, (62, 65, 69)), (46, (62, 65, 70))]
    melody = [72, None, 74, 72, 69, None, 65, None, 67, 69, None, 67, 65, None, 62, None]  # 16 nốt móc đơn / 2 ô nhịp
    breaks = [(b0 - 0.05, b1) for b0, b1 in build.MUSIC_BREAKS]

    def muted(at):
        return any(b0 <= at < b1 for b0, b1 in breaks)

    nb = int(TOTAL / bar) + 2
    for b in range(nb):
        root, ch = prog[b % 4]; t0 = b * bar
        for q in range(4):
            at = t0 + q * beat
            if muted(at): continue
            # um-pa: bass ở phách 1, 3; hợp âm pizz ở phách 2, 4
            if q % 2 == 0:
                add(mix, tuba(f(root - 12 + (7 if q == 2 else 0)), beat * 0.8), at, 0.42)
                add(mix, kick(), at, 0.35)
            else:
                for k, note in enumerate(ch):
                    add(mix, pizz(f(note)), at + k * 0.008, 0.13)
            add(mix, hat(), at + beat / 2, 0.08)
        if b % 2 == 0:  # giai điệu dài 2 ô nhịp
            for k, note in enumerate(melody):
                at = t0 + k * beat / 2
                if note is not None and not muted(at):
                    add(mix, marimba(f(note + 12)), at, 0.16)
    fo = int(2.0 * SR); mix[-fo:] *= np.linspace(1, 0, fo)
    save("music2.wav", mix)

    # ── Tiếng "chạy chữ": 1 tick nhẹ cho mỗi từ phụ đề, trộn sẵn thành 1 track ──
    ticks = np.zeros(n)
    for at in build.caption_word_times():
        add(ticks, tick(), at, 1.0)
    save("ticks.wav", ticks, peak=0.5)

    # ── SFX ──
    tt = t(0.45); nz = rng.standard_normal(len(tt))
    sweep = np.convolve(nz, np.ones(8) / 8, "same") * np.sin(np.pi * tt / 0.45) ** 2
    save("whoosh.wav", sweep * (0.4 + 0.6 * np.sin(2*np.pi*3*tt)**2))
    tt = t(0.12); fr = 900 - 500 * tt / 0.12
    save("pop.wav", np.sin(2*np.pi*np.cumsum(fr)/SR) * np.exp(-tt*35))
    tt = t(0.6); fr = 700 * (1 + 0.6*np.sin(2*np.pi*7*tt)) * np.exp(-tt*2)
    scratch = np.sign(np.sin(2*np.pi*np.cumsum(fr)/SR)) * 0.3 + rng.standard_normal(len(tt)) * 0.4
    save("scratch.wav", np.convolve(scratch, np.ones(6)/6, "same") * np.exp(-tt*3))
    tt = t(0.9)
    save("ding.wav", (np.sin(2*np.pi*1320*tt) + 0.4*np.sin(2*np.pi*1980*tt)) * np.exp(-tt*5))
    # boing (lò xo)
    tt = t(0.7); fr = 180 + 220 * np.exp(-tt * 3) * (1 + 0.5 * np.sin(2*np.pi*14*tt))
    save("boing.wav", np.sin(2*np.pi*np.cumsum(fr)/SR) * np.exp(-tt * 4))
    # kèn buồn wah-wah-wah-waaah
    sad = []
    for k, (note, d) in enumerate([(58, 0.3), (57, 0.3), (56, 0.3), (55, 0.9)]):
        tt = t(d); vib = 1 + (0.012 * np.sin(2*np.pi*6*tt) if k == 3 else 0)
        ph = 2*np.pi*np.cumsum(f(note) * vib)/SR
        saw = sum(np.sin(h * ph) / h for h in range(1, 9))
        env = np.minimum(1, tt * 25) * np.minimum(1, (d - tt) * 12) * (1 - 0.5 * np.minimum(1, tt / d))
        wah = 0.55 + 0.45 * np.sin(np.pi * np.minimum(1, tt / 0.18))
        sad.append(saw * env * wah)
    save("sadtrombone.wav", np.concatenate(sad))
    # ba-dum-tss
    rim = np.zeros(int(1.3 * SR))
    def drum(fr0, d):
        tt = t(d); return np.sin(2*np.pi*np.cumsum(fr0 * (1 + np.exp(-tt*30)))/SR) * np.exp(-tt * 18)
    add(rim, drum(180, 0.25), 0.0); add(rim, drum(120, 0.25), 0.18)
    tt = t(1.0); cym = np.diff(rng.standard_normal(len(tt)), prepend=0) * np.exp(-tt * 3.5)
    add(rim, cym, 0.42, 0.7); add(rim, drum(80, 0.3), 0.42, 0.6)
    save("badumtss.wav", rim)

    # giọng đọc v2
    (A / "vo2").mkdir(exist_ok=True)
    for fp in (P / "vo2").glob("*"):
        shutil.copy(fp, A / "vo2" / fp.name)
