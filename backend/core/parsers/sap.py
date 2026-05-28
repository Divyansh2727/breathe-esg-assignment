"""
Parse SAP ME2N/ME23N-style semicolon export (common sustainability-team extract).

Handles German/English header aliases, DD.MM.YYYY dates, and mixed units.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from dateutil import parser as date_parser

# Real exports often use semicolon when Excel locale is DE
HEADER_ALIASES = {
    "material_document": [
        "material document",
        "materialdocument",
        "mblnr",
        "material doc",
        "materialbeleg",
    ],
    "posting_date": [
        "posting date",
        "budat",
        "buchungsdatum",
        "postingdate",
    ],
    "plant": ["plant", "werks", "plant code"],
    "material": ["material", "matnr", "material number", "materialnummer"],
    "description": ["short text", "material description", "maktx", "kurztext"],
    "quantity": ["quantity", "menge", "qty"],
    "unit": ["unit", "meins", "base unit", "basiseinheit"],
    "amount": ["amount", "net value", "dmbtr", "nettowert"],
    "vendor": ["vendor", "lifnr", "supplier", "lieferant"],
    "movement_type": ["movement type", "bwart", "bewegungsart"],
}

FUEL_KEYWORDS = re.compile(
    r"diesel|gasoline|petrol|benzin|heating oil|fuel|kerosene|lpg|gas oil",
    re.I,
)
PROCUREMENT_SKIP = re.compile(r"service|consulting|software license", re.I)

UNIT_TO_LITERS = {
    "L": Decimal("1"),
    "LTR": Decimal("1"),
    "LT": Decimal("1"),
    "GAL": Decimal("3.78541"),
    "GA": Decimal("3.78541"),
    "USG": Decimal("3.78541"),
    "KG": None,  # mass-based fuel needs density — flag suspicious
    "TO": None,
    "T": None,
}


def _normalize_header(h: str) -> str:
    key = h.strip().lower().replace("_", " ").replace("-", " ")
    for canonical, aliases in HEADER_ALIASES.items():
        if key in aliases or key == canonical.replace("_", " "):
            return canonical
    return key.replace(" ", "_")


def _parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return date_parser.parse(value, dayfirst=True)
    except (ValueError, TypeError):
        return None


def _parse_decimal(value: str) -> Decimal | None:
    value = (value or "").strip().replace(" ", "")
    if not value:
        return None
    # German thousands: 1.234,56
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_sap_file(
    content: bytes | str,
    plant_lookup: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    # Detect delimiter
    sample = text[:2048]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("SAP file has no header row")

    col_map = {_normalize_header(h): h for h in reader.fieldnames if h}

    def col(canonical: str) -> str | None:
        return col_map.get(canonical)

    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(reader, start=2):
        payload = dict(raw)

        def get(canonical: str, default: str = "") -> str:
            name = col(canonical)
            if name and raw.get(name) is not None:
                return str(raw.get(name, default)).strip()
            return default

        desc = get("description")
        mat = get("material")
        movement = get("movement_type")

        if PROCUREMENT_SKIP.search(desc):
            rows.append(
                {
                    "line_number": line_no,
                    "raw_payload": payload,
                    "parse_status": "skipped",
                    "parse_errors": ["Non-fuel procurement row skipped"],
                    "activity": None,
                }
            )
            continue

        is_fuel = bool(FUEL_KEYWORDS.search(desc) or FUEL_KEYWORDS.search(mat))
        qty = _parse_decimal(get("quantity"))
        unit = get("unit").upper()
        posting = _parse_date(get("posting_date"))
        plant = get("plant")

        errors: list[str] = []
        if qty is None:
            errors.append("Missing or invalid quantity")
        if not unit:
            errors.append("Missing unit of measure")
        if not posting:
            errors.append(f"Unparseable posting date: {get('posting_date')!r}")

        activity = None
        if not errors:
            facility_name = (plant_lookup or {}).get(plant, "")
            normalized_qty = qty
            normalized_unit = "L"
            suspicion: list[str] = []

            if is_fuel:
                factor = UNIT_TO_LITERS.get(unit)
                if factor is None:
                    suspicion.append(
                        f"Fuel quantity in {unit} — needs density conversion"
                    )
                    normalized_unit = unit
                else:
                    normalized_qty = qty * factor
                scope = "1"
                category = "mobile_combustion" if "fleet" in desc.lower() else "stationary_combustion"
                subcategory = "diesel" if "diesel" in desc.lower() else "fuel"
            else:
                scope = "3"
                category = "purchased_goods"
                subcategory = "procurement"
                normalized_unit = unit
                normalized_qty = qty
                if qty and qty > Decimal("100000"):
                    suspicion.append("Unusually large procurement quantity")

            if not facility_name and plant:
                suspicion.append(f"Unknown plant code {plant}")

            activity = {
                "scope": scope,
                "category": category,
                "subcategory": subcategory,
                "activity_date": posting.date().isoformat() if posting else None,
                "period_start": posting.date().isoformat() if posting else None,
                "period_end": posting.date().isoformat() if posting else None,
                "facility_code": plant,
                "facility_name": facility_name,
                "description": desc or mat,
                "quantity": str(normalized_qty) if normalized_qty is not None else None,
                "unit": normalized_unit,
                "original_quantity": str(qty) if qty is not None else None,
                "original_unit": unit,
                "source_reference": get("material_document"),
                "metadata": {
                    "material": mat,
                    "vendor": get("vendor"),
                    "movement_type": movement,
                    "amount": get("amount"),
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
