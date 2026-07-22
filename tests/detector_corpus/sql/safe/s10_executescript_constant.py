SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
"""


def init_db(conn):
    conn.executescript(SCHEMA)
