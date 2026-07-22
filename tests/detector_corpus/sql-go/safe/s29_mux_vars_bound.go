package handlers

import (
	"database/sql"
	"net/http"

	"github.com/gorilla/mux"
)

// GetByID reads the "id" route variable with gorilla/mux, but binds it as
// a query parameter rather than interpolating it into the SQL text.
func GetByID(db *sql.DB, r *http.Request) (*sql.Row, error) {
	id := mux.Vars(r)["id"]
	return db.QueryRow("SELECT id, name FROM users WHERE id = ?", id), nil
}
