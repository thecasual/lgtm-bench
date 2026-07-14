use rusqlite::{Connection, Result};

// A fully constant query string -- nothing interpolated, safe.
fn all_active(conn: &Connection) -> Result<usize> {
    conn.execute("SELECT id, name FROM users WHERE active = 1", [])
}
