package db

import (
	"database/sql"
	"fmt"
	"strings"
)

// GetOrdersByIDs expands the id slice into `?` placeholders with
// fmt.Sprintf + strings.Join, and passes the actual ids as separate bound
// arguments — the same safe pattern as the `+`-based join, just spelled
// with Sprintf instead of `+`.
func GetOrdersByIDs(db *sql.DB, orderIDs []int) (*sql.Rows, error) {
	if len(orderIDs) == 0 {
		return nil, nil
	}

	placeholders := make([]string, len(orderIDs))
	args := make([]interface{}, len(orderIDs))
	for i, id := range orderIDs {
		placeholders[i] = "?"
		args[i] = id
	}

	query := fmt.Sprintf(
		"SELECT id, customer_id, total FROM orders WHERE id IN (%s)",
		strings.Join(placeholders, ", "),
	)

	return db.Query(query, args...)
}
