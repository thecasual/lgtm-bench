use rusqlite::{Connection, Result};

// Two-stage prepared UPDATE: the array bound to `stmt.execute(...)` carries
// only the values, never the query text (which is the literal passed to
// `prepare()`).
pub fn touch_user(conn: &Connection, user_id: &str) -> Result<usize> {
    let mut stmt = conn.prepare("UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?1")?;
    stmt.execute([user_id])
}
