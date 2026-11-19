import pytest
from pydantic import ValidationError

from html5adbuilder import catalog, cta
from html5adbuilder.models import AdSize, ContentSet, Design, Project


def _set(**kw):
    base = {"name": "Bộ 1", "headline": "Fast PDF", "description": "Open any PDF", "cta": "Learn more", "lang": "en"}
    return ContentSet(**{**base, **kw})


def test_headline_limit_ac1():
    _set(headline="x" * 20)
    with pytest.raises(ValidationError, match="20"):
        _set(headline="x" * 21)
    with pytest.raises(ValidationError, match="100"):
        _set(description="y" * 101)
    with pytest.raises(ValidationError):
        _set(headline="   ")


def test_unknown_language_rejected():
    with pytest.raises(ValidationError):
        _set(lang="xx")


def test_size_parse_and_bounds():
    assert AdSize.parse("300x250") == AdSize(w=300, h=250)
    assert AdSize.parse(" 728 × 90 ").key == "728x90"
    with pytest.raises(ValueError):
        AdSize.parse("abc")
    with pytest.raises(ValidationError):
        AdSize(w=5, h=250)


def test_catalog_has_google_sizes_and_groups():
    keys = {s["key"] for s in catalog.SIZES}
    assert {"300x250", "728x90", "320x50", "160x600", "970x250"} <= keys
    assert {s["group"] for s in catalog.SIZES} == {"display", "mobile", "other"}
    assert len(catalog.SCHEMES) == 6 and len(catalog.GRADIENTS) == 4 and len(catalog.BADGES) == 5
    assert len(catalog.LANGUAGES) == 15


def test_creative_count_ac3():
    p = Project(sets=[_set(), _set(name="b"), _set(name="c")],
                sizes=[AdSize(w=300, h=250)] * 1 + [AdSize(w=728, h=90)],
                design=Design(schemes=["clean_white"], badges=["free"]))
    assert p.creative_count == 3 * 2 * 1 * 1
    p20 = p.model_copy(update={"sizes": [AdSize.parse(s["key"]) for s in catalog.SIZES[:20]]})
    assert p20.creative_count == 60
    nobadge = p.model_copy(update={"design": Design(schemes=["clean_white", "dark"], badges=[])})
    assert nobadge.creative_count == 3 * 2 * 2


def test_design_rejects_unknown_values():
    with pytest.raises(ValidationError):
        Design(schemes=["nope"])
    with pytest.raises(ValidationError):
        Design(schemes=[])
    with pytest.raises(ValidationError):
        Design(badges=["zzz"])


def test_cta_banned_ac2():
    words = cta.load_banned()
    assert "download" in words
    assert cta.find_banned("Download now", words) == ["download"]
    assert cta.find_banned("Learn more", words) == []
    assert cta.find_banned("지금 다운로드", words) == ["다운로드"]


def test_cta_banned_list_editable():
    cta.save_banned(["  Spam ", "spam", "", "free money"])
    assert cta.load_banned() == ["free money", "spam"]
    assert cta.find_banned("SPAM here", cta.load_banned()) == ["spam"]
    cta.reset_banned()
    assert "download" in cta.load_banned()


def test_cta_presets_cover_all_languages_with_glosses():
    assert set(catalog.CTA_PRESETS) == set(catalog.LANGUAGES)
    ko = catalog.CTA_PRESETS["ko"]
    assert len(ko) == 5
    assert ko[0] == {"concept": "learn_more", "text": "자세히 보기", "vi": "Xem chi tiết",
                     "en": "Learn more"}
    # Nút tiếng Việt thì nghĩa trùng chữ trên nút (giao diện sẽ không hiện thêm)
    vi = catalog.CTA_PRESETS["vi"][0]
    assert vi["text"] == vi["vi"]
    for lang, presets in catalog.CTA_PRESETS.items():
        for p in presets:
            assert p["text"] and len(p["text"]) <= 25, (lang, p)
            assert p["vi"] and p["en"]


def test_cta_presets_carry_concept_for_language_swap():
    ko = {p["concept"]: p["text"] for p in catalog.CTA_PRESETS["ko"]}
    vi = {p["concept"]: p["text"] for p in catalog.CTA_PRESETS["vi"]}
    assert ko.keys() == vi.keys()
    assert ko["learn_more"] == "자세히 보기" and vi["learn_more"] == "Xem chi tiết"
