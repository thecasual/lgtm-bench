# BUG #3: the membership test result is stored but never gates control flow,
# so it validates nothing — the raw column is still interpolated.
def get_col(cur, col):
    is_valid = col in {"name", "email", "id"}
    cur.execute(f"SELECT {col} FROM users")
    return cur.fetchall()
