# BUG #5 (safe twin): the reject-branch comparator is `ALLOWED.keys()` over a
# constant mapping — a recognized allowlist view, so the column is validated.
ALLOWED = {"name": "users.name", "email": "users.email", "id": "users.id"}


def get_col(cur, col):
    if col not in ALLOWED.keys():
        raise ValueError("bad column")
    cur.execute(f"SELECT {col} FROM users")
    return cur.fetchall()
