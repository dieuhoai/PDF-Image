# HTML5 Ad Builder

Tạo banner quảng cáo HTML5 hàng loạt để upload Google Ads. Chạy ngay trên máy, không cần mạng,
nội dung không gửi đi đâu cả.

Nhập một bộ nội dung → chọn kích thước và màu → xem trước cả lô và kéo chỉnh từng cái →
xuất ra file `.zip` đúng chuẩn Google Ads (kèm ảnh PNG nếu muốn).

**Người dùng cuối đọc [HUONG-DAN.md](HUONG-DAN.md).**

## Tải bản chạy được

Vào mục **Releases** của kho này, tải `HTML5AdBuilder-windows.zip` hoặc `HTML5AdBuilder-macos.zip`,
giải nén rồi nhấp đúp. Không cần cài Python.

macOS báo "nhà phát triển không xác định": chuột phải vào app → **Open** → **Open**.

## Làm được gì

- **Nội dung**: nhiều bộ cùng lúc, 15 ngôn ngữ, nhập hàng loạt từ CSV, cảnh báo chữ dễ bị Google Ads
  từ chối trong nút bấm, thư viện lưu lại dùng sau.
- **Ảnh tham chiếu**: thả một ảnh quảng cáo mẫu vào, tool đọc chỗ đặt chữ, cỡ chữ và màu rồi áp cho
  mọi kích thước — đỡ phải kéo tay từng cái.
- **Thiết kế**: 22 kích thước chuẩn + tự nhập, 6 bảng màu, 4 nền chuyển màu, 4 hiệu ứng, 5 nhãn góc,
  nút kiểu chữ hoặc nút bo tròn, màu nút tự chọn, nút nhấp nháy.
- **Hai kiểu quảng cáo**: banner thường (ZIP tự chạy, không gọi gì từ mạng) và toàn màn hình
  (tự co vừa màn hình điện thoại, mở link qua ExitApi của Google).
- **Xem trước cả lô**: kéo thả chữ và đổi cỡ ngay trên từng creative, lưu tức thì, bỏ bớt cái không cần.
- **Xuất**: mỗi creative một `.zip` ≤ 150 KB có `ad.size` và `clickTag`, kèm `manifest.json`,
  `report.csv` và trang xem cả lô. Ảnh PNG nét tới 4×.

## Chạy khi phát triển

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q                      # toàn bộ test
.venv/bin/python -m pytest -q -m "not ui"          # bỏ test trình duyệt (nhanh)
.venv/bin/ruff check .
.venv/bin/python -m web.server                     # mở giao diện
```

Dòng lệnh, khi muốn chạy tự động:

```bash
.venv/bin/python -m html5adbuilder export noi-dung.csv ket-qua/ --sizes all --badge new --png
```

## Cấu trúc

```
html5adbuilder/      lõi nghiệp vụ — thuần Python, không biết gì về web
  catalog.py     danh mục kích thước, bảng màu, nhãn, ngôn ngữ, nút bấm mẫu
  models.py      pydantic model, validate mọi input
  fonts.py       đo chữ, chọn font đậm theo từng bảng chữ
  layout.py      tính chỗ đặt và cỡ chữ — một nguồn duy nhất cho cả HTML lẫn PNG
  analyze.py     dò bố cục từ ảnh tham chiếu
  recipe.py      quy bố cục đó ra vị trí, cỡ chữ, bề rộng cho từng kích thước
  render_html.py sinh file HTML5 đúng chuẩn Google Ads
  render_png.py  vẽ ảnh PNG từ đúng bố cục đó
  exporter.py    xuất hàng loạt, manifest, báo cáo, trang xem cả lô
  csv_import.py  nhập nội dung từ CSV
  palette.py     gợi ý bảng màu và màu nhấn từ ảnh
  cta.py         kiểm nút bấm chứa từ cấm
  __main__.py    CLI
web/                 FastAPI server local + API + giao diện (Alpine.js, không CDN)
tests/               129 bài: unit / web (API) / ui (Playwright)
build/               PyInstaller spec + launcher + bản thay thế lipo cho máy thiếu Xcode
scripts/             setup_env, build_exe, bump_version, check_privacy
docs/                spec, plan, các quyết định kiến trúc (ADR)
.github/             CI test, build release theo tag
```

### Vài quyết định đáng nhớ

- **Một nguồn bố cục duy nhất.** `layout.py` tính sẵn chỗ đặt và cỡ chữ; bản HTML và bản PNG đều vẽ
  theo đúng số đó nên không bao giờ lệch nhau ([ADR 0002](docs/adr/0002-layout-engine-python.md)).
- **Chép bố cục từ ảnh mẫu không cần AI.** `analyze.py` dò các mảng chữ trong ảnh, `recipe.py` quy ra
  tỉ lệ rồi áp cho từng khung — có đo chữ thật nên không để các khối đè lên nhau; khung nào chật quá
  thì quay về bố cục tự động thay vì ép cho bằng được.
- **Font đậm chọn theo bảng chữ.** Mỗi font chỉ phủ vài bảng chữ (Arial Bold không có tiếng Hàn,
  font Hàn lại thiếu dấu tiếng Việt), nên `fonts.py` thử vẽ từng chữ đại diện rồi mới chọn.

## Phát hành

Đẩy tag `vX.Y.Z` khớp với version trong `pyproject.toml`; GitHub Actions tự build Windows + macOS
và đính kèm vào Releases. Xem [docs/RELEASE.md](docs/RELEASE.md).

## Giấy phép

MIT — xem [LICENSE](LICENSE).
