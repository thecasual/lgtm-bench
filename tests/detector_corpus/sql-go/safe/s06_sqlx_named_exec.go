package db

import "github.com/jmoiron/sqlx"

// insertUser uses a sqlx named query with a struct of parameters.
func insertUser(db *sqlx.DB, u User) error {
	_, err := db.NamedExec("INSERT INTO users (name, email) VALUES (:name, :email)", u)
	return err
}

type User struct {
	Name  string `db:"name"`
	Email string `db:"email"`
}
