package db

import (
	"context"

	"github.com/jmoiron/sqlx"
)

type User struct {
	ID   int
	Name string
}

// GetUser loads a single row with sqlx GetContext and a bound placeholder.
func GetUser(ctx context.Context, db *sqlx.DB, email string) (User, error) {
	var u User
	err := db.GetContext(ctx, &u, "SELECT id, name FROM users WHERE email = ?", email)
	return u, err
}
