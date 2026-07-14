package db

import (
	"fmt"

	"gorm.io/gorm"
)

// findUsers filters with a GORM Where clause built by Sprintf.
func findUsers(db *gorm.DB, name string) ([]User, error) {
	var users []User
	err := db.Where(fmt.Sprintf("name = '%s'", name)).Find(&users).Error
	return users, err
}

type User struct {
	ID   int
	Name string
}
