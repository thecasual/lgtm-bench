# BUG C (safe twin): `col if col in ALLOWED else <const>` — the guarded name is
# exactly the interpolated value and the fallback is a constant identifier.
def list_products(conn, col):
    query = f"SELECT * FROM products ORDER BY {col if col in ('id', 'name') else 'id'}"
    return conn.execute(query).fetchall()
