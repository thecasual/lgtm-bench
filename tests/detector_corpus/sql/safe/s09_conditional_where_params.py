def find_orders(conn, status=None, min_total=None):
    query = "SELECT id, status, total FROM orders WHERE 1 = 1"
    params = []
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if min_total is not None:
        query += " AND total >= ?"
        params.append(min_total)
    return conn.execute(query, params).fetchall()
