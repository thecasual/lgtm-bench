package products

import (
	"database/sql"
	"fmt"
)

var allowedSortColumns = map[string]string{
	"name":       "name",
	"price":      "price",
	"created_at": "created_at",
}

// ListProducts orders by the column named in sortBy. sortBy is checked
// against a fixed allowlist first; only the map's own literal value (never
// the raw caller-supplied sortBy) is interpolated into ORDER BY.
func ListProducts(db *sql.DB, sortBy string) (*sql.Rows, error) {
	column, ok := allowedSortColumns[sortBy]
	if !ok {
		return nil, fmt.Errorf("invalid sort column %q", sortBy)
	}

	query := fmt.Sprintf("SELECT id, name, price, created_at FROM products ORDER BY %s", column)
	return db.Query(query)
}
