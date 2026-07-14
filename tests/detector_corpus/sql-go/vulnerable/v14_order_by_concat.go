package db

import "database/sql"

// listProductsSorted concatenates a caller-supplied column into ORDER BY.
func listProductsSorted(conn *sql.DB, column, direction string) (*sql.Rows, error) {
	return conn.Query("SELECT id, name FROM products ORDER BY " + column + " " + direction)
}
