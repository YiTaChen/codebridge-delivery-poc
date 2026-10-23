from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.models import ModelReading
from backend.reconcile import reconcile, validate_sources


def reading(observations=None, qty=2):
    return ModelReading.model_validate({
        "rows": [{"row_id": "PL-01", "source_line": 1, "sku": "TEA-101", "label": "Green Tea", "expected_qty": qty}],
        "observations": observations or [], "warnings": [],
    })


def observation(marker="ITEM-01", sku="TEA-101", photo="photo_1", visibility="clear", row="PL-01"):
    return {"object_id": marker, "sku_read": sku, "label_read": "Green Tea", "photo_id": photo,
            "region_description": "front left box", "visibility": visibility,
            "confidence_note": "Label text is legible" if visibility == "clear" else "Label is covered", "related_row_id": row}


def test_same_marker_across_photos_counts_once():
    result = reconcile(reading([observation(), observation(photo="photo_2"), observation(marker="ITEM-02")]))
    assert result["rows"][0]["confirmed_qty"] == 2
    assert result["rows"][0]["status"] == "matched"
    assert len(result["rows"][0]["evidence"]) == 3


def test_unseen_units_never_become_confirmed_missing():
    row = reconcile(reading())["rows"][0]
    assert row["confirmed_qty"] == 0
    assert row["status"] == "unverified"
    assert "missing delivery" in row["reason"]


def test_obscured_sku_not_counted_even_if_model_guessed_it():
    row = reconcile(reading([observation(visibility="obscured")], qty=1))["rows"][0]
    assert row["confirmed_qty"] == 0
    assert row["status"] == "unverified"


def test_similar_label_different_sku_never_counts_as_match():
    result = reconcile(reading([observation(sku="TEA-103")], qty=1))
    assert result["rows"][0]["confirmed_qty"] == 0
    assert result["rows"][0]["status"] == "identity_mismatch"
    assert result["extra_items"][0]["sku_read"] == "TEA-103"


def test_visible_extra_unit_quantity_mismatch():
    row = reconcile(reading([observation(), observation(marker="ITEM-02")], qty=1))["rows"][0]
    assert row["confirmed_qty"] == 2
    assert row["status"] == "quantity_mismatch"


def test_conflicting_marker_reads_are_excluded():
    result = reconcile(reading([observation(), observation(sku="TEA-102", photo="photo_2")]))
    assert result["rows"][0]["confirmed_qty"] == 0
    assert any("Conflicting" in warning for warning in result["warnings"])


def test_marker_reused_in_same_photo_is_ambiguous():
    result = reconcile(reading([observation(), observation()], qty=1))
    assert result["rows"][0]["status"] == "unverified"
    assert result["rows"][0]["confirmed_qty"] == 0


def test_no_marker_no_confirmed_count():
    result = reconcile(reading([observation(marker=None)], qty=1))
    assert result["rows"][0]["status"] == "unverified"
    assert result["rows"][0]["confirmed_qty"] == 0


@pytest.mark.parametrize("mutation", ["line", "sku", "qty", "photo", "row"])
def test_invented_sources_rejected(mutation):
    data = reading([observation()]).model_dump()
    if mutation == "line": data["rows"][0]["source_line"] = 99
    if mutation == "sku": data["rows"][0]["sku"] = "TEA-999"
    if mutation == "qty": data["rows"][0]["expected_qty"] = 99
    if mutation == "photo": data["observations"][0]["photo_id"] = "photo_9"
    if mutation == "row": data["observations"][0]["related_row_id"] = "PL-99"
    with pytest.raises(ValueError):
        validate_sources(ModelReading.model_validate(data), [{"line": 1, "text": "TEA-101 Green Tea 2"}], {"photo_1"})


def test_valid_source_accepted_and_partial_sku_not_accepted():
    validate_sources(reading([observation()]), [{"line": 1, "text": "TEA-101 Green Tea 2"}], {"photo_1"})
    with pytest.raises(ValueError):
        validate_sources(reading(), [{"line": 1, "text": "TEA-1010 Green Tea 2"}], {"photo_1"})


@pytest.mark.parametrize("qty", [-1, 1.5, "2"])
def test_invalid_quantities_rejected(qty):
    with pytest.raises(ValidationError): reading(qty=qty)
