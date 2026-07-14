use sqlx::{postgres::PgRow, PgPool};
use std::collections::HashMap;

// Harvested (regraded) from sql-rust/dynamic-filter-where: each present
// filter key is unwrapped via `if let Some(...) = filters.get(...)`, then
// its *raw* value (not a bind placeholder) is formatted straight into a
// clause fragment, accumulated into a Vec, and joined back into the query
// text. No `.bind()`/`push_bind()` call ever touches these values.
async fn fetch_customers(
    pool: &PgPool,
    filters: HashMap<String, String>,
) -> Result<Vec<PgRow>, sqlx::Error> {
    let mut clauses: Vec<String> = Vec::new();

    if let Some(status) = filters.get("status") {
        clauses.push(format!("status = '{}'", status));
    }
    if let Some(city) = filters.get("city") {
        clauses.push(format!("city = '{}'", city));
    }

    let joined = clauses.join(" AND ");
    let query = format!("SELECT * FROM customers WHERE {}", joined);
    sqlx::query(&query).fetch_all(pool).await
}
