"""Sinh index.html + compositions/ cho bản ngang (H) hoặc dọc (V). v2: kịch bản tấu hài giọng kiểu "Adam".
python -I build.py H <edit dir> | V <edit-vertical dir>
"""
import json, sys
from pathlib import Path

P = Path(r"D:\Ai agent edit video life\projects\2026-11-14-141022")
VO_DIR = P / "vo2"
TOTAL = 59.0
BG, INK, ACC, YEL = "#14121c", "#ffffff", "#ff4f9a", "#ffd84d"
V, W, H = False, 1920, 1080  # đặt lại trong main()

# Giọng đọc: id -> thời điểm bắt đầu (giây, toàn cục)
VO = {"a01": 0.15, "a02": 4.45, "a03": 8.85, "a04": 14.85, "a05": 20.5, "a06": 25.2, "a07": 28.65,
      "a08": 31.5, "a09": 33.1, "a10": 43.25, "a11": 48.15, "a12": 52.75}


def words(lid):
    return json.loads((VO_DIR / f"{lid}.words.json").read_text(encoding="utf-8"))["words"]


def wt(lid, i, scene_start=0.0):
    """Mốc (cục bộ theo scene) của từ thứ i trong câu lid."""
    return round(VO[lid] + words(lid)[i]["start"] - scene_start, 2)


# Scene: id, start, dur, media[(kind v|img, file, local_start, dur, has_audio)], kicker, title, size(H), extra
SCENES = [
    ("s01", 0.0, 4.3, [("v", "s01", 0, 4.3, False)], "Hello các con vợ!",
     "Lại là một ngày<br><b>bình thường</b><br>của công ty", 84, {}),
    ("s01b", 4.3, 4.4, [("img", "s01f.jpg", 0, 4.4, False)], "À nhầm!",
     "Sếp cho đi<br><b>NGHỈ DƯỠNG</b><br>cấm làm việc!", 92, {"punch": True}),
    ("s02", 8.7, 5.9, [("v", "s02", 0, 5.9, False)], "Hành lý",
     "", 76, {"lines": [("Đồ bơi: có", ("a03", 2)), ("Kem chống nắng: có", ("a03", 6)), ("<b>Laptop: cũng có</b>", ("a03", 10))]}),
    ("s03", 14.6, 2.8, [("v", "s03", 0, 2.8, False)], "", "Người thì<br>ngắm cảnh…", 104, {}),
    ("s04", 17.4, 2.9, [("v", "s04", 0, 2.9, False)], "Người thì lướt TikTok",
     "<b>Nghiên cứu</b><br>cách nghỉ ngơi", 92, {}),
    ("s05", 20.3, 4.7, [("v", "s05", 0, 4.7, True)], "", "<b>TẠM BIỆT</b><br>VĂN PHÒNG!", 112, {}),
    ("s06", 25.0, 3.5, [("v", "s06", 0, 3.5, False)], "Slow motion",
     "Chill như chưa<br>từng có <b>deadline</b>", 92, {}),
    ("s07", 28.5, 2.9, [("v", "s07", 0, 2.9, False)], "", "Gió mát,<br>sóng êm…", 112, {}),
    ("s10", 43.0, 4.9, [("v", "s10a", 0, 2.0, True), ("v", "s10c", 2.0, 1.4, True), ("v", "s10b", 3.4, 1.5, True)],
     "Bữa tối", "Ăn bắp xào<br><b>cho đỡ tủi</b>", 104, {}),
    ("s11", 47.9, 4.6, [("v", "s11", 0, 4.6, True)], "Anh hùng thầm lặng",
     "Tự nguyện<br>tăng ca ở<br><b>bồn rửa chén</b>", 92, {}),
    ("s12", 52.5, 6.5, [("v", "s12", 0, 6.5, False)], "", "", 0, {"end": True}),
]
CARD = ("s08", 31.4, 1.6)
CAROUSEL = ("carousel", 33.0, 10.0)
CAR_FRONTS = [0.7, 2.55, 4.85]  # lúc mỗi tấm ra trước, khớp "Báo cáo…", "Tối về…", "Sáng ra…"
CAR_STAMP = round(VO["a09"] + words("a09")[19]["start"] - CAROUSEL[1] - 0.05, 2)  # "Nghỉ dưỡng mà tưởng đi công tác"
BOUNDARIES = sorted({s[1] for s in SCENES} | {CARD[1], CAROUSEL[1]})
MUSIC_BREAKS = [(4.3, 4.95), (31.4, 33.0), (41.55, 43.3)]

