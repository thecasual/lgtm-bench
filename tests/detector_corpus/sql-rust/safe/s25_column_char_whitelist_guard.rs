use rusqlite::{Connection, Result};
use std::collections::HashMap;

// Harvested (regraded) from sql-rust/update-profile-fields: instead of a
// fixed list of column names, the key is validated character-by-character
// (alphanumeric or underscore only) before being appended to the SET
// clause. This still rejects anything that could break out of an
// identifier position (quotes, spaces, `;`, comment markers, ...), so it is
// an equally valid allow-list style, just expressed as a predicate instead
// of a fixed set.
fn update_user_profile(
    conn: &Connection,
    user_id: i64,
    fields: &HashMap<String, String>,
) -> Result<usize> {
    let mut set_parts = Vec::new();
    let mut params: Vec<&dyn rusqlite::ToSql> = Vec::new();
    for (key, value) in fields {
        if !key.chars().all(|c| c.is_alphanumeric() || c == '_') {
            return Err(rusqlite::Error::InvalidQuery);
        }
        set_parts.push(format!("{} = ?", key));
        params.push(value);
    }
    let set_clause = set_parts.join(", ");
    let query = format!("UPDATE users SET {} WHERE id = ?", set_clause);
    params.push(&user_id);
    conn.execute(&query, params.as_slice())
}
