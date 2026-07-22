package db

import (
	"database/sql"
	"fmt"
)

// updateProfile builds an UPDATE with Sprintf and runs it through Exec.
func updateProfile(conn *sql.DB, name, id string) error {
	_, err := conn.Exec(fmt.Sprintf("UPDATE users SET name = '%s' WHERE id = %s", name, id))
	return err
}