CAPTIONED = ["a01", "a02", "a03", "a04", "a05", "a06", "a07", "a10", "a11"]  # a08 thẻ chữ, a09 nhãn carousel, a12 thẻ kết
SPLITS = {"a01": [4, 4, 5], "a02": [2, 4, 5, 5], "a03": [3, 4, 4, 5], "a04": [4, 2, 4, 5, 3], "a05": [2, 4, 5],
          "a06": [5, 6], "a07": [2, 4], "a10": [5, 3, 5], "a11": [4, 4, 4, 4]}

SFXLEN = {"pop": 0.12, "whoosh": 0.45, "scratch": 0.6, "ding": 0.9, "boing": 0.7, "sadtrombone": 1.8, "badumtss": 1.3}
SFXVOL = {"pop": 0.4, "whoosh": 0.25, "scratch": 0.5, "ding": 0.3, "boing": 0.35, "sadtrombone": 0.45, "badumtss": 0.55}


def sfx_list():
    out = []
    for s in SCENES:
        sid, st = s[0], s[1]
        if st > 0:
            out.append(("whoosh", st - 0.15))
        if s[4]:
            out.append(("pop", st + 0.1))
        if s[5]:
            out.append(("pop", st + 0.2))
        for _, (lid, i) in s[7].get("lines", []):
            out.append(("pop", st + wt(lid, i, st)))
    out += [("whoosh", CARD[1] - 0.15), ("whoosh", CAROUSEL[1] - 0.15),
            ("scratch", 4.3), ("scratch", CARD[1]), ("boing", 25.1), ("ding", 20.45),
            ("pop", CAROUSEL[1] + CAR_FRONTS[1]), ("pop", CAROUSEL[1] + CAR_FRONTS[2]),
            ("scratch", CAROUSEL[1] + CAR_STAMP), ("sadtrombone", 41.55),
            ("ding", 52.6), ("badumtss", round(VO["a12"] + words("a12")[-1]["end"] + 0.1, 2))]
    return sorted(out, key=lambda x: x[1])


def caption_groups():
    groups = []
    for lid in CAPTIONED:
        ws = words(lid); off = VO[lid]; i = 0
        for n in SPLITS[lid]:
            groups.append([dict(x, start=x["start"] + off, end=x["end"] + off) for x in ws[i:i + n]]); i += n
        assert i == len(ws), lid
    return groups


def caption_word_times():
    return [w["start"] for g in caption_groups() for w in g]


