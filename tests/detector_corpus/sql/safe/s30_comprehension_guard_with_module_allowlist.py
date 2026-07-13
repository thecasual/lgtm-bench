# BUG A (safe twin): the function's own comprehension is membership-guarded
# against a module allowlist, so its keys are validated. The shadowing fix
# must not break this legitimate in-comprehension allowlist idiom.
ALLOWED = {"status", "city", "signup_year"}


def fetch_customers(conn, filters):
    query = "SELECT * FROM customers"
    if filters:
        clauses = [f"{k} = ?" for k in filters if k in ALLOWED]
        query += " WHERE " + " AND ".join(clauses)
    return conn.execute(query, tuple(filters.values())).fetchall()
