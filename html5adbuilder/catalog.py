"""Danh mục cố định: kích thước, bảng màu, gradient, badge, ngôn ngữ, CTA gợi ý.

Mọi màu đã chọn để chữ trên nền đạt tương phản ≥ 4.5:1.
"""
from __future__ import annotations

# Kích thước HTML5 Google Ads hỗ trợ. group dùng cho bộ lọc trong UI.
_DISPLAY = ["300x250", "336x280", "728x90", "300x600", "160x600", "120x600", "970x90", "970x250", "468x60",
            "250x250", "200x200", "300x1050"]
_MOBILE = ["320x50", "320x100", "300x50", "320x480", "480x320"]
_OTHER = ["930x180", "980x120", "580x400", "250x360", "240x400"]
SIZES: list[dict] = [
    {"key": k, "w": int(k.split("x")[0]), "h": int(k.split("x")[1]), "group": g}
    for g, keys in (("display", _DISPLAY), ("mobile", _MOBILE), ("other", _OTHER))
    for k in keys
]

SCHEMES: dict[str, dict] = {
    "clean_white": {"name": "Clean White", "bg": "#ffffff", "text": "#1a1a1a", "sub": "#5f6368",
                    "cta_bg": "#1a73e8", "cta_text": "#ffffff", "border": "#e0e0e0"},
    "soft_gray": {"name": "Soft Gray", "bg": "#f5f5f5", "text": "#202124", "sub": "#5f6368",
                  "cta_bg": "#1557b0", "cta_text": "#ffffff", "border": "#e0e0e0"},
    "dark": {"name": "Dark Mode", "bg": "#1a1a2e", "text": "#ffffff", "sub": "#c9c9d9",
             "cta_bg": "#f9ab00", "cta_text": "#1a1a1a", "border": "#1a1a2e"},
    "warm_cream": {"name": "Warm Cream", "bg": "#fff8f0", "text": "#3e2723", "sub": "#6d4c41",
                   "cta_bg": "#c62f17", "cta_text": "#ffffff", "border": "#f0e2d0"},
    "blue_trust": {"name": "Blue Trust", "bg": "#e8f0fe", "text": "#0b2a5b", "sub": "#3c4a63",
                   "cta_bg": "#1557b0", "cta_text": "#ffffff", "border": "#d2e3fc"},
    "green_fresh": {"name": "Green Fresh", "bg": "#e8f5e9", "text": "#1b3d22", "sub": "#3f5e45",
                    "cta_bg": "#2d7a3e", "cta_text": "#ffffff", "border": "#cfe8d2"},
}

GRADIENTS: dict[str, dict] = {
    "sunset": {"name": "Sunset", "from": "#FF6B35", "to": "#F7931E"},
    "ocean": {"name": "Ocean", "from": "#0052D4", "to": "#65C7F7"},
    "berry": {"name": "Berry", "from": "#8E2DE2", "to": "#4A00E0"},
    "forest": {"name": "Forest", "from": "#134E5E", "to": "#71B280"},
}
# Trên nền gradient (đậm, nhiều màu) chữ luôn trắng, nút CTA nền trắng.
GRADIENT_COLORS = {"text": "#ffffff", "sub": "#ffffff", "cta_bg": "#ffffff", "cta_text": "#1a1a1a"}

BADGES: dict[str, dict] = {
    "free": {"label": "FREE", "bg": "#c62f17", "text": "#ffffff"},
    "new": {"label": "NEW", "bg": "#1a73e8", "text": "#ffffff"},
    "off50": {"label": "50% OFF", "bg": "#f9ab00", "text": "#1a1a1a"},
    "hot": {"label": "HOT", "bg": "#d93025", "text": "#ffffff"},
    "pro": {"label": "PRO", "bg": "#8e24aa", "text": "#ffffff"},
}

