use rusqlite::{Connection, OptionalExtension, Result};

// Harvested (regraded) from sql-rust/user-lookup-by-email: same two-stage
// prepared-statement idiom as s26, this time going through `.optional()`
// instead of matching `QueryReturnedNoRows` by hand. `email` only ever
// reaches the bind-parameter array `[email]`, never the query text.
struct User {
    id: i32,
    email: String,
}

fn get_user_by_email(conn: &Connection, email: &str) -> Result<Option<User>> {
    let mut stmt = conn.prepare("SELECT id, email FROM users WHERE email = ?")?;

    let user = stmt
        .query_row([email], |row| {
            Ok(User {
                id: row.get(0)?,
                email: row.get(1)?,
            })
        })
        .optional()?;

    Ok(user)
}
