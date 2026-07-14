package handlers

import (
	"database/sql"

	"github.com/gin-gonic/gin"
)

// GetByID reads the "id" path parameter with gin, but binds it as a query
// parameter rather than interpolating it into the SQL text.
func GetByID(db *sql.DB, c *gin.Context) (*sql.Row, error) {
	id := c.Param("id")
	return db.QueryRow("SELECT id, name FROM users WHERE id = ?", id), nil
}
