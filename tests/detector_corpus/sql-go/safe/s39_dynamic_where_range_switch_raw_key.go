package main

import (
	"database/sql"
	"strings"
)

type Customer struct {
	ID         int
	Name       string
	Status     string
	City       string
	SignupYear int
}

// FindCustomers ranges over the caller-supplied filter map and, for each
// entry, MEMBERSHIP-guards the key with a switch over a fixed literal case
// list before concatenating the key itself (not a distinct mapped value)
// into the WHERE clause. Any key outside {"status", "city",
// "signup_year"} simply falls through the switch untouched, so no
// unlisted column name can ever reach the query text.
func FindCustomers(db *sql.DB, filters map[string]string) ([]Customer, error) {
	query := "SELECT id, name, status, city, signup_year FROM customers"

	var args []interface{}
	var conditions []string

	for key, value := range filters {
		switch key {
		case "status", "city", "signup_year":
			conditions = append(conditions, key+" = ?")
			args = append(args, value)
		}
	}

	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}

	rows, err := db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var customers []Customer
	for rows.Next() {
		var c Customer
		if err := rows.Scan(&c.ID, &c.Name, &c.Status, &c.City, &c.SignupYear); err != nil {
			return nil, err
		}
		customers = append(customers, c)
	}

	if err = rows.Err(); err != nil {
		return nil, err
	}

	return customers, nil
}
