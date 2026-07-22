package db

import "database/sql"

// getUserByName uses a parameterized query with a placeholder — no injection.
func getUserByName(conn *sql.DB, name string) (*sql.Rows, error) {
	return conn.Query("SELECT id, name FROM users WHERE name = ?", name)
}
