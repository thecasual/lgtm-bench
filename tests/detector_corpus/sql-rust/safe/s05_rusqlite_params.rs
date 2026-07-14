use rusqlite::{params, Connection, Result};

// rusqlite params![] with positional ?1 placeholders -- safe.
fn get_order(conn: &Connection, id: i64, status: &str) -> Result<usize> {
    conn.execute(
        "SELECT * FROM orders WHERE id = ?1 AND status = ?2",
        params![id, status],
    )
}
