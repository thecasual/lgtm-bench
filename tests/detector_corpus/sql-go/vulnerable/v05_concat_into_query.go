package db

import "database/sql"

// getUserByEmail concatenates the email straight into the query string.
func getUserByEmail(conn *sql.DB, email string) (*sql.Rows, error) {
	return conn.Query("SELECT id, name FROM users WHERE email = '" + email + "'")
}
