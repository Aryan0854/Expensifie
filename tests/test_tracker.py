from __future__ import annotations

from expense_tracker.parser import normalize_merchant_name, parse_sms_transaction
from expense_tracker.tracker import ExpenseTracker


def test_sms_parser_extracts_fields() -> None:
    sms = "HDFC Bank: Rs 522 debited from A/c XXXX at GoodSense Eateries on 21-Feb."
    parsed = parse_sms_transaction(sms)

    assert parsed is not None
    assert parsed.amount == 522
    assert parsed.tx_type == "debit"
    assert parsed.merchant == "GoodSense Eateries"




def test_credit_sms_parser_sender_name() -> None:
    sms = "HDFC Bank: Rs 10000 credited to A/c XXXX from Chitrangi Bhatnagar on 22-Feb."
    parsed = parse_sms_transaction(sms)

    assert parsed is not None
    assert parsed.tx_type == "credit"
    assert parsed.merchant == "Chitrangi Bhatnagar"

def test_merchant_normalization() -> None:
    assert normalize_merchant_name("SWIGGY*BLR") == "Swiggy"
    assert normalize_merchant_name("SWIGGY PAYMENTS") == "Swiggy"


def test_known_merchant_auto_category(tmp_path) -> None:
    tracker = ExpenseTracker(str(tmp_path / "test.db"))
    sms = "HDFC Bank: Rs 522 debited from A/c XXXX at GoodSense Eateries on 21-Feb."

    tx_id = tracker.detect_and_store_sms(sms)
    assert tx_id is not None

    row = tracker.conn.execute("SELECT category FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    assert row[0] == "Food / Eating Out"
    tracker.close()


def test_new_merchant_learning(tmp_path) -> None:
    tracker = ExpenseTracker(str(tmp_path / "test.db"))
    sms = "HDFC Bank: Rs 300 debited from A/c XXXX at New Bistro on 21-Feb."

    tx_id = tracker.detect_and_store_sms(sms, prompt_for_category=lambda _: "Food / Eating Out")
    assert tx_id is not None

    saved = tracker.get_category_for_merchant("New Bistro")
    assert saved == "Food / Eating Out"

    tx_id2 = tracker.detect_and_store_sms(sms)
    row = tracker.conn.execute("SELECT category FROM transactions WHERE id = ?", (tx_id2,)).fetchone()
    assert row[0] == "Food / Eating Out"
    tracker.close()


def test_alerts_and_dashboard(tmp_path) -> None:
    tracker = ExpenseTracker(str(tmp_path / "test.db"))
    tracker.set_budget("Food / Eating Out", 1000)

    for _ in range(3):
        tracker.add_transaction(
            date="2026-02-10",
            merchant="GoodSense Eateries",
            amount=400,
            tx_type="debit",
            category="Food / Eating Out",
            source="manual",
        )

    dashboard = tracker.dashboard("2026-02")
    assert dashboard["monthly_spending"] == 1200

    alerts = tracker.alerts("2026-02", daily_limit=1000)
    assert any("Budget exceeded" in a for a in alerts)
    assert any("Daily spending limit exceeded" in a for a in alerts)
    assert any("Possible subscription detected" in a for a in alerts)
    tracker.close()
