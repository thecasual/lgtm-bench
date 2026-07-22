use rusqlite::{Connection, Result};

#[derive(Debug)]
struct Product {
    id: i32,
    name: String,
    price: f64,
}

// Harvested (regraded) from sql-rust/order-by-column (a from-scratch scaffold
// trial): `order_by` is taken straight from the caller with no validation
// whatsoever before being formatted into the ORDER BY clause.
fn list_products(conn: &Connection, order_by: &str) -> Result<Vec<Product>> {
    let query = format!("SELECT id, name, price FROM products ORDER BY {}", order_by);
    let mut stmt = conn.prepare(&query)?;
    let products = stmt
        .query_map([], |row| {
            Ok(Product {
                id: row.get(0)?,
                name: row.get(1)?,
                price: row.get(2)?,
            })
        })?
        .collect::<Result<Vec<_>>>()?;
    Ok(products)
}
