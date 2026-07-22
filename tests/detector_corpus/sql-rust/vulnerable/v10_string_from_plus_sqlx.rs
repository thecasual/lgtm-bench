use sqlx::PgPool;

// String::from(...) + user input, passed to sqlx::query.
async fn search(pool: &PgPool, term: &str) -> Result<(), sqlx::Error> {
    sqlx::query(&(String::from("SELECT * FROM products WHERE name LIKE '%") + term))
        .execute(pool)
        .await?;
    Ok(())
}
