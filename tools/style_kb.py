"""EDITING STYLE KNOWLEDGE BASE: lập chỉ mục và tra cứu thư viện phong cách trong styles/.

Dùng:
  python tools/style_kb.py index
        -> ghi styles/INDEX.json + styles/INDEX.md (mọi phong cách, kèm 8 nhóm phân tích và cấu trúc timeline)
  python tools/style_kb.py match --topic "một ngày đi làm, hài, văn phòng" [--format 9:16] [--duration 30] [--speech yes|no]
        -> xếp hạng các phong cách ĐÃ DUYỆT theo độ hợp với video mới (điểm + lý do). Chỉ là gợi ý:
           Creative Director quyết định cuối cùng và có quyền không chọn phong cách nào.
  python tools/style_kb.py show <slug>
        -> in đầy đủ quy tắc dựng + cấu trúc timeline của một phong cách

Một phong cách chỉ được dùng để dựng khi status là "approved" hoặc "personal".
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

from common import ROOT, read_json, write_json

STYLES = ROOT / "styles"
GROUPS = [("pacing", "Pacing · nhịp dựng"), ("transition", "Transition · chuyển cảnh"), ("camera", "Camera · góc và chuyển động máy"),
          ("typography", "Typography · chữ"), ("color", "Color grading · màu"), ("sound", "Sound design · âm thanh"),
          ("storytelling", "Storytelling · cách kể"), ("composition", "Composition · bố cục")]
USABLE = ("approved", "personal")
STOP = set("va la cua cho voi mot cac nhung the nay khi thi de trong tren duoi tu den co khong video clip canh doan di ve ra vao".split())


def fold(text):
    t = unicodedata.normalize("NFD", str(text or "").lower()).replace("đ", "d")
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", fold(text)) if len(w) > 1 and w not in STOP}


def load_all():
    out = []
    for d in sorted(STYLES.iterdir()) if STYLES.exists() else []:
        if d.is_dir() and not d.name.startswith("_"):
            s = read_json(d / "style.json")
            if s:
                s["slug"] = d.name
                out.append(s)
    return out


def entry(s):
    an, st = s.get("analysis") or {}, s.get("structure") or {}
    return {
        "slug": s["slug"], "name": s.get("name"), "status": s.get("status"), "usable": s.get("status") in USABLE,
        "summary": s.get("summary"), "topics": s.get("topics") or [], "best_for": s.get("best_for"), "avoid_for": s.get("avoid_for"),
        "format": st.get("aspect"), "duration": st.get("duration"),
        "pacing": (s.get("tokens") or {}).get("pacing"),
        "analysis": {k: {"summary": (an.get(k) or {}).get("summary", ""), "rules": (an.get(k) or {}).get("rules", [])} for k, _ in GROUPS if an.get(k)},
        "structure": [{"role": g.get("role"), "label": g.get("label"), "share": g.get("share"), "what": g.get("what")} for g in st.get("segments") or []],
        "techniques": [{"id": t.get("id"), "name": t.get("name"), "when": t.get("when"), "avoid": t.get("avoid"), "file": t.get("file")}
                       for t in s.get("techniques") or []],
        "uses": s.get("uses", 0),
    }


def cmd_index(_):
    items = [entry(s) for s in load_all()]
    write_json(STYLES / "INDEX.json", {"groups": [k for k, _ in GROUPS], "styles": items})
    L = ["# Kho tri thức phong cách dựng", "",
         "Tự sinh bằng `python tools/style_kb.py index`. Chỉ phong cách **dùng được** (đã duyệt hoặc cá nhân) mới được áp dụng.", ""]
    for e in items:
        L += [f"## {e['name']} (`{e['slug']}`) — {e['status']}{'' if e['usable'] else ' · CHƯA dùng được'}",
              f"- Chủ đề: {', '.join(e['topics']) or '—'}", f"- Hợp với: {e['best_for'] or '—'}", f"- Không hợp: {e['avoid_for'] or '—'}"]
        if e["structure"]:
            L.append("- Cấu trúc: " + " → ".join(f"{g['label'] or g['role']} ({int((g['share'] or 0) * 100)}%)" for g in e["structure"]))
        if e["techniques"]:
            L.append("- Kỹ thuật: " + ", ".join(t["name"] or t["id"] for t in e["techniques"]))
        L.append("")
    (STYLES / "INDEX.md").write_text("\n".join(L), encoding="utf-8")
    print(f"Đã lập chỉ mục {len(items)} phong cách ({sum(1 for e in items if e['usable'])} dùng được) -> styles/INDEX.json")


def cmd_match(a):
    q = words(a.topic)
    results = []
    for s in load_all():
        if s.get("status") not in USABLE:
            continue
        e, reasons, score = entry(s), [], 0.0
        topic_hit = q & words(" ".join(e["topics"]))
        fit_hit = q & words(e["best_for"])
        sum_hit = q & words(e["summary"])
        avoid_hit = q & words(e["avoid_for"])
        score += 3 * len(topic_hit) + 2 * len(fit_hit) + 1 * len(sum_hit) - 4 * len(avoid_hit)
        if topic_hit:
            reasons.append(f"trùng chủ đề: {', '.join(sorted(topic_hit))}")
        if fit_hit:
            reasons.append(f"hợp mô tả 'hợp với': {', '.join(sorted(fit_hit))}")
        if avoid_hit:
            reasons.append(f"CẢNH BÁO trùng mục 'không hợp': {', '.join(sorted(avoid_hit))}")
        if a.format and e["format"]:
            same = fold(a.format).replace("x", ":") in fold(e["format"]).replace("x", ":")
            score += 1 if same else -0.5
            reasons.append("cùng khổ hình" if same else f"khác khổ hình (mẫu {e['format']}): phải bố cục lại")
        if a.duration and e["duration"]:
            ratio = a.duration / max(1, e["duration"])
            if 0.5 <= ratio <= 2:
                score += 1
                reasons.append("thời lượng tương đương: dùng được cấu trúc timeline")
            else:
                reasons.append(f"thời lượng lệch nhiều (mẫu {e['duration']}s): chỉ lấy tỉ lệ các phần, không lấy số giây")
        if a.speech:
            voice = fold(((s.get("analysis") or {}).get("sound") or {}).get("summary", ""))
            has = any(k in voice for k in ("loi thoai", "giong doc", "voice"))
            if a.speech == "yes" and has:
                score += 1
                reasons.append("mẫu cũng dựa trên lời thoại/giọng đọc")
        if s.get("status") == "personal":
            reasons.append("phong cách cá nhân: LUÔN áp dụng làm nền")
        whole = bool(topic_hit) and not avoid_hit
        results.append({
            "slug": e["slug"], "name": e["name"], "status": e["status"], "score": round(score, 1),
            "apply": "toàn bộ cấu trúc + kỹ thuật (cùng chủ đề)" if whole else "chỉ từng kỹ thuật ở phân đoạn hợp nội dung",
            "reasons": reasons, "structure": e["structure"], "techniques": e["techniques"],
        })
    results.sort(key=lambda r: (r["status"] != "personal", -r["score"]))
    print(json.dumps({"query": a.topic, "matches": results,
                      "note": "Điểm chỉ là gợi ý từ khoá. Không phong cách nào đủ hợp thì chỉ dùng phong cách cá nhân."},
                     ensure_ascii=False, indent=2))


def cmd_show(a):
    s = read_json(STYLES / a.slug / "style.json")
    if not s:
        raise SystemExit(f"Không có phong cách {a.slug}")
    print(f"# {s.get('name')} ({a.slug}) — {s.get('status')}\n{s.get('summary', '')}\n")
    an = s.get("analysis") or {}
    for k, label in GROUPS:
        g = an.get(k) or {}
        print(f"## {label}\n{g.get('summary', '(chưa phân tích)')}")
        for r in g.get("rules", []):
            print(f"- {r}")
        print()
    st = s.get("structure") or {}
    if st.get("segments"):
        print(f"## Cấu trúc timeline ({st.get('duration')}s, {st.get('aspect')})")
        for g in st["segments"]:
            print(f"- [{g.get('start')}–{g.get('end')}s · {int((g.get('share') or 0) * 100)}%] {g.get('label') or g.get('role')}: "
                  f"{g.get('what', '')} | nhịp: {g.get('pacing', '')} | kỹ thuật: {', '.join(g.get('techniques') or [])}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index")
    m = sub.add_parser("match")
    m.add_argument("--topic", required=True)
    m.add_argument("--format", default="")
    m.add_argument("--duration", type=float, default=0)
    m.add_argument("--speech", choices=["yes", "no"], default="")
    sh = sub.add_parser("show")
    sh.add_argument("slug")
    a = ap.parse_args()
    {"index": cmd_index, "match": cmd_match, "show": cmd_show}[a.cmd](a)


if __name__ == "__main__":
    main()
