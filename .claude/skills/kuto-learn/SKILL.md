---
name: kuto-learn
description: Học phong cách dựng từ một video mẫu (YouTube, TikTok, Instagram, Facebook, nguồn được cấp phép hoặc file người dùng cung cấp) - thu thập bằng yt-dlp (video, audio, phụ đề, metadata), phân tích thành 8 nhóm dữ liệu (pacing, transition, camera, typography, color grading, sound design, storytelling, composition) cùng cấu trúc timeline, lưu vào kho tri thức styles/, dựng demo để người dùng duyệt và chỉnh. Dùng khi người dùng gửi video mẫu, nói "học video này", "tham khảo", "video này edit hay", hoặc góp ý cho một phong cách đang chờ duyệt.
---

# Reference Video Learning — học từ video mẫu

Đọc `CLAUDE.md` ở gốc dự án trước. Mỗi lệnh PowerShell nạp `tools\env.ps1`.

**Không xem rồi bắt chước.** Video mẫu được tách thành dữ liệu theo 8 nhóm và một cấu trúc timeline; thứ được lưu là **quy tắc dựng áp dụng được cho video khác**. Nội dung của mẫu (hình, nhạc, logo, nhân vật, câu chữ, trò đùa) không được chép.

```
Nguồn (YouTube / nguồn được cấp phép / file người dùng)
  → 1. Media Acquisition        tools/fetch_reference.py (yt-dlp)
  → 2. Video Analysis Agent     tools/analyze_style.py + agent kuto-video-analyst
  → 3. Editing Style Knowledge Base   styles/<slug>/style.json + tools/style_kb.py
  → 4. Demo + duyệt             người dùng xem, sửa, duyệt trên giao diện
  ⇒ dùng lại ở /kuto-edit: Creative Director Agent chọn → Timeline & Editing Agent dựng
```

Thư mục phong cách: `styles/<slug>/`. Lời nhắc đã cho sẵn `slug` thì dùng đúng nó. Ghi `style.json` bằng Python (`ensure_ascii=False`); cập nhật `status` và `message` ở mỗi tầng để giao diện thấy tiến trình (`status: "learning"` cho tới khi có demo).

## 1. Media Acquisition (yt-dlp)

```powershell
python tools\fetch_reference.py "<link hoặc file>" "styles\<slug>"      # thêm --max-seconds 300, --langs vi,en, --cookies-browser chrome khi cần
```

Thu về trong `source/`: `reference.mp4`, `audio.wav`, `subtitles.json` (nếu nguồn có), `thumbnail.jpg`, `info.json` (tiêu đề, kênh, thời lượng, lượt xem/thích, thẻ, mô tả, chương, giấy phép, loại nguồn).

- Mã thoát 2: đặt `status: "error"`, ghi nguyên nhân và cách xử lý vào `message` (tải file lên qua giao diện, hoặc `--cookies-browser`), rồi dừng.
- Video dài hơn `--max-seconds` chỉ được phân tích phần đầu: ghi rõ điều này trong `STYLE.md`.
- Ghi `source`, `source_type`, `license` vào `style.json`.

## 2. Video Analysis Agent

Giao cho agent **`kuto-video-analyst`** (công cụ Agent, `subagent_type: "kuto-video-analyst"`), lời nhắc gồm: thư mục `styles/<slug>`, ghi chú của người dùng về điều họ thích ở video này (nếu có). Agent đó chạy `analyze_video.py` + `analyze_style.py`, xem bảng khung hình, ảnh tĩnh, dải dày, rồi ghi `styles/<slug>/analysis/groups.json`.

Nếu phiên này không có agent đó: tự làm đúng theo `.claude/agents/kuto-video-analyst.md`.

Nhận kết quả xong, **kiểm lại** `groups.json` trước khi dùng:

- Đủ 8 nhóm: `pacing`, `transition`, `camera`, `typography`, `color`, `sound`, `storytelling`, `composition`. Mỗi nhóm có `summary`, `rules`, `confidence`.
- `rules` là quy tắc áp dụng được cho video khác, có số cụ thể; không phải mô tả lại video mẫu.
- `structure.segments` có `role` (`hook`, `setup`, `main`, `climax`, `cta`, `outro`), `share` cộng lại ≈ 1.
- Thiếu hoặc mơ hồ thì tự bổ sung bằng cách xem lại dải dày của đoạn liên quan.

## 3. Editing Style Knowledge Base

### Tách kỹ thuật dùng lại

Mỗi `technique_candidates` đáng giữ thành một scene HyperFrames trong `styles/<slug>/techniques/<id>.html` (theo hợp đồng `/hyperframes`: nằm trong `<template>`, có khối CONFIG, chữ và màu là biến), dựng lại bằng nội dung trung tính của riêng ta. Tìm trong `/hyperframes-registry` trước; có khối gần giống thì cài rồi chỉnh.

### `style.json` — bản ghi trong kho

