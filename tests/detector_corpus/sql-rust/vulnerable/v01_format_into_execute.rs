use rusqlite::{Connection, Result};

// get_user interpolates untrusted input into the query with format!.
fn get_user(conn: &Connection, name: &str) -> Result<usize> {
    let query = format!("SELECT id, name FROM users WHERE name = '{}'", name);
    conn.execute(&query, [])
}
