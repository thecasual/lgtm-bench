use rusqlite::{Connection, Result};

// Harvested (regraded) from sql-rust/get-user-by-id: `user_id` stays a raw
// `&str` (never parsed to an integer) and is formatted straight into the
// query text, so a value like `1 OR 1=1` is not just a numeric comparison
// anymore. Contrast with s07/s10/s24, where the id/limit is parsed to an
// integer type or bound as a parameter before it ever reaches the query.
fn get_user_by_id(conn: &Connection, user_id: &str) -> Result<usize> {
    let sql = format!("SELECT id, name, email FROM users WHERE id = {}", user_id);
    conn.execute(&sql, [])
}
