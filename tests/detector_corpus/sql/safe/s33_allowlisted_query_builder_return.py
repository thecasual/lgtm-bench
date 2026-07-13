# BUG D (safe twin): a returned query builder whose column names are
# allowlist-guarded and whose values are bound parameters — the query string
# skeleton is constant, so returning it must NOT flag.
ALLOWED_FIELDS = {"email", "name", "city"}


def build_update(user_id, updates):
    cols = ", ".join(f"{k} = ?" for k in updates if k in ALLOWED_FIELDS)
    params = [updates[k] for k in updates if k in ALLOWED_FIELDS] + [user_id]
    return f"UPDATE users SET {cols} WHERE id = ?", params
