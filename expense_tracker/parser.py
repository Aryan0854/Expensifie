from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from .constants import MERCHANT_NORMALIZATION


@dataclass
class ParsedTransaction:
    merchant: str
    amount: float
    date: str
    tx_type: str


SMS_PATTERNS = [
    re.compile(
        r"Rs\.?\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*(?P<type>debited|credited).*?(?:at|to|from)\s*(?P<merchant>[A-Za-z0-9*\-&\s.]+?)\s*on\s*(?P<date>\d{1,2}[-/][A-Za-z]{3}(?:[-/]\d{2,4})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<type>debited|credited)\s*INR\s*(?P<amount>[\d,]+(?:\.\d{1,2})?).*?(?:to|at|from)\s*(?P<merchant>[A-Za-z0-9*\-&\s.]+?)\s*on\s*(?P<date>\d{1,2}[-/][A-Za-z]{3}(?:[-/]\d{2,4})?)",
        re.IGNORECASE,
    ),
]


def normalize_merchant_name(raw_name: str) -> str:
    candidate = " ".join(raw_name.strip().split())
    upper = candidate.upper()

    for key, normalized in MERCHANT_NORMALIZATION.items():
        if key.endswith("*") and upper.startswith(key[:-1]):
            return normalized
        if key == upper:
            return normalized

    return candidate


def parse_sms_transaction(sms_text: str) -> ParsedTransaction | None:
    for pattern in SMS_PATTERNS:
        match = pattern.search(sms_text)
        if not match:
            continue

        amount = float(match.group("amount").replace(",", ""))
        tx_type = "debit" if match.group("type").lower().startswith("debit") else "credit"
        merchant = normalize_merchant_name(match.group("merchant"))
        raw_date = match.group("date")

        date = _normalize_date(raw_date)
        return ParsedTransaction(merchant=merchant, amount=amount, date=date, tx_type=tx_type)

    return None


def _normalize_date(raw_date: str) -> str:
    clean = raw_date.replace("/", "-")
    parts = clean.split("-")

    if len(parts) == 2:
        clean = f"{parts[0]}-{parts[1]}-{datetime.now().year}"

    for fmt in ("%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return datetime.now().strftime("%Y-%m-%d")
