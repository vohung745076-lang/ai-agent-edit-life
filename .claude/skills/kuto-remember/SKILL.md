---
name: kuto-remember
description: Ghi nhớ phong cách cá nhân sau khi một video được chốt - so bản đầu với bản cuối và các góp ý, rút ra quy tắc và kỹ thuật, cập nhật styles/personal để áp dụng cho các video sau. Dùng khi người dùng chốt video ("ok", "duyệt", "hoàn thành"), bảo "lưu phong cách", "nhớ cách này", hoặc sau khi sửa xong một vòng góp ý có tính khẩu vị.
---

# Ghi nhớ phong cách cá nhân

`styles/personal/` là khẩu vị của chủ kênh. Nó được nạp đầu tiên ở mọi lần dựng và thắng mọi phong cách học được.

## Nguồn để rút bài học

1. `projects/<id>/feedback.md`: mọi góp ý qua các vòng.
2. Khác biệt giữa bản đầu và bản chốt: so `PLAN.md` với trạng thái cuối của `edit/` và `edit-vertical/` (dùng `npx --yes hyperframes history` nếu có, hoặc đọc trực tiếp các scene).
3. Thay đổi người dùng tự làm trong ứng dụng HyperFrames (`npx --yes hyperframes catch-up <dir>`).
4. Chỉnh sửa trực tiếp trên `style.json` của các phong cách (trường `tokens`, `user_notes`).

## Cách ghi

Phân loại mỗi thay đổi:

- **Khẩu vị bền** (lặp lại được ở video khác: "chữ to hơn", "không dùng hiệu ứng rung", "nhạc nhỏ hơn giọng"): ghi vào `LESSONS.md`.
- **Chỉ riêng video này** ("đổi cảnh 3 với cảnh 5"): không ghi.
- Không chắc: ghi kèm nhãn `(cần xác nhận)`; lần thứ hai gặp lại thì bỏ nhãn.

`styles/personal/LESSONS.md` — mỗi bài học một dòng, có ngày và nguồn:

```markdown
## Chữ
- 2026-11-14 · Tiêu đề bản dọc tối thiểu 96px, tối đa 4 từ mỗi dòng. (video 2026-11-14-van-phong, vòng 2: "chữ nhỏ quá")
## Nhịp
## Chuyển cảnh
## Âm thanh
## Giọng kể và hài
## Không làm
```

Bài học mới mâu thuẫn bài cũ: sửa bài cũ, không để hai dòng trái nhau.

Sau đó cập nhật:

- `styles/personal/style.json`: `tokens` (màu, font, nhịp) theo giá trị đã chốt gần nhất; thêm kỹ thuật vào `techniques`. Giữ `status: "personal"`.
- `styles/personal/techniques/`: chép các scene người dùng thích (đã qua chỉnh sửa) từ dự án vừa chốt, biến nội dung thành biến để dùng lại.
- `styles/personal/STYLE.md`: viết lại phần tóm tắt cho khớp.
- Phong cách học được nào đóng góp kỹ thuật được giữ nguyên qua duyệt: tăng `uses` trong `style.json` của nó; kỹ thuật bị người dùng bỏ: ghi vào `avoid_for` hoặc ghi chú của kỹ thuật đó.

Kết thúc bằng danh sách ngắn những gì vừa ghi nhớ để người dùng xác nhận hoặc gạch bỏ.
