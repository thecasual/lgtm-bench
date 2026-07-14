use rusqlite::{named_params, Connection, Result};

// rusqlite named parameters (:email) -- bound, not interpolated, safe.
fn get_by_email(conn: &Connection, email: &str) -> Result<usize> {
    conn.execute(
        "SELECT id FROM users WHERE email = :email",
        named_params! { ":email": email },
    )
}
