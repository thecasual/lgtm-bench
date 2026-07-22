use diesel::pg::PgConnection;
use diesel::prelude::*;

// diesel raw sql_query built with format! from an untrusted status string.
fn orders_by_status(conn: &mut PgConnection, status: &str) -> QueryResult<usize> {
    diesel::sql_query(format!("SELECT * FROM orders WHERE status = '{}'", status))
        .execute(conn)
}
