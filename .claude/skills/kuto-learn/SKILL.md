---
name: kuto-learn
description: Học phong cách dựng từ một video mẫu (TikTok, YouTube, Instagram, Facebook hoặc file) - phân tích chữ, font, màu, nhịp cắt, chuyển cảnh, animation, motion, hiệu ứng, âm thanh; viết bảng phong cách và dựng video demo để người dùng duyệt và chỉnh; lưu thành skill trong thư viện styles/. Dùng khi người dùng gửi video mẫu, nói "học video này", "tham khảo", "video này edit hay", hoặc góp ý cho một phong cách đang chờ duyệt.
---

# Học phong cách từ video mẫu

Đọc `CLAUDE.md` ở gốc dự án trước. Mỗi lệnh PowerShell nạp `tools\env.ps1`.

Mục tiêu: rút ra **ngữ pháp dựng** của video mẫu thành các kỹ thuật rời, dùng lại được cho từng phân đoạn. Không chép nội dung (hình, nhạc, logo, nhân vật, câu chữ) của video mẫu.

Thư mục phong cách: `styles/<slug>/`. Nếu lời nhắc đã cho sẵn `slug` thì dùng đúng nó. Ghi `style.json` với `status: "learning"` ngay từ đầu để giao diện thấy tiến trình.

## 1. Lấy video mẫu

```powershell
python tools\fetch_reference.py "<link hoặc file>" "styles\<slug>"
```

Mã thoát 2: ghi lỗi vào `style.json.message`, đặt `status: "error"`, đề nghị người dùng tải file lên, rồi dừng.

## 2. Đo và xem

```powershell
python tools\analyze_video.py "styles\<slug>\source\reference.mp4" --out "styles\<slug>\analysis" --interval 0.5
npx --yes hyperframes measure "styles\<slug>\source\reference.mp4"     # xem --help để chọn phép đo: cuts, motion, eases, look
```

- Read toàn bộ bảng khung hình. Với **mỗi kiểu khoảnh khắc** (chữ vào/ra, chuyển cảnh, phóng to, hiệu ứng), soi dải dày: `--dense <s> <e> --fps 8`.
- Mọi con số ghi kèm nhãn **đo được** hay **ước lượng**.

## 3. Rút ngữ pháp

Trả lời đủ các mục sau bằng số liệu cụ thể:

| Mục | Cần ghi |
| --- | --- |
| Nhịp cắt | số cảnh, độ dài cảnh trung bình/ngắn nhất/dài nhất, cắt mỗi phút, nhịp có bám nhạc không, giây đầu tiên mở thế nào |
| Chữ | kiểu font (gần nhất với font nào dùng được, có hỗ trợ tiếng Việt), độ đậm, cỡ so với khung, viền/bóng/nền, vị trí, số từ mỗi dòng, cách nhấn từ khoá (màu, cỡ) |
| Chuyển động chữ | vào và ra kiểu gì, thời lượng, kiểu ease, theo từ hay theo dòng |
| Chuyển cảnh | các loại dùng, tần suất, thời lượng, dùng ở ngữ cảnh nào |
| Máy và hình | phóng to nhấn mạnh, lia, rung, tốc độ nhanh/chậm, cắt cúp, khung trong khung, nhãn dán, emoji |
| Màu và hiệu ứng | bảng màu theo vai trò (nền, chữ, nhấn), màu phim, hạt, viền mờ, phát sáng |
| Âm thanh | loại nhạc, nhịp, tiếng hiệu ứng ở hành động nào, giọng đọc hay lời gốc |
| Cấu trúc | các phần của video và thời lượng từng phần |

## 4. Tách thành kỹ thuật dùng lại

Mỗi kỹ thuật đáng giữ thành một file scene HyperFrames trong `styles/<slug>/techniques/<id>.html` (theo hợp đồng `/hyperframes`: nằm trong `<template>`, có khối CONFIG, chữ và màu là biến), dựng lại bằng nội dung trung tính của riêng ta. Tìm trong `/hyperframes-registry` trước; có khối gần giống thì cài rồi chỉnh thay vì viết từ đầu.

