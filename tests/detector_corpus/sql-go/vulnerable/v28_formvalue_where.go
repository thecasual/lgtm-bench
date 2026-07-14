package handlers

import (
	"database/sql"
	"net/http"
)

// SearchByName reads the "name" form field and concatenates it directly
// into the query text.
func SearchByName(db *sql.DB, r *http.Request) (*sql.Rows, error) {
	name := r.FormValue("name")
	return db.Query("SELECT id, name FROM users WHERE name = '" + name + "'")
}
