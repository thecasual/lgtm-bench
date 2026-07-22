package products

import "database/sql"

// SearchProducts wraps term with LIKE wildcards, but the concatenation
// happens on the bound *value*, not the query text: the query string
// itself is a constant, and "%"+term+"%" is passed as a parameter.
func SearchProducts(db *sql.DB, term string) (*sql.Rows, error) {
	const query = `SELECT id, name, price FROM products WHERE name LIKE ?`
	return db.Query(query, "%"+term+"%")
}
