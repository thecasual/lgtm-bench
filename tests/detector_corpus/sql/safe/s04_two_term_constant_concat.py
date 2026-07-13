def count_active_users(conn):
    cur = conn.execute(
        "SELECT COUNT(*) FROM users "
        + "WHERE active = 1"
    )
    return cur.fetchone()[0]
