use rusqlite::{Connection, Result};

// A string-valued sibling of the (safe) integer id-list expansion: because
// the values are strings, not integers, quoting them by hand instead of
// binding them lets a tag containing a quote break out of the IN (...)
// list. Contrast with s13/s14, which only ever put the literal "?"
// placeholder character into the query text.
fn find_by_tags(conn: &Connection, tags: &[String]) -> Result<usize> {
    let quoted: Vec<String> = tags.iter().map(|t| format!("'{}'", t)).collect();
    let joined = quoted.join(",");
    let sql = format!("SELECT id FROM products WHERE tag IN ({})", joined);
    conn.execute(&sql, [])
}
