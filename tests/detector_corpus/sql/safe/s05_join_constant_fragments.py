def open_orders(conn):
    query = " ".join(
        [
            "SELECT id, status, total FROM orders",
            "WHERE status = ?",
            "ORDER BY created_at DESC",
        ]
    )
    return conn.execute(query, ("open",)).fetchall()
