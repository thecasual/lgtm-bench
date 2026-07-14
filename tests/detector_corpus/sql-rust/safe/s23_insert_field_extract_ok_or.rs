use rusqlite::{params, Connection, Result};
use std::collections::HashMap;

// Harvested (regraded) from sql-rust/insert-from-form: field values are
// pulled out with `.ok_or_else(...)` (erroring on a missing key) instead of
// `.unwrap_or("")`, but still bound as `?1`/`?2` parameters -- never
// interpolated into the query text.
fn create_user_from_form(conn: &Connection, form: &HashMap<String, String>) -> Result<i64> {
    let email = form
        .get("email")
        .ok_or_else(|| rusqlite::Error::InvalidParameterName("email".into()))?;
    let name = form
        .get("name")
        .ok_or_else(|| rusqlite::Error::InvalidParameterName("name".into()))?;

    conn.execute(
        "INSERT INTO users (email, name) VALUES (?1, ?2)",
        params![email, name],
    )?;
    Ok(conn.last_insert_rowid())
}
