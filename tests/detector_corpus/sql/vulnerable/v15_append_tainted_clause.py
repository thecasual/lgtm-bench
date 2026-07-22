def search(conn, name, city):
    clauses = []
    if name:
        clauses.append(f"name = '{name}'")
    if city:
        clauses.append(f"city = '{city}'")
    sql = "SELECT * FROM users"
    if clauses:
        sql = sql + " WHERE " + " AND ".join(clauses)
    return conn.execute(sql).fetchall()
