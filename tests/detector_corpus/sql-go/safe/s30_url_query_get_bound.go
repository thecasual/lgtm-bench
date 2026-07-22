package handlers

import (
	"database/sql"
	"net/http"
)

// SearchByName reads the "name" query string parameter directly from the
// request URL, but binds it as a query parameter rather than interpolating
// it into the SQL text.
func SearchByName(db *sql.DB, r *http.Request) (*sql.Rows, error) {
	name := r.URL.Query().Get("name")
	return db.Query("SELECT id, name FROM users WHERE name = ?", name)
}
