use rusqlite::Connection;
use std::collections::HashMap;

// Same shape as v23, but destructured with a `let Some(...) = ... else {
// ... };` binding instead of `if let`. `tag` is taken straight out of the
// tainted HashMap and interpolated into the query text with no bound
// parameter.
pub fn find_by_tag(conn: &Connection, filters: &HashMap<String, String>) -> rusqlite::Result<usize> {
    let Some(tag) = filters.get("tag") else {
        return Ok(0);
    };
    let sql = format!("SELECT COUNT(*) FROM products WHERE tag = '{}'", tag);
    conn.execute(&sql, [])
}
