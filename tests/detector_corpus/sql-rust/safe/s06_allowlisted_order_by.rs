use rusqlite::{Connection, Result, Statement};

// Dynamic sort resolved through an allowlist `match` -> a *constant* query
// string per branch. The user's string never reaches the SQL text.
fn list_products<'a>(conn: &'a Connection, sort_by: &str) -> Result<Statement<'a>> {
    let query = match sort_by {
        "name" => "SELECT id, name, price FROM products ORDER BY name",
        "price" => "SELECT id, name, price FROM products ORDER BY price",
        _ => "SELECT id, name, price FROM products ORDER BY created_at",
    };
    conn.prepare(query)
}
