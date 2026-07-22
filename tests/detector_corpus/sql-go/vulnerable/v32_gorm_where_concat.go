package db

import "gorm.io/gorm"

// FindByName concatenates the caller-supplied name directly into a GORM
// Where clause.
func FindByName(db *gorm.DB, name string) ([]User, error) {
	var users []User
	err := db.Where("name = '" + name + "'").Find(&users).Error
	return users, err
}

type User struct {
	ID   int
	Name string
}
