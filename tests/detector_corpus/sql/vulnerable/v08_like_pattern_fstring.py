def search_products(conn, term):
    cur = conn.execute(f"SELECT id, name FROM products WHERE name LIKE '%{term}%'")
    return cur.fetchall()
