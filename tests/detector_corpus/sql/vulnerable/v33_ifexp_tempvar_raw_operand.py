# BUG #11: the conditional expression sanitizes only its RESULT (`safe_col`),
# but the query interpolates the RAW `col`, which was never validated.
def list_products(cur, col):
    safe_col = col if col in ("name", "price") else "name"
    cur.execute(f"SELECT * FROM products ORDER BY {col}")
    return cur.fetchall()
