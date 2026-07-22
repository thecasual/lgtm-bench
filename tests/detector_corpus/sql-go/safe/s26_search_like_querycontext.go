package products

import (
	"context"
	"database/sql"
)

// SearchProducts binds the wildcarded term as a parameter via
// QueryContext; the query text is a constant.
func SearchProducts(ctx context.Context, db *sql.DB, q string) (*sql.Rows, error) {
	return db.QueryContext(ctx,
		`SELECT id, name, price FROM products WHERE name LIKE ?`,
		"%"+q+"%")
}
