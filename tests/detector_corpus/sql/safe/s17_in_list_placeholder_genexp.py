def fetch_by_ids(conn, ids):
    """Fetch rows for a list of ids."""
    marks = ", ".join("?" for _ in ids)
    sql = f"SELECT id, email FROM users WHERE id IN ({marks})"
    return conn.execute(sql, tuple(ids)).fetchall()
