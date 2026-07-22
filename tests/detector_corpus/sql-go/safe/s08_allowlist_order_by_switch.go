package db

import "database/sql"

// listUsersSorted selects a full constant query per allowlisted sort key, so
// no untrusted text ever reaches the query string.
func listUsersSorted(conn *sql.DB, sortKey string) (*sql.Rows, error) {
	var query string
	switch sortKey {
	case "name":
		query = "SELECT id, name FROM users ORDER BY name"
	case "email":
		query = "SELECT id, name FROM users ORDER BY email"
	default:
		query = "SELECT id, name FROM users ORDER BY id"
	}
	return conn.Query(query)
}
