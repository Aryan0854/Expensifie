# Personal Expense Tracker

A Python-based personal finance tracker that ingests bank SMS-style text, auto-detects transaction details, auto-categorizes known merchants, and learns categories for new merchants.

## Features Implemented

- SMS transaction detection and extraction:
  - amount
  - debit/credit type
  - merchant
  - date
- Pre-seeded merchant-to-category mapping (from your provided history).
- Auto-categorization for known merchants.
- One-time prompt flow for unknown merchants, then merchant learning.
- Transaction storage in SQLite with fields:
  - `id, date, merchant, amount, type, category, source`
- Manual category correction support.
- Insights:
  - total spent
  - category-wise spending
  - monthly trend
  - biggest transactions
- Alerts:
  - budget nearing/exceeded
  - daily spending limit exceeded
  - subscription-like repeated merchant detection
- Dashboard summary:
  - total balance (credits - debits)
  - monthly spending
  - category breakdown
  - recent transactions
- Merchant normalization support (e.g. SWIGGY variants).

## Project Structure

- `expense_tracker/constants.py` – categories, seeded mappings, normalization rules
- `expense_tracker/db.py` – SQLite schema + seed logic
- `expense_tracker/parser.py` – SMS parsing + merchant normalization
- `expense_tracker/tracker.py` – core app services and analytics
- `app.py` – runnable demo CLI
- `tests/test_tracker.py` – unit tests

## Run demo

```bash
python app.py
```

## Run tests

```bash
pytest -q
```

## Notes

This implementation is intentionally backend-first and framework-agnostic so you can attach a Flutter/React Native UI later while preserving core logic.
