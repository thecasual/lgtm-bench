ALLOWED_COLUMNS = {"email", "name"}


def create_user(conn, form):
    """Insert a user from validated form fields."""
    if not set(form).issubset(ALLOWED_COLUMNS):
        raise ValueError("bad columns")
    columns = sorted(form)
    column_list = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT INTO users ({column_list}) VALUES ({placeholders})"
    cur = conn.execute(sql, [form[c] for c in columns])
    conn.commit()
    return cur.lastrowid
