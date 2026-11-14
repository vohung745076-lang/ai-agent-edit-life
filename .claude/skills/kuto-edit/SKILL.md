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

## 3. Creative Director — chọn phong cách và cấu trúc — `status: planning`

Giao cho agent **`kuto-creative-director`** (công cụ Agent, `subagent_type: "kuto-creative-director"`), lời nhắc gồm: thư mục `projects/<id>`, yêu cầu của người dùng, thời lượng mong muốn nếu có. Agent đó đọc ghi chú cảnh quay, nạp `styles/personal` (luật), tra kho bằng `tools/style_kb.py` (`index`, `match`, `show`), rồi ghi:

- `projects/<id>/direction.json`: ý tưởng, kế hoạch tiếng, phong cách nào áp dụng ở mức nào (`nền` / `toàn bộ` / `từng kỹ thuật` / `không dùng`) kèm lý do, **cấu trúc timeline** theo vai trò (`hook → setup → main → climax → cta/outro`) với cảnh quay và kỹ thuật cho từng phân đoạn, các quy tắc dựng phải tuân theo, những gì đã loại.
- `projects/<id>/DIRECTION.md`: bản cho người đọc.

Nếu phiên này không có agent đó: tự làm đúng theo `.claude/agents/kuto-creative-director.md`.

Kiểm lại quyết định trước khi dựng:

- Chỉ có phong cách `approved` / `personal`. Phong cách được áp `toàn bộ` phải cùng chủ đề với video; nếu không thì hạ xuống `từng kỹ thuật`.
- Mỗi kỹ thuật có lý do gắn với nội dung của chính phân đoạn đó. Không trái `styles/personal/LESSONS.md`.
- Cảnh quay được gán có thật trong `analysis/NOTES.md`.

## 3b. Timeline & Editing — kịch bản chi tiết

Từ đây bạn là **Timeline & Editing Agent**: biến chỉ đạo thành timeline cụ thể rồi dựng.

1. **Tiếng** (theo `audio_plan` của chỉ đạo):
   - Cảnh quay **có lời thoại rõ**: giữ lời gốc làm xương sống, phụ đề chạy theo từng từ (mốc từ trong `analysis/*.json`), nhạc nền nhỏ. Thêm câu dẫn/chữ chêm gây cười nếu hợp.
   - Cảnh quay **không lời**: viết kịch bản dẫn chuyện vui nhộn về đời sống công sở rồi tạo giọng đọc AI (`tools/tts_vi.py`), hoặc nhạc + chữ nếu hình ảnh tự kể được.
   - Nhạc: xem `library/music/` trước; không có thì theo `/media-use` (mục nhạc nền). Âm thanh hiệu ứng (whoosh, pop) lấy từ `/media-use`. Phong cách được chọn có quy tắc "cắt theo beat" thì đo beat của bản nhạc (`npx --yes hyperframes beats`) và đặt điểm cắt lên lưới beat.
2. **Kỹ thuật**: lấy file từ `styles/<slug>/techniques/` của phong cách được chỉ định, rồi `styles/personal/techniques/`, `/hyperframes-registry`, `blocks/`. Chỉnh thông số theo `analysis.*.rules` của phong cách đó (`python tools\style_kb.py show <slug>`). Carousel 3D (`blocks/carousel-3d`) hợp với đoạn điểm danh nhiều khoảnh khắc ngắn, không dùng cho đoạn cần xem kỹ một cảnh.
3. Viết **`PLAN.md`** (timeline dựng):
   - Ý tưởng một câu, thời lượng mục tiêu (dọc 20–45 giây, ngang 30–90 giây trừ khi được yêu cầu khác), dòng LOOK (màu hex, font, cỡ chữ).
   - Bảng phân cảnh theo đúng cấu trúc của chỉ đạo: `# · vai trò (hook/main/…) · thời điểm · nguồn (file, từ–đến) · hình · chữ trên màn hình · lời/giọng đọc · chuyển cảnh · kỹ thuật (nguồn phong cách) · lý do`.
   - Kịch bản lời đầy đủ.
   - Mục "Lấy từ phong cách nào" và "Cố ý không dùng" (chép từ chỉ đạo, bổ sung nếu có thay đổi khi dựng).
4. Ghi `styles_used` vào `project.json` (mảng JSON thật). Không dừng chờ duyệt kế hoạch trừ khi người dùng yêu cầu duyệt kịch bản trước.

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

Đối chiếu với chỉ đạo bằng số: `python tools\analyze_style.py "projects\<id>\out\<bản 16x9>.mp4" --out "projects\<id>\out\_check"` rồi so nhịp cắt, kiểu chuyển cảnh, tông màu với quy tắc của phong cách đã chọn (`rules_in_force` trong `direction.json`). Lệch rõ thì sửa.

## 7. Giao duyệt — `status: review`

Cập nhật `project.json`: `outputs` (cả hai khổ, kèm số phiên bản), `version`, và `message` gồm: ý tưởng đã chọn, kỹ thuật nổi bật và nguồn phong cách, những chỗ còn phân vân cần người dùng quyết định. Kết thúc lượt bằng tóm tắt ngắn cho người dùng.

## Sửa theo góp ý

Khi lời nhắc chứa góp ý cho một dự án đã có:

1. Chép nguyên văn góp ý vào `feedback.md` kèm số vòng và thời gian.
2. Sửa **đúng chỗ được góp ý** trong cả `edit/` và `edit-vertical/`; không đổi những chỗ không được nhắc.
3. Tăng `version`, render lại (`-vN`), tự kiểm, đặt `status: review`, ghi trong `message` đã sửa gì.
4. Khi người dùng chốt ("ok", "duyệt", "chốt"): render bản giao `-q delivery`, đặt `status: done`, rồi chạy `/kuto-remember`.
