package main

import (
	"database/sql"
	"net/http"
	"strings"
)

// Handler builds a WHERE clause from parsed form field names with no
// allowlist check at all: r.Form is directly attacker-controlled (any
// field name a client puts in the request body/query string), and each
// key is concatenated straight into the query text as a column name.
func Handler(w http.ResponseWriter, r *http.Request, db *sql.DB) {
	r.ParseForm()

	var conditions []string
	var args []interface{}
	for key, vals := range r.Form {
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
