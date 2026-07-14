use rusqlite::{Connection, Result};

// Untrusted `name` is interpolated straight into the query passed to execute().
fn find_user(conn: &Connection, name: &str) -> Result<usize> {
    conn.execute(
        &format!("SELECT id, name FROM users WHERE name = '{}'", name),
        [],
    )
}
