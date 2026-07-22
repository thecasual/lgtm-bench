def update_email(conn, user_id, new_email):
    conn.execute(
        "UPDATE users SET email = ? WHERE id = ?", (new_email, user_id)
    )
    conn.commit()
