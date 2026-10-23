import asyncio
from io import BytesIO
import json
from pathlib import Path

import pytest
from PIL import Image

from backend import providers


@pytest.mark.parametrize("mime,format_name,suffix", [("image/jpeg", "JPEG", ".jpg"), ("image/webp", "WEBP", ".webp"), ("image/png", "PNG", ".png")])
def test_codex_preserves_validated_image_format_and_bytes(monkeypatch, mime, format_name, suffix):
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, format=format_name)
    image_data = buffer.getvalue()

    async def fake_process(*command, **kwargs):
        image_path = Path(command[command.index("--image") + 1])
        assert image_path.suffix == suffix
        assert image_path.read_bytes() == image_data
        with Image.open(image_path) as image:
            assert image.format == format_name
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps({"rows": [{"row_id": "PL-01", "source_line": 1, "sku": "A", "label": "Box", "expected_qty": 1}], "observations": [], "warnings": []}))

        class FakeProcess:
            returncode = 0

            async def communicate(self, stdin):
                return b'{"type":"item.completed","item":{"type":"agent_message"}}\n{"type":"turn.completed","usage":{"input_tokens":42,"output_tokens":20}}\n', b""

        return FakeProcess()

    monkeypatch.setattr(providers.asyncio, "create_subprocess_exec", fake_process)
    monkeypatch.setattr(providers.shutil, "which", lambda executable: "/fake/codex")
    reading, usage, model = asyncio.run(providers.call_codex([{"line": 1, "text": "A Box 1"}], [{"photo_id": "photo_1", "mime": mime, "data": image_data}]))
    assert reading.rows[0].sku == "A"
    assert usage["input_tokens"] == 42
    assert model == providers.CODEX_MODEL


def test_codex_rejects_tool_events_even_with_a_valid_final_json(monkeypatch):
    async def fake_process(*command, **kwargs):
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps({"rows": [{"row_id": "PL-01", "source_line": 1, "sku": "A", "label": "Box", "expected_qty": 1}], "observations": [], "warnings": []}))
        assert "--ignore-user-config" in command
        assert "features.shell_tool=false" in command
        assert "--sandbox" in command and "read-only" in command
        assert "shell" not in kwargs
        class FakeProcess:
            returncode = 0
            async def communicate(self, stdin):
                return b'{"type":"item.started","item":{"type":"command_execution"}}\n', b""
        return FakeProcess()
    monkeypatch.setattr(providers.asyncio, "create_subprocess_exec", fake_process)
    monkeypatch.setattr(providers.shutil, "which", lambda executable: "/fake/codex")
    with pytest.raises(RuntimeError, match="tool/action"):
        asyncio.run(providers.call_codex([{"line": 1, "text": "A Box 1"}], []))


def test_api_cost_uses_reported_cached_input_and_images_in_total_input():
    cost = providers.inference_cost("openai", {"input_tokens": 6000, "cached_input_tokens": 1000, "output_tokens": 1500})
    assert cost["estimated_usd"] == pytest.approx((5000 * .40 + 1000 * .10 + 1500 * 1.60) / 1_000_000)
    assert "API-reported" in cost["basis"]


def test_subscription_cost_not_claimed_free():
    cost = providers.inference_cost("codex", {"input_tokens": 1000, "output_tokens": 500, "cached_input_tokens": 0})
    assert cost["estimated_usd"] is None
    assert "plan fees" in cost["assumptions"]
