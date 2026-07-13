ALLOWED_FIELDS = {"email", "name"}


def create_user_from_form(conn, form):
    """Insert only allowlisted fields; keys never come from raw form input."""
    fields = {k: form[k] for k in ALLOWED_FIELDS if k in form}
    if not fields:
        raise ValueError("form contains no insertable user fields")
    columns = ", ".join(fields)
    placeholders = ", ".join("?" * len(fields))
    cur = conn.execute(
        f"INSERT INTO users ({columns}) VALUES ({placeholders})",
        list(fields.values()),
    )
    conn.commit()
    return cur.lastrowid
