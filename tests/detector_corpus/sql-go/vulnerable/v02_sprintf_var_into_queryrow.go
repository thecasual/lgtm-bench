package db

import (
	"database/sql"
	"fmt"
)

// getUserByID interpolates the id into the query with Sprintf, then reuses
// the built string in QueryRow.
func getUserByID(conn *sql.DB, id string) *sql.Row {
	query := fmt.Sprintf("SELECT id, name, email FROM users WHERE id = %s", id)
	return conn.QueryRow(query)
}
