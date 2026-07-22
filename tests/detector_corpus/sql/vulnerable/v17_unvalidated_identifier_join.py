def create_user(conn, form):
    columns = list(form.keys())
    column_list = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT INTO users ({column_list}) VALUES ({placeholders})"
    cur = conn.execute(sql, [form[c] for c in columns])
    conn.commit()
    return cur.lastrowid
