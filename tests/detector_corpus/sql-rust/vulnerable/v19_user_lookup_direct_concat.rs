use rusqlite::{Connection, Result};

// Harvested (regraded) from sql-rust/user-lookup-by-email: the email is
// interpolated straight into the query text with format! instead of being
// bound as ?1 -- the exact "user-derived string interpolated directly into
// the query, no parameter binding" shape the taint rule targets.
fn get_user_by_email(conn: &Connection, email: &str) -> Result<usize> {
    let sql = format!("SELECT id, name FROM users WHERE email = '{}'", email);
    conn.execute(&sql, [])
}
