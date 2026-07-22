package main

import (
	"database/sql"
	"strconv"
	"strings"
)

// UpdateUser is the $N-placeholder (Postgres-style) sibling of the "?"
// version: values are properly bound, but the column NAME (the range key
// over the caller-supplied updates map) is concatenated straight into the
// SET clause with no allowlist check.
func UpdateUser(db *sql.DB, userID int, updates map[string]any) error {
	if len(updates) == 0 {
		return nil
	}

	var sets []string
	var args []any
	i := 1

	for col, val := range updates {
		sets = append(sets, col+" = $"+strconv.Itoa(i))
		args = append(args, val)
		i++
	}
	args = append(args, userID)

	query := "UPDATE users SET " + strings.Join(sets, ", ") + " WHERE id = $" + strconv.Itoa(i)
	_, err := db.Exec(query, args...)
	return err
}