def scene_html(sid, dur, media, kicker, title, size, extra):
    end = extra.get("end")
    lines = extra.get("lines", [])
    mh = []
    for i, (kind, f, ls, d, au) in enumerate(media):
        if kind == "img":
            mh.append(f'        <img id="{sid}-m{i}" class="clip" data-start="{ls}" data-duration="{d}" data-track-index="{i+1}" src="assets/video/{f}" alt="" />')
        else:
            mh.append(f'        <video id="{sid}-m{i}" class="clip" data-start="{ls}" data-duration="{d}" data-media-start="0" '
                      f'data-track-index="{i+1}" src="assets/video/{f}.mp4" '
                      + ('data-has-audio="true" data-volume="0.2"' if au else "muted") + ' playsinline></video>')
    media_html = "\n".join(mh)
    if V:
        frame_css = f"""
    #{sid}-frame {{ position: absolute; inset: 0; overflow: hidden; }}
    #{sid}-zoom {{ position: absolute; inset: 0; }}
    #{sid}-frame video, #{sid}-frame img {{ position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: cover; }}
    #{sid}-shade {{ position: absolute; left: 0; right: 0; top: 0; height: 820px;
      background: linear-gradient(180deg, rgba(20,18,28,0.9) 0%, rgba(20,18,28,0.62) 60%, rgba(20,18,28,0) 100%); }}
    #{sid}-text {{ position: absolute; left: 120px; right: 120px; top: 300px; text-align: center; }}"""
        if end:
            frame_css += f"""
    #{sid}-shade {{ top: 0; bottom: 0; height: auto; background: rgba(20,18,28,0.55); }}
    #{sid}-text {{ top: 560px; }}"""
    else:
        frame_css = f"""
    #{sid}-glow {{ position: absolute; left: -10%; top: -30%; width: 70%; height: 160%;
      background: radial-gradient(closest-side, {ACC} 0%, transparent 70%); opacity: 0.22; }}
    #{sid}-frame {{ position: absolute; left: 300px; top: 70px; width: 529px; height: 940px; overflow: hidden;
      border: 8px solid #fff; border-radius: 34px; box-shadow: 0 40px 90px rgba(0,0,0,0.55); background: #000; }}
    #{sid}-zoom {{ position: absolute; inset: 0; }}
    #{sid}-frame video, #{sid}-frame img {{ position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: cover; }}
    #{sid}-text {{ position: absolute; left: 960px; width: 880px; top: {250 if end else 170}px; text-align: left; }}"""
    if end:
        text_html = f"""<div id="{sid}-text">
        <div id="{sid}-t1" class="title end">Nghỉ dưỡng<br>kiểu <b>dân<br>văn phòng</b></div>
        <div id="{sid}-sub" class="sub">Thứ Hai gặp lại nha<br>các con vợ!</div>
      </div>"""
    else:
        k = f'\n        <div id="{sid}-k" class="kicker"><span>{kicker}</span></div>' if kicker else ""
        t = f'\n        <div id="{sid}-t1" class="title">{title}</div>' if title else ""
        ls = "".join(f'\n        <div id="{sid}-l{j}" class="title line">{html}</div>' for j, (html, _) in enumerate(lines))
        text_html = f'<div id="{sid}-text">{k}{t}{ls}\n      </div>'
    fs = round(min((size or 104) * (1.15 if V else 1.0), 88 if (V and size < 100) else 999))
    if V and lines:
        fs = 74
    deco = "" if V else f'\n    <div id="{sid}-glow" data-layout-ignore></div>'
    shade = f'\n    <div id="{sid}-shade" data-layout-ignore></div>' if V else ""
    js = []
    if extra.get("punch"):  # đứng hình + phóng to giật cục + rung
        js.append(f'tl.fromTo("#{sid}-zoom", {{ scale: 1.0, x: 0 }}, {{ scale: 1.18, duration: 0.12, ease: "power4.out" }}, 0);')
        for j, at in enumerate([0.12, 0.17, 0.22, 0.27, 0.32]):
            js.append(f'tl.to("#{sid}-zoom", {{ x: {(-1) ** j * 12}, duration: 0.05, ease: "none" }}, {at});')
        js.append(f'tl.to("#{sid}-zoom", {{ x: 0, scale: 1.26, duration: {round(dur - 0.4, 2)}, ease: "none" }}, 0.37);')
        if not V:
            js.append(f'tl.fromTo("#{sid}-frame", {{ rotation: -2.5 }}, {{ rotation: -1, duration: {dur}, ease: "none" }}, 0);')
    elif V:
        js.append(f'tl.fromTo("#{sid}-frame", {{ scale: 1.0 }}, {{ scale: 1.06, duration: {dur}, ease: "none" }}, 0);')
    else:
        js.append(f'tl.fromTo("#{sid}-frame", {{ rotation: -2.5, scale: 0.96 }}, {{ rotation: -1, scale: 1.0, duration: {dur}, ease: "none" }}, 0);')
    if kicker:
        js.append(f'tl.fromTo("#{sid}-k span", {{ opacity: 0, scale: 0.6, rotation: -8 }}, {{ opacity: 1, scale: 1, rotation: -4, duration: 0.3, ease: "back.out(2.5)" }}, 0.1);')
    if title or end:
        js.append(f'tl.fromTo("#{sid}-t1", {{ opacity: 0, y: 40, scale: 0.8 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(2)" }}, 0.2);')
    st = next(s[1] for s in SCENES if s[0] == sid)
    for j, (_, (lid, i)) in enumerate(lines):
        js.append(f'tl.fromTo("#{sid}-l{j}", {{ opacity: 0, x: -40, scale: 0.85 }}, {{ opacity: 1, x: 0, scale: 1, duration: 0.28, ease: "back.out(2.2)" }}, {wt(lid, i, st)});')
    if end:
        js.append(f'tl.fromTo("#{sid}-sub", {{ opacity: 0, y: 30, scale: 0.8 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(2)" }}, {wt("a12", 9, st)});')
    js_s = "\n      ".join(js)
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; background: {BG}; font-family: "Montserrat", sans-serif; }}{frame_css}
    #{sid}-text .title {{ color: {INK}; font-weight: 900; font-size: {fs}px; line-height: 1.06; letter-spacing: -0.02em;
      text-shadow: 0 6px 0 rgba(0,0,0,0.35), 0 0 28px rgba(0,0,0,0.55); }}
    #{sid}-text .title.line {{ margin-top: 10px; }}
    #{sid}-text .title b {{ color: {ACC}; font-weight: 900; }}
    #{sid}-text .title.end b {{ color: {YEL}; }}
    #{sid}-text .kicker {{ margin-bottom: 18px; }}
    #{sid}-text .kicker span {{ display: inline-block; padding: 8px 26px; background: {YEL}; color: {BG};
      font-weight: 900; font-size: {round(50 * (1.15 if V else 1))}px; border-radius: 14px; }}
    #{sid}-text .sub {{ margin-top: 34px; display: inline-block; padding: 12px 30px; background: {ACC}; color: #fff;
      font-weight: 800; font-size: {round(48 * (1.15 if V else 1))}px; line-height: 1.15; border-radius: 16px; }}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">{deco}
    <div id="{sid}-frame">
      <div id="{sid}-zoom">
{media_html}
      </div>
    </div>{shade}
    {text_html}
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
      {js_s}
      window.__timelines["{sid}"] = tl;
    }})();
  </script>
