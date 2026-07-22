def get_user(conn, user_id):
    cur = conn.execute("SELECT id, name FROM users WHERE id = " + user_id)
    return cur.fetchone()
