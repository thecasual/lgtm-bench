def orders_for_status(conn, status):
    cur = conn.execute(
        "SELECT id, status, total FROM orders WHERE status = :status",
        {"status": status},
    )
    return cur.fetchall()
