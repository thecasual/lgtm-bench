package main

import (
	"database/sql"
	"fmt"
)

// allowedSortColumns is the fixed set of columns callers may sort by.
var allowedSortColumns = map[string]bool{
	"id":         true,
	"name":       true,
	"price":      true,
	"created_at": true,
}

type Product struct {
	ID        int
	Name      string
	Price     float64
	CreatedAt string
}

// ListProducts validates sortBy by MEMBERSHIP against the fixed allowlist
// above and, on success, interpolates the ORIGINAL sortBy string directly
// (not a distinct mapped value). The membership check constrains sortBy to
// one of the allowlist's own literal keys before it can ever reach the
// query text, so this is safe despite not going through a $MAP[$KEY]
// lookup.
func ListProducts(db *sql.DB, sortBy string) ([]Product, error) {
	if !allowedSortColumns[sortBy] {
		return nil, fmt.Errorf("invalid sort column: %s", sortBy)
	}

	// Safe to use sortBy here because it's been validated against the
	// allowlist above.
	query := fmt.Sprintf("SELECT id, name, price, created_at FROM products ORDER BY %s", sortBy)

	rows, err := db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var products []Product
	for rows.Next() {
		var p Product
		if err := rows.Scan(&p.ID, &p.Name, &p.Price, &p.CreatedAt); err != nil {
			return nil, err
		}
		products = append(products, p)
	}
	return products, rows.Err()
}
