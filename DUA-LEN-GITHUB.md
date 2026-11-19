# Đưa tool lên GitHub để gửi cho người khác

GitHub sẽ **tự đóng gói hộ** cả bản Windows (`.exe`) lẫn bản macOS (`.app`) — máy bạn không cần
Xcode. Đồng nghiệp chỉ vào trang Releases, tải về, giải nén, nhấp đúp là chạy.

Không cần cài gì trên máy. Làm trên trình duyệt, khoảng 10 phút.

---

## Bước 1 — Tạo kho

1. Vào <https://github.com/new> (đăng nhập tài khoản GitHub của bạn).
2. **Repository name**: `html5-ad-builder`
3. Chọn **Public**.
4. **Không** tích thêm README, .gitignore hay license nào cả.
5. Bấm **Create repository**.

## Bước 2 — Kéo thả toàn bộ file

1. Ở trang vừa hiện, bấm dòng chữ **uploading an existing file**.
2. Mở Finder tới thư mục **`~/LutechTools/_upload/html5-ad-builder`**
   (mình đã mở sẵn cửa sổ Finder này cho bạn).
3. Bấm Cmd+A chọn tất cả, rồi kéo thả vào khung trên trình duyệt. Chờ 98 file tải xong.
4. Bấm **Commit changes**.

## Bước 3 — Kiểm thư mục `.github` (quan trọng)

Trình duyệt hay bỏ qua thư mục bắt đầu bằng dấu chấm. Nhìn danh sách file trên GitHub:

- **Thấy thư mục `.github`** → sang Bước 4 luôn.
- **Không thấy** → làm thêm:
  1. Bấm **Add file → Create new file**.
  2. Ô tên file gõ đúng: `.github/workflows/release.yml`
  3. Mở file **`~/LutechTools/release.yml-chep-vao-github.txt`** (nhấp đúp, nó mở bằng TextEdit),
     chọn tất cả, chép, rồi dán vào khung soạn thảo trên GitHub.
  4. Bấm **Commit changes**.

Thiếu file này thì GitHub không build hộ, Bước 4 sẽ không ra gì.

## Bước 4 — Tạo bản phát hành để GitHub build

1. Ở trang kho, cột bên phải bấm **Releases** → **Create a new release**.
2. Ô *Choose a tag*: gõ **`v0.1.0`** rồi bấm **Create new tag on publish**.
   Phải đúng `v0.1.0` — lệch một chữ là GitHub báo lỗi và dừng.
3. *Release title*: `HTML5 Ad Builder 0.1.0`
4. Bấm **Publish release**.
5. Sang tab **Actions** xem tiến độ. Khoảng 5–10 phút, hai dấu tích xanh là xong.

## Bước 5 — Gửi cho đồng nghiệp

Quay lại **Releases**, bạn sẽ thấy hai file đính kèm:

- `HTML5AdBuilder-windows.zip`
- `HTML5AdBuilder-macos.zip`

Copy link trang Releases gửi cho họ. Kho để Public nên họ tải được mà không cần tài khoản GitHub.

Dặn người dùng macOS: lần đầu máy sẽ chặn vì app chưa ký số — chuột phải vào app →
**Open** → **Open**. Từ lần sau nhấp đúp bình thường.

---

## Lần sau ra bản mới

1. Sửa dòng `version = "0.1.0"` trong `pyproject.toml` thành số mới, ví dụ `0.2.0`.
2. Trên GitHub bấm **Add file → Upload files**, kéo thả các file đã đổi vào, **Commit**.
3. Tạo release mới với tag `v0.2.0`.

## Nếu tab Actions báo dấu X đỏ

Bấm vào lần chạy hỏng, xem bước nào có dấu X. Hai lỗi hay gặp:

| Dòng báo lỗi | Cách sửa |
|---|---|
| `Tag v0.x.y ≠ version v0.1.0` | Tag không khớp `pyproject.toml`. Xoá release rồi tạo lại đúng tag. |
| Không có lần chạy nào | Thiếu `.github/workflows/release.yml` — xem lại Bước 3. |

Chụp màn hình gửi mình, mình đọc giúp.
