package handlers

import (
	"database/sql"
	"fmt"
	"net/http"
)

// SearchByName reads the "name" query string parameter directly from the
// request URL and interpolates it into the query text with Sprintf.
func SearchByName(db *sql.DB, r *http.Request) (*sql.Rows, error) {
	name := r.URL.Query().Get("name")
	return db.Query(fmt.Sprintf("SELECT id, name FROM users WHERE name = '%s'", name))
}
