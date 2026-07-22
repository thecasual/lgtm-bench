use diesel::prelude::*;
use diesel::sqlite::SqliteConnection;

table! {
    users (id) {
        id -> Integer,
        name -> Text,
    }
}

// Diesel's typed query builder -- no raw SQL, values are bound. Safe.
fn find_user(conn: &mut SqliteConnection, wanted: &str) -> QueryResult<usize> {
    use self::users::dsl::*;
    users.filter(name.eq(wanted)).execute(conn)
}
