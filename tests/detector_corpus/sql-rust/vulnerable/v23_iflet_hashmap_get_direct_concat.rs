use sqlx::PgPool;
use std::collections::HashMap;

// Harvested (regraded, simplified) from sql-rust/dynamic-filter-where: the
// caller-supplied `status` filter is pulled out of the HashMap through an
// `if let Some(status) = filters.get("status")` binding and interpolated
// straight into the query text with no bind parameter. Taint mode must
// carry the HashMap's taint through the if-let destructure into `status`
// for this to be caught.
pub async fn find_customers(
    pool: &PgPool,
    filters: &HashMap<String, String>,
) -> Result<(), sqlx::Error> {
    if let Some(status) = filters.get("status") {
        let query = format!("SELECT * FROM customers WHERE status = '{}'", status);
        sqlx::query(&query).fetch_all(pool).await?;
    }
    Ok(())
}
