def list_users(conn, col):
    if col not in {"name", "email", "created_at"}:
        raise ValueError("unsupported sort column")
    cur = conn.execute(f"SELECT id, name, email FROM users ORDER BY {col}")
    return cur.fetchall()
