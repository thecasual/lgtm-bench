package customers

import (
	"database/sql"
	"fmt"
	"strings"
)

var allowedFilterColumns = map[string]bool{
	"status": true,
	"city":   true,
}

// FindCustomersByFields builds a WHERE clause by ranging over the caller's
// filter map, rejecting any column not in the allowlist before it can reach
// the query text. Values are always bound as parameters.
func FindCustomersByFields(db *sql.DB, fields map[string]string) (*sql.Rows, error) {
	var conditions []string
	var args []interface{}

	for col, val := range fields {
		if !allowedFilterColumns[col] {
			return nil, fmt.Errorf("column %q is not filterable", col)
		}
		conditions = append(conditions, fmt.Sprintf("%s = ?", col))
		args = append(args, val)
	}

	query := "SELECT id, name FROM customers"
	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}

	return db.Query(query, args...)
}
