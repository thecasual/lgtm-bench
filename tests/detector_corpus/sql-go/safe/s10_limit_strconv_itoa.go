package db

import (
	"database/sql"
	"strconv"
)

// recentLogs builds a LIMIT clause from an integer converted with strconv,
// which cannot carry SQL syntax.
func recentLogs(conn *sql.DB, limit int) (*sql.Rows, error) {
	query := "SELECT id, message FROM logs ORDER BY id DESC LIMIT " + strconv.Itoa(limit)
	return conn.Query(query)
}
