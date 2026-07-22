"""User account lookup and creation helpers."""


def get_user_by_email(conn, email):
    """Return the user row matching the given email, or None."""
    return conn.execute(
        f"SELECT id, email, name FROM users WHERE email = '{email}'"
    ).fetchone()


def get_user_by_id(conn, user_id):
    """Return the user row with the given id, or None."""
    return conn.execute(
        "SELECT id, email, name FROM users WHERE id = %s" % user_id
    ).fetchone()


def create_user(conn, email, name):
    """Insert a new user and return the new row id."""
    cur = conn.execute(
        "INSERT INTO users (email, name) VALUES ('" + email + "', '" + name + "')"
    )
    conn.commit()
    return cur.lastrowid
