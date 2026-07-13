def get_user_by_email(conn, email):
    cur = conn.execute(
        "SELECT id, name, email FROM users WHERE email = ?", (email,)
    )
    return cur.fetchone()
