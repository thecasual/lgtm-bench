def list_products(conn, sort_by):
    # An allowlist is defined but never actually used to gate the column.
    allowed = {"name", "price", "created_at", "id"}
    query = f"SELECT * FROM products ORDER BY {sort_by}"
    return conn.execute(query).fetchall()
