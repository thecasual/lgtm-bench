def find_customers(conn, filters):
    """Filtered lookup building WHERE from an allowlist mapping."""
    allowed = {
        "status": "status",
        "city": "city",
        "signup_year": "signup_year",
    }

    conditions = []
    params = []
    for key, column in allowed.items():
        if key in filters:
            conditions.append(f"{column} = ?")
            params.append(filters[key])

    query = "SELECT * FROM customers"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cursor = conn.execute(query, params)
    return cursor.fetchall()
