# BUG D: a helper that BUILDS SQL with tainted column keys and RETURNS the
# query string (plus params) without ever calling execute().
def update_user(user_id, updates):
    cols = ", ".join(f"{k} = :{k}" for k in updates)
    return f"UPDATE users SET {cols} WHERE id = :id", {**updates, "id": user_id}
