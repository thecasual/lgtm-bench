package db

import "database/sql"

// DeleteNote concatenates the caller-supplied id directly into a DELETE
// statement run on a transaction receiver.
func DeleteNote(tx *sql.Tx, id string) error {
	_, err := tx.Exec("DELETE FROM notes WHERE id = " + id)
	return err
}