# Nhãn góc dịch theo ngôn ngữ của nội dung — quảng cáo tiếng Hàn thì nhãn cũng phải tiếng Hàn.
BADGE_LABELS: dict[str, dict[str, str]] = {
    "free": {"en": "FREE", "vi": "MIỄN PHÍ", "ko": "무료", "ja": "無料", "zh": "免费", "th": "ฟรี",
             "id": "GRATIS", "ms": "PERCUMA", "hi": "मुफ़्त", "ar": "مجاني", "pt": "GRÁTIS",
             "es": "GRATIS", "fr": "GRATUIT", "de": "GRATIS", "ru": "БЕСПЛАТНО"},
    "new": {"en": "NEW", "vi": "MỚI", "ko": "신규", "ja": "新着", "zh": "新品", "th": "ใหม่",
            "id": "BARU", "ms": "BARU", "hi": "नया", "ar": "جديد", "pt": "NOVO",
            "es": "NUEVO", "fr": "NOUVEAU", "de": "NEU", "ru": "НОВОЕ"},
    "off50": {"en": "50% OFF", "vi": "GIẢM 50%", "ko": "50% 할인", "ja": "50%オフ", "zh": "五折",
              "th": "ลด 50%", "id": "DISKON 50%", "ms": "DISKAUN 50%", "hi": "50% छूट",
              "ar": "خصم ٥٠٪", "pt": "50% OFF", "es": "50% DTO", "fr": "-50%", "de": "50% RABATT",
              "ru": "-50%"},
    "hot": {"en": "HOT", "vi": "HOT", "ko": "인기", "ja": "人気", "zh": "热门", "th": "ฮิต",
            "id": "POPULER", "ms": "POPULAR", "hi": "हॉट", "ar": "الأكثر رواجًا", "pt": "EM ALTA",
            "es": "POPULAR", "fr": "TENDANCE", "de": "BELIEBT", "ru": "ХИТ"},
    "pro": {"en": "PRO", "vi": "PRO", "ko": "프로", "ja": "PRO", "zh": "专业版", "th": "PRO",
            "id": "PRO", "ms": "PRO", "hi": "प्रो", "ar": "برو", "pt": "PRO", "es": "PRO",
            "fr": "PRO", "de": "PRO", "ru": "PRO"},
}

def badge_label(badge: str, lang: str) -> str:
    """Chữ trên nhãn góc, theo ngôn ngữ của nội dung."""
    table = BADGE_LABELS.get(badge, {})
    return table.get(lang) or table.get("en") or BADGES[badge]["label"]


LANGUAGES: dict[str, str] = {
    "ko": "한국어", "en": "English", "vi": "Tiếng Việt", "ja": "日本語", "th": "ไทย", "zh": "中文",
    "id": "Bahasa Indonesia", "ms": "Bahasa Melayu", "hi": "हिन्दी", "ar": "العربية", "pt": "Português",
    "es": "Español", "fr": "Français", "de": "Deutsch", "ru": "Русский",
}
# Những bảng chữ cần xếp dấu phức tạp — ảnh PNG có thể đặt sai dấu.
COMPLEX_SCRIPT_LANGS = {"th", "ar", "hi"}

# Ngôn ngữ không dùng khoảng trắng giữa từ → xuống dòng theo ký tự.
CHAR_WRAP_LANGS = {"ja", "zh", "th"}
RTL_LANGS = {"ar"}

