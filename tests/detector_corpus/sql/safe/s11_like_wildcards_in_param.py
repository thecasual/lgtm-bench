def search_users(conn, term):
    pattern = "%" + term + "%"
    cur = conn.execute(
        "SELECT id, name, email FROM users WHERE name LIKE ?", (pattern,)
    )
    return cur.fetchall()
