def get_orders(conn, ids):
    """Fetch orders whose id is in the given list."""
    q = f"SELECT * FROM orders WHERE id IN ({','.join('?' * len(ids))})"
    return conn.execute(q, list(ids)).fetchall()