</template>
"""


def card_html():
    sid, _, dur = CARD
    fs = 170 if V else 190
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; background: {BG}; font-family: "Montserrat", sans-serif; }}
    #s08-wrap {{ position: absolute; left: 0; right: 0; top: 0; bottom: 0; display: flex; align-items: center; justify-content: center; }}
    #s08-t {{ color: {INK}; font-weight: 900; font-size: {fs}px; letter-spacing: -0.03em; text-align: center; line-height: 1; }}
    #s08-t b {{ color: {ACC}; }}
    #s08-bar {{ position: absolute; left: 0; right: 0; top: 50%; height: 14px; margin-top: {round(fs*1.12) if V else round(fs*0.62)}px; background: {YEL}; }}
  </style>
  <div id="root" data-composition-id="s08" data-width="{W}" data-height="{H}">
    <div id="s08-bar" data-layout-ignore></div>
    <div id="s08-wrap" data-layout-allow-overflow>
      <div id="s08-t">NHƯNG{'<br>' if V else ' '}<b>MÀ!</b></div>
    </div>
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#s08-t", {{ scale: 2.2, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.22, ease: "power4.out" }}, 0);
      tl.fromTo("#s08-bar", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.35, ease: "power3.out" }}, 0.15);
      tl.fromTo("#s08-wrap", {{ x: 0, scale: 1 }}, {{ x: 0, scale: 1, duration: 0.01 }}, 0);
      [0.25, 0.31, 0.37, 0.43, 0.49, 0.55].forEach((at, i) => tl.to("#s08-wrap", {{ x: i % 2 ? -14 : 14, duration: 0.06, ease: "none" }}, at));
      tl.to("#s08-wrap", {{ x: 0, duration: 0.06, ease: "none" }}, 0.61);
      tl.to("#s08-wrap", {{ scale: 1.08, duration: {round(dur - 0.7, 2)}, ease: "none" }}, 0.67);
      window.__timelines["s08"] = tl;
    }})();
  </script>
</template>
"""


