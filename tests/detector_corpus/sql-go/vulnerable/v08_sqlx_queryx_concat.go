package db

import "github.com/jmoiron/sqlx"

// searchProducts concatenates the term into a sqlx Queryx call.
func searchProducts(db *sqlx.DB, term string) (*sqlx.Rows, error) {
	return db.Queryx("SELECT id, name FROM products WHERE name LIKE '%" + term + "%'")
}