```json
{
  "slug": "<slug>",
  "name": "Tên dễ nhớ do bạn đặt",
  "status": "draft",
  "source": "<link>", "source_type": "Youtube qua yt-dlp", "license": null,
  "created": "2026-11-14",
  "summary": "2–3 câu: phong cách này là gì, mạnh ở đâu",
  "topics": ["công sở", "vlog một ngày"],
  "best_for": "Loại nội dung và phân đoạn hợp nhất",
  "avoid_for": "Loại nội dung không hợp",
  "tokens": {
    "palette": [{ "role": "nền", "hex": "#101014" }, { "role": "chữ", "hex": "#ffffff" }, { "role": "nhấn", "hex": "#ffd60a" }],
    "fonts": [{ "role": "tiêu đề", "family": "Montserrat", "weight": 900, "note": "gần nhất với font gốc, đủ dấu tiếng Việt" }],
    "pacing": { "avg_shot": 1.6, "cuts_per_min": 38, "hook_seconds": 1.2 },
    "transitions": ["cắt thẳng theo nhịp"], "text_motion": ["từng từ bật lên, back.out, 0.18s"],
    "effects": ["phóng 108% vào câu chốt"], "audio": ["nhạc lo-fi 90 BPM", "pop khi chữ xuất hiện"]
  },
  "analysis": {
    "pacing":       { "summary": "…", "rules": ["…"], "measured": {}, "confidence": "đo được" },
    "transition":   { "summary": "…", "rules": ["…"], "confidence": "ước lượng" },
    "camera":       { "summary": "…", "rules": ["…"], "confidence": "ước lượng" },
    "typography":   { "summary": "…", "rules": ["…"], "confidence": "nhìn bằng mắt" },
    "color":        { "summary": "…", "rules": ["…"], "measured": {}, "confidence": "đo được" },
    "sound":        { "summary": "…", "rules": ["…"], "measured": {}, "confidence": "đo được" },
    "storytelling": { "summary": "…", "rules": ["…"], "confidence": "nhìn bằng mắt" },
    "composition":  { "summary": "…", "rules": ["…"], "confidence": "nhìn bằng mắt" }
  },
  "structure": {
    "duration": 32.5, "aspect": "9:16",
    "segments": [
      { "role": "hook", "label": "Mở đầu gây chú ý", "start": 0, "end": 2.1, "share": 0.06,
        "what": "…", "pacing": "…", "techniques": ["caption-pop"] }
    ]
  },
  "techniques": [
    { "id": "caption-pop", "name": "Phụ đề bật từng từ", "group": "typography", "when": "lời thoại nhanh, hài",
      "avoid": "cảnh tĩnh, trang trọng", "file": "techniques/caption-pop.html" }
  ],
  "demo": "demo.mp4", "demo_vertical": "demo-9x16.mp4",
  "user_notes": "", "message": "Điều cần người duyệt quyết định"
}
```

- `analysis` và `structure` chép từ `groups.json` (đã kiểm). `tokens` là bản rút gọn để người dùng sửa nhanh; phải khớp với `analysis`.
- `tokens.palette` lấy từ bảng màu đo được, gán vai trò; `tokens.pacing` lấy từ số đo.

### `STYLE.md` — bảng phong cách cho người đọc

Nguồn và giấy phép; tóm tắt; **8 mục theo 8 nhóm** (mỗi mục: nhận định + số liệu kèm nhãn đo được / ước lượng / nhìn bằng mắt + quy tắc); sơ đồ cấu trúc timeline; danh sách kỹ thuật kèm khi nào dùng; những gì cố ý không lấy; gợi ý điều chỉnh để thành phong cách riêng của chủ kênh.

### Lập chỉ mục

```powershell
python tools\style_kb.py index
```

## 4. Demo để duyệt

- Dự án HyperFrames `styles/<slug>/demo/` dài 10–15 giây, đi theo **cấu trúc đã học** thu nhỏ (hook → main → kết) và trình diễn các kỹ thuật bằng **nội dung của người dùng**: ưu tiên cảnh quay trong `projects/*/raw` gần nhất; chưa có thì dùng nền màu, hình khối và chữ mẫu chủ đề công sở.
- `check`, render `-q draft` ra `styles/<slug>/demo.mp4`; làm bản dọc bằng `tools\fork_vertical.ps1` rồi render ra `demo-9x16.mp4` nếu video mẫu là khổ dọc hoặc kỹ thuật phụ thuộc bố cục.
- Tự kiểm: chạy `analyze_style.py` trên demo và so với số đo của mẫu (nhịp cắt, kiểu chuyển cảnh, tông màu). Lệch nhiều thì sửa demo.
- Đặt `status: "draft"`, điền `message`. Kết thúc lượt bằng tóm tắt: học được gì theo 8 nhóm (mỗi nhóm một dòng), cấu trúc timeline, đề xuất dùng ở loại video nào, cần duyệt gì.

Phong cách `draft` **chưa được dùng** để dựng video. Người dùng duyệt trên giao diện (đặt `status: "approved"`) hoặc nói "duyệt".

## Sửa theo góp ý

1. Đọc lại `style.json` trước: người dùng có thể đã sửa trực tiếp `tokens`, `analysis.*.rules`, `best_for`, `user_notes` trên giao diện. Coi những giá trị đó là đúng.
2. Ghi góp ý vào `styles/<slug>/feedback.md`.
3. Sửa kỹ thuật, `analysis`, `structure`, `STYLE.md` cho khớp; dựng lại demo; chạy `style_kb.py index`; giữ `status: "draft"` cho tới khi được duyệt.
4. Thay đổi người dùng yêu cầu là **khẩu vị riêng**: ghi thêm một dòng vào `styles/personal/LESSONS.md` (xem `/kuto-remember`).
