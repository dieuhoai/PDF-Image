import base64
import io
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from web.server import COOKIE, TOKEN_HEADER, create_app

TOKEN = "test-token"
HOST = "testserver"

CONTENT = {"id": "s1", "name": "EN", "headline": "Fast PDF", "description": "Open any PDF",
           "cta": "Learn more", "lang": "en"}


@pytest.fixture
def client():
    c = TestClient(create_app(TOKEN, {HOST}))
    c.headers[TOKEN_HEADER] = TOKEN
    return c


def test_requires_token():
    c = TestClient(create_app(TOKEN, {HOST}))
    assert c.get("/api/catalog").status_code == 401
    assert c.get("/").status_code == 401
    r = c.get(f"/?t={TOKEN}", follow_redirects=False)
    assert r.status_code == 303 and COOKIE in r.headers["set-cookie"]


def test_bad_host_and_origin(client):
    assert client.get("/api/catalog", headers={"host": "evil.com"}).status_code == 403
    assert client.get("/api/catalog", headers={"origin": "http://evil.com"}).status_code == 403


def test_index_has_csp(client):
    r = client.get("/")
    assert r.status_code == 200 and "default-src 'self'" in r.headers["content-security-policy"]


def test_catalog(client):
    c = client.get("/api/catalog").json()
    assert len(c["sizes"]) >= 20 and len(c["schemes"]) == 6 and len(c["languages"]) == 15
    assert c["max_zip_kb"] == 150 and "fade" in c["animations"]


def test_cta_check_and_edit_banned(client):
    assert client.post("/api/cta/check", json={"text": "Download now"}).json() == {"ok": False,
                                                                                  "banned": ["download"]}
    assert client.post("/api/cta/check", json={"text": "Learn more"}).json()["ok"] is True
    assert client.put("/api/banned-cta", json={"words": ["abc"]}).json()["words"] == ["abc"]
    assert client.post("/api/cta/check", json={"text": "Download now"}).json()["ok"] is True
    assert "download" in client.post("/api/banned-cta/reset").json()["words"]


def test_csv_import_api(client):
    r = client.post("/api/csv/import", json={"text": "headline,cta,lang\nFast PDF,Learn more,en\nX,Y,zz\n"})
    data = r.json()
    assert len(data["sets"]) == 1 and len(data["errors"]) == 1
    assert client.post("/api/csv/import", json={"path": "/khong/co.csv"}).status_code == 422
    assert client.post("/api/csv/import", json={}).status_code == 422


def test_palette_api(client):
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (26, 115, 232)).save(buf, "PNG")
    url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    assert client.post("/api/palette/suggest", json={"data_url": url}).json()["scheme"] == "blue_trust"
    assert client.post("/api/palette/suggest", json={"data_url": "data:,xx"}).status_code == 422


def test_preview_api(client):
    r = client.post("/api/preview", json={"content": CONTENT, "size": "300x250", "badge": "new"})
    data = r.json()
    assert "ad.size" in data["html"] and data["size"] == {"w": 300, "h": 250}
    assert data["bytes"] > 0 and {b["element"] for b in data["boxes"]} >= {"headline", "cta"}
    assert client.post("/api/preview", json={"content": CONTENT, "size": "nope"}).status_code == 422
    bad = {**CONTENT, "headline": "x" * 30}
    assert client.post("/api/preview", json={"content": bad}).status_code == 422


def test_library_roundtrip(client):
    proj = {"sets": [CONTENT], "sizes": [{"w": 300, "h": 250}]}
    assert client.put("/api/library", json={"name": "Chiến dịch 1", "project": proj}).status_code == 200
    assert client.get("/api/library").json()["items"][0]["name"] == "Chiến dịch 1"
    assert len(client.get("/api/library/Chiến dịch 1").json()["project"]["sets"]) == 1
    assert client.get("/api/library/khong-co").status_code == 404
    assert client.put("/api/library", json={"name": "a/b", "project": proj}).status_code == 422
    client.delete("/api/library/Chiến dịch 1")
    assert client.get("/api/library").json()["items"] == []


def _wait(client, tries=200):
    for _ in range(tries):
        job = client.get("/api/jobs").json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError("job không kết thúc")


def test_export_job(client, tmp_path):
    body = {"output_dir": str(tmp_path),
            "project": {"sets": [CONTENT], "sizes": [{"w": 300, "h": 250}, {"w": 728, "h": 90}],
                        "design": {"schemes": ["clean_white"], "badges": ["new"]}}}
    r = client.post("/api/jobs", json=body)
    assert r.status_code == 200 and r.json()["total"] == 2
    job = _wait(client)
    assert job["status"] == "done" and job["ok"] == 2 and job["failed"] == []
    assert job["folder"] and job["zip_path"].endswith(".zip")
    assert client.post("/api/library/reveal", json={"path": "/khong/co"}).status_code == 404


def test_export_validation(client, tmp_path):
    assert client.post("/api/jobs", json={"output_dir": str(tmp_path), "project": {"sets": []}}).status_code == 422
    assert client.post("/api/jobs", json={"output_dir": str(tmp_path / "nope"),
                                          "project": {"sets": [CONTENT]}}).status_code == 422


def _ref_png() -> str:
    from PIL import ImageDraw
    img = Image.new("RGB", (1200, 630), (245, 245, 245))
    d = ImageDraw.Draw(img)
    d.rectangle([90, 80, 830, 160], fill=(20, 20, 20))
    d.rectangle([92, 220, 700, 252], fill=(90, 90, 90))
    d.rectangle([980, 540, 1120, 580], fill=(232, 52, 26))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_reference_returns_colours_and_layout(client):
    r = client.post("/api/reference", json={"data_url": _ref_png(), "sizes": ["300x250", "728x90"]})
    data = r.json()
    assert data["layout_found"] is True and data["scheme"]
    roles = {b["element"]: b for b in data["blocks"]}
    assert roles["headline"]["vertical"] == "top" and roles["headline"]["align"] == "left"
    assert roles["cta"]["vertical"] == "bottom" and roles["cta"]["align"] == "right"
    plan = data["plan"]
    assert set(plan["positions"]) == {"300x250", "728x90"}
    assert plan["positions"]["300x250"]["cta"]["y"] > 0.6
    assert plan["cta_color"].startswith("#e") and plan["layout"] == "left"


def test_reference_rejects_bad_image(client):
    assert client.post("/api/reference", json={"data_url": "data:,xx"}).status_code == 422
    assert client.post("/api/reference", json={}).status_code == 422