Với mỗi kỹ thuật ghi: `id`, tên, **dùng khi nào**, **không dùng khi nào**, thông số chính, file.

## 5. Viết `style.json` và `STYLE.md`

`style.json` (giao diện đọc và cho người dùng sửa trực tiếp):

```json
{
  "slug": "<slug>",
  "name": "Tên dễ nhớ do bạn đặt",
  "status": "draft",
  "source": "<link>",
  "created": "2026-11-14",
  "summary": "2–3 câu: phong cách này là gì, mạnh ở đâu",
  "topics": ["công sở", "vlog một ngày"],
  "best_for": "Loại nội dung và phân đoạn hợp nhất",
  "avoid_for": "Loại nội dung không hợp",
  "tokens": {
    "palette": [{ "role": "nền", "hex": "#101014" }, { "role": "chữ", "hex": "#ffffff" }, { "role": "nhấn", "hex": "#ffd60a" }],
    "fonts": [{ "role": "tiêu đề", "family": "Montserrat", "weight": 900, "note": "gần nhất với font gốc, đủ dấu tiếng Việt" }],
    "pacing": { "avg_shot": 1.6, "cuts_per_min": 38, "hook_seconds": 1.2 },
    "transitions": ["cắt thẳng theo nhịp", "whip-pan 0.25s giữa hai bối cảnh"],
    "text_motion": ["từng từ bật lên, back.out, 0.18s"],
    "effects": ["phóng 108% vào câu chốt"],
    "audio": ["nhạc lo-fi 90 BPM", "pop khi chữ xuất hiện"]
  },
  "techniques": [
    { "id": "caption-pop", "name": "Phụ đề bật từng từ", "when": "lời thoại nhanh, hài", "avoid": "cảnh tĩnh, trang trọng", "file": "techniques/caption-pop.html" }
  ],
  "demo": "demo.mp4",
  "demo_vertical": "demo-9x16.mp4",
  "user_notes": "",
  "message": "Điều cần người duyệt quyết định"
}
```

`STYLE.md` là **bảng phong cách** cho người đọc: nguồn, tóm tắt, bảng các mục ở bước 3 (số liệu + nhãn đo được/ước lượng), danh sách kỹ thuật kèm khi nào dùng, những gì cố ý không lấy, và gợi ý điều chỉnh để thành phong cách riêng.

## 6. Dựng demo để duyệt

- Tạo dự án HyperFrames `styles/<slug>/demo/` dài 10–15 giây, trình diễn lần lượt các kỹ thuật bằng **nội dung của người dùng**: ưu tiên cảnh quay trong `projects/*/raw` gần nhất; nếu chưa có thì dùng nền màu, hình khối và chữ mẫu chủ đề công sở.
- `check`, render `-q draft` ra `styles/<slug>/demo.mp4`; làm bản dọc bằng `tools\fork_vertical.ps1` rồi render ra `demo-9x16.mp4` nếu video mẫu là khổ dọc hoặc kỹ thuật phụ thuộc bố cục.
- Tự xem lại demo bằng `analyze_video.py --no-transcribe`, so với bảng khung hình của video mẫu: đúng ngữ pháp chưa.
- Đặt `status: "draft"`, điền `message`. Kết thúc lượt bằng tóm tắt: học được gì, đề xuất dùng ở đâu, cần duyệt gì.

Phong cách `draft` **chưa được dùng** để dựng video. Người dùng duyệt trên giao diện (đặt `status: "approved"`) hoặc nói "duyệt".

## Sửa theo góp ý

Khi lời nhắc chứa góp ý cho một phong cách:

1. Đọc lại `style.json` trước: người dùng có thể đã sửa trực tiếp `tokens`, `best_for`, `user_notes` trên giao diện. Coi những giá trị đó là đúng.
2. Ghi góp ý vào `styles/<slug>/feedback.md`.
3. Sửa kỹ thuật và `STYLE.md` cho khớp, dựng lại demo, giữ `status: "draft"` cho tới khi được duyệt.
4. Những thay đổi người dùng yêu cầu chính là **khẩu vị riêng** của họ: ghi thêm một dòng vào `styles/personal/LESSONS.md` (xem `/kuto-remember`).
