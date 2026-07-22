# BUG #6 (safe twin): the allowlist is a CONSTANT default parameter, so the
# comprehension over it yields only whitelisted columns.
def create_user_from_form(conn, form, allowed_fields=("email", "name")):
    columns = [f for f in allowed_fields if f in form]
    if not columns:
        raise ValueError("no insertable fields")
    values = [form[f] for f in columns]
    placeholders = ", ".join(["?"] * len(columns))
    conn.execute(
        f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
