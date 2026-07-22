package main

import (
	"database/sql"
	"net/http"
)

// allowedProductSort maps each acceptable sort key to itself; only its
// presence (not its value) is used by the handler below.
var allowedProductSort = map[string]bool{
	"name":  true,
	"price": true,
}

// ListProductsHandler validates the caller-supplied "sort" query parameter
// by a comma-ok MEMBERSHIP lookup. On the negative branch it writes an HTTP
// error and returns before any query runs; on the positive branch the
// ORIGINAL "sort" string (never a mapped value) is concatenated directly
// into the ORDER BY clause. The membership check is what makes that safe.
func ListProductsHandler(w http.ResponseWriter, r *http.Request, db *sql.DB) {
	sort := r.URL.Query().Get("sort")

	if _, ok := allowedProductSort[sort]; !ok {
		http.Error(w, "unsupported sort column", http.StatusBadRequest)
		return
	}

	query := "SELECT id, name, price FROM products ORDER BY " + sort
	rows, err := db.Query(query)
	if err != nil {
		http.Error(w, "query failed", http.StatusInternalServerError)
		return
	}
	defer rows.Close()
}
