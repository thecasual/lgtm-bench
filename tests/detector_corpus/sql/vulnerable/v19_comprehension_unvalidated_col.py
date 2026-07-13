def fetch_customers(conn, filters):
    query = "SELECT * FROM customers"
    if filters:
        clauses = [f"{col} = ?" for col in filters]
        query += " WHERE " + " AND ".join(clauses)
    return conn.execute(query, tuple(filters.values())).fetchall()
