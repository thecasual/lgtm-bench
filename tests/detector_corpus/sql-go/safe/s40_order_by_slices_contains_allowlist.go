package main

import (
	"database/sql"
	"fmt"
	"slices"
)

// ListOrdersSorted validates sortBy with slices.Contains against a fixed
// allowlist slice before interpolating the ORIGINAL sortBy string directly
// into the ORDER BY clause.
func ListOrdersSorted(db *sql.DB, sortBy string) (*sql.Rows, error) {
	allowedColumns := []string{"id", "total", "created_at"}
	if !slices.Contains(allowedColumns, sortBy) {
		return nil, fmt.Errorf("invalid sort column: %s", sortBy)
	}

	query := fmt.Sprintf("SELECT id, total, created_at FROM orders ORDER BY %s", sortBy)
	return db.Query(query)
}
