def update_profile(conn, user_id, fields):
    assignments = ", ".join(f"{col} = '{val}'" for col, val in fields.items())
    conn.execute(f"UPDATE users SET {assignments} WHERE id = {user_id}")
    conn.commit()
