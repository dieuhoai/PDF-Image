# Plan: HTML5 Ad Builder

Spec: docs/specs/2026-11-18-html5-ad-builder.md

| # | Task | File | Test viết trước | AC |
|---|------|------|-----------------|----|
| 1 | Danh mục + model + kiểm CTA | catalog.py, models.py, cta.py | tests/unit/test_models.py | AC1–3 |
| 2 | Đo chữ + bố cục + vị trí ghi đè | fonts.py, layout.py | tests/unit/test_layout.py | AC5, AC10 |
| 3 | Render HTML5 + PNG | render_html.py, render_png.py | tests/unit/test_render.py | AC4, AC9 |
| 4 | CSV + gợi ý màu | csv_import.py, palette.py | tests/unit/test_inputs.py | AC11, AC12 |
| 5 | Xuất hàng loạt + CLI | exporter.py, __main__.py | tests/unit/test_exporter.py, test_cli.py | AC6–8, AC13–14 |
| 6 | API web | web/api/*.py, server.py | tests/web/test_api.py | toàn bộ qua HTTP |
| 7 | Giao diện 4 bước | web/static/* | tests/ui/test_ui_smoke.py | luồng chính |
| 8 | Đóng gói + hướng dẫn | build/app.spec, docs/HUONG-DAN-UA.md, README | build thử | — |

Rủi ro: font khác nhau giữa Windows/macOS (bù biên an toàn); chữ phải-sang-trái; dung lượng ZIP (không nhúng font).
