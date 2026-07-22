# BUG #4: a `not in FORBIDDEN` comprehension filter is a blocklist; the
# surviving columns are still attacker-controlled and joined into the query.
FORBIDDEN = {"password", "ssn"}


def select_columns(cur, user_cols):
    cols = [c for c in user_cols if c not in FORBIDDEN]
    cur.execute(f"SELECT {', '.join(cols)} FROM accounts")
    return cur.fetchall()
