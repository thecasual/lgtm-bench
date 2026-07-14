package handlers

import (
	"database/sql"

	"github.com/gin-gonic/gin"
)

// GetByID reads the "id" path parameter with gin and concatenates it
// directly into the query text.
func GetByID(db *sql.DB, c *gin.Context) (*sql.Rows, error) {
	id := c.Param("id")
	return db.Query("SELECT id, name FROM users WHERE id = " + id)
}
