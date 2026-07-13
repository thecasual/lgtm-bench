USER_BY_EMAIL = "SELECT id, name, email FROM users WHERE email = ?"


def get_user_by_email(conn, email):
    cur = conn.execute(USER_BY_EMAIL, (email,))
    return cur.fetchone()
