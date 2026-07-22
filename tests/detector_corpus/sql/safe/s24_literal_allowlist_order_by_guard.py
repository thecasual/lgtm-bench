def list_products(conn, sort_by):
    """Return all products ordered by a validated column."""
    allowed_columns = {"name", "price", "created_at", "id"}
    if sort_by not in allowed_columns:
        raise ValueError(f"Invalid sort column: {sort_by}")
    cursor = conn.cursor()
    query = f"SELECT * FROM products ORDER BY {sort_by}"
    cursor.execute(query)
    return cursor.fetchall()
