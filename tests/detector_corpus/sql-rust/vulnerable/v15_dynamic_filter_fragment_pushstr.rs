use sqlx::PgPool;
use std::collections::HashMap;

// Harvested (regraded) from sql-rust/dynamic-filter-where: each filter value
// is spliced straight into a WHERE fragment with format! (quoted, not
// bound) and appended to the query text with push_str. No parameter
// binding anywhere -- classic fragment-based injection that a per-call
// "does this format! call contain a SQL keyword" heuristic misses, since no
// single fragment contains SELECT/INSERT/etc, but taint mode follows the
// value all the way from the HashMap into the final query string.
async fn find_customers(
    pool: &PgPool,
    filters: &HashMap<String, String>,
) -> Result<(), sqlx::Error> {
    let mut query = String::from("SELECT * FROM customers WHERE 1=1");
    for (key, value) in filters {
        query.push_str(&format!(" AND {} = '{}'", key, value));
    }
    sqlx::query(&query).execute(pool).await?;
    Ok(())
}
