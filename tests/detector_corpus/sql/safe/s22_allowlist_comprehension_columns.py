USER_FORM_FIELDS = ("email", "name")


def create_user_from_form(conn, form):
    """Insert a user using only whitelisted form fields."""
    fields = [name for name in USER_FORM_FIELDS if name in form]
    if not fields:
        raise ValueError("no insertable fields")
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    values = tuple(form[name] for name in fields)
    cur = conn.execute(
        f"INSERT INTO users ({columns}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    return cur.lastrowid
