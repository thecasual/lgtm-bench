def recent(conn, limit):
    # str(int(limit)) can only ever be a decimal integer string — no injection.
    return conn.execute(f"SELECT * FROM items ORDER BY id DESC LIMIT {str(int(limit))}").fetchall()
