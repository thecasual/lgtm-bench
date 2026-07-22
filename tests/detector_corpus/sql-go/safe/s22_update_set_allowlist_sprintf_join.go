package users

import (
	"database/sql"
	"fmt"
	"strings"
)

var allowedProfileColumns = map[string]bool{
	"email":        true,
	"display_name": true,
	"bio":          true,
}

// UpdateUserProfile updates only the columns named in fields for userID.
// Column names are validated against a fixed allowlist before they can
// reach the SQL text; values are always bound as parameters.
func UpdateUserProfile(db *sql.DB, userID string, fields map[string]string) error {
	if len(fields) == 0 {
		return nil
	}

	setClauses := make([]string, 0, len(fields))
	args := make([]interface{}, 0, len(fields)+1)

	for col, val := range fields {
		if !allowedProfileColumns[col] {
			return fmt.Errorf("column %q is not updatable", col)
		}
		setClauses = append(setClauses, fmt.Sprintf("%s = ?", col))
		args = append(args, val)
	}
	args = append(args, userID)

	query := fmt.Sprintf("UPDATE users SET %s WHERE id = ?", strings.Join(setClauses, ", "))
	_, err := db.Exec(query, args...)
	return err
}
