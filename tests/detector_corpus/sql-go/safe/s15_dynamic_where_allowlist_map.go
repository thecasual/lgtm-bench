package customers

import (
	"database/sql"
	"fmt"
	"strings"
)

// FindCustomers applies an equality WHERE condition for each of a fixed set
// of filter keys that is present in filters. Only the allowlisted keys are
// ever consulted, and the map value (never the caller-supplied key) is what
// gets interpolated into the query text; the filter value itself is always
// bound as a parameter.
func FindCustomers(db *sql.DB, filters map[string]string) (*sql.Rows, error) {
	allowed := map[string]string{
		"status": "status",
		"city":   "city",
	}

	query := "SELECT id, name FROM customers"
	var conditions []string
	var args []interface{}

	for _, key := range []string{"status", "city"} {
		if val, ok := filters[key]; ok {
			conditions = append(conditions, fmt.Sprintf("%s = ?", allowed[key]))
			args = append(args, val)
		}
	}

	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}

	return db.Query(query, args...)
}
