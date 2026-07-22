use rusqlite::{Connection, Result};

// Dynamic WHERE built with format! and executed via query_map.
fn find_ids(conn: &Connection, city: &str) -> Result<Vec<i64>> {
    let sql = format!("SELECT id FROM customers WHERE city = '{}'", city);
    let mut stmt = conn.prepare(&sql)?;
    let ids = stmt
        .query_map([], |row| row.get(0))?
        .collect::<Result<Vec<i64>>>()?;
    Ok(ids)
}
