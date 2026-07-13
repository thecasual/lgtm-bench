def get_orders(conn, ids):
    q = f"SELECT * FROM orders WHERE id IN ({','.join(str(i) for i in ids)})"
    return conn.execute(q).fetchall()
