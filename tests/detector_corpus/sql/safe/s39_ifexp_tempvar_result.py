# BUG #11 (safe twin): the query interpolates the guarded RESULT of the
# conditional expression (`safe_col`), every value of which is allowlisted.
def list_products(cur, col):
    safe_col = col if col in ("name", "price") else "name"
    cur.execute(f"SELECT * FROM products ORDER BY {safe_col}")
    return cur.fetchall()
