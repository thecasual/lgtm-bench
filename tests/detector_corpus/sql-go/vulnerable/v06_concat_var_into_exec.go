package db

import "database/sql"

// deleteByName concatenates user input into a DELETE statement.
func deleteByName(conn *sql.DB, name string) error {
	query := "DELETE FROM users WHERE name = '" + name + "'"
	_, err := conn.Exec(query)
	return err
}
