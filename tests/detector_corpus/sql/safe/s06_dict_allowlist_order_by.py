SORT_COLS = {"name": "name", "price": "price", "created": "created_at"}


def list_products(conn, sort):
    order_col = SORT_COLS[sort]
    query = "SELECT id, name, price FROM products ORDER BY " + order_col
    return conn.execute(query).fetchall()
