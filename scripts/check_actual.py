#!/usr/bin/env python3
"""Compare saved real runs with the predeclared tiny synthetic oracle. No model calls."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main import extract_pdf  # noqa: E402


def marker(value):
    return re.sub(r"[-_ ]", "", (value or "").upper())


def normalized(value):
    return " ".join((value or "").upper().split())


def compare_case(case, expected, actual, sample_dir):
    failures = []
    checks = []

    def check(condition, message):
        checks.append({"check": message, "passed": bool(condition)})
        if not condition:
            failures.append(message)

    packing = {r["sku"]: r for r in expected["packing_rows"][case["pdf"]]}
    rows = actual.get("rows", [])
    by_sku = {r.get("sku"): r for r in rows}
    check(len(by_sku) == len(rows) and set(by_sku) == set(packing), "All and only expected PDF SKU rows are present without duplicates")
    original_lines = extract_pdf((sample_dir / case["pdf"]).read_bytes())
    actual_lines = actual.get("pdf_lines", [])
    check(actual_lines == original_lines, "Returned numbered PDF lines match extraction of the original uploaded PDF")
    line_map = {r["line"]: r["text"] for r in original_lines}
    photo_ids = {f"photo_{i + 1}" for i in range(len(case["photos"]))}

    for oracle in case["rows"]:
        sku = oracle["sku"]
        row = by_sku.get(sku, {})
        source = packing[sku]
        check(row.get("confirmed_qty") == oracle["confirmed_qty"], f"{sku}: confirmed quantity equals {oracle['confirmed_qty']}")
        check(row.get("status") in oracle["acceptable_statuses"], f"{sku}: status is one of {', '.join(oracle['acceptable_statuses'])}")
        check(row.get("expected_qty") == source["expected_qty"] and row.get("source_line") == source["source_line"], f"{sku}: expected quantity and source line equal the PDF oracle")
        check(normalized(row.get("label")) == normalized(source["label"]), f"{sku}: product label equals the PDF oracle")
        line = line_map.get(row.get("source_line"), "")
        check(sku in line, f"{sku}: cited source line contains the literal SKU")
        evidence = row.get("evidence", [])
        check(all(e.get("photo_id") in photo_ids and e.get("region_description") and e.get("region_verified") is False for e in evidence), f"{sku}: every evidence region references an uploaded photo and remains explicitly unverified")
        if oracle["confirmed_qty"]:
            exact = [e for e in evidence if e.get("visibility") == "clear" and e.get("sku_read") == sku and e.get("object_id")]
            distinct = {marker(e["object_id"]) for e in exact}
            check(len(distinct) == oracle["confirmed_qty"], f"{sku}: confirmed count equals distinct marked exact-SKU evidence, not photo appearances")

    allowed_statuses = {"matched", "identity_mismatch", "quantity_mismatch", "unverified"}
    check(all(r.get("status") in allowed_statuses for r in rows), "No row reports confirmed_missing or any unsupported status")
    extras = actual.get("extra_items", [])
    extra_skus = {e.get("sku_read") for e in extras if e.get("status") == "quantity_mismatch" and e.get("sku_read")}
    check(extra_skus == set(case.get("extra_skus", [])), "Visible unexpected SKUs equal the predeclared extras")
    for extra in extras:
        check(extra.get("status") in {"quantity_mismatch", "unverified"}, "Unexpected/uncertain object has a supported conservative status")
        check(all(e.get("photo_id") in photo_ids and e.get("region_description") for e in extra.get("evidence", [])), "Unexpected/uncertain object cites an uploaded photo and descriptive region")

    observations = actual.get("observations", [])
    check(all(o.get("photo_id") in photo_ids for o in observations), "Every visual observation references an uploaded photo")
    observed = defaultdict(list)
    for obs in observations:
        observed[marker(obs.get("object_id"))].append(obs)
    object_oracle = expected["issue_delivery_objects" if case["id"] == "issue_delivery" else "corrected_delivery_objects"]
    for obj in object_oracle:
        sightings = observed.get(marker(obj["object_id"]), [])
        check(bool(sightings), f"{obj['object_id']}: object was observed")
        expected_views = set(obj.get("photos", ["photo_1"]))
        check({o.get("photo_id") for o in sightings} == expected_views, f"{obj['object_id']}: observed in the expected view(s), including repeated views")
        if obj["sku"] is not None:
            check(all(o.get("sku_read") == obj["sku"] and o.get("visibility") == "clear" for o in sightings), f"{obj['object_id']}: visible SKU equals synthetic ground truth")
        else:
            check(all(o.get("sku_read") is None and o.get("visibility") != "clear" for o in sightings), f"{obj['object_id']}: obscured SKU was not guessed")
            unknown_extra = [e for e in extras if marker(e.get("object_id")) == marker(obj["object_id"])]
            check(bool(unknown_extra) and all(e.get("status") == "unverified" for e in unknown_extra), f"{obj['object_id']}: remains explicitly unverified and uncounted")

    metrics = actual.get("metrics", {})
    check(metrics.get("elapsed_measured") is True and isinstance(metrics.get("elapsed_seconds"), (int, float)) and metrics["elapsed_seconds"] > 0, "Actual run has a positive measured processing duration")
    check(bool(metrics.get("model")) and metrics.get("provider") in {"codex", "openai"}, "Actual provider and model are disclosed")
    check("estimated_usd" in metrics.get("cost", {}) and bool(metrics["cost"].get("basis")), "Cost basis is disclosed and distinct from measured duration")
    return {"id": case["id"], "passed": not failures, "checks_passed": sum(c["passed"] for c in checks),
            "checks_total": len(checks), "failures": failures, "checks": checks,
            "observed_rows": [{k: r.get(k) for k in ("sku", "expected_qty", "confirmed_qty", "status", "source_line")} for r in rows],
            "elapsed_seconds": metrics.get("elapsed_seconds"), "model": metrics.get("model")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-dir", type=Path, default=ROOT / "sample-data")
    args = parser.parse_args()
    expected = json.loads((args.sample_dir / "expected_results.json").read_text())
    cases = []
    for case in expected["cases"]:
        path = args.sample_dir / "actual" / f"{case['id']}.json"
        if not path.exists():
            cases.append({"id": case["id"], "passed": False, "checks_passed": 0, "checks_total": 1,
                          "failures": [f"Missing saved real result: {path.name}"]})
            continue
        try:
            cases.append(compare_case(case, expected, json.loads(path.read_text()), args.sample_dir))
        except (ValueError, TypeError, KeyError, OSError) as error:
            cases.append({"id": case["id"], "passed": False, "checks_passed": 0, "checks_total": 1,
                          "failures": [f"Could not verify saved result: {error}"]})
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "Three predeclared synthetic cases; no real-world accuracy claim and no new model calls.",
              "passed": all(c["passed"] for c in cases), "cases": cases}
    report_path = args.sample_dir / "actual" / "comparison.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    for case in cases:
        print(f"{'PASS' if case['passed'] else 'FAIL'} {case['id']}: {case['checks_passed']}/{case['checks_total']} checks")
        for failure in case["failures"]:
            print(f"  - {failure}")
    print(f"Report: {report_path.relative_to(ROOT) if report_path.is_relative_to(ROOT) else report_path}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
