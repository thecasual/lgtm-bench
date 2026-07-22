package products

import (
	"database/sql"
	"fmt"
)

// ListProducts binds the status value as $1, but still interpolates the
// caller-supplied sort column into ORDER BY with no allowlist — a bound
// placeholder for the value does not make the unrelated column
// interpolation safe.
func ListProducts(db *sql.DB, status, sortBy string) (*sql.Rows, error) {
	query := fmt.Sprintf("SELECT id, name FROM products WHERE status = $1 ORDER BY %s", sortBy)
	return db.Query(query, status)
}