# Nút bấm mẫu: cùng 5 ý nghĩa, dịch sẵn cho mọi ngôn ngữ. Nhờ bảng này mà giao diện
# hiện được nghĩa tiếng Việt/Anh bên cạnh nút tiếng Hàn, Nhật, Thái…
_CTA_TEXTS: dict[str, dict[str, str]] = {
    "learn_more": {"en": "Learn more", "vi": "Xem chi tiết", "ko": "자세히 보기", "ja": "詳しく見る",
                   "zh": "了解更多", "th": "ดูรายละเอียด", "id": "Pelajari", "ms": "Ketahui lagi",
                   "hi": "और जानें", "ar": "اعرف المزيد", "es": "Más información", "pt": "Saiba mais",
                   "fr": "En savoir plus", "de": "Mehr erfahren", "ru": "Подробнее"},
    "get_started": {"en": "Get started", "vi": "Bắt đầu ngay", "ko": "시작하기", "ja": "今すぐ始める",
                    "zh": "立即开始", "th": "เริ่มเลย", "id": "Mulai sekarang", "ms": "Mula sekarang",
                    "hi": "शुरू करें", "ar": "ابدأ الآن", "es": "Empezar", "pt": "Começar",
                    "fr": "Commencer", "de": "Jetzt starten", "ru": "Начать"},
    "shop_now": {"en": "Shop now", "vi": "Mua ngay", "ko": "지금 구매", "ja": "購入する",
                 "zh": "立即购买", "th": "ซื้อเลย", "id": "Beli sekarang", "ms": "Beli sekarang",
                 "hi": "अभी खरीदें", "ar": "تسوق الآن", "es": "Comprar", "pt": "Comprar",
                 "fr": "Acheter", "de": "Jetzt kaufen", "ru": "Купить"},
    "sign_up": {"en": "Sign up", "vi": "Đăng ký", "ko": "가입하기", "ja": "登録する",
                "zh": "注册", "th": "สมัคร", "id": "Daftar", "ms": "Daftar",
                "hi": "साइन अप करें", "ar": "سجل الآن", "es": "Regístrate", "pt": "Cadastre-se",
                "fr": "S'inscrire", "de": "Registrieren", "ru": "Регистрация"},
    "try_now": {"en": "Try it now", "vi": "Dùng thử", "ko": "체험하기", "ja": "試してみる",
                "zh": "立即试用", "th": "ทดลองใช้", "id": "Coba sekarang", "ms": "Cuba sekarang",
                "hi": "अभी आज़माएं", "ar": "جرّب الآن", "es": "Pruébalo", "pt": "Experimente",
                "fr": "Essayer", "de": "Ausprobieren", "ru": "Попробовать"},
}

# Mỗi nút mẫu kèm nghĩa tiếng Việt và tiếng Anh để người soạn hiểu mình đang chọn gì.
CTA_PRESETS: dict[str, list[dict[str, str]]] = {
    lang: [{"concept": concept, "text": texts[lang], "vi": texts["vi"], "en": texts["en"]}
           for concept, texts in _CTA_TEXTS.items() if lang in texts]
    for lang in LANGUAGES
}

ANIMATIONS = ["none", "fade", "slide", "scale"]
# Kiểu nút bấm: "text" = chỉ chữ có màu (mặc định), "button" = khối bo tròn có nền.
CTA_STYLES = ["text", "button"]
# Kiểu quảng cáo: banner thường (ZIP tự chạy, không gọi gì bên ngoài) hoặc toàn màn hình
# (tự co vừa màn hình điện thoại và dùng ExitApi của Google để mở link).
AD_FORMATS = ["banner", "fullscreen"]
EXIT_API_URL = "https://tpc.googlesyndication.com/pagead/gadgets/html5/api/exitapi.js"
# Màu chữ/nút CTA gợi ý sẵn (vẫn nhập được mã màu bất kỳ).
CTA_COLORS = ["#1a73e8", "#d93025", "#2d7a3e", "#f9ab00", "#8e24aa", "#1a1a1a", "#ffffff"]
LAYOUTS = ["auto", "center", "left", "top_bottom"]
GROUP_BY = ["set", "size", "flat"]
ELEMENTS = ["badge", "headline", "description", "cta"]

# Danh sách từ cấm mặc định trong CTA (người dùng sửa được trong tool).
DEFAULT_BANNED_CTA = ["다운로드", "설치", "업데이트", "download", "install", "update", "click here", "tải xuống",
                      "cài đặt", "100% free", "guaranteed", "free money"]

MAX_ZIP_BYTES = 150 * 1024  # giới hạn của Google Ads cho mỗi ZIP HTML5
