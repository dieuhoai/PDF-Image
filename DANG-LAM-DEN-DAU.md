# HTML5 Ad Builder — tình trạng (19/11/2026)

Tool tạo banner quảng cáo HTML5 hàng loạt cho Google Ads. Hướng dẫn dùng: [HUONG-DAN.md](HUONG-DAN.md).

## Đã xong

Đủ 4 bước và chạy được. **129 bài kiểm tra tự động đều đạt** (gồm 16 bài chạy thật trên trình duyệt).

- Nội dung: nhiều bộ, nhập CSV, cảnh báo từ cấm trong nút bấm, nút bấm mẫu dịch theo 15 ngôn ngữ,
  thư viện lưu lại dùng sau.
- Ảnh tham chiếu: đọc chỗ đặt chữ, cỡ chữ, màu từ ảnh mẫu rồi áp cho mọi kích thước.
- Cấu hình: 22 kích thước + tự nhập, 6 bảng màu, 4 gradient, 4 hiệu ứng, 5 nhãn góc,
  nút kiểu chữ hoặc nút bo tròn, màu nút tự chọn, nút nhấp nháy,
  hai kiểu quảng cáo (banner thường / toàn màn hình có ExitApi).
- Xem trước: hiện mọi creative, kéo thả và đổi cỡ chữ ngay trên từng ô, lưu tức thì,
  bỏ bớt creative không muốn xuất.
- Xuất: file HTML5 .zip đúng chuẩn (≤ 150 KB) và/hoặc ảnh PNG nét tới 4×,
  tách thư mục `html5/` và `images/`, kèm manifest, báo cáo và trang xem cả lô.

## Chưa xong — vì máy thiếu Xcode Command Line Tools

Máy đang chạy macOS 26.0.1 và **chưa có Xcode Command Line Tools**. Thiếu nó thì:

1. **Không đóng gói được `.app`** — PyInstaller cần `lipo` và `install_name_tool`.
   (`lipo` đã có bản thay thế viết bằng Python trong `build/tools/lipo`, nhưng `install_name_tool`
   thì không thay được an toàn: nó sửa cấu trúc bên trong file thực thi.)
2. **Không dùng được Git** — `git` trên máy chỉ là vỏ rỗng trỏ tới bộ công cụ chưa cài.
3. **Không đưa lên GitHub được** — hệ quả của mục 2.

`xcode-select --install` báo *"phần mềm hiện không khả dụng từ máy chủ Cập nhật phần mềm"* —
lỗi phía Apple, hay gặp với bản macOS mới. Hai cách khác:

- Tải thẳng **Command Line Tools for Xcode** tại <https://developer.apple.com/download/all/>
  (đăng nhập Apple ID miễn phí), mở file .dmg rồi cài. Khoảng 1 GB.
- Hoặc cài **Xcode** từ App Store (~17 GB, có sẵn Command Line Tools bên trong).

Cài xong chỉ cần chạy `python3 scripts/build_exe.py`, phần còn lại đã sẵn sàng.

## Dùng tool ngay bây giờ

Nhấp đúp `Mở HTML5 Ad Builder.command`. Tool chạy đầy đủ, không thiếu tính năng nào —
chỉ là chưa gói thành một file gửi cho người chưa cài Python.

Bản `.exe` cho Windows phải build trên máy Windows (`python scripts/build_exe.py`), không build
từ máy Mac được.
