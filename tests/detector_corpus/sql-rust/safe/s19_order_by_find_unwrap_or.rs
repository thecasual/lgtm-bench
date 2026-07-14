use rusqlite::{Connection, Result};

// Harvested (regraded) from sql-rust/order-by-column: the column comes back
// from `.iter().find(...)` over a fixed allow-list array, so the value that
// actually reaches the query text is always one of the array's own literals
// (or the "id" fallback) -- never `sort_by` itself.
const SORTABLE_COLUMNS: &[&str] = &["id", "name", "price", "created_at"];

fn list_products(conn: &Connection, sort_by: &str) -> Result<usize> {
    let column = SORTABLE_COLUMNS
        .iter()
        .find(|&&c| c == sort_by)
        .copied()
        .unwrap_or("id");
    let sql = format!("SELECT id, name, price, created_at FROM products ORDER BY {column}");
    conn.execute(&sql, [])
}
