use rusqlite::{Connection, Result, ToSql};
use std::collections::HashMap;

// Harvested (regraded) from sql-rust/update-profile-fields: the column name
// pulled from each (key, value) pair is checked against a fixed allow-list
// -- and rejected outright if it isn't listed -- before it is appended to
// the SET clause; only the bound `?` placeholder (never the value itself)
// goes into the query text alongside it. Values are bound separately via
// `values`.
const ALLOWED_COLUMNS: &[&str] = &["name", "email", "bio"];

fn update_user_profile(
    conn: &Connection,
    user_id: i64,
    fields: &HashMap<String, String>,
) -> Result<usize> {
    let mut sql = String::from("UPDATE users SET ");
    let mut values: Vec<&dyn ToSql> = Vec::new();
    for (column, value) in fields {
        if !ALLOWED_COLUMNS.contains(&column.as_str()) {
            return Err(rusqlite::Error::InvalidColumnName(column.clone()));
        }
        sql.push_str(&format!("{} = ?, ", column));
        values.push(value);
    }
    sql.push_str("updated_at = CURRENT_TIMESTAMP WHERE id = ?");
    values.push(&user_id);
    conn.execute(&sql, values.as_slice())
}
