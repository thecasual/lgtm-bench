use sqlx::PgPool;

// LIMIT/OFFSET parsed to an integer and bound as a parameter -- safe. A
// sibling of s07 (bind) covering the paging/offset shape rather than a bare
// limit.
async fn page_events(pool: &PgPool, limit: i64, offset: i64) -> Result<(), sqlx::Error> {
    sqlx::query("SELECT id FROM events ORDER BY created_at DESC LIMIT $1 OFFSET $2")
        .bind(limit)
        .bind(offset)
        .execute(pool)
        .await?;
    Ok(())
}
