use rusqlite::{Connection, Result};

// Harvested (regraded) from sql-rust/search-products-like: the term is first
// escaped for LIKE metacharacters, then wrapped in wildcards and bound as a
// parameter. Still safe (and still a format! call whose result never touches
// the query text) even with the extra escaping step in between.
fn escape_like(term: &str) -> String {
    term.replace('\\', "\\\\").replace('%', "\\%").replace('_', "\\_")
}

fn search_products(conn: &Connection, term: &str) -> Result<usize> {
    let mut stmt = conn.prepare("SELECT id, name, price FROM products WHERE name LIKE ?1 ESCAPE '\\'")?;
    let pattern = format!("%{}%", escape_like(term));
    stmt.execute([pattern])
}
