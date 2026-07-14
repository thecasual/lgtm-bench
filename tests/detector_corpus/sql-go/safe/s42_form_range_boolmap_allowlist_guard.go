package main

import (
	"database/sql"
	"net/http"
	"strings"
)

var allowedFormColumns = map[string]bool{
	"status": true,
	"city":   true,
}

// Handler builds a WHERE clause from parsed form field names, but each key
// is MEMBERSHIP-guarded against the fixed allowlist above before being
// concatenated as a column name; unlisted fields are simply skipped.
func Handler(w http.ResponseWriter, r *http.Request, db *sql.DB) {
	r.ParseForm()

	var conditions []string
	var args []interface{}
	for key, vals := range r.Form {
		if !allowedFormColumns[key] {
			continue
		}
		conditions = append(conditions, key+" = ?")
		if len(vals) > 0 {
			args = append(args, vals[0])
		}
	}

	query := "SELECT * FROM items"
	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}
	db.Query(query, args...)
}
