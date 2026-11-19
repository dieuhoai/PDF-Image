# HTML5 Ad Builder — hướng dẫn dùng

Tool tạo banner quảng cáo HTML5 hàng loạt để upload Google Ads. Chạy trên máy bạn, **không cần mạng**,
không gửi nội dung đi đâu cả.

## Mở tool

Nhấp đúp **`Mở HTML5 Ad Builder.command`** trong thư mục tool. Trình duyệt tự bật sau vài giây.
Đóng cửa sổ Terminal là tool tắt.

**Lần đầu trên macOS**, máy có thể chặn vì file chưa ký số: chuột phải vào file → *Open* → *Open*.

> Bản đóng gói thành `.app` / `.exe` (gửi được cho người chưa cài gì) cần Xcode Command Line Tools.
> Cài bằng cách mở Terminal gõ `xcode-select --install`, rồi chạy `python3 scripts/build_exe.py`.

## Bốn bước

### 1. Nội dung

Mỗi "bộ nội dung" là một thông điệp quảng cáo: tiêu đề (tối đa 20 ký tự), mô tả (tối đa 100),
nút bấm, ngôn ngữ. Thêm bao nhiêu bộ cũng được.

- **Nút bấm**: chọn mẫu có sẵn hoặc tự gõ. Tool cảnh báo nếu chữ dễ bị Google Ads từ chối
  (ví dụ "tải xuống", "click here"). Danh sách từ cấm sửa được.
- **Đổi ngôn ngữ** thì nút bấm mẫu tự dịch theo. Chữ bạn tự gõ thì giữ nguyên.
- **Nhập từ CSV**: file cần các cột `headline`, `description`, `cta`, `lang`. Xuất từ Excel hay
  Google Sheets đều được. Dòng nào lỗi sẽ được liệt kê, không làm hỏng cả file.
- **Thư viện**: lưu lại cả bộ nội dung + cấu hình để lần sau mở ra dùng tiếp.
- **Ảnh tham chiếu**: kéo thả một ảnh quảng cáo mẫu vào. Tool đọc **chỗ đặt chữ, cỡ chữ và màu**
  rồi áp cho mọi kích thước, đỡ phải kéo tay từng cái. Tool **không đọc được chữ hay font** trong ảnh.

### 2. Cấu hình

Chọn kích thước (22 khổ chuẩn Google Ads, hoặc tự nhập), bảng màu, nền chuyển màu, hiệu ứng,
nhãn góc, cách xếp chữ, kiểu và màu nút bấm. Ảnh bên phải đổi theo ngay mỗi lần bấm.

**Kiểu quảng cáo**:

| Kiểu | Dùng khi nào |
|---|---|
| Banner thường | Quảng cáo hiển thị Google Ads. File .zip tự chạy, không gọi gì từ mạng. |
| Toàn màn hình | Quảng cáo xen kẽ trên điện thoại. Tự co vừa màn hình, bấm đâu cũng mở link qua ExitApi của Google. |

### 3. Xem trước

Hiện **tất cả** creative sẽ xuất. Trên từng ô:

- Kéo chữ để đổi chỗ. Bấm vào chữ rồi kéo tay nắm xanh: **cạnh phải** đổi bề rộng ô chữ,
  **góc dưới** đổi cỡ chữ. Phím mũi tên nhích từng pixel, phím `+` `−` đổi cỡ chữ.
- Mọi thay đổi **lưu ngay**, không cần bấm nút nào. Ô đã chỉnh có nhãn "đã chỉnh".
- Bỏ tích ở ô nào thì creative đó không được xuất.

### 4. Xuất file

Chọn định dạng (**File HTML5 .zip** để upload Google Ads, và/hoặc **ảnh PNG** — chọn độ nét 2× trở lên),
thư mục lưu, link đích, rồi bấm **Xuất ngay**.

Kết quả trong `creatives_<ngày>/`:

```
html5/    mỗi creative một file .zip đúng chuẩn Google Ads (≤ 150 KB)
images/   ảnh PNG tĩnh (nếu có chọn)
manifest.json   danh sách mọi creative kèm thông tin
report.csv      kết quả từng file, cảnh báo nếu có
preview/index.html   mở bằng trình duyệt để xem cả lô
```

Kèm một file zip gộp cả thư mục để gửi cho người khác.

## Những điều nên biết

- **Chữ Thái, Ả Rập, Hindi**: ảnh PNG có thể đặt sai dấu (thư viện vẽ ảnh thiếu phần xếp chữ phức tạp).
  Bản HTML5 vẫn đúng. Tool sẽ cảnh báo khi gặp.
- **Font**: bản HTML5 dùng font có sẵn trên máy người xem, nên có thể lệch vài pixel so với bản xem trước.
  Tool đã chừa 8 % biên an toàn.
- **Khổ quá nhỏ**: nếu chép bố cục từ ảnh mẫu mà khung quá chật, tool dùng bố cục tự động của nó
  thay vì ép theo ảnh rồi chữ chồng lên nhau.

Cần thêm hay sửa gì, mở Claude Code trong thư mục tool và gõ `/lutech-tools:fix-tool <mô tả bằng lời thường>`.
