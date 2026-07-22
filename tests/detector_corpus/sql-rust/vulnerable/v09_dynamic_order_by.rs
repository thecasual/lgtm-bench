use rusqlite::{Connection, Result, Statement};

// Dynamic ORDER BY: the caller-chosen column is interpolated with format!.
fn list_products<'a>(conn: &'a Connection, sort_by: &str) -> Result<Statement<'a>> {
    let sql = format!("SELECT id, name, price FROM products ORDER BY {}", sort_by);
    conn.prepare(&sql)
}
