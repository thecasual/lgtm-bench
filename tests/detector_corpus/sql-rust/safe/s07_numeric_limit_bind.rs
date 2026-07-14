use sqlx::PgPool;

// A numeric LIMIT bound as a parameter -- safe.
async fn recent_events(pool: &PgPool, limit: i64) -> Result<(), sqlx::Error> {
    sqlx::query("SELECT id FROM events ORDER BY created_at DESC LIMIT $1")
        .bind(limit)
        .execute(pool)
        .await?;
    Ok(())
}
