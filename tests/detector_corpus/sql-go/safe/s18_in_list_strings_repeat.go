package db

import (
	"database/sql"
	"strings"
)

// ordersByIDs builds the placeholder list with strings.Repeat instead of
// strings.Join; the ids themselves are always passed as bound arguments.
func ordersByIDs(db *sql.DB, ids []int) (*sql.Rows, error) {
	if len(ids) == 0 {
		return nil, nil
	}
	q := `SELECT id, user_id, total FROM orders WHERE id IN (?` + strings.Repeat(",?", len(ids)-1) + `)`
	args := make([]any, len(ids))
	for i, id := range ids {
		args[i] = id
	}
	return db.Query(q, args...)
}
