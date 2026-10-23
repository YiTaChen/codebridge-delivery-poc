from io import BytesIO

import fitz
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend import main
from backend.models import ModelReading


def pdf_bytes(text="TEA-101 Green Tea 1", pages=1):
    document = fitz.open()
    for _ in range(pages):
        page = document.new_page()
        if text: page.insert_text((72, 72), text)
    result = document.tobytes()
    document.close()
    return result


def image_bytes():
    stream = BytesIO()
    Image.new("RGB", (64, 64), "white").save(stream, format="PNG")
    return stream.getvalue()


def files(pdf=None, count=1):
    return [("packing_list", ("packing.pdf", pdf if pdf is not None else pdf_bytes(), "application/pdf"))] + [
        ("photos", (f"photo_{index}.png", image_bytes(), "image/png")) for index in range(count)]


@pytest.fixture
def client():
    with TestClient(main.app, base_url="http://localhost:8000") as client:
        yield client


def test_text_pdf_rows_preserved():
    lines = main.extract_pdf(pdf_bytes())
    assert lines == [{"line": 1, "text": "TEA-101 Green Tea 1"}]


@pytest.mark.parametrize("pdf", [b"not a pdf", pdf_bytes(pages=2), pdf_bytes(text="")])
def test_invalid_multipage_scanned_pdf_rejected_before_model(client, monkeypatch, pdf):
    async def must_not_call(*args): raise AssertionError("Model must not be called")
    monkeypatch.setattr(main, "call_codex", must_not_call)
    response = client.post("/api/analyze", files=files(pdf))
    assert response.status_code == 400


def test_too_many_images_rejected(client):
    response = client.post("/api/analyze", files=files(count=4))
    assert response.status_code == 400


def test_bad_image_bytes_rejected(client):
    upload = files()
    upload[1] = ("photos", ("fake.png", b"not image", "image/png"))
    assert client.post("/api/analyze", files=upload).status_code == 400


def test_api_key_required_but_never_echoed(client):
    response = client.post("/api/analyze", data={"provider": "openai"}, files=files())
    assert response.status_code == 400
    assert "masked" in response.json()["detail"]


def test_cross_origin_and_remote_host_rejected(client):
    assert client.post("/api/analyze", headers={"Origin": "https://evil.example"}, files=files()).status_code == 403
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 403


def test_mocked_provider_end_to_end_records_timing_and_evidence(client, monkeypatch):
    async def fake_provider(pdf_lines, photos):
        assert pdf_lines[0]["text"] == "TEA-101 Green Tea 1"
        assert photos[0]["photo_id"] == "photo_1"
        return ModelReading.model_validate({
            "rows": [{"row_id": "PL-01", "source_line": 1, "sku": "TEA-101", "label": "Green Tea", "expected_qty": 1}],
            "observations": [{"object_id": "ITEM-01", "sku_read": "TEA-101", "label_read": "Green Tea", "photo_id": "photo_1",
                "region_description": "front left", "visibility": "clear", "confidence_note": "legible", "related_row_id": "PL-01"}], "warnings": []
        }), {"input_tokens": 123, "cached_input_tokens": 0, "output_tokens": 80}, "unit-test-model"
    monkeypatch.setattr(main, "call_codex", fake_provider)
    response = client.post("/api/analyze", files=files())
    assert response.status_code == 200
    result = response.json()
    assert result["rows"][0]["status"] == "matched"
    assert result["rows"][0]["evidence"][0]["region_verified"] is False
    assert result["metrics"]["elapsed_measured"] is True
    assert result["metrics"]["cost"]["estimated_usd"] is None
    assert result["metrics"]["model"] == "unit-test-model"


def test_invalid_model_source_returns_safe_error(client, monkeypatch):
    async def fake_provider(*args):
        return ModelReading.model_validate({"rows": [{"row_id": "PL-01", "source_line": 99, "sku": "TEA-101", "label": "Green Tea", "expected_qty": 1}], "observations": [], "warnings": []}), None, "fake"
    monkeypatch.setattr(main, "call_codex", fake_provider)
    response = client.post("/api/analyze", files=files())
    assert response.status_code == 502
    assert "No conclusion was accepted" in response.json()["detail"]
