use rusqlite::{Connection, Result};

// Query assembled with push_str; the untrusted `email` is appended verbatim.
fn count_by_email(conn: &Connection, email: &str) -> Result<usize> {
    let mut query = String::from("SELECT COUNT(*) FROM users WHERE email = '");
    query.push_str(email);
    query.push_str("'");
    conn.execute(&query, [])
}
