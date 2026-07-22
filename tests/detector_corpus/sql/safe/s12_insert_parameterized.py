def create_user(conn, form):
    conn.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        (form["name"], form["email"]),
    )
    conn.commit()
