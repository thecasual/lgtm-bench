use sqlx::PgPool;

#[derive(sqlx::FromRow)]
struct User {
    id: i64,
    email: String,
}

// sqlx::query_as with a format!-built query string; `email` is interpolated.
async fn load_user(pool: &PgPool, email: &str) -> Result<User, sqlx::Error> {
    let q = format!("SELECT id, email FROM users WHERE email = '{}'", email);
    sqlx::query_as::<_, User>(&q).fetch_one(pool).await
}
