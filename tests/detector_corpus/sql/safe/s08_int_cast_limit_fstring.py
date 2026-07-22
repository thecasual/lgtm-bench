def recent_items(conn, limit):
    cur = conn.execute(
        f"SELECT id, title FROM items ORDER BY id DESC LIMIT {int(limit)}"
    )
    return cur.fetchall()
