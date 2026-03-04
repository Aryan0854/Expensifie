from __future__ import annotations

from expense_tracker.constants import CATEGORIES
from expense_tracker.tracker import ExpenseTracker


def ask_category(merchant: str) -> str:
    print(f"\nNew merchant detected: {merchant}")
    print("Please choose a category:")
    for i, c in enumerate(CATEGORIES, start=1):
        print(f"{i}. {c}")

    try:
        idx = int(input("Category number: ").strip()) - 1
    except ValueError:
        idx = -1

    if 0 <= idx < len(CATEGORIES):
        return CATEGORIES[idx]
    return "Other"


def main() -> None:
    tracker = ExpenseTracker()

    sms_samples = [
        "HDFC Bank: Rs 522 debited from A/c XXXX at GoodSense Eateries on 21-Feb.",
        "HDFC Bank: Rs 2450 debited from A/c XXXX at SWIGGY*BLR on 22-Feb.",
        "HDFC Bank: Rs 10000 credited to A/c XXXX from Chitrangi Bhatnagar on 22-Feb.",
    ]

    for sms in sms_samples:
        tx_id = tracker.detect_and_store_sms(sms, prompt_for_category=ask_category)
        print(f"Processed SMS -> transaction id: {tx_id}")

    tracker.set_budget("Food / Eating Out", 5000)

    print("\nDashboard")
    print(tracker.dashboard())

    print("\nInsights")
    print(tracker.spending_insights())

    print("\nAlerts")
    for warning in tracker.alerts():
        print(f"- {warning}")

    tracker.close()


if __name__ == "__main__":
    main()
