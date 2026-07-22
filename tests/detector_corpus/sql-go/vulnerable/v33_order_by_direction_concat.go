package products

import "database/sql"

// ListProductsSorted concatenates a caller-supplied column and direction
// into ORDER BY, with no allowlist.
func ListProductsSorted(db *sql.DB, column, direction string) (*sql.Rows, error) {
	return db.Query("SELECT id, name FROM products ORDER BY " + column + " " + direction)
}
