package db

import (
	"fmt"

	"gorm.io/gorm"
)

// CountByStatus builds a GORM Having clause with Sprintf, interpolating
// the caller-supplied status directly.
func CountByStatus(db *gorm.DB, status string) ([]int, error) {
	var out []int
	err := db.Having(fmt.Sprintf("status = '%s'", status)).Find(&out).Error
	return out, err
}
