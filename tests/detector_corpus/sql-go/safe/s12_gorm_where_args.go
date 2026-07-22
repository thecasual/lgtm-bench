package db

import "gorm.io/gorm"

// findUsers filters with a GORM Where clause using a `?` placeholder.
func findUsers(db *gorm.DB, name string) ([]User, error) {
	var users []User
	err := db.Where("name = ?", name).Find(&users).Error
	return users, err
}

type User struct {
	ID   int
	Name string
}
