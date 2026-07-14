package main

import (
	"database/sql"
	"fmt"
	"strings"
)

// UpdateUser builds an UPDATE ... SET clause from the caller-supplied
// fields map. Each value is bound as a placeholder argument, but the
// column NAME (the range key) is concatenated straight into the query
// text with no allowlist check at all: any key an attacker can get into
// fields (e.g. via a decoded JSON request body) becomes arbitrary SQL in
// the SET clause.
func UpdateUser(db *sql.DB, id int, fields map[string]interface{}) error {
	if len(fields) == 0 {
		return nil
	}

	set := make([]string, 0, len(fields))
	args := make([]interface{}, 0, len(fields)+1)
	for k, v := range fields {
		set = append(set, k+" = ?")
		args = append(args, v)
	}
	args = append(args, id)

	query := fmt.Sprintf("UPDATE users SET %s WHERE id = ?", strings.Join(set, ", "))
	_, err := db.Exec(query, args...)
	return err
}
