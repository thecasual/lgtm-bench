def list_events(conn, newest_first):
    direction = "DESC" if newest_first else "ASC"
    query = "SELECT id, name, created_at FROM events ORDER BY created_at " + direction
    return conn.execute(query).fetchall()
