# The surviving (last) definition is the vulnerable one — still counts.
def get_user(conn, name):
    return conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()


def get_user(conn, name):
    return conn.execute(f"SELECT * FROM users WHERE name = '{name}'").fetchone()
