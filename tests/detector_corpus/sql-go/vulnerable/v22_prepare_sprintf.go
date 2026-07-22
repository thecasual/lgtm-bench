package db

import (
	"database/sql"
	"fmt"
)

// PrepareUserQuery interpolates the caller-supplied name into the query
// text with Sprintf before preparing it.
func PrepareUserQuery(conn *sql.DB, name string) (*sql.Stmt, error) {
	return conn.Prepare(fmt.Sprintf("SELECT id, name FROM users WHERE name = '%s'", name))
}
