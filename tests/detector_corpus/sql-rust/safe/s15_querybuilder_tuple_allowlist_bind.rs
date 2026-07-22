use sqlx::{PgPool, Postgres, QueryBuilder};
use std::collections::HashMap;

// Harvested (regraded) from sql-rust/dynamic-filter-where: sqlx's
// QueryBuilder is fed column identifiers from a hardcoded (key, column)
// tuple list -- never from the caller's HashMap keys -- and every value is
// bound with push_bind. The column text can never carry attacker input.
pub async fn find_customers(
    pool: &PgPool,
    filters: &HashMap<String, String>,
) -> Result<u64, sqlx::Error> {
    let mut qb: QueryBuilder<Postgres> = QueryBuilder::new("SELECT id FROM customers");
    let mut first = true;
    for (key, column) in [("status", "status"), ("city", "city")] {
        if let Some(value) = filters.get(key) {
            qb.push(if first { " WHERE " } else { " AND " });
            first = false;
            qb.push(column).push(" = ").push_bind(value.clone());
        }
    }
    let result = qb.build().execute(pool).await?;
    Ok(result.rows_affected())
}
