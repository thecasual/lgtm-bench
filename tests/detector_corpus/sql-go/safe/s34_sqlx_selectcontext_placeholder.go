package db

import (
	"context"

	"github.com/jmoiron/sqlx"
)

type User struct {
	ID   int
	Role string
}

// ListByRole loads many rows with sqlx SelectContext and a bound
// placeholder.
func ListByRole(ctx context.Context, db *sqlx.DB, role string) ([]User, error) {
	var users []User
	err := db.SelectContext(ctx, &users, "SELECT id, role FROM users WHERE role = ?", role)
	return users, err
}
