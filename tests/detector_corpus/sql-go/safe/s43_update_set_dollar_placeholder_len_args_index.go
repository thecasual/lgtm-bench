package users

import (
	"database/sql"
	"fmt"
	"strings"
)

// s43: safe $N positional-placeholder UPDATE builder. Column names are
// allowlist-guarded (membership check on allowedProfileColumns) before they
// reach the query text, and every VALUE — including the string userID param —
// is bound via args, never interpolated. The placeholder indices are
// fmt.Sprintf("...$%d", len(args)...): len() returns an int count, so even
// though userID is folded into args (making len(args) taint-derived), only an
// integer index ever reaches the query string. No injection is possible.
var allowedProfileColumns = map[string]bool{
	"display_name": true,
	"email":        true,
	"bio":          true,
	"avatar_url":   true,
}

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
		setClauses = append(setClauses, fmt.Sprintf("%s = $%d", col, len(args)+1))
		args = append(args, val)
	}
	args = append(args, userID)
	query := fmt.Sprintf(
		"UPDATE users SET %s WHERE id = $%d",
		strings.Join(setClauses, ", "),
		len(args),
	)
	_, err := db.Exec(query, args...)
	return err
}
