package db

import (
	"database/sql"
	"strings"
)

// getUsersByIDs expands the id slice into `?` placeholders and passes the
// values as separate arguments.
func getUsersByIDs(conn *sql.DB, ids []int) (*sql.Rows, error) {
	placeholders := make([]string, len(ids))
	args := make([]interface{}, len(ids))
	for i, id := range ids {
		placeholders[i] = "?"
		args[i] = id
	}
	query := "SELECT id, name FROM users WHERE id IN (" + strings.Join(placeholders, ",") + ")"
	return conn.Query(query, args...)
}
