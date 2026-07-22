package products

import (
	"context"
	"database/sql"
)

// ListProducts interpolates the caller-supplied sort column directly into
// ORDER BY via concatenation, with no allowlist, using QueryContext.
func ListProducts(ctx context.Context, db *sql.DB, sortBy string) (*sql.Rows, error) {
	query := "SELECT id, name, price FROM products ORDER BY " + sortBy
	return db.QueryContext(ctx, query)
}
