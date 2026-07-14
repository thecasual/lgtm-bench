package db

import "database/sql"

// getUserByID uses a ? placeholder for the id.
func getUserByID(conn *sql.DB, id int) *sql.Row {
	return conn.QueryRow("SELECT id, name, email FROM users WHERE id = ?", id)
}
