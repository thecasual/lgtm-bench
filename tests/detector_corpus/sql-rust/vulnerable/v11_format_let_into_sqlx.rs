use sqlx::PgPool;

// let intermediate format! query then run through sqlx::query.
async fn update_role(pool: &PgPool, role: &str, id: &str) -> Result<(), sqlx::Error> {
    let q = format!("UPDATE users SET role = '{}' WHERE id = {}", role, id);
    sqlx::query(&q).execute(pool).await?;
    Ok(())
}
