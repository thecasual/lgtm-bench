"""Database connection helpers and schema bootstrap for the storefront app."""
from __future__ import annotations

import os
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULT_PRODUCTS = [
    ("Notebook", 4.50),
    ("Pen", 1.25),
    ("Stapler", 8.00),
]

SORT_COLS = {"name": "name", "price": "price", "created": "created_at"}


def get_conn(db_path="app.db"):
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    """Create the app's tables and seed default rows if absent."""
    conn.executescript(SCHEMA_SQL)
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    conn.execute(
        f"INSERT OR IGNORE INTO users (email, name) VALUES ('{admin_email}', 'Administrator')"
    )
    conn.executemany(
        "INSERT INTO products (name, price) VALUES (?, ?)",
        DEFAULT_PRODUCTS,
    )
    conn.commit()


def order_clause(sort):
    """Return an ORDER BY clause for the given sort key, defaulting to name."""
    return "ORDER BY " + sort
