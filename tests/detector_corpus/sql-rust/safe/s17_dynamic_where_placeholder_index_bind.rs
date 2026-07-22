use sqlx::PgPool;
use std::collections::HashMap;

// Harvested (regraded) from sql-rust/dynamic-filter-where: each WHERE
// fragment interpolates only a fixed column-name literal and a computed
// placeholder *index* ($1, $2, ...) -- never the filter value itself. The
// real values are collected into `bind_values` and bound afterwards. The old
// rule flagged the format! calls on sight; taint mode sees that only
// non-attacker-controlled data (literals, a usize count) ever reaches the
// query text.
pub async fn find_customers(
    pool: &PgPool,
    filters: &HashMap<String, String>,
) -> Result<(), sqlx::Error> {
    let mut where_clauses: Vec<String> = Vec::new();
    let mut bind_values: Vec<String> = Vec::new();

    if let Some(status) = filters.get("status") {
        where_clauses.push(format!("status = ${}", bind_values.len() + 1));
        bind_values.push(status.clone());
    }
    if let Some(city) = filters.get("city") {
        where_clauses.push(format!("city = ${}", bind_values.len() + 1));
        bind_values.push(city.clone());
    }

    let mut query = String::from("SELECT id FROM customers");
    if !where_clauses.is_empty() {
        query.push_str(" WHERE ");
        query.push_str(&where_clauses.join(" AND "));
    }

    let mut q = sqlx::query(&query);
    for value in bind_values {
        q = q.bind(value);
    }
    q.fetch_all(pool).await?;
    Ok(())
}
