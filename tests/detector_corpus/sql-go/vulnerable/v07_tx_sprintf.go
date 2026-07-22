package db

import (
	"database/sql"
	"fmt"
)

// insertNote runs a Sprintf-built statement on a transaction receiver.
func insertNote(tx *sql.Tx, body string) error {
	_, err := tx.Exec(fmt.Sprintf("INSERT INTO notes (body) VALUES ('%s')", body))
	return err
}
