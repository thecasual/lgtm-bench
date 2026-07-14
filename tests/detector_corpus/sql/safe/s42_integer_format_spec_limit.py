def page(conn, n):
    # The :d format spec forces integer conversion at format time, so n cannot
    # carry SQL text (format(n, "d") raises for non-integers).
    return conn.execute(f"SELECT * FROM items LIMIT {n:d}").fetchall()
