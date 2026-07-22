use rusqlite::{params, Connection, Result};

// Same two-stage idiom as s26/s27, but binding through the `params![...]`
// macro instead of a bare array literal, and using `query_map` (a list
// query) instead of `query_row` (a single-row lookup). Still safe: `user_id`
// only ever reaches the bind-parameter position.
pub fn list_orders_for_user(conn: &Connection, user_id: &str) -> Result<Vec<i64>> {
    let mut stmt = conn.prepare("SELECT order_id FROM orders WHERE user_id = ?1")?;
    let rows = stmt.query_map(params![user_id], |row| row.get(0))?;
    rows.collect()
}
