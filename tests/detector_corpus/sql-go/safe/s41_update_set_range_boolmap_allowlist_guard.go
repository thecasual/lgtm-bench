package users

import (
	"database/sql"
	"fmt"
	"strings"
)

// allowedProfileColumns is the set of columns UpdateUserProfile is permitted
// to modify. Column names cannot be passed as query parameters, so they are
// interpolated into the SQL text directly; restricting them to this fixed
// set is what keeps that interpolation safe.
var allowedProfileColumns = map[string]bool{
	"email":        true,
	"display_name": true,
	"bio":          true,
	"avatar_url":   true,
	"locale":       true,
}

// UpdateUserProfile updates the columns named in fields for the user
// identified by userID. fields is caller-controlled (e.g. a decoded JSON
// request body), so each range KEY is MEMBERSHIP-guarded against the fixed
// allowlist above before it is interpolated as a column name; the
// corresponding value is always bound as a parameter, never concatenated.
func UpdateUserProfile(db *sql.DB, userID string, fields map[string]string) error {
	if len(fields) == 0 {
		return nil // nothing to update
	}

	setClauses := make([]string, 0, len(fields))
	args := make([]interface{}, 0, len(fields)+1)

	for col, val := range fields {
		if !allowedProfileColumns[col] {
			return fmt.Errorf("column %q is not updatable", col)
		}
		// col comes from the whitelist above, so it is safe to interpolate.
		// val is bound as a parameter and never concatenated into the SQL.
		setClauses = append(setClauses, fmt.Sprintf("%s = ?", col))
		args = append(args, val)
	}

	args = append(args, userID)

	query := fmt.Sprintf(
		"UPDATE users SET %s WHERE id = ?",
		strings.Join(setClauses, ", "),
	)

	result, err := db.Exec(query, args...)
	if err != nil {
		return fmt.Errorf("updating user %s: %w", userID, err)
	}

	rows, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("checking rows affected for user %s: %w", userID, err)
	}
	if rows == 0 {
		return fmt.Errorf("no user found with id %s", userID)
	}

	return nil
}
