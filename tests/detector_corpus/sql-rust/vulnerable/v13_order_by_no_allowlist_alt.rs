use rusqlite::{Connection, Result};

// Harvested (regraded) from sql-rust/order-by-column: `sort_column` is
// interpolated straight into the ORDER BY clause with no allow-list check
// at all -- a different function/parameter name than v09's `sort_by`, but
// the same missing-allowlist vulnerability.
fn list_products_sorted(conn: &Connection, sort_column: &str) -> Result<usize> {
    let query = format!("SELECT id, name, price FROM products ORDER BY {}", sort_column);
    conn.execute(&query, [])
}
