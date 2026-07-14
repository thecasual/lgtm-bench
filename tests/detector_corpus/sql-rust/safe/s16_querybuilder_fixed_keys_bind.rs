use sqlx::{PgPool, Postgres, QueryBuilder};
use std::collections::HashMap;

// Variant harvested from the same dynamic-filter-where trials: the loop
// walks a fixed array literal of column names (never the caller's map keys),
// so the identifier pushed into the builder is always one of "status" /
// "city" / "signup_year". Values are still bound via push_bind.
pub async fn find_customers(
    pool: &PgPool,
    filters: &HashMap<String, String>,
) -> Result<u64, sqlx::Error> {
    let mut qb: QueryBuilder<Postgres> = QueryBuilder::new("SELECT id FROM customers WHERE 1=1");
    for key in ["status", "city", "signup_year"] {
        if let Some(val) = filters.get(key) {
            qb.push(format!(" AND {key} = "));
            qb.push_bind(val.clone());
        }
    }
    let result = qb.build().execute(pool).await?;
    Ok(result.rows_affected())
}
