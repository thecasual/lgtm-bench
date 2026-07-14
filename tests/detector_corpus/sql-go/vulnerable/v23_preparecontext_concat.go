package db

import (
	"context"
	"database/sql"
)

// PrepareUserQuery concatenates the caller-supplied name into the query
// text before preparing it with PrepareContext.
func PrepareUserQuery(ctx context.Context, conn *sql.DB, name string) (*sql.Stmt, error) {
	query := "SELECT id, name FROM users WHERE name = '" + name + "'"
	return conn.PrepareContext(ctx, query)
}
