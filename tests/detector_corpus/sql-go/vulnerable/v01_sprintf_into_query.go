package db

import (
	"database/sql"
	"fmt"
)

// getUserByName interpolates untrusted input into the query with Sprintf.
func getUserByName(conn *sql.DB, name string) (*sql.Rows, error) {
	query := fmt.Sprintf("SELECT id, name FROM users WHERE name = '%s'", name)
	return conn.Query(query)
}
