def list_products(conn, sort_by, direction="ASC"):
    """Order by a validated column and direction."""
    allowed_columns = {"id", "name", "price", "created_at"}
    allowed_directions = {"ASC", "DESC"}
    if sort_by not in allowed_columns:
        raise ValueError("bad column")
    if direction.upper() not in allowed_directions:
        raise ValueError("bad direction")
    query = f"SELECT * FROM products ORDER BY {sort_by} {direction}"
    return conn.execute(query).fetchall()
