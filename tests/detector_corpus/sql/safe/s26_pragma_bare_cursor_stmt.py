def list_products(conn, sort_by):
    """Order by a column validated against the table's real columns."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(products)")
    valid_columns = {row[1] for row in cursor.fetchall()}
    if sort_by not in valid_columns:
        raise ValueError(f"Invalid column: {sort_by}")
    cursor.execute(f"SELECT * FROM products ORDER BY {sort_by}")
    return cursor.fetchall()
