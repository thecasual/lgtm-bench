package main

import (
	"database/sql"
	"fmt"
	"strings"
)

// UpdateUserProfile is a partial-update helper: fields is a caller-supplied
// map (e.g. decoded from a JSON PATCH body). Each value is bound as a
// parameter, but each column NAME (the range key) is interpolated via
// fmt.Sprintf with no allowlist/membership check, so an attacker-chosen
// key becomes arbitrary SQL in the SET clause.
func UpdateUserProfile(db *sql.DB, userID string, fields map[string]string) error {
	if len(fields) == 0 {
		return nil // Nothing to update
	}

	var setClauses []string
	var args []interface{}

	for column, value := range fields {
		setClauses = append(setClauses, fmt.Sprintf("%s = ?", column))
		args = append(args, value)
	}

	args = append(args, userID)

	query := fmt.Sprintf(
		"UPDATE users SET %s WHERE id = ?",
		strings.Join(setClauses, ", "),
	)

	result, err := db.Exec(query, args...)
	if err != nil {
		return fmt.Errorf("failed to update user profile: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to get rows affected: %w", err)
	}

	if rowsAffected == 0 {
		return fmt.Errorf("user with ID %s not found", userID)
	}

	return nil
}
