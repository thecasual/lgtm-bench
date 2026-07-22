package db

import (
	"fmt"

	"gorm.io/gorm"
)

// countByStatus runs a Sprintf-built raw query through GORM.
func countByStatus(db *gorm.DB, status string) (int64, error) {
	var n int64
	err := db.Raw(fmt.Sprintf("SELECT count(*) FROM orders WHERE status = '%s'", status)).Scan(&n).Error
	return n, err
}
