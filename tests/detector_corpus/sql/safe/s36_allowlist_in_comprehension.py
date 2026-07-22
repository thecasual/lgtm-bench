# BUG #4 (safe twin): a POSITIVE `in ALLOW` comprehension filter is an
# allowlist, so only validated columns survive to be joined into the query.
ALLOW = {"id", "name", "email"}


def select_columns(cur, user_cols):
    cols = [c for c in user_cols if c in ALLOW]
    cur.execute(f"SELECT {', '.join(cols)} FROM accounts")
    return cur.fetchall()
