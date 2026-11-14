---
name: kuto-edit
description: Dựng video hoàn chỉnh từ link Google Drive hoặc thư mục cảnh quay - tải về, xem hiểu toàn bộ video, lên ý tưởng và thứ tự cảnh, viết kịch bản, dựng bằng HyperFrames + FFmpeg (chuyển cảnh, chữ, motion, carousel 3D, nhạc, giọng đọc AI), xuất cả 16:9 và 9:16. Dùng khi người dùng đưa link Drive, bảo "dựng video", "edit video", hoặc góp ý sửa một video đang chờ duyệt.
---

# Dựng video từ cảnh quay

Đọc `CLAUDE.md` ở gốc dự án trước (môi trường, công cụ, `project.json`). Mỗi lệnh PowerShell nạp `tools\env.ps1`. Cập nhật `project.json` (`status`, `step`) trước khi bắt đầu mỗi bước để giao diện hiển thị tiến trình.

Nếu lời nhắc đã cho sẵn thư mục dự án (`projects/<id>`), dùng đúng thư mục đó. Nếu chưa, tạo `projects/<yyyy-mm-dd>-<slug>`.

## 1. Tải cảnh quay — `status: downloading`

```powershell
python tools\drive_fetch.py "<link>" "projects\<id>"
```

- Mã thoát 2 = link riêng tư hoặc lỗi tải. Thử connector Google Drive nếu phiên này có (`mcp__claude_ai_Google_Drive__*`); không được thì đặt `status: "error"`, ghi hướng dẫn mở quyền chia sẻ vào `message` rồi dừng.
- Nếu `raw/` đã có file (người dùng tự chép vào) thì bỏ qua bước tải.

## 2. Xem hiểu — `status: analyzing`

```powershell
python tools\analyze_video.py "projects\<id>\raw" --out "projects\<id>\analysis"
```

- Đọc `analysis/INDEX.md`, rồi **Read từng file `.sheet-NN.jpg`** để thật sự nhìn nội dung. Không lên kế hoạch khi chưa xem hết bảng khung hình.
- Với mỗi video ghi nhận: đang diễn ra chuyện gì, ai, ở đâu, khoảnh khắc đắt (mốc giây), đoạn hỏng (rung, tối, lặp), có lời thoại không và nói gì, khổ ngang hay dọc.
- Cần soi kỹ một khoảnh khắc: `--dense <bắt đầu> <kết thúc> --fps 6`.
- Viết `analysis/NOTES.md`: bảng `file · đoạn dùng được (từ–đến) · nội dung · điểm chất lượng 1–5 · vai trò gợi ý (mở đầu / cao trào / chuyển ý / kết)`.

## 3. Ý tưởng và kịch bản — `status: planning`

1. **Nạp phong cách**: đọc `styles/personal/STYLE.md` và `styles/personal/LESSONS.md` (bắt buộc theo), rồi `style.json` của mọi phong cách `approved`. Với mỗi phong cách xem `topics`, `best_for`, `avoid_for`, `techniques`.
2. **Chọn hướng kể**: một câu ý tưởng + cấu trúc (mở đầu gây chú ý trong 1–2 giây đầu → diễn biến → cao trào → kết có điểm rơi). Chủ đề mặc định là chuyện công sở hằng ngày, giọng vui nhộn.
3. **Chọn tiếng**:
   - Cảnh quay **có lời thoại rõ**: giữ lời gốc làm xương sống, phụ đề chạy theo từng từ (mốc từ trong `analysis/*.json`), nhạc nền nhỏ. Đề xuất thêm câu dẫn/chữ chêm gây cười nếu hợp.
   - Cảnh quay **không lời**: viết kịch bản dẫn chuyện vui nhộn rồi tạo giọng đọc AI (`tools/tts_vi.py`), hoặc chỉ nhạc + chữ trên màn hình nếu hình ảnh tự kể được. Nêu lý do chọn trong `PLAN.md`.
   - Nhạc: xem `library/music/` trước; không có thì theo `/media-use` (mục nhạc nền). Âm thanh hiệu ứng (whoosh, pop) lấy từ `/media-use`.
