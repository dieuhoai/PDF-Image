#!/bin/bash
# Nhấp đúp file này để mở tool. Đóng cửa sổ Terminal là tool tắt.
cd "$(dirname "$0")" || exit 1

if [ ! -x .venv/bin/python ]; then
  echo "Chưa có môi trường. Mở Terminal, gõ: python3 scripts/setup_env.py --ui"
  read -r -p "Nhấn Enter để đóng..."
  exit 1
fi

echo "Đang mở HTML5 Ad Builder... Trình duyệt sẽ tự bật sau vài giây."
echo "Đóng cửa sổ này để tắt tool."
exec .venv/bin/python -m web.server
