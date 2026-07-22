use tokio_postgres::{Client, Error, Row};

// tokio-postgres: the query is built with format! and run via client.query.
async fn users_by_city(client: &Client, city: &str) -> Result<Vec<Row>, Error> {
    let sql = format!("SELECT id, name FROM users WHERE city = '{}'", city);
    client.query(&sql, &[]).await
}
