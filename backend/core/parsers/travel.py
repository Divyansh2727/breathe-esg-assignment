"""
Parse Concur Expense Report v4–style JSON export (subset for business travel).
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from dateutil import parser as date_parser

import re

AIR_TYPES = re.compile(r"air|flight|airfare", re.I)
HOTEL_TYPES = re.compile(r"hotel|lodging|accommodation", re.I)
GROUND_TYPES = re.compile(r"rail|train|taxi|uber|lyft|car rental|ground|mileage", re.I)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, TypeError):
        return None


def _infer_mode(expense_type: str, travel: dict) -> str:
    name = (expense_type or "").lower()
    if AIR_TYPES.search(name):
        return "air"
    if HOTEL_TYPES.search(name):
        return "hotel"
    if GROUND_TYPES.search(name):
        return "ground"
    if travel.get("ticketNumber") or travel.get("startLocation") and "—" in str(
        travel.get("startLocation", "")
    ):
        return "air"
    if travel.get("hotelCheckinDate"):
        return "hotel"
    return "ground"


def _airport_distance_proxy(start: str, end: str) -> tuple[Decimal | None, list[str]]:
    """Without a geodesic service, airport-pair-only rows get flagged."""
    suspicion = []
    codes = re.findall(r"\b[A-Z]{3}\b", f"{start} {end}")
    if len(codes) >= 2 and not any(c.isdigit() for c in start + end):
        suspicion.append(
            f"Distance inferred from airports {codes[0]}–{codes[1]} — needs validation"
        )
        # Rough placeholder: analysts must confirm; mark suspicious not fake km
        return None, suspicion
    return None, suspicion


def parse_travel_file(content: bytes | str) -> list[dict[str, Any]]:
    text = content.decode("utf-8") if isinstance(content, bytes) else content
    data = json.loads(text)

    entries = data.get("expenses") or data.get("ExpenseEntries") or data
    if isinstance(entries, dict):
        entries = entries.get("expenses", [])

    rows: list[dict[str, Any]] = []
    for line_no, entry in enumerate(entries, start=1):
        payload = entry
        expense_type = ""
        et = entry.get("expenseType") or entry.get("ExpenseType")
        if isinstance(et, dict):
            expense_type = et.get("name") or et.get("Name") or ""
        elif isinstance(et, str):
            expense_type = et

        travel = entry.get("travel") or {}
        txn_date = _parse_date(
            entry.get("transactionDate")
            or entry.get("TransactionDate")
            or travel.get("departureDate")
        )
        amount = entry.get("transactionAmount") or entry.get("Amount")
        currency = ""
        if isinstance(amount, dict):
            currency = amount.get("currencyCode") or amount.get("CurrencyCode") or ""
            amount = amount.get("value") or amount.get("Value")
        start_loc = travel.get("startLocation") or entry.get("startLocation") or ""
        end_loc = travel.get("endLocation") or entry.get("endLocation") or ""
        mode = _infer_mode(expense_type, travel)

        errors: list[str] = []
        suspicion: list[str] = []

        quantity = None
        unit = ""
        subcategory = mode

        if mode == "air":
            mileage = travel.get("flightDistance") or travel.get("distance")
            if mileage:
                quantity = Decimal(str(mileage))
                unit = "km"
            else:
                quantity, suspicion = _airport_distance_proxy(start_loc, end_loc)
                unit = "km" if quantity else ""
            scope = "3"
            category = "business_travel"
            desc = f"Flight {start_loc} → {end_loc}".strip()
        elif mode == "hotel":
            checkin = _parse_date(travel.get("hotelCheckinDate"))
            checkout = _parse_date(travel.get("hotelCheckoutDate"))
            if checkin and checkout:
                nights = (checkout - checkin).days
                quantity = Decimal(max(nights, 1))
                unit = "nights"
            else:
                errors.append("Hotel stay missing check-in/out dates")
            scope = "3"
            category = "business_travel"
            desc = f"Hotel — {travel.get('hotelName') or expense_type}"
        else:
            days = travel.get("carRentalDays")
            if days is not None:
                quantity = Decimal(str(days))
                unit = "days"
            else:
                dist = travel.get("distance") or entry.get("mileage")
                if dist:
                    quantity = Decimal(str(dist))
                    unit = "km"
                else:
                    suspicion.append("Ground travel without distance or rental days")
            scope = "3"
            category = "business_travel"
            desc = f"Ground travel — {expense_type}"

        if not txn_date and not errors:
            suspicion.append("Missing transaction date")

        activity = None
        if not errors:
            activity = {
                "scope": scope,
                "category": category,
                "subcategory": subcategory,
                "activity_date": txn_date.date().isoformat() if txn_date else None,
                "period_start": txn_date.date().isoformat() if txn_date else None,
                "period_end": txn_date.date().isoformat() if txn_date else None,
                "facility_code": entry.get("orgUnit1") or "",
                "facility_name": "",
                "description": desc[:500],
                "quantity": str(quantity) if quantity is not None else None,
                "unit": unit,
                "original_quantity": str(quantity) if quantity is not None else None,
                "original_unit": unit,
                "source_reference": entry.get("id") or entry.get("ReportEntryID") or "",
                "metadata": {
                    "expense_type": expense_type,
                    "ticket_number": travel.get("ticketNumber"),
                    "service_class": travel.get("airlineServiceClassCode"),
                    "currency": currency,
                    "amount": str(amount) if amount is not None else None,
                    "start_location": start_loc,
                    "end_location": end_loc,
                },
                "suspicion_reasons": suspicion,
                "validation_errors": [],
            }
            if quantity is None and mode == "air":
                activity["validation_errors"] = []
                activity["suspicion_reasons"] = list(
                    set(activity["suspicion_reasons"] + ["No distance — airport pair only"])
                )

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
