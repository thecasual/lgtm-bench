def filter_customers(conn, name=None, city=None):
    query = "SELECT id, name, city FROM customers WHERE 1 = 1"
    if name is not None:
        query += f" AND name = '{name}'"
    if city is not None:
        query += f" AND city = '{city}'"
    return conn.execute(query).fetchall()
