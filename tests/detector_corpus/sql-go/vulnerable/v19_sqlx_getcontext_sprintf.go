package db

import (
	"context"
	"fmt"

	"github.com/jmoiron/sqlx"
)

type User struct {
	ID    int
	Email string
}

// GetUser interpolates the email into the query with Sprintf, then runs it
// through sqlx GetContext.
func GetUser(ctx context.Context, db *sqlx.DB, email string) (User, error) {
	var u User
	err := db.GetContext(ctx, &u, fmt.Sprintf("SELECT id, email FROM users WHERE email = '%s'", email))
	return u, err
}
