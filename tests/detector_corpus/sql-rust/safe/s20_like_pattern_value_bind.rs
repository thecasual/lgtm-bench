use rusqlite::{Connection, Result};

// Harvested (regraded) from sql-rust/search-products-like: format! is used
// only to wrap the search term in LIKE wildcards ("%{}%"); the result is
// then bound as a query parameter, never spliced into the query text (which
// stays the constant literal "... LIKE ?1"). The old rule's SQL-keyword
// check never matched this format! call anyway, but taint mode confirms it
// structurally: the sink's query-string argument is the literal, not `term`.
fn search_products(conn: &Connection, term: &str) -> Result<usize> {
    let mut stmt = conn.prepare("SELECT id, name, price FROM products WHERE name LIKE ?1")?;
    let pattern = format!("%{}%", term);
    stmt.execute([pattern])
}
