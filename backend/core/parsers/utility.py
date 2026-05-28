"""
Parse Green Button–style utility portal CSV (billing period rows, kWh).
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from dateutil import parser as date_parser

HEADER_ALIASES = {
    "account": ["account", "account number", "service account", "account id"],
    "meter": ["meter", "meter id", "meter number"],
    "site": ["service address", "site", "facility", "location name"],
    "period_start": [
        "bill start",
        "billing period start",
        "period start",
        "start date",
        "bill period start",
    ],
    "period_end": [
        "bill end",
        "billing period end",
        "period end",
        "end date",
        "bill period end",
    ],
    "usage": ["usage", "consumption", "kwh", "energy (kwh)", "total kwh"],
    "units": ["units", "unit", "uom"],
    "cost": ["total charges", "amount due", "cost", "total cost"],
    "tariff": ["rate schedule", "tariff", "rate plan"],
}


def _normalize_header(h: str) -> str:
    key = h.strip().lower()
    for canonical, aliases in HEADER_ALIASES.items():
        if key in aliases:
            return canonical
    return key.replace(" ", "_")


def _parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, TypeError):
        return None


def _parse_decimal(value: str) -> Decimal | None:
    value = (value or "").strip().replace(",", "")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_utility_file(content: bytes | str) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Utility CSV has no header row")

    col_map = {_normalize_header(h): h for h in reader.fieldnames if h}

    def col(canonical: str) -> str | None:
        return col_map.get(canonical)

    def get(raw: dict, canonical: str, default: str = "") -> str:
        name = col(canonical)
        if name and raw.get(name) is not None:
            return str(raw.get(name, default)).strip()
        return default

    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(reader, start=2):
        payload = dict(raw)
        usage = _parse_decimal(get(raw, "usage"))
        units = get(raw, "units").upper() or "KWH"
        p_start = _parse_date(get(raw, "period_start"))
        p_end = _parse_date(get(raw, "period_end"))
        account = get(raw, "account")
        meter = get(raw, "meter")

        errors: list[str] = []
        suspicion: list[str] = []

        if usage is None:
            errors.append("Missing or invalid usage quantity")
        if not p_start or not p_end:
            errors.append("Billing period start/end required")
        if p_start and p_end and p_start > p_end:
            errors.append("Period start after period end")

        if units not in ("KWH", "KW·H", "KWH.", ""):
            if units == "MWH":
                if usage is not None:
                    usage = usage * Decimal("1000")
                units = "KWH"
            else:
                suspicion.append(f"Non-kWh unit: {units}")

        # Billing periods often span partial months
        if p_start and p_end:
            days = (p_end - p_start).days
            if days > 45:
                suspicion.append(f"Long billing period ({days} days)")
            if days < 20:
                suspicion.append(f"Short billing period ({days} days)")

        activity = None
        if not errors:
            activity = {
                "scope": "2",
                "category": "purchased_electricity",
                "subcategory": "grid_electricity",
                "activity_date": p_end.date().isoformat() if p_end else None,
                "period_start": p_start.date().isoformat() if p_start else None,
                "period_end": p_end.date().isoformat() if p_end else None,
                "facility_code": account,
                "facility_name": get(raw, "site"),
                "description": f"Electricity — meter {meter or 'n/a'}",
                "quantity": str(usage),
                "unit": "kWh",
                "original_quantity": str(usage),
                "original_unit": units or "kWh",
                "source_reference": f"{account}:{p_start.date().isoformat() if p_start else ''}",
                "metadata": {
                    "meter": meter,
                    "tariff": get(raw, "tariff"),
                    "cost": get(raw, "cost"),
                },
                "suspicion_reasons": suspicion,
                "validation_errors": [],
            }

        rows.append(
            {
                "line_number": line_no,
                "raw_payload": payload,
                "parse_status": "error" if errors else "ok",
                "parse_errors": errors,
                "activity": activity,
            }
        )

    return rows
