package db

import (
	"context"
	"database/sql"
)

// GetUserByID concatenates the caller-supplied id into the query text
// before running it through QueryRowContext.
func GetUserByID(ctx context.Context, conn *sql.DB, id string) *sql.Row {
	query := "SELECT id, name FROM users WHERE id = " + id
	return conn.QueryRowContext(ctx, query)
}
