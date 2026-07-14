package customers

import (
	"database/sql"
	"fmt"
)

// FindCustomersByColumn builds a WHERE clause using the caller-supplied
// column name directly, with no allowlist check.
func FindCustomersByColumn(db *sql.DB, column, value string) (*sql.Rows, error) {
	query := fmt.Sprintf("SELECT id, name FROM customers WHERE %s = ?", column)
	return db.Query(query, value)
}
