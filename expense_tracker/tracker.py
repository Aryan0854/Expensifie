from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Callable

from .constants import CATEGORIES
from .db import ExpenseDB
from .parser import parse_sms_transaction


class ExpenseTracker:
    def __init__(self, db_path: str = "expense_tracker.db") -> None:
        self.db = ExpenseDB(db_path)

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.conn

    def detect_and_store_sms(
        self,
        sms_text: str,
        prompt_for_category: Callable[[str], str] | None = None,
    ) -> int | None:
        parsed = parse_sms_transaction(sms_text)
        if not parsed:
            return None

        category = self.get_category_for_merchant(parsed.merchant)
        if not category:
            if prompt_for_category is None:
                category = "Other"
            else:
                category = prompt_for_category(parsed.merchant)
            self.set_merchant_category(parsed.merchant, category)

        return self.add_transaction(
            date=parsed.date,
            merchant=parsed.merchant,
            amount=parsed.amount,
            tx_type=parsed.tx_type,
            category=category,
            source="SMS",
        )

    def add_transaction(
        self,
        date: str,
        merchant: str,
        amount: float,
        tx_type: str,
        category: str,
        source: str = "manual",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO transactions(date, merchant, amount, type, category, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (date, merchant, amount, tx_type, category, source),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_category_for_merchant(self, merchant: str) -> str | None:
        row = self.conn.execute(
            "SELECT category FROM merchant_categories WHERE merchant_name = ?", (merchant,)
        ).fetchone()
        return row[0] if row else None

    def set_merchant_category(self, merchant: str, category: str) -> None:
        if category not in CATEGORIES:
            category = "Other"
        self.conn.execute(
            """
            INSERT INTO merchant_categories(merchant_name, category)
            VALUES (?, ?)
            ON CONFLICT(merchant_name) DO UPDATE SET category=excluded.category
            """,
            (merchant, category),
        )
        self.conn.commit()

    def update_transaction_category(self, transaction_id: int, category: str) -> None:
        self.conn.execute("UPDATE transactions SET category = ? WHERE id = ?", (category, transaction_id))
        self.conn.commit()

    def set_budget(self, category: str, monthly_limit: float) -> None:
        self.conn.execute(
            """
            INSERT INTO budgets(category, monthly_limit)
            VALUES (?, ?)
            ON CONFLICT(category) DO UPDATE SET monthly_limit=excluded.monthly_limit
            """,
            (category, monthly_limit),
        )
        self.conn.commit()

    def spending_insights(self, month: str | None = None) -> dict:
        if month is None:
            month = datetime.now().strftime("%Y-%m")

        rows = self.conn.execute(
            """
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE type='debit' AND date LIKE ?
            GROUP BY category
            """,
            (f"{month}%",),
        ).fetchall()

        total = sum(float(r[1]) for r in rows)
        by_category = {r[0]: float(r[1]) for r in rows}

        largest = self.conn.execute(
            """
            SELECT id, date, merchant, amount, category
            FROM transactions
            WHERE type='debit' AND date LIKE ?
            ORDER BY amount DESC LIMIT 5
            """,
            (f"{month}%",),
        ).fetchall()

        return {
            "month": month,
            "total_spent": total,
            "by_category": by_category,
            "largest_transactions": [dict(r) for r in largest],
            "monthly_trend": self._monthly_trend(),
        }

    def _monthly_trend(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT substr(date, 1, 7) as month, SUM(amount) as total
            FROM transactions
            WHERE type='debit'
            GROUP BY substr(date, 1, 7)
            ORDER BY month
            """
        ).fetchall()
        return [{"month": r[0], "spent": float(r[1])} for r in rows]

    def alerts(self, month: str | None = None, daily_limit: float = 2000) -> list[str]:
        if month is None:
            month = datetime.now().strftime("%Y-%m")

        warnings: list[str] = []

        budget_rows = self.conn.execute(
            """
            SELECT b.category, b.monthly_limit, COALESCE(SUM(t.amount), 0) as spent
            FROM budgets b
            LEFT JOIN transactions t
              ON t.category=b.category AND t.type='debit' AND t.date LIKE ?
            GROUP BY b.category, b.monthly_limit
            """,
            (f"{month}%",),
        ).fetchall()

        for row in budget_rows:
            spent = float(row[2])
            limit = float(row[1])
            if spent >= limit:
                warnings.append(f"Budget exceeded for {row[0]}: {spent:.2f}/{limit:.2f}")
            elif spent >= 0.8 * limit:
                warnings.append(f"Budget nearing limit for {row[0]}: {spent:.2f}/{limit:.2f}")

        daily_rows = self.conn.execute(
            """
            SELECT date, SUM(amount) AS spent
            FROM transactions
            WHERE type='debit' AND date LIKE ?
            GROUP BY date
            HAVING spent > ?
            """,
            (f"{month}%", daily_limit),
        ).fetchall()
        for row in daily_rows:
            warnings.append(f"Daily spending limit exceeded on {row[0]}: {row[1]:.2f}")

        subscriptions = self._detect_subscriptions()
        warnings.extend(subscriptions)

        return warnings

    def _detect_subscriptions(self) -> list[str]:
        rows = self.conn.execute(
            """
            SELECT merchant, COUNT(*) as tx_count
            FROM transactions
            WHERE type='debit'
            GROUP BY merchant
            HAVING tx_count >= 3
            """
        ).fetchall()
        return [f"Possible subscription detected: {r[0]} ({r[1]} payments)" for r in rows]

    def dashboard(self, month: str | None = None) -> dict:
        insights = self.spending_insights(month)

        credit = self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='credit'"
        ).fetchone()[0]
        debit = self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='debit'"
        ).fetchone()[0]
        balance = float(credit) - float(debit)

        recent = self.conn.execute(
            """
            SELECT id, date, merchant, amount, type, category, source
            FROM transactions
            ORDER BY date DESC, id DESC
            LIMIT 10
            """
        ).fetchall()

        return {
            "total_balance": balance,
            "monthly_spending": insights["total_spent"],
            "category_breakdown": insights["by_category"],
            "recent_transactions": [dict(r) for r in recent],
        }

    def close(self) -> None:
        self.db.close()
