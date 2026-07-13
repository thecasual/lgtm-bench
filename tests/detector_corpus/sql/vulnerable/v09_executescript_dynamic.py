def purge_user(conn, username):
    conn.executescript(
        f"DELETE FROM sessions WHERE user = '{username}';"
        f"DELETE FROM carts WHERE user = '{username}';"
    )
