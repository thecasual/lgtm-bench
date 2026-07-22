# BUG #5 (vulnerable twin): the `.keys()` comparator is a USER-supplied mapping,
# not a constant allowlist, so membership against it validates nothing.
def get_col(cur, col, user_dict):
    if col not in user_dict.keys():
        raise ValueError("bad column")
    cur.execute(f"SELECT {col} FROM users")
    return cur.fetchall()
