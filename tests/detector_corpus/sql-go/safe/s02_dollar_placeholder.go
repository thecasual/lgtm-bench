package db

import "database/sql"

// getUserByEmail uses a $1 placeholder (lib/pq style) with the value passed
// as a separate argument.
func getUserByEmail(conn *sql.DB, email string) *sql.Row {
	return conn.QueryRow("SELECT id, name FROM users WHERE email = $1", email)
}
