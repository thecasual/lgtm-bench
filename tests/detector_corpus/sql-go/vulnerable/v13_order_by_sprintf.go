package db

import (
	"database/sql"
	"fmt"
)

// listUsersSorted interpolates a caller-supplied sort column into ORDER BY.
func listUsersSorted(conn *sql.DB, sortColumn string) (*sql.Rows, error) {
	query := fmt.Sprintf("SELECT id, name FROM users ORDER BY %s", sortColumn)
	return conn.Query(query)
}
