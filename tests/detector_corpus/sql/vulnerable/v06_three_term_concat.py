def get_user_by_username(conn, username):
    cur = conn.execute(
        "SELECT id, name, email FROM users WHERE username = '" + username + "'"
    )
    return cur.fetchone()
