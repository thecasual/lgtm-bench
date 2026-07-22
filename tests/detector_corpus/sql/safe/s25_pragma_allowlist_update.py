def update_user_profile(conn, user_id, fields):
    """Update only the columns named in `fields`, validated against the
    table's real column names (never against untrusted keys)."""
    if not fields:
        return 0
    cursor = conn.execute("PRAGMA table_info(users)")
    allowed = {row[1] for row in cursor.fetchall()}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unknown column(s): {', '.join(sorted(unknown))}")
    set_clause = ", ".join(f"{col} = ?" for col in fields)
    values = list(fields.values()) + [user_id]
    cur = conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    conn.commit()
    return cur.rowcount
