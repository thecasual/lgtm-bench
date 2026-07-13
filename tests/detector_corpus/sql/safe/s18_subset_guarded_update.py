ALLOWED = {"email", "name", "city"}


def update_profile(conn, user_id, fields):
    """Update only the provided profile fields."""
    extra = set(fields) - ALLOWED
    if extra:
        raise ValueError(f"unexpected fields: {extra}")
    assignments = ", ".join(f"{col} = ?" for col in fields)
    values = list(fields.values()) + [user_id]
    conn.execute(f"UPDATE users SET {assignments} WHERE id = ?", values)
    conn.commit()
