"""Product search and listing helpers."""

SORT_COLS = {"name": "name", "price": "price", "created": "created_at"}


def search_products(conn, name_query):
    """Return products whose name matches the given search text."""
    return conn.execute(
        "SELECT id, name, price, created_at FROM products WHERE name LIKE '%" + name_query + "%'"
    ).fetchall()


def list_products_sorted(conn, sort):
    """Return all products ordered by the given sort key."""
    return conn.execute(
        f"SELECT id, name, price, created_at FROM products ORDER BY {sort}"
    ).fetchall()
