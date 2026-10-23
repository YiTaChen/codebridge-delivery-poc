"""Small deterministic guardrails; deliberately not general object tracking."""

import re
from collections import defaultdict

from .models import ModelReading


def canonical(value: str | None) -> str:
    return (value or "").strip().upper()


def validate_sources(reading: ModelReading, pdf_lines: list[dict], photo_ids: set[str]) -> None:
    lines = {entry["line"]: entry["text"] for entry in pdf_lines}
    row_ids = {row.row_id for row in reading.rows}
    if len(row_ids) != len(reading.rows):
        raise ValueError("Model returned duplicate PDF row IDs.")
    if len({canonical(row.sku) for row in reading.rows}) != len(reading.rows):
        raise ValueError("Duplicate packing-list SKUs are unsupported; combine their quantities first.")
    for row in reading.rows:
        source = lines.get(row.source_line)
        if not source or not re.search(r"(?<![\w-])" + re.escape(canonical(row.sku)) + r"(?![\w-])", canonical(source)):
            raise ValueError("A model row references a missing PDF line or a SKU absent from that line.")
        # Quantities must be literal values in the source, never free model arithmetic.
        if not re.search(r"(?<![\w.-])" + re.escape(str(row.expected_qty)) + r"(?![\w.-])", source):
            raise ValueError("A model quantity is absent from its cited PDF line.")
    for item in reading.observations:
        if item.photo_id not in photo_ids:
            raise ValueError("A model observation references a photo that was not uploaded.")
        if item.related_row_id is not None and item.related_row_id not in row_ids:
            raise ValueError("A model observation references an unknown PDF row.")


def evidence(item) -> dict:
    return {
        "photo_id": item.photo_id,
        "region_description": item.region_description,
        "region_verified": False,
        "object_id": item.object_id,
        "sku_read": item.sku_read,
        "visibility": item.visibility,
        "confidence_note": item.confidence_note,
    }


def reconcile(reading: ModelReading) -> dict:
    """Only clear SKU + stable ITEM marker can contribute a confirmed unit."""
    groups = defaultdict(list)
    unidentified = []
    for item in reading.observations:
        if item.object_id and re.fullmatch(r"ITEM[-_ ]?\d{1,4}", item.object_id, re.I):
            marker = re.sub(r"[-_ ]", "", item.object_id.upper())
            groups[marker].append(item)
        else:
            unidentified.append(item)

    confirmed = defaultdict(list)
    uncertain = []
    warnings = list(reading.warnings)
    for marker, appearances in groups.items():
        if len({o.photo_id for o in appearances}) != len(appearances):
            uncertain.extend(appearances)
            warnings.append(f"Marker {marker} was read more than once in the same photo; identity is ambiguous and excluded from confirmed counts.")
            continue
        clear = [o for o in appearances if o.visibility == "clear" and o.sku_read]
        skus = {canonical(o.sku_read) for o in clear}
        if len(skus) == 1:
            confirmed[next(iter(skus))].append((marker, appearances))
        else:
            uncertain.extend(appearances)
            if len(skus) > 1:
                warnings.append(f"Conflicting SKU readings for {marker}; excluded from confirmed counts.")
    uncertain.extend(unidentified)
    if unidentified:
        warnings.append("Some objects have no readable stable ITEM marker; they are excluded from confirmed counts. Add unique markers and retake photos.")

    rows = []
    requested_skus = {canonical(row.sku) for row in reading.rows}
    for row in reading.rows:
        sku = canonical(row.sku)
        units = confirmed.get(sku, [])
        count = len(units)
        related_uncertain = [o for o in uncertain if canonical(o.sku_read) == sku or o.related_row_id == row.row_id]
        wrong = [o for units_by_sku in confirmed.values() for _, appearances in units_by_sku for o in appearances
                 if o.visibility == "clear" and o.related_row_id == row.row_id and canonical(o.sku_read) != sku]
        row_evidence = [evidence(o) for _, appearances in units for o in appearances]
        row_evidence += [evidence(o) for o in related_uncertain + wrong]
        if count > row.expected_qty:
            status = "quantity_mismatch"
            reason = f"{count} distinct marked units have the exact SKU; the PDF expects {row.expected_qty}."
        elif count == row.expected_qty and not related_uncertain:
            status = "matched"
            reason = f"{count} distinct marked units have the exact SKU. Repeated markers across photos count once."
        elif wrong:
            status = "identity_mismatch"
            reason = "A related/similar label has a different visible SKU and is not counted as the requested item. Expected units remain unverified; this does not prove substitution or absence."
        else:
            status = "unverified"
            reason = f"Only {count} of {row.expected_qty} requested units can be verified. Obscured labels, uncertain identity, or items outside the photos do not prove missing delivery."
        rows.append({**row.model_dump(), "confirmed_qty": count, "status": status,
                     "evidence": row_evidence, "reason": reason})

    extras = []
    for sku, units in confirmed.items():
        if sku not in requested_skus:
            for marker, appearances in units:
                first = appearances[0]
                extras.append({"object_id": first.object_id, "sku_read": sku, "label_read": first.label_read,
                               "status": "quantity_mismatch", "evidence": [evidence(o) for o in appearances],
                               "reason": "A distinct object with this visible SKU is not on the packing list."})
    # One unknown object may occur in multiple photos; keep all evidence but do not claim its count.
    unknown_groups = defaultdict(list)
    for index, item in enumerate(uncertain):
        unknown_groups[canonical(item.object_id) or f"unknown-{index}"].append(item)
    for appearances in unknown_groups.values():
        first = appearances[0]
        extras.append({"object_id": first.object_id, "sku_read": first.sku_read, "label_read": first.label_read,
                       "status": "unverified", "evidence": [evidence(o) for o in appearances],
                       "reason": "Identity or stable marker cannot be confirmed; excluded from exact counts."})
    return {"rows": rows, "observations": [o.model_dump() for o in reading.observations],
            "extra_items": extras, "warnings": list(dict.fromkeys(warnings))}
