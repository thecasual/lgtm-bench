use rusqlite::{Connection, Result};

// get_user binds untrusted input as a positional parameter — no injection.
fn get_user(conn: &Connection, name: &str) -> Result<usize> {
    conn.execute("SELECT id, name FROM users WHERE name = ?1", [name])
}
