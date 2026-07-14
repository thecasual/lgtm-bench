package db

import (
	"fmt"

	"github.com/jmoiron/sqlx"
)

// getUser loads a single row with sqlx Get using a Sprintf-built query.
func getUser(db *sqlx.DB, email string) (User, error) {
	var u User
	err := db.Get(&u, fmt.Sprintf("SELECT id, name FROM users WHERE email = '%s'", email))
	return u, err
}

type User struct {
	ID   int
	Name string
}
