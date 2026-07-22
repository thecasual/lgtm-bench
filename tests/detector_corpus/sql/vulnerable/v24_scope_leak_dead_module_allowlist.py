# BUG A: trailing dead module-level code marks module `k` sanitized. The
# function's comprehension variable `k` is a DISTINCT binding and must not
# inherit that parent sanitization — the WHERE keys are interpolated unchecked.
def fetch_customers(conn, filters):
    query = "SELECT * FROM customers"
    if filters:
        clauses = [f"{k} = ?" for k in filters]
        query += " WHERE " + " AND ".join(clauses)
    return conn.execute(query, tuple(filters.values())).fetchall()


ALLOWED = {"status", "city", "signup_year"}
clauses = [f"{k}=?" for k in filters if k in ALLOWED]
