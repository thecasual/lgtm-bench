package db

import "github.com/jmoiron/sqlx"

// getUser loads a single row with a sqlx Get and a bound placeholder.
func getUser(db *sqlx.DB, email string) (User, error) {
	var u User
	err := db.Get(&u, "SELECT id, name FROM users WHERE email = ?", email)
	return u, err
}

type User struct {
	ID   int
	Name string
}