def carousel_html():
    total = CAROUSEL[2]
    src = Path(r"D:\Ai agent edit video life\blocks\carousel-3d\carousel.html").read_text(encoding="utf-8")
    body = src[src.index("<template>"):]
    panels = [("c1", "Duyệt báo cáo trên bãi cát"), ("c2", "Tối về: điện thoại vẫn reo"), ("c3", "Sáng ra: lại họp tiếp")]
    ph = "\n".join(
        f'''          <div class="car-panel" id="car-p{i+1}">
            <video id="car-v{i+1}" class="clip" data-start="0" data-duration="{total}" data-media-start="0" data-track-index="{i+1}" src="assets/video/{c}.mp4" muted playsinline></video>
            <div class="car-shade"></div>
          </div>''' for i, (c, _) in enumerate(panels))
    lh = "\n".join(
        f'    <div class="car-label clip" id="car-l{i+1}" data-start="0" data-duration="{total}" data-track-index="{i+4}"><span>{lab}</span></div>'
        for i, (_, lab) in enumerate(panels))
    stamp_dur = round(total - CAR_STAMP, 2)
    lh += (f'\n    <div class="car-stamp clip" id="car-stamp" data-start="{CAR_STAMP}" data-duration="{stamp_dur}" data-track-index="7" data-layout-allow-overlap>'
           f'<span id="car-stamp-in">Nghỉ dưỡng<br>hay <b>đi công tác?!</b></span></div>')
    a = body.index('          <!-- Mỗi tấm'); b = body.index("        </div>\n      </div>\n    </div>")
    body = body[:a] + ph + "\n" + body[b:]
    a = body.index("    <!-- Nhãn cho"); b = body.index("  </div>\n\n  <script>")
    body = body[:a] + lh + "\n" + body[b:]
    body = body.replace('data-width="1920" data-height="1080"', f'data-width="{W}" data-height="{H}"')
    body = body.replace(
        "const ratio = vertical ? 4 / 5 : CONFIG.panelRatio;\n      const pw = Math.round(vertical ? W * 0.72 : W * 0.44);\n      const ph = Math.round(pw / ratio);",
        "const ratio = 9 / 16;\n      const pw = Math.round(vertical ? W * 0.62 : H * 0.78 * ratio);\n      const ph = Math.round(pw / ratio);")
    body = body.replace('gsap.set(l, { fontSize: 62, bottom: "24%" })', 'gsap.set(l, { fontSize: 60, top: "25%", bottom: "auto" })')
    body = body.replace("bottom: 7%;", "top: 23%;" if V else "bottom: 4%;")
    body = body.replace("turn: 0.75,", "turn: 0.45,")
    body = body.replace("total: 8, // thời lượng", f"total: {total}, // thời lượng")
    # mốc ra trước của từng tấm khớp giọng đọc thay vì chia đều
    body = body.replace("const hold = (CONFIG.total - CONFIG.intro) / n;",
                        f"const FRONTS = {json.dumps(CAR_FRONTS)};\n      const holdOf = (i) => (i < n - 1 ? FRONTS[i + 1] : CONFIG.total) - FRONTS[i];")
    body = body.replace("const t0 = CONFIG.intro + i * hold;", "const t0 = FRONTS[i];\n        const hold = holdOf(i);")
    stamp_css = f"""
    .car-stamp {{ position: absolute; left: 0; right: 0; top: {'34%' if V else '30%'}; text-align: center; }}
    #car-stamp-in {{ display: inline-block; padding: 18px 40px; background: {BG}; color: #fff; border: 8px solid {ACC};
      border-radius: 22px; font-weight: 900; font-size: {80 if V else 92}px; line-height: 1.05; letter-spacing: -0.02em; }}
    #car-stamp-in b {{ color: {YEL}; }}
  </style>"""
    body = body.replace("\n  </style>", stamp_css, 1)
    body = body.replace('      window.__timelines["carousel"] = tl;',
                        f'      tl.fromTo("#car-stamp-in", {{ opacity: 0, scale: 2.4, rotation: -14 }}, {{ opacity: 1, scale: 1, rotation: -6, duration: 0.25, ease: "power4.in" }}, {CAR_STAMP});\n'
                        f'      [0.27, 0.32, 0.37].forEach((d, i) => tl.to("#car-stamp-in", {{ x: i % 2 ? -10 : 10, duration: 0.05, ease: "none" }}, {CAR_STAMP} + d));\n'
                        f'      tl.to("#car-stamp-in", {{ x: 0, duration: 0.05, ease: "none" }}, {CAR_STAMP} + 0.42);\n'
                        '      window.__timelines["carousel"] = tl;')
    assert "const ratio = 9 / 16" in body and "FRONTS[i]" in body and "car-stamp-in\", { opacity: 0" in body
    return body


