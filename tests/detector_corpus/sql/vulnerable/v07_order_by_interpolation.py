def list_products(conn, sort_col):
    cur = conn.execute(f"SELECT id, name, price FROM products ORDER BY {sort_col}")
    return cur.fetchall()
