package db

import (
	"fmt"

	"github.com/jmoiron/sqlx"
)

// listByRole loads many rows with sqlx Select using a Sprintf-built query.
func listByRole(db *sqlx.DB, role string) ([]User, error) {
	var users []User
	err := db.Select(&users, fmt.Sprintf("SELECT id, name FROM users WHERE role = '%s'", role))
	return users, err
}

type User struct {
	ID   int
	Name string
}
