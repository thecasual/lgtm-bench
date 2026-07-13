# BUG C: the conditional guards `direction` but interpolates `sort_col` in
# BOTH branches — the membership test validates the wrong operand.
def list_products(conn, sort_col, direction):
    query = f"SELECT * FROM products ORDER BY {sort_col if direction in ('ASC', 'DESC') else sort_col}"
    return conn.execute(query).fetchall()
