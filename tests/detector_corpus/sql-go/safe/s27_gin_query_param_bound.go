package handlers

import (
	"database/sql"

	"github.com/gin-gonic/gin"
)

// ListByName reads the "name" query parameter with gin, but binds it as a
// query parameter rather than interpolating it into the SQL text.
func ListByName(db *sql.DB, c *gin.Context) (*sql.Rows, error) {
	name := c.Query("name")
	return db.Query("SELECT id, name FROM users WHERE name = ?", name)
}
