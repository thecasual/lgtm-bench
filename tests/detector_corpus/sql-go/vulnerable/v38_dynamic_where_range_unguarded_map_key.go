package main

import (
	"database/sql"
	"fmt"
	"strings"
)

// FindCustomers builds a WHERE clause from a caller-supplied filters map
// (e.g. decoded from a JSON request body). Each value is bound as a
// parameter, but the column NAME (the range key) is concatenated straight
// into the query text with no allowlist/membership check at all, so an
// attacker-chosen filter key becomes arbitrary SQL in the WHERE clause.
func FindCustomers(db *sql.DB, filters map[string]string) (*sql.Rows, error) {
	query := "SELECT id, name, status, city, signup_year FROM customers"

	var conditions []string
	var args []interface{}

	for key, value := range filters {
		conditions = append(conditions, key+" = ?")
		args = append(args, value)
	}

	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}

	return db.Query(query, args...)
}
