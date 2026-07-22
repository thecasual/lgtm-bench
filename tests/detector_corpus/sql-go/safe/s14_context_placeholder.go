package db

import (
	"context"
	"database/sql"
)

// searchByCity uses QueryContext with a bound placeholder.
func searchByCity(ctx context.Context, conn *sql.DB, city string) (*sql.Rows, error) {
	return conn.QueryContext(ctx, "SELECT id, name FROM users WHERE city = ?", city)
}
