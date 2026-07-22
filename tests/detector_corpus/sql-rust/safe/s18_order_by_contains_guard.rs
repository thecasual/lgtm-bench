use rusqlite::{Connection, Error, Result};

// Harvested (regraded) from sql-rust/order-by-column: instead of remapping
// `sort_by` through a `match`, this variant validates it against a fixed
// allow-list with `.contains()` and returns an error on anything else,
// *then* interpolates the same (now-guaranteed-safe) value. Functionally
// identical to the match idiom -- column identifiers can't be bound, so the
// allow-list check is what keeps the interpolation below safe.
fn list_products(conn: &Connection, sort_by: &str) -> Result<usize> {
    let allowed_columns = ["id", "name", "price", "created_at"];
    if !allowed_columns.contains(&sort_by) {
        return Err(Error::InvalidParameterName(format!(
            "invalid sort column: {sort_by}"
        )));
    }
    let query = format!("SELECT id, name, price, created_at FROM products ORDER BY {sort_by}");
    conn.execute(&query, [])
}
