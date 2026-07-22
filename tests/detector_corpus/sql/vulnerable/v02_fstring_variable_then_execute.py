def get_account(conn, account_id):
    query = f"SELECT id, owner, balance FROM accounts WHERE id = {account_id}"
    cur = conn.execute(query)
    return cur.fetchone()
