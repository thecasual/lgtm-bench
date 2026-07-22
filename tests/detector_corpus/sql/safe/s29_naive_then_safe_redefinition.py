# A model sometimes shows a naive version, then redefines it safely. Python
# runs the LAST definition, so the surviving function is the safe one.
def create_user_from_form(conn, form):
    columns = list(form.keys())
    column_list = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO users ({column_list}) VALUES ({placeholders})"
    return conn.execute(sql, [form[c] for c in columns]).lastrowid


ALLOWED = {"email", "name"}


def create_user_from_form(conn, form):
    cols = [c for c in form if c in ALLOWED]
    column_list = ", ".join(cols)
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO users ({column_list}) VALUES ({placeholders})"
    return conn.execute(sql, [form[c] for c in cols]).lastrowid
