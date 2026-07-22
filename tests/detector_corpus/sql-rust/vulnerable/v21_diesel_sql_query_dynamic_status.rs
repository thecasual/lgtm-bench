use diesel::pg::PgConnection;
use diesel::prelude::*;

// A second diesel::sql_query variant distinct from v06: the status is
// appended with push_str instead of format!, still with no allow-list and
// no bind parameter.
fn orders_by_status(conn: &mut PgConnection, status: &str) -> QueryResult<usize> {
    let mut sql = String::from("SELECT * FROM orders WHERE status = '");
    sql.push_str(status);
    sql.push('\'');
    diesel::sql_query(sql).execute(conn)
}
