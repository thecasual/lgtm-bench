use sqlx::PgPool;

// sqlx: format! output handed directly to sqlx::query (not the query! macro).
async fn delete_session(pool: &PgPool, token: &str) -> Result<(), sqlx::Error> {
    sqlx::query(&format!("DELETE FROM sessions WHERE token = '{}'", token))
        .execute(pool)
        .await?;
    Ok(())
}