4. **Chọn kỹ thuật theo từng phân đoạn**: với mỗi phân đoạn, chọn kỹ thuật hợp nội dung của chính phân đoạn đó từ phong cách cá nhân → phong cách đã duyệt → registry HyperFrames (`/hyperframes-registry`) → `blocks/`. Chỉ áp trọn một phong cách khi chủ đề video trùng `topics` của nó. Carousel 3D (`blocks/carousel-3d`) hợp với đoạn điểm danh nhiều khoảnh khắc ngắn (ví dụ "một ngày của tôi"), không dùng cho đoạn cần xem kỹ một cảnh.
5. Viết **`PLAN.md`**:
   - Ý tưởng một câu, thời lượng mục tiêu (dọc 20–45 giây, ngang 30–90 giây trừ khi được yêu cầu khác), dòng LOOK (màu hex, font, cỡ chữ).
   - Bảng phân cảnh: `# · thời điểm · nguồn (file, từ–đến) · hình · chữ trên màn hình · lời/giọng đọc · chuyển cảnh · kỹ thuật (nguồn phong cách) · lý do`.
   - Kịch bản lời đầy đủ.
   - Mục "Lấy từ phong cách nào" và "Cố ý không dùng".
6. Ghi `styles_used` vào `project.json`. Không dừng chờ duyệt kế hoạch trừ khi người dùng yêu cầu duyệt kịch bản trước.

## 4. Dựng bản ngang — `status: editing`

1. Chuẩn bị nguồn bằng FFmpeg: cắt đúng đoạn dùng, chuẩn hoá về H.264 30fps, xoay đúng chiều, vào `edit/assets/`. Ví dụ:
   ```powershell
   ffmpeg -y -ss 12.4 -to 17.0 -i raw\a.mp4 -vf "fps=30,scale=1920:-2" -c:v libx264 -crf 18 -c:a aac edit\assets\s03.mp4
   ```
2. Khởi tạo: `npx --yes hyperframes init edit --skip-skills --skill=hyperframes --example blank --skip-transcribe` (trong `projects/<id>`), rồi theo đúng hợp đồng của `/hyperframes`: mỗi phân cảnh một file trong `compositions/`, root chỉ chứa host, media, audio.
3. Giọng đọc: viết `script.json` → `python tools\tts_vi.py --script ... --outdir edit\assets\vo`; dùng `*.words.json` để căn phụ đề theo từng từ (`references/captions.md` của `/hyperframes`).
4. Chữ tiếng Việt: dùng font có dấu đầy đủ (Montserrat, Be Vietnam Pro, Inter, Nunito, Oswald…). Font ngoài bộ có sẵn phải tải `.woff2` vào `assets/fonts/` và khai `@font-face`. Luôn chụp thử một khung có dấu (`ắ ở ữ ệ`) để kiểm tra.
5. `npx --yes hyperframes check` → sửa hết lỗi, cân nhắc cảnh báo.

## 5. Dựng bản dọc

```powershell
& tools\fork_vertical.ps1 "projects\<id>\edit"
```

Rồi **bố cục lại từng scene** trong `edit-vertical/` theo `references/types/vertical.md` của `/hyperframes`: một chủ thể ở giữa, xếp chồng dọc, chữ to hơn khoảng 1,35 lần, chữ quan trọng nằm trong dải 168–1330 px, cảnh ngang thì cắt cúp vào chủ thể hoặc đặt trên nền mờ; nhịp nhanh hơn bản ngang. Chạy `check` lại.

## 6. Xuất và tự kiểm — `status: rendering`

```powershell
npx --yes hyperframes render -q draft -o ..\out\<id>-16x9-v<N>.mp4      # trong edit
npx --yes hyperframes render -q draft -o ..\out\<id>-9x16-v<N>.mp4      # trong edit-vertical
python tools\analyze_video.py "projects\<id>\out" --out "projects\<id>\out\_check" --no-transcribe
```

Read các bảng khung hình trong `out/_check/` và soát: chữ có bị tràn, sai dấu, che mặt không; cảnh có đen hoặc đứng hình không; nhịp có đúng kế hoạch không. Sửa rồi render lại cho tới khi đạt.

## 7. Giao duyệt — `status: review`

Cập nhật `project.json`: `outputs` (cả hai khổ, kèm số phiên bản), `version`, và `message` gồm: ý tưởng đã chọn, kỹ thuật nổi bật và nguồn phong cách, những chỗ còn phân vân cần người dùng quyết định. Kết thúc lượt bằng tóm tắt ngắn cho người dùng.

## Sửa theo góp ý

Khi lời nhắc chứa góp ý cho một dự án đã có:

1. Chép nguyên văn góp ý vào `feedback.md` kèm số vòng và thời gian.
2. Sửa **đúng chỗ được góp ý** trong cả `edit/` và `edit-vertical/`; không đổi những chỗ không được nhắc.
3. Tăng `version`, render lại (`-vN`), tự kiểm, đặt `status: review`, ghi trong `message` đã sửa gì.
4. Khi người dùng chốt ("ok", "duyệt", "chốt"): render bản giao `-q delivery`, đặt `status: done`, rồi chạy `/kuto-remember`.
