use sqlx::SqlitePool;

// Several bound parameters, constant SQL text -- safe.
async fn update_profile(pool: &SqlitePool, name: &str, email: &str, id: i64)
    -> Result<(), sqlx::Error>
{
    sqlx::query("UPDATE users SET name = ?, email = ? WHERE id = ?")
        .bind(name)
        .bind(email)
        .bind(id)
        .execute(pool)
        .await?;
    Ok(())
}
