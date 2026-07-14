package users

import "database/sql"

// CreateUserFromForm inserts a row and reads back the generated id via
// RETURNING, with every value bound as a parameter.
func CreateUserFromForm(db *sql.DB, email, name string) (int64, error) {
	var id int64
	err := db.QueryRow(
		"INSERT INTO users (email, name) VALUES ($1, $2) RETURNING id",
		email, name,
	).Scan(&id)
	if err != nil {
		return 0, err
	}
	return id, nil
}
