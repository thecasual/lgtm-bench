use rusqlite::{Connection, Result, Statement};

// A numeric LIMIT interpolated as an integer type -- an `as i64` value cannot
// carry a SQL payload, so this is safe even though format! is used.
fn top_products<'a>(conn: &'a Connection, limit: u32) -> Result<Statement<'a>> {
    let sql = format!("SELECT id, name FROM products ORDER BY id LIMIT {}", limit as i64);
    conn.prepare(&sql)
}
