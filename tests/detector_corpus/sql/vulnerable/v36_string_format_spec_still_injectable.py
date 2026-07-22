def find(conn, name):
    # A string format spec does not sanitize — name flows into SQL verbatim.
    return conn.execute(f"SELECT * FROM users WHERE name = '{name:s}'").fetchall()
