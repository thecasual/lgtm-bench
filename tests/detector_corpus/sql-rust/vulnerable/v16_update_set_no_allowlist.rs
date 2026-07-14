use rusqlite::{Connection, Result};
use std::collections::HashMap;

// Harvested (regraded) from sql-rust/update-profile-fields: both the column
// name *and* the value come straight from the caller-supplied HashMap with
// no allow-list check and no parameter binding -- everything is spliced
// into the SET clause with format!/push_str.
fn update_user_profile(
    conn: &Connection,
    user_id: i64,
    fields: &HashMap<String, String>,
) -> Result<usize> {
    let mut sql = String::from("UPDATE users SET ");
    for (column, value) in fields {
        sql.push_str(&format!("{} = '{}', ", column, value));
    }
    sql.push_str("updated_at = CURRENT_TIMESTAMP WHERE id = ");
    sql.push_str(&user_id.to_string());
    conn.execute(&sql, [])
}
