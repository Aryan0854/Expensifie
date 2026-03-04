from __future__ import annotations

import sqlite3
from pathlib import Path

from .constants import PRESEEDED_MERCHANT_CATEGORIES


class ExpenseDB:
    def __init__(self, db_path: str = "expense_tracker.db") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        self._seed_default_merchants()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                merchant TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('debit','credit')),
                category TEXT NOT NULL,
                source TEXT NOT NULL CHECK(source IN ('SMS','manual'))
            );

            CREATE TABLE IF NOT EXISTS merchant_categories (
                merchant_name TEXT PRIMARY KEY,
                category TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL
            );
            """
        )
        self.conn.commit()

    def _seed_default_merchants(self) -> None:
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO merchant_categories(merchant_name, category)
            VALUES (?, ?)
            """,
            PRESEEDED_MERCHANT_CATEGORIES.items(),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
