package db

import (
	"database/sql"
	"fmt"
	"strings"
)

// getOrders builds a Postgres-style `$1, $2, ...` placeholder list for the
// IN clause; the ids are still passed as bound arguments, never
// interpolated into the query text.
func getOrders(db *sql.DB, ids []int64) (*sql.Rows, error) {
	if len(ids) == 0 {
		return nil, nil
	}
	ph := make([]string, len(ids))
	args := make([]any, len(ids))
	for i, id := range ids {
		ph[i] = fmt.Sprintf("$%d", i+1)
		args[i] = id
	}
	query := "SELECT id, customer_id, total FROM orders WHERE id IN (" + strings.Join(ph, ", ") + ")"
	return db.Query(query, args...)
}
