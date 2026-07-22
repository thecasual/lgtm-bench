def fetch_by_ids(conn, ids):
    """Fetch rows for a list of ids."""
    placeholders = ", ".join(["?"] * len(ids))
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id IN ({placeholders})", list(ids))
    return cur.fetchall()
