package db

import (
	"context"
	"fmt"

	"github.com/jmoiron/sqlx"
)

type User struct {
	ID   int
	Role string
}

// ListByRole interpolates the role into the query with Sprintf, then runs
// it through sqlx SelectContext.
func ListByRole(ctx context.Context, db *sqlx.DB, role string) ([]User, error) {
	var users []User
	err := db.SelectContext(ctx, &users, fmt.Sprintf("SELECT id, role FROM users WHERE role = '%s'", role))
	return users, err
}
