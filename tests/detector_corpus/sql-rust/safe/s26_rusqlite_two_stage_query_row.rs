use rusqlite::{Connection, Result};

// Harvested (regraded) from sql-rust/get-user-by-id: the query TEXT is the
// literal passed to `prepare()`; the array passed to the subsequent
// `query_row` call is the BOUND PARAMETER, not query text, so this is a
// safe, fully-parameterized two-stage rusqlite lookup. The old v0.2 rule
// treated that array as a second sink argument and flagged it.
#[derive(Debug)]
pub struct User {
    pub id: i32,
    pub name: String,
    pub email: String,
}

pub fn get_user(conn: &Connection, id: i32) -> Result<Option<User>> {
    let mut stmt = conn.prepare("SELECT id, name, email FROM users WHERE id = ?")?;

    stmt.query_row([id], |row| {
        Ok(User {
            id: row.get(0)?,
            name: row.get(1)?,
            email: row.get(2)?,
        })
    })
    .map(Some)
    .or_else(|e| match e {
        rusqlite::Error::QueryReturnedNoRows => Ok(None),
        other => Err(other),
    })
}
