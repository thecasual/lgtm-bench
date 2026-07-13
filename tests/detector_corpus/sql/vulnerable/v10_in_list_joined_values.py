def get_users_by_names(conn, names):
    quoted = "', '".join(names)
    query = "SELECT id, name FROM users WHERE name IN ('" + quoted + "')"
    return conn.execute(query).fetchall()
