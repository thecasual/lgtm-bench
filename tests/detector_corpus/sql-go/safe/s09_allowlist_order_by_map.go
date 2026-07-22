package db

import "database/sql"

// listProductsSorted maps an allowlisted sort key to a full constant query.
func listProductsSorted(conn *sql.DB, sortKey string) (*sql.Rows, error) {
	queries := map[string]string{
		"name":  "SELECT id, name FROM products ORDER BY name",
		"price": "SELECT id, name FROM products ORDER BY price",
	}
	query, ok := queries[sortKey]
	if !ok {
		query = "SELECT id, name FROM products ORDER BY id"
	}
	return conn.Query(query)
}
