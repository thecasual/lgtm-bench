package db

import "database/sql"

// getUserByName prepares a statement and binds the value at execution time.
func getUserByName(conn *sql.DB, name string) (*sql.Rows, error) {
	stmt, err := conn.Prepare("SELECT id, name FROM users WHERE name = ?")
	if err != nil {
		return nil, err
	}
	defer stmt.Close()
	return stmt.Query(name)
}
