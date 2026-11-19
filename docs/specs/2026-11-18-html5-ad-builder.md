# Spec: HTML5 Ad Builder — tạo banner HTML5 hàng loạt cho Google Ads

- Ngày: 2026-11-18 · Trạng thái: Đã duyệt · Người duyệt: người yêu cầu (qua phiếu tool)

## 1. Bối cảnh & vấn đề
Team UA tự làm banner display cho Google Ads: mỗi bộ nội dung (headline/description/CTA) phải dựng thủ công
cho ~20 kích thước, nhiều ngôn ngữ, rồi nén ZIP đúng chuẩn HTML5 của Google. Lặp lại, dễ sai kích thước/dung lượng.

## 2. Người dùng mục tiêu
Nhân viên UA/marketing không biết code, Windows hoặc macOS. Điển hình 1–10 bộ nội dung × 5–25 size.

## 3. Luồng chính
1. **Nội dung**: thêm bộ (Headline ≤ 20 ký tự, Description ≤ 100, CTA có sẵn hoặc tự nhập, ngôn ngữ).
   Nhập nhiều bộ từ CSV. Tuỳ chọn thả ảnh tham chiếu → gợi ý bảng màu theo màu chủ đạo.
2. **Cấu hình**: chọn size (lọc Display/Mobile/Khác, tự nhập), bảng màu (chọn nhiều), gradient, animation,
   badge (chọn nhiều hoặc không), bố cục (Tự động/Giữa/Trái/Trên-Dưới), cách gom file (Bộ/Size/Phẳng).
   Live preview + tổng số creative = bộ × size × bảng màu × max(1, số badge).
3. **Preview**: xem từng size, kéo thả headline/description/CTA/badge; lưu vị trí cho creative này hoặc cả size.
4. **Xuất**: chọn thư mục → `creatives_<YYYY-MM-DD>/` + file `.zip` cùng tên.

## 4. Yêu cầu chức năng
| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| F1 | Bộ nội dung + kiểm độ dài + CSV import | P0 |
| F2 | Kiểm CTA chứa từ cấm; danh sách từ cấm sửa được trong tool, lưu ở máy | P0 |
| F3 | Danh mục size Google Ads + size tự nhập | P0 |
| F4 | 6 bảng màu, 4 gradient, 3 animation + không, 5 badge, 4 bố cục | P0 |
| F5 | Tự co cỡ chữ cho vừa size; báo size nào chữ vẫn tràn | P0 |
| F6 | Xuất ZIP HTML5 đúng chuẩn: `index.html` có `<meta name="ad.size">`, biến `clickTag`, không tài nguyên ngoài, ≤ 150 KB | P0 |
| F7 | manifest.json, preview/index.html dạng lưới, tuỳ chọn PNG tĩnh | P1 |
| F8 | Kéo thả vị trí, lưu theo creative hoặc theo size | P1 |
| F9 | Ảnh tham chiếu → gợi ý bảng màu gần nhất (offline) | P2 |

## 5. Yêu cầu phi chức năng
Offline hoàn toàn. 3 bộ × 20 size xuất < 30 s. Windows + macOS. Giao diện vi/en, sáng/tối, 375–1440 px.

## 6. Tiêu chí chấp nhận
- [ ] AC1: Cho headline 21 ký tự, khi tạo bộ, thì bị từ chối với thông báo tiếng Việt.
- [ ] AC2: Cho CTA "Download now", khi kiểm, thì báo chứa từ cấm "download"; "Learn more" thì hợp lệ.
- [ ] AC3: Cho 3 bộ × 20 size × 1 màu × 1 badge, khi tính, thì tổng = 60.
- [ ] AC4: Cho 1 creative 300×250, khi xuất, thì ZIP có `index.html` chứa `ad.size` width=300,height=250 và `clickTag`, không có URL http(s) ngoài trừ clickTag mặc định, dung lượng ≤ 150 KB.
- [ ] AC5: Cho headline dài ở size 320×50, khi bố cục, thì cỡ chữ giảm; nếu không vừa ở cỡ tối thiểu thì có cảnh báo tràn cho size đó.
- [ ] AC6: Cho group_by = set/size/flat, khi xuất, thì cấu trúc thư mục đúng tương ứng.
- [ ] AC7: Cho manifest bật, thì `manifest.json` liệt kê đủ mọi file với set, size, scheme, badge, bytes.
- [ ] AC8: Cho preview bật, thì `preview/index.html` có một ô cho mỗi creative.
- [ ] AC9: Cho PNG bật, thì mỗi creative có thêm PNG đúng kích thước pixel.
- [ ] AC10: Cho vị trí ghi đè theo size, thì mọi creative cùng size dùng vị trí đó; ghi đè theo creative thắng ghi đè theo size.
- [ ] AC11: Cho CSV có cột headline,description,cta,lang (UTF-8, có BOM hoặc không), khi nhập, thì ra đủ bộ; dòng lỗi được liệt kê, không dừng.
- [ ] AC12: Cho ảnh nền xanh dương, khi gợi ý, thì đề xuất "Blue Trust".
- [ ] AC13: Cho lỗi ở 1 creative, khi xuất, thì các creative khác vẫn ra và lỗi nằm trong báo cáo.
- [ ] AC14: Bấm Dừng giữa chừng thì dừng sau creative đang làm.

## 7. Edge case
Tên bộ có dấu/emoji/Hàn → tên file ASCII an toàn, không trùng. Ký tự HTML (`<`, `&`, `"`) trong nội dung được escape.
Thư mục xuất trùng tên → thêm hậu tố `-2`. Chữ Hàn/Nhật/Trung/Thái xuống dòng theo ký tự. Tiếng Ả Rập hiển thị phải-sang-trái.

## 8. Kiến trúc
Lõi `html5adbuilder/`: `catalog.py` (danh mục), `models.py`, `fonts.py` (đo chữ bằng Pillow), `layout.py`
(tính hộp + cỡ chữ — một nguồn sự thật cho HTML và PNG), `render_html.py`, `render_png.py`, `cta.py`, `palette.py`,
`csv_import.py`, `exporter.py`. Web: `web/api/{catalog,project,jobs}.py`. Preview trong UI dùng Shadow DOM để kéo thả.
UI thiết kế theo nguyên tắc ui-ux-pro-max (đã có token trong template).

## 9. Ngoài phạm vi
Upload lên Google Ads, dịch tự động, gợi ý font/bố cục bằng AI, thư viện nội dung dùng chung nhiều máy.

## 10. Câu hỏi mở
(không)
