use rusqlite::{Connection, Result};

// String concatenation with `+` splices `name` into the query.
fn get_account(conn: &Connection, name: &str) -> Result<usize> {
    conn.execute(
        &("SELECT id FROM accounts WHERE name = '".to_string() + name + "'"),
        [],
    )
}
