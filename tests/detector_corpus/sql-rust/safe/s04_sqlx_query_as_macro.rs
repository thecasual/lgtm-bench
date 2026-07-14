use sqlx::PgPool;

#[derive(sqlx::FromRow)]
struct User {
    id: i64,
    email: String,
}

// query_as! macro: compile-time checked, $1 is bound -- safe.
async fn load_user(pool: &PgPool, email: &str) -> Result<User, sqlx::Error> {
    sqlx::query_as!(User, "SELECT id, email FROM users WHERE email = $1", email)
        .fetch_one(pool)
        .await
}
