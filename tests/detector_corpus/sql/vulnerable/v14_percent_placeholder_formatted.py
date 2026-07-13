def get_user_by_name(conn, name):
    # Looks like a DB-API placeholder, but the string is %-formatted in Python
    # before it ever reaches the driver.
    query = "SELECT id, name, email FROM users WHERE name = %s" % name
    return conn.execute(query).fetchone()
