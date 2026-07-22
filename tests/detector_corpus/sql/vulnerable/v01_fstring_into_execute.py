def get_user_by_email(conn, email):
    cur = conn.execute(f"SELECT id, name, email FROM users WHERE email = '{email}'")
    return cur.fetchone()
