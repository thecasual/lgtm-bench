package main

import (
	"database/sql"
	"fmt"
)

var allowedCustomerSort = map[string]bool{
	"name":       true,
	"signup_year": true,
}

// FindCustomersSorted validates sortBy with a comma-ok MEMBERSHIP lookup
// and, only inside the positive ("found") branch, interpolates the
// ORIGINAL sortBy string directly into the query. Because the interpolated
// value is used exclusively within the branch that already proved
// membership, it can only ever be one of the allowlist's own keys.
func FindCustomersSorted(db *sql.DB, sortBy string) (*sql.Rows, error) {
	if _, ok := allowedCustomerSort[sortBy]; ok {
		query := fmt.Sprintf("SELECT id, name, signup_year FROM customers ORDER BY %s", sortBy)
		return db.Query(query)
	}
	return nil, fmt.Errorf("unsupported sort column: %q", sortBy)
}
