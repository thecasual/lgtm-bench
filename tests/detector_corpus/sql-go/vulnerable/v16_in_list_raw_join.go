package db

import (
	"database/sql"
	"fmt"
)

// GetOrdersByIDList splices the caller-supplied, comma-separated id list
// directly into the IN (...) clause instead of expanding it into bound
// placeholders.
func GetOrdersByIDList(db *sql.DB, idList string) (*sql.Rows, error) {
	query := fmt.Sprintf("SELECT id, total FROM orders WHERE id IN (%s)", idList)
	return db.Query(query)
}
