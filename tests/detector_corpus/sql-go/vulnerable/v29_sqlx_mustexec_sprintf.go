package db

import (
	"fmt"

	"github.com/jmoiron/sqlx"
)

// DeleteByEmail interpolates the caller-supplied email into the query text
// with Sprintf before running it through sqlx MustExec.
func DeleteByEmail(db *sqlx.DB, email string) {
	db.MustExec(fmt.Sprintf("DELETE FROM users WHERE email = '%s'", email))
}
