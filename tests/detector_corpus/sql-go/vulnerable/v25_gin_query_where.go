package handlers

import (
	"database/sql"
	"fmt"

	"github.com/gin-gonic/gin"
)

// SearchByName reads the "name" query parameter with gin and interpolates
// it directly into the query text with Sprintf.
func SearchByName(db *sql.DB, c *gin.Context) (*sql.Rows, error) {
	name := c.Query("name")
	query := fmt.Sprintf("SELECT id, name FROM users WHERE name = '%s'", name)
	return db.Query(query)
}
