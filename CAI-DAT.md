# HTML5 Ad Builder — hướng dẫn cài đặt

Tool tạo banner quảng cáo HTML5 hàng loạt để upload Google Ads.
Chạy hoàn toàn trên máy bạn, **không cần mạng**, nội dung không gửi đi đâu.

Trang tải: **https://github.com/dieuhoai/PDF-Image/releases**

---

## Windows

### Cài

1. Mở trang tải ở trên, tìm mục **Assets**, bấm **`HTML5AdBuilder-windows.zip`** để tải về.
2. Vào thư mục Downloads, chuột phải file zip → **Extract All…** → **Extract**.
   Nên giải nén vào chỗ cố định, ví dụ `C:\Tools\HTML5AdBuilder`, đừng để trong Downloads
   vì dễ bị dọn nhầm.
3. Mở thư mục vừa giải nén, nhấp đúp **`HTML5AdBuilder.exe`**.

### Lần đầu Windows sẽ cảnh báo

Hiện bảng xanh **"Windows protected your PC"** — vì file chưa mua chữ ký số (vài trăm đô một năm),
không phải vì có virus.

Bấm **More info** → hiện nút **Run anyway** → bấm vào đó. Chỉ phải làm một lần.

Nếu máy có phần mềm diệt virus riêng (Kaspersky, Bkav…) và nó chặn, thêm thư mục tool vào
danh sách loại trừ, hoặc hỏi bộ phận IT.

### Khi chạy

- Hiện một **cửa sổ đen** (Command Prompt) — đó là tool đang chạy, **đừng đóng**.
- Sau 2–5 giây trình duyệt tự mở. Nếu không, nhìn trong cửa sổ đen có dòng
  `http://127.0.0.1:8765/?t=...`, chép nguyên dòng đó dán vào trình duyệt.
- Windows có thể hỏi **"Allow access"** về tường lửa → bấm **Cancel** cũng được, tool vẫn chạy.
  Nó chỉ nói chuyện với chính máy bạn, không ra Internet.
- **Tắt tool**: đóng cửa sổ đen.

---

## macOS

### Cài

1. Mở trang tải, trong mục **Assets** bấm **`HTML5AdBuilder-macos.zip`**.
2. Nhấp đúp file zip trong Downloads để giải nén, kéo **`HTML5AdBuilder.app`** vào thư mục
   **Applications** (hoặc chỗ nào bạn thích).

### Lần đầu macOS sẽ chặn — làm đúng cách này

**Đừng nhấp đúp lần đầu.** macOS sẽ báo *"không mở được vì nhà phát triển không xác định"*
và chỉ cho nút OK, không có cách nào mở.

Làm thế này:

1. **Chuột phải** (hoặc giữ Control rồi bấm) vào `HTML5AdBuilder.app`
2. Chọn **Open** trong menu hiện ra
3. Hộp thoại lần này có nút **Open** → bấm vào

Từ lần sau nhấp đúp bình thường.

Nếu chuột phải → Open vẫn không được (macOS 15 trở lên đôi khi chặn chặt hơn):
mở **System Settings** → **Privacy & Security** → cuộn xuống gần cuối, thấy dòng
*"HTML5AdBuilder đã bị chặn"* → bấm **Open Anyway** → nhập mật khẩu máy.

### Khi chạy

- Hiện một **cửa sổ Terminal** — đó là tool đang chạy, **đừng đóng**.
- Trình duyệt tự mở sau vài giây. Nếu không, chép dòng `http://127.0.0.1:8765/?t=...`
  trong cửa sổ Terminal dán vào trình duyệt.
- **Tắt tool**: đóng cửa sổ Terminal, hoặc bấm Ctrl+C trong đó.

---

## Dùng thử ngay — 5 phút

1. **Bước 1 Nội dung**: gõ tiêu đề (tối đa 20 ký tự), mô tả, chọn một nút bấm mẫu,
   bấm **Thêm bộ nội dung**.
