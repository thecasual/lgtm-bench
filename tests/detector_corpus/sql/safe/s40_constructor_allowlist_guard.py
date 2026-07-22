# BUG #12 (safe twin): the allowlist is built with a constructor wrapping a
# literal collection (`set((...))`); a reject-branch guard against it validates
# the column even though the name is not ALLCAPS.
def get_col(cur, col):
    allowed = set(("name", "email", "id"))
    if col not in allowed:
        raise ValueError("bad column")
    cur.execute(f"SELECT {col} FROM users")
    return cur.fetchall()
