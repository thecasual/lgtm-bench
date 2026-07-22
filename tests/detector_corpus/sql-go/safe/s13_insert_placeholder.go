package db

import "database/sql"

// insertUser inserts a row with parameterized placeholders.
func insertUser(conn *sql.DB, name, email string) error {
	_, err := conn.Exec("INSERT INTO users (name, email) VALUES (?, ?)", name, email)
	return err
}