2. **Bước 2 Cấu hình**: tích vài kích thước, chọn bảng màu. Ảnh bên phải đổi ngay.
3. **Bước 3 Xem trước**: xem tất cả creative. Kéo chữ để đổi chỗ, bấm vào chữ rồi kéo tay nắm
   xanh để đổi bề rộng ô hoặc cỡ chữ. Lưu tự động.
4. **Bước 4 Xuất file**: bấm **Chọn…** chọn thư mục lưu, bấm **Xuất ngay**, xong bấm
   **Mở thư mục**.

Kết quả bạn nhận được trong thư mục `creatives_<ngày>/`:

| Thứ | Là gì |
|---|---|
| `html5/` | Mỗi creative một file `.zip` — đây là thứ upload lên Google Ads |
| `images/` | Ảnh PNG tĩnh (nếu bạn tích chọn) |
| `preview/index.html` | Mở bằng trình duyệt để xem cả lô một lượt |
| `manifest.json` | Danh sách mọi creative kèm thông tin |
| `report.csv` | Kết quả từng file, có cảnh báo nếu chữ bị tràn |

Và một file zip gộp cả thư mục, tiện gửi cho người khác.

---

## Hỏi đáp

**Có cần cài Python không?** Không. Bản tải từ Releases đã gói sẵn mọi thứ.

**Tool có gửi nội dung của tôi đi đâu không?** Không. Nó chạy hẳn trên máy bạn, không gọi mạng.
Bạn rút dây mạng vẫn dùng bình thường.

**Mở được trên máy không có quyền admin không?** Được, miễn là giải nén vào thư mục cá nhân
(Documents, Desktop) thay vì `Program Files`.

**Hai người mở cùng lúc trên một máy được không?** Được, tool tự đổi sang cổng khác.

**File tôi nhập có bị mất khi đóng tool không?** Nội dung đang gõ được nhớ tạm trong trình duyệt.
Muốn giữ lâu dài, dùng nút **Thư viện** ở Bước 1 để lưu lại có tên.

**Upload file nào lên Google Ads?** Các file `.zip` trong thư mục `html5/`, mỗi file một kích thước.
Đừng upload file zip gộp cả thư mục.

---

## Khi gặp trục trặc

| Hiện tượng | Cách xử lý |
|---|---|
| Nhấp đúp không thấy gì | Chờ 10 giây, trình duyệt mở hơi chậm lần đầu. Vẫn không thì xem cửa sổ đen/Terminal có báo lỗi gì không, chụp màn hình gửi người đưa bạn tool này. |
| Trình duyệt báo *"Phiên đã hết hạn"* | Bạn mở lại tab cũ sau khi tool đã tắt. Đóng tab, mở lại tool từ đầu. |
| *"Mất kết nối với tool"* | Cửa sổ đen/Terminal đã bị đóng. Mở lại tool rồi tải lại trang. |
| Chữ Thái, Ả Rập, Hindi trong ảnh PNG bị sai dấu | Đây là hạn chế đã biết của phần vẽ ảnh. **Bản HTML5 vẫn đúng** — dùng bản HTML5 để chạy quảng cáo. |
| Chữ trong banner hơi khác lúc xem trước | Bản HTML5 dùng font có sẵn trên máy người xem nên lệch vài pixel. Tool đã chừa sẵn 8% biên an toàn. |
| Kích thước nhỏ như 320×50 bố cục khác ảnh mẫu | Cố ý. Khung quá chật thì tool dùng bố cục tự động thay vì ép theo ảnh mẫu rồi chữ chồng lên nhau. |

---

## Cách khác: chạy từ mã nguồn

Dành cho người đã có Python 3.10 trở lên, hoặc khi chưa có bản đóng gói cho hệ điều hành của bạn.

1. Trên trang GitHub bấm **Code → Download ZIP**, giải nén.
2. Mở Terminal (macOS) hoặc Command Prompt (Windows), chuyển vào thư mục vừa giải nén, chạy:

```
python3 scripts/setup_env.py --ui
```

3. Lần sau mỗi khi muốn mở tool:

```
.venv/bin/python -m web.server
```

(Windows thay bằng `.venv\Scripts\python -m web.server`)
