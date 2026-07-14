use rusqlite::{params_from_iter, Connection, Result};

// Harvested (regraded) from sql-rust/in-list-expansion trials: the query
// text only ever gets "?,?,?" (built from the *count* of ids, never their
// values) interpolated via format!; the actual ids are bound separately via
// params_from_iter. The old search-mode rule flagged this because it sees
// format! feeding a SELECT string -- taint mode sees that no untrusted value
// ever reaches the query text itself.
fn get_orders_by_ids(conn: &Connection, order_ids: &[i64]) -> Result<usize> {
    if order_ids.is_empty() {
        return Ok(0);
    }
    let placeholders = vec!["?"; order_ids.len()].join(",");
    let sql = format!("SELECT id, total FROM orders WHERE id IN ({placeholders})");
    conn.execute(&sql, params_from_iter(order_ids.iter()))
}
