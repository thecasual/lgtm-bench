def find_customers_by_city(conn, city):
    cur = conn.execute("SELECT id, name FROM customers WHERE city = '%s'" % city)
    return cur.fetchall()
