use rusqlite::{Connection, Result};

// Harvested (regraded) from sql-rust/search-products-like: unlike s20/s21,
// the wildcarded pattern here is spliced directly into the query text
// itself (not bound as a parameter), so a term containing a quote breaks
// out of the LIKE literal.
fn search_products(conn: &Connection, term: &str) -> Result<usize> {
    let sql = format!("SELECT id, name FROM products WHERE name LIKE '%{}%'", term);
    conn.execute(&sql, [])
}
