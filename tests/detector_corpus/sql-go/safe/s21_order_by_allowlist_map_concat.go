package products

import (
	"database/sql"
	"fmt"
)

var productSortColumns = map[string]string{
	"name":       "name",
	"price":      "price",
	"created_at": "created_at",
}

// ListProductsSorted orders by the column named in sortBy, joined with `+`
// instead of Sprintf. col comes from the allowlist map, not the raw
// caller-supplied sortBy value.
func ListProductsSorted(db *sql.DB, sortBy string) (*sql.Rows, error) {
	col, ok := productSortColumns[sortBy]
	if !ok {
		return nil, fmt.Errorf("invalid sort column %q", sortBy)
	}

	return db.Query("SELECT id, name, price, created_at FROM products ORDER BY " + col)
}
