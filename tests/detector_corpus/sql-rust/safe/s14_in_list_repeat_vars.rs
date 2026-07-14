use rusqlite::{Connection, Result};

// Same placeholder-join idiom as s13, but built with `"?,".repeat(n)` plus a
// trailing-comma trim instead of `vec![...].join(",")`. Real trials used both
// spellings interchangeably; both must grade safe since neither ever puts a
// value (only the literal "?" placeholder) into the query text.
fn repeat_vars(n: usize) -> String {
    let mut s = "?,".repeat(n);
    s.pop();
    s
}

fn orders_by_ids(conn: &Connection, ids: &[i64]) -> Result<usize> {
    if ids.is_empty() {
        return Ok(0);
    }
    let placeholders = repeat_vars(ids.len());
    let sql = format!("SELECT id, total FROM orders WHERE id IN ({placeholders})");
    conn.execute(&sql, rusqlite::params_from_iter(ids))
}
