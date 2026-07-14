use sqlx::PgPool;

// Parameterized with a bound placeholder ($1) -- input never touches the SQL.
async fn get_user(pool: &PgPool, name: &str) -> Result<(), sqlx::Error> {
    sqlx::query("SELECT id, name FROM users WHERE name = $1")
        .bind(name)
        .execute(pool)
        .await?;
    Ok(())
}
