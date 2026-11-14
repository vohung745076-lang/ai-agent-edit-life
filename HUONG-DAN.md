# Kuto — hướng dẫn dùng nhanh

## Cài lần đầu (máy mới, sau khi clone)

Cần sẵn: Python 3, Git, Claude Code (`claude` đã đăng nhập). Rồi chạy:

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
```

Lệnh này tải Node 22 và FFmpeg bản portable vào `.runtime/`, cài thư viện Python, cài bộ skill HyperFrames.

## Mở giao diện

Bấm đúp **`start.bat`**. Trình duyệt mở `http://localhost:4173`. Giữ cửa sổ đen mở trong lúc dùng.

## Ba việc chính

| Bạn muốn | Làm gì |
| --- | --- |
| Dựng video | Trang chủ → dán link thư mục Google Drive (kèm ghi chú nếu muốn) → Enter |
| Cho Kuto học một video hay | Trang chủ → dán link TikTok/YouTube/Instagram/Facebook, hoặc bấm "Tải file mẫu lên" |
| Sửa hoặc chốt | Tab Dự án → xem bản dựng → gõ góp ý, hoặc bấm "Chốt video này" |

- Link Drive phải bật chia sẻ **"Bất kỳ ai có đường liên kết"**, mỗi thư mục tối đa 50 file. Cách khác: chép video vào `projects/<mã dự án>/raw/`.
- Video mẫu sau khi học nằm ở tab **Thư viện phong cách**, trạng thái "Chờ duyệt". Bạn xem demo, sửa trực tiếp màu, font, nhịp, ghi chú, rồi bấm **Duyệt**. Kuto chỉ dùng phong cách đã duyệt.
- Mỗi lần bạn chốt một video, Kuto ghi những gì bạn đã sửa vào **Phong cách cá nhân** (`styles/personal/LESSONS.md`) và áp dụng cho các video sau.
- Nhạc của riêng bạn: bỏ vào `library/music/`.

## Dùng thẳng trong Claude Code

Mở thư mục này bằng Claude Code rồi gõ như bình thường, ví dụ:

- `Dựng video từ link này: https://drive.google.com/drive/folders/...`
- `Học video này, mình thích cách chữ bật theo nhạc: https://www.tiktok.com/...`
- `/kuto-edit`, `/kuto-learn`, `/kuto-remember`

## Cần biết

- Kuto chạy bằng Claude Code trên gói thuê bao của bạn; mỗi video là một phiên làm việc dài của agent.
- Khi chạy từ giao diện, agent được phép tự chạy lệnh và ghi file trong thư mục này mà không hỏi lại từng bước. Danh sách công cụ được phép nằm ở đầu `app/server.mjs` (`ALLOWED_TOOLS`).
- Kuto làm lần lượt từng việc. Render một video 30 giây ở bản nháp mất vài phút trên máy này.
- Giao diện chỉ mở trên máy bạn (`127.0.0.1`), không ai khác truy cập được.
