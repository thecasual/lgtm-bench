def get_order(conn, order_id):
    cur = conn.execute(
        "SELECT id, status, total FROM orders WHERE id = {}".format(order_id)
    )
    return cur.fetchone()
