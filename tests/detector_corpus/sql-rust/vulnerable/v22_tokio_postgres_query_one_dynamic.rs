use tokio_postgres::{Client, Error, Row};

// tokio-postgres query_one variant: the query text is built with format!
// from an untrusted username and passed straight to query_one, with no
// bind parameters.
async fn find_by_username(client: &Client, username: &str) -> Result<Row, Error> {
    let sql = format!("SELECT id, email FROM users WHERE username = '{}'", username);
    client.query_one(&sql, &[]).await
}
