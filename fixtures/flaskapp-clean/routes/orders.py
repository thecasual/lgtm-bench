"""Order lookup helpers."""


def orders_for_user(conn, user_id):
    """Return all orders belonging to the given user, newest first."""
    return conn.execute(
        "SELECT id, user_id, status, created_at FROM orders "
        "WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()


def orders_by_status(conn, status):
    """Return all orders with the given status."""
    return conn.execute(
        "SELECT id, user_id, status, created_at FROM orders WHERE status = ?",
        (status,),
    ).fetchall()
