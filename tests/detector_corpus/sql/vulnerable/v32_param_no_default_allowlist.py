# BUG #6 (vulnerable twin): `allowed_fields` has NO constant default, so it is
# untrusted — the comprehension over it does not produce an allowlist.
def create_user_from_form(conn, form, allowed_fields):
    columns = [f for f in allowed_fields if f in form]
    values = [form[f] for f in columns]
    placeholders = ", ".join(["?"] * len(columns))
    conn.execute(
        f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
