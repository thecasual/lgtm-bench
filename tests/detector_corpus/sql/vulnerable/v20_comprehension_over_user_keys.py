def create_user(conn, form):
    fields = [k for k in form.keys()]
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    conn.execute(
        f"INSERT INTO users ({columns}) VALUES ({placeholders})",
        list(form.values()),
    )
