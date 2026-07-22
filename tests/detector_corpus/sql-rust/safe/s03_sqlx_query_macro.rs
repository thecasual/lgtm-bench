use sqlx::PgPool;

// The query! macro is compile-time checked and parameterizes $1 -- safe.
async fn delete_session(pool: &PgPool, token: &str) -> Result<(), sqlx::Error> {
    sqlx::query!("DELETE FROM sessions WHERE token = $1", token)
        .execute(pool)
        .await?;
    Ok(())
}
