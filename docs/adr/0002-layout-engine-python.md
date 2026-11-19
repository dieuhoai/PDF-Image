# ADR 0002: Tính bố cục banner bằng Python (một nguồn cho HTML và PNG)

- Trạng thái: Chấp nhận · 2026-11-18

## Bối cảnh
Cần xuất cùng một creative ra HTML5 và PNG, và cảnh báo khi chữ tràn. Dùng trình duyệt để chụp PNG thì phải
đóng gói Chromium (~150 MB).

## Quyết định
`layout.py` tự xuống dòng và co cỡ chữ bằng số đo của Pillow, trả về hộp tuyệt đối. HTML in từng dòng sẵn
(`white-space: nowrap`), PNG vẽ đúng các hộp đó. Font HTML là font hệ thống phổ biến (Arial…) để file nhẹ.

## Hệ quả
+ PNG không cần trình duyệt, exe nhẹ; cảnh báo tràn chính xác ở mức đủ dùng.
− Máy xem dùng font khác Arial có thể lệch vài px; bù bằng biên an toàn 8 %.