def captions_html():
    groups = caption_groups()
    out = []; js = []
    for gi, g in enumerate(groups):
        s = round(g[0]["start"] - 0.05, 3)
        nxt = groups[gi + 1][0]["start"] - 0.05 if gi + 1 < len(groups) else 99
        cut = min([b for b in BOUNDARIES if b > g[0]["start"] + 0.3], default=99) - 0.1  # tắt trước khi chuyển cảnh
        e = round(max(min(g[-1]["end"] + 0.4, nxt, cut), g[0]["start"] + 0.4), 3)
        spans = " ".join(f'<span id="cg{gi}w{wi}" class="w">{w["text"]}</span>' for wi, w in enumerate(g))
        out.append(f'    <div id="cg{gi}" class="cap clip" data-start="{s}" data-duration="{round(e - s, 3)}" data-track-index="1"><span class="in">{spans}</span></div>')
        js.append(f'      tl.fromTo("#cg{gi} .in", {{ opacity: 0, y: 16, scale: 0.92 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.14, ease: "back.out(2)" }}, {s});')
        for wi, w in enumerate(g):
            js.append(f'      tl.fromTo("#cg{gi}w{wi}", {{ color: "#ffffff" }}, {{ color: "{YEL}", duration: 0.05 }}, {round(w["start"], 3)});')
            js.append(f'      tl.to("#cg{gi}w{wi}", {{ color: "#ffffff", duration: 0.05 }}, {round(max(w["end"], w["start"] + 0.12), 3)});')
        js.append(f'      tl.set("#cg{gi} .in", {{ opacity: 0 }}, {round(e - 0.001, 3)});')
    pos = ("left: 60px; right: 60px; top: 1100px; text-align: center;" if V
           else "left: 960px; width: 880px; top: 720px; text-align: left;")
    fs = 64 if V else 54
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; font-family: "Montserrat", sans-serif; }}
    .cap {{ position: absolute; {pos} overflow: visible; }}
    .cap .in {{ display: inline-block; padding: 10px 24px; background: rgba(0,0,0,0.55); border-radius: 16px;
      font-weight: 800; font-size: {fs}px; line-height: 1.2; color: #fff; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
{chr(10).join(out)}
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
      window.__timelines["captions"] = tl;
    }})();
  </script>
</template>
"""


def index_html():
    hosts = []
    items = [(s[0], s[1], s[2]) for s in SCENES] + [CARD, CAROUSEL]
    items.sort(key=lambda x: x[1])
    for sid, st, d in items:
        hosts.append(f'      <div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" '
                     f'data-start="{st}" data-duration="{d}" data-track-index="1" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}" style="z-index: 1"></div>')
    hosts.append(f'      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" '
                 f'data-start="0" data-duration="{TOTAL}" data-track-index="2" data-track-kind="captions" '
                 f'data-width="{W}" data-height="{H}" style="z-index: 5"></div>')
    aud = [f'      <audio id="music" class="clip" data-start="0" data-duration="{TOTAL}" data-track-index="10" src="assets/audio/music2.wav" data-volume="0.16" data-fade-out="1.5"></audio>',
           f'      <audio id="ticks" class="clip" data-start="0" data-duration="{TOTAL}" data-track-index="13" src="assets/audio/ticks.wav" data-volume="0.35"></audio>']
    for lid, at in VO.items():
        d = json.loads((VO_DIR / f"{lid}.words.json").read_text(encoding="utf-8"))["duration"]
        aud.append(f'      <audio id="vo-{lid}" class="clip" data-start="{at}" data-duration="{d}" data-track-index="11" src="assets/vo2/{lid}.mp3" data-volume="1.15"></audio>')
    for i, (n, at) in enumerate(sfx_list()):
        aud.append(f'      <audio id="sfx{i}" class="clip" data-start="{round(at, 2)}" data-duration="{SFXLEN[n]}" data-track-index="{12 if i % 2 == 0 else 14}" src="assets/audio/{n}.wav" data-volume="{SFXVOL[n]}"></audio>')
    return f"""<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: {BG}; }}
      #root {{ width: 100%; height: 100%; position: relative; font-family: "Montserrat", sans-serif; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}">
{chr(10).join(hosts)}
{chr(10).join(aud)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def main():
    global V, W, H
    mode, out = sys.argv[1], Path(sys.argv[2])
    V = mode == "V"
    W, H = (1080, 1920) if V else (1920, 1080)
    comp = out / "compositions"
    comp.mkdir(parents=True, exist_ok=True)
    keep = {f"{s[0]}.html" for s in SCENES} | {"s08.html", "carousel.html", "captions.html"}
    for old in comp.glob("*.html"):
        if old.name not in keep:
            old.unlink()
    for s in SCENES:
        (comp / f"{s[0]}.html").write_text(scene_html(s[0], s[2], s[3], s[4], s[5], s[6], s[7]), encoding="utf-8")
    (comp / "s08.html").write_text(card_html(), encoding="utf-8")
    (comp / "carousel.html").write_text(carousel_html(), encoding="utf-8")
    (comp / "captions.html").write_text(captions_html(), encoding="utf-8")
    (out / "index.html").write_text(index_html(), encoding="utf-8")
    print("built", mode, out, "stamp", CAR_STAMP)


if __name__ == "__main__":
    main()
