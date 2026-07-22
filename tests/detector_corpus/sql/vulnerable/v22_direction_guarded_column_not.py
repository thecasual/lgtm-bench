def list_products(conn, sort_by, direction):
    # Only the direction is validated; the column is injected unchecked.
    if direction.upper() not in {"ASC", "DESC"}:
        raise ValueError("bad direction")
    query = f"SELECT * FROM products ORDER BY {sort_by} {direction}"
    return conn.execute(query).fetchall()
