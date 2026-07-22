package db

import (
	"context"
	"database/sql"
	"fmt"
)

// searchByCity interpolates input into a QueryContext call via Sprintf.
func searchByCity(ctx context.Context, conn *sql.DB, city string) (*sql.Rows, error) {
	q := fmt.Sprintf("SELECT id, name FROM users WHERE city = '%s'", city)
	return conn.QueryContext(ctx, q)
}
