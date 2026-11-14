"""Tạo giọng đọc AI tiếng Việt (miễn phí, Microsoft Edge TTS) kèm mốc thời gian từng từ.

Dùng:
  python tools/tts_vi.py --text "Sáng thứ hai, deadline dí." --out projects/<id>/edit/assets/vo/line01.mp3
  python tools/tts_vi.py --script projects/<id>/script.json --outdir projects/<id>/edit/assets/vo

script.json: [{"id": "line01", "text": "...", "voice": "nu", "rate": "+8%"}, ...]
Giọng: nu = vi-VN-HoaiMyNeural, nam = vi-VN-NamMinhNeural (hoặc tên voice đầy đủ của Edge TTS).
Mỗi câu sinh ra <id>.mp3 và <id>.words.json ([{text, start, end}] tính bằng giây) để làm phụ đề chạy chữ.
"""
import argparse
import asyncio
import json
from pathlib import Path

from common import FFPROBE, run, write_json

VOICES = {"nu": "vi-VN-HoaiMyNeural", "nam": "vi-VN-NamMinhNeural"}


async def synth(text, out, voice="nu", rate="+0%", pitch="+0Hz"):
    import edge_tts

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Dịch vụ thỉnh thoảng trả về rỗng -> thử lại vài lần
    for attempt in range(5):
        com = edge_tts.Communicate(text, VOICES.get(voice, voice), rate=rate, pitch=pitch, boundary="WordBoundary")
        words = []
        try:
            with open(out, "wb") as f:
                async for chunk in com.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        s = chunk["offset"] / 1e7
                        words.append({"text": chunk["text"], "start": round(s, 3), "end": round(s + chunk["duration"] / 1e7, 3)})
            break
        except Exception:
            if attempt == 4:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))
    _, dur, _ = run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)])
    meta = {"file": out.name, "text": text, "duration": round(float(dur.strip() or 0), 3), "words": words}
    write_json(out.with_suffix(".words.json"), meta)
    return meta


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--out")
    ap.add_argument("--script")
    ap.add_argument("--outdir")
    ap.add_argument("--voice", default="nu")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--pitch", default="+0Hz")
    a = ap.parse_args()

    if a.script:
        lines = json.loads(Path(a.script).read_text(encoding="utf-8"))
        outdir = Path(a.outdir or Path(a.script).parent / "vo")
        for ln in lines:
            m = await synth(ln["text"], outdir / f"{ln['id']}.mp3", ln.get("voice", a.voice), ln.get("rate", a.rate), ln.get("pitch", a.pitch))
            print(f"{ln['id']}: {m['duration']}s  {ln['text'][:60]}")
    elif a.text and a.out:
        m = await synth(a.text, a.out, a.voice, a.rate, a.pitch)
        print(f"{a.out}: {m['duration']}s, {len(m['words'])} từ")
    else:
        ap.print_help()


if __name__ == "__main__":
    asyncio.run(main())
