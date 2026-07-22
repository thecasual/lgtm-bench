package handlers

import (
	"database/sql"
	"net/http"

	"github.com/gorilla/mux"
)

// ListSorted reads the "col" route variable with gorilla/mux and
// interpolates it directly into ORDER BY, with no allowlist.
func ListSorted(db *sql.DB, r *http.Request) (*sql.Rows, error) {
	col := mux.Vars(r)["col"]
	return db.Query("SELECT id, name FROM users ORDER BY " + col)
}
