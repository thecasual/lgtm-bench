package users

import (
	"database/sql"
	"fmt"
)

// UpdateUserColumn writes to the caller-supplied column name directly, with
// no allowlist check.
func UpdateUserColumn(db *sql.DB, column, value, userID string) error {
	query := fmt.Sprintf("UPDATE users SET %s = ? WHERE id = ?", column)
	_, err := db.Exec(query, value, userID)
	return err
}
