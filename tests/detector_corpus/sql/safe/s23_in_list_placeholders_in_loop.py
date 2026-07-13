def get_orders_by_ids(conn, order_ids, chunk_size=900):
    """Fetch orders by id, chunked to stay under the parameter limit."""
    rows = []
    for i in range(0, len(order_ids), chunk_size):
        chunk = order_ids[i:i + chunk_size]
        placeholders = ",".join("?" * len(chunk))
        query = f"SELECT * FROM orders WHERE id IN ({placeholders})"
        rows.extend(conn.execute(query, list(chunk)).fetchall())
    return rows
