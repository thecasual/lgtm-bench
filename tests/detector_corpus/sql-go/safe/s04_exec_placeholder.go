package db

import "database/sql"

// updateEmail runs a parameterized UPDATE with placeholders.
func updateEmail(conn *sql.DB, email string, id int) error {
	_, err := conn.Exec("UPDATE users SET email = ? WHERE id = ?", email, id)
	return err
}
